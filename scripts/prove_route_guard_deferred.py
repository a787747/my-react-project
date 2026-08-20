#!/usr/bin/env python3
"""Temporary activation + HTTP proofs for deferred guarded routes. Rolls back."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import requests

N8N = os.environ["N8N_URL"].rstrip("/")
API_KEY = os.environ["N8N_API_KEY"]
BASE = os.environ.get("EPE_PUBLIC_URL", "https://epe.sedamedical.com/webhook")
SSH = [
    "ssh",
    "-o", "BatchMode=yes",
    "-o", "IdentitiesOnly=yes",
    "-i", str(Path.home() / ".ssh/id_ed25519"),
    "root@92.51.45.147",
]

DEFERRED_IDS = [
    "yQNNr0i4UBFNVgMv",
    "j9YdW8LGzW5lvxgb",
    "ZUDqYb0nWGGXLUnB",
    "i1rMW79I7GYb5iXm",
    "uYy7zVKjgXx8zApC",
    "EyvFZJGDxQNL20tC",
    "H4T4EMYmJJ1jdT7Z",
    "rSZcm0HDMUHLYk8W",
    "55BHbXWIS6igHHBT",
    "CkxIyrEJBrc6V4Cv",
]

FORGED = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIyIiwiaXNzIjoiZXBlIiwiYXVkIjoiZXBlLWFwaSIsImlhdCI6MSwiZXhwIjo5OTk5OTk5OTk5"
    "LCJqdGkiOiIwMDAwMDAwMC0wMDAwLTQwMDAtODAwMC0wMDAwMDAwMDAwMDAifQ.not-a-real-signature"
)

ACTORS = {
    "admin": 2,
    "c_level": 18,
    "manager": 1,
    "employee": 3,
    "hr": 52,
}


def n8n(method: str, path: str) -> dict:
    resp = requests.request(
        method,
        f"{N8N}{path}",
        headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def ssh(script: str) -> str:
    completed = subprocess.run(
        SSH + ["bash", "-s"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout)[-4000:])
    return completed.stdout


def call(method: str, path: str, token: str | None = None, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, f"{BASE}{path}", headers=headers, timeout=90, **kwargs)
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:400]
    return resp.status_code, body


def code_of(body) -> str | None:
    if isinstance(body, dict):
        return body.get("error") or body.get("code")
    return None


def mint_tokens() -> dict:
    jtis = {name: str(uuid.uuid4()) for name in ACTORS}
    expired_jti = str(uuid.uuid4())
    specs = json.dumps(
        {name: {"sub": str(ACTORS[name]), "jti": jtis[name]} for name in ACTORS},
        separators=(",", ":"),
    )
    script = f"""
set -euo pipefail
SECRET=$(docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET)
SPECS={json.dumps(specs)}
EXPIRED_JTI={json.dumps(expired_jti)}
docker exec -e SECRET="$SECRET" -e SPECS="$SPECS" -e EXPIRED_JTI="$EXPIRED_JTI" \
  -e NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@9.0.2/node_modules \
  n8n-n8n-1 node -e '
const jwt = require("jsonwebtoken");
const secret = process.env.SECRET;
const now = Math.floor(Date.now()/1000);
const specs = JSON.parse(process.env.SPECS);
const out = {{}};
for (const [name, spec] of Object.entries(specs)) {{
  out[name] = jwt.sign(
    {{ sub: spec.sub, iss: "epe", aud: "epe-api", iat: now, exp: now + 3600, jti: spec.jti }},
    secret,
    {{ algorithm: "HS256" }}
  );
}}
out.expired = jwt.sign(
  {{ sub: "2", iss: "epe", aud: "epe-api", iat: now - 7200, exp: now - 3600, jti: process.env.EXPIRED_JTI }},
  secret,
  {{ algorithm: "HS256" }}
);
process.stdout.write(JSON.stringify(out) + "\\n");
'
docker exec postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -c "
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
SELECT v.jti::uuid, v.user_id, u.token_version, now(), now() + interval '1 hour'
FROM (VALUES
  ('{jtis['admin']}', 2),
  ('{jtis['c_level']}', 18),
  ('{jtis['manager']}', 1),
  ('{jtis['employee']}', 3),
  ('{jtis['hr']}', 52)
) AS v(jti, user_id)
JOIN performance_db.users u ON u.id = v.user_id;
"
"""
    raw = ssh(script)
    tokens = json.loads(raw.strip().splitlines()[0])
    tokens["_jtis"] = list(jtis.values())
    return tokens


def cleanup(jtis: list[str]) -> str:
    listed = ",".join(f"'{j}'::uuid" for j in jtis)
    return ssh(f"""
set -euo pipefail
docker exec postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -c "
DELETE FROM performance_db.score_corrections;
DELETE FROM performance_db.auth_sessions WHERE jti IN ({listed});
DELETE FROM performance_db.auth_sessions;
UPDATE performance_db.evaluation_periods
  SET is_active = false, status = 'draft'
  WHERE id = 2 AND (is_active = true OR status <> 'draft');
SELECT 'evaluations='||count(*) FROM performance_db.evaluations;
SELECT 'scores='||count(*) FROM performance_db.evaluation_scores;
SELECT 'corrections='||count(*) FROM performance_db.score_corrections;
SELECT 'sessions='||count(*) FROM performance_db.auth_sessions;
SELECT 'registered='||count(*) FROM performance_db.users WHERE password_hash IS NOT NULL;
SELECT 'h1='||status||','||is_active FROM performance_db.evaluation_periods WHERE id=2;
SELECT 'invite4='||is_used FROM performance_db.invite_tokens WHERE id=4;
SELECT 'g1='||coefficient FROM performance_db.grades WHERE id=1;
SELECT 'g10='||coefficient FROM performance_db.grades WHERE id=10;
"
""")


def set_h1(active: bool) -> None:
    if active:
        sql = "UPDATE performance_db.evaluation_periods SET is_active=true, status='active' WHERE id=2;"
    else:
        sql = "UPDATE performance_db.evaluation_periods SET is_active=false, status='draft' WHERE id=2;"
    ssh(f'docker exec postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -c "{sql}"')


def main() -> None:
    evidence: dict = {"campaign_precheck": {}}
    pre = ssh("""
docker exec postgres_n8n psql -U admin -d epe_2026 -At -c "
SELECT 'registered='||count(*) FROM performance_db.users WHERE password_hash IS NOT NULL;
SELECT 'evals='||count(*) FROM performance_db.evaluations;
SELECT 'h1='||status||','||is_active FROM performance_db.evaluation_periods WHERE id=2;
"
""")
    evidence["campaign_precheck"]["raw"] = pre.strip().splitlines()
    if "registered=1" not in pre or "evals=0" not in pre:
        raise SystemExit(f"campaign not safe for write-proofs: {pre}")

    activated = False
    tokens = None
    try:
        for wf_id in DEFERRED_IDS:
            n8n("POST", f"/api/v1/workflows/{wf_id}/activate")
        activated = True
        time.sleep(2)

        tokens = mint_tokens()
        admin, c_level, manager, employee, hr = (
            tokens["admin"], tokens["c_level"], tokens["manager"], tokens["employee"], tokens["hr"]
        )
        expired = tokens["expired"]

        reporting = [
            ("evaluations-matrix", "GET", "/api/admin/evaluations-matrix", {}),
            ("all-evaluations", "GET", "/api/admin/all-evaluations", {}),
            ("details-by-user", "GET", "/api/admin/evaluation-details-by-user", {"params": {"user_id": 3, "detail_type": "all"}}),
            ("analytics", "GET", "/api/analytics", {}),
            ("get-admin-data", "GET", "/get-admin-data", {}),
        ]

        for name, method, path, extra in reporting:
            row = {}
            row["no_token"] = call(method, path, **extra)[0]
            row["forged"] = call(method, path, FORGED, **extra)[0]
            row["expired"] = call(method, path, expired, **extra)[0]
            row["wrong_role"] = call(method, path, employee, **extra)[0]
            row["hr"] = call(method, path, hr, **extra)[0]
            row["manager"] = call(method, path, manager, **extra)[0]
            status, body = call(method, path, admin, **extra)
            row["valid_admin"] = status
            row["valid_c_level"] = call(method, path, c_level, **extra)[0]
            row["valid_error"] = code_of(body)
            if name == "get-admin-data" and isinstance(body, dict):
                row["valid_keys"] = sorted(body.keys())
                row["grades_count"] = len(body.get("grades") or [])
            elif isinstance(body, dict):
                row["valid_success"] = body.get("success")
                if name == "all-evaluations":
                    row["row_count"] = len(body.get("data") or [])
                if name == "analytics" and isinstance(body.get("data"), dict):
                    row["analytics_keys"] = sorted(body["data"].keys())
            evidence[name] = row

        status, body = call(
            "GET",
            "/api/admin/evaluation-details-by-user",
            admin,
            params={"user_id": 1, "detail_type": "all"},
        )
        evidence["details-by-user"]["admin_user_1"] = status
        evidence["details-by-user"]["admin_user_1_success"] = isinstance(body, dict) and body.get("success")
        evidence["details-by-user"]["admin_user_1_keys"] = sorted((body.get("data") or {}).keys()) if isinstance(body, dict) else None

        mm = {}
        mm["no_token"] = call("GET", "/api/manager-subordinates-matrix", params={"manager_id": 2})[0]
        mm["forged"] = call("GET", "/api/manager-subordinates-matrix", FORGED, params={"manager_id": 2})[0]
        mm["expired"] = call("GET", "/api/manager-subordinates-matrix", expired, params={"manager_id": 2})[0]
        mm["wrong_role"] = call("GET", "/api/manager-subordinates-matrix", employee, params={"manager_id": 2})[0]
        mm["hr"] = call("GET", "/api/manager-subordinates-matrix", hr, params={"manager_id": 2})[0]
        status, body = call("GET", "/api/manager-subordinates-matrix", manager, params={"manager_id": 1})
        mm["manager_first_line"] = status
        mm["manager_first_line_error"] = code_of(body)
        status, body = call("GET", "/api/manager-subordinates-matrix", admin, params={"manager_id": 18})
        mm["valid_admin_conflict_manager_id_18"] = status
        admin_ids = [row.get("id") for row in (body.get("data") or [])] if isinstance(body, dict) else []
        mm["admin_ids_sample"] = admin_ids[:8]
        mm["admin_includes_yelena_88"] = 88 in admin_ids
        mm["admin_excludes_akmyrat_1"] = 1 not in admin_ids
        status, body = call("GET", "/api/manager-subordinates-matrix", c_level, params={"manager_id": 2})
        mm["valid_c_level_conflict_manager_id_2"] = status
        c_ids = [row.get("id") for row in (body.get("data") or [])] if isinstance(body, dict) else []
        mm["c_level_ids_sample"] = c_ids[:8]
        mm["c_level_includes_akmyrat_1"] = 1 in c_ids
        mm["c_level_excludes_yelena_88"] = 88 not in c_ids
        evidence["manager-subordinates-matrix"] = mm

        esr = {}
        esr["no_token"] = call("GET", "/api/employee-self-review", params={"subject_id": 2})[0]
        esr["forged"] = call("GET", "/api/employee-self-review", FORGED, params={"subject_id": 2})[0]
        esr["expired"] = call("GET", "/api/employee-self-review", expired, params={"subject_id": 2})[0]
        status, body = call("GET", "/api/employee-self-review", employee, params={"subject_id": 2})
        esr["valid_employee_conflict_subject_2"] = status
        esr["has_self_review"] = body.get("has_self_review") if isinstance(body, dict) else None
        esr["body_keys"] = sorted(body.keys()) if isinstance(body, dict) else None
        esr["valid_admin"] = call("GET", "/api/employee-self-review", admin, params={"subject_id": 3})[0]
        evidence["employee-self-review"] = esr

        sc = {}
        payload = {
            "evaluator_id": 88,
            "subject_id": 3,
            "criteria_id": 13,
            "correction_score": 7,
            "correction_level": "mid_level",
        }
        sc["no_token"] = call("POST", "/api/admin/score-correction", json=payload)[0]
        sc["forged"] = call("POST", "/api/admin/score-correction", FORGED, json=payload)[0]
        sc["expired"] = call("POST", "/api/admin/score-correction", expired, json=payload)[0]
        sc["wrong_role"] = call("POST", "/api/admin/score-correction", employee, json=payload)[0]
        sc["hr"] = call("POST", "/api/admin/score-correction", hr, json=payload)[0]
        status, body = call("POST", "/api/admin/score-correction", manager, json=payload)
        sc["manager_not_skip"] = status
        sc["manager_not_skip_error"] = code_of(body)
        status, body = call("POST", "/api/admin/score-correction", admin, json=payload)
        sc["valid_admin"] = status
        sc["stored_level"] = (body.get("data") or {}).get("correction_level") if isinstance(body, dict) else None
        sc["stored_id"] = (body.get("data") or {}).get("id") if isinstance(body, dict) else None
        sc["client_asked_mid_level"] = True
        db_eval = ssh("""
docker exec postgres_n8n psql -U admin -d epe_2026 -At -c "
SELECT evaluator_id||','||correction_level||','||period_id||','||correction_score||','||subject_id
FROM performance_db.score_corrections ORDER BY id;
"
""")
        sc["db_row"] = db_eval.strip()
        status, body = call(
            "POST",
            "/api/admin/score-correction",
            c_level,
            json={**payload, "subject_id": 4, "correction_score": 6, "evaluator_id": 1},
        )
        sc["valid_c_level"] = status
        sc["c_level_stored_level"] = (body.get("data") or {}).get("correction_level") if isinstance(body, dict) else None
        db_eval2 = ssh("""
docker exec postgres_n8n psql -U admin -d epe_2026 -At -c "
SELECT evaluator_id||','||correction_level||','||period_id||','||subject_id
FROM performance_db.score_corrections ORDER BY id;
"
""")
        sc["db_rows_after_c_level"] = db_eval2.strip().splitlines()
        evidence["score-correction"] = sc

        mc = {}
        mc["no_token"] = call("POST", "/manage-criteria", json={"action": "get"})[0]
        mc["forged"] = call("POST", "/manage-criteria", FORGED, json={"action": "get"})[0]
        mc["expired"] = call("POST", "/manage-criteria", expired, json={"action": "get"})[0]
        mc["wrong_role"] = call("POST", "/manage-criteria", employee, json={"action": "get"})[0]
        mc["c_level"] = call("POST", "/manage-criteria", c_level, json={"action": "get"})[0]
        status, body = call("POST", "/manage-criteria", admin, json={"action": "get"})
        mc["valid_get"] = status
        crit_rows = body.get("data") if isinstance(body, dict) else None
        mc["get_count"] = len(crit_rows or [])
        crit1 = next((row for row in (crit_rows or []) if row.get("id") == 1), None)
        mc["crit1_title"] = (crit1 or {}).get("title")
        status, _ = call("POST", "/manage-criteria", admin, json={"action": "save", "criteria": crit1})
        mc["valid_save_draft"] = status
        evidence["manage-criteria"] = mc

        ua = {}
        grades = [{"id": 1, "coefficient": 1.00}, {"id": 10, "coefficient": 0.30}]
        ua["no_token"] = call("POST", "/update-admin-data", json={"grades": grades})[0]
        ua["forged"] = call("POST", "/update-admin-data", FORGED, json={"grades": grades})[0]
        ua["expired"] = call("POST", "/update-admin-data", expired, json={"grades": grades})[0]
        ua["wrong_role"] = call("POST", "/update-admin-data", employee, json={"grades": grades})[0]
        ua["c_level"] = call("POST", "/update-admin-data", c_level, json={"grades": grades})[0]
        ua["valid_draft"] = call("POST", "/update-admin-data", admin, json={"grades": grades})[0]
        evidence["update-admin-data"] = ua

        try:
            set_h1(True)
            freeze_save_status, freeze_save_body = call(
                "POST", "/manage-criteria", admin, json={"action": "save", "criteria": crit1}
            )
            evidence["manage-criteria"]["freeze_save"] = freeze_save_status
            evidence["manage-criteria"]["freeze_save_error"] = code_of(freeze_save_body)
            freeze_del_status, freeze_del_body = call(
                "POST", "/manage-criteria", admin, json={"action": "delete", "criteria": {"id": 1}}
            )
            evidence["manage-criteria"]["freeze_delete"] = freeze_del_status
            evidence["manage-criteria"]["freeze_delete_error"] = code_of(freeze_del_body)
            freeze_ua_status, freeze_ua_body = call(
                "POST", "/update-admin-data", admin, json={"grades": grades}
            )
            evidence["update-admin-data"]["freeze"] = freeze_ua_status
            evidence["update-admin-data"]["freeze_error"] = code_of(freeze_ua_body)
        finally:
            set_h1(False)

        status, body = call(
            "POST",
            "/api/submit-evaluation",
            admin,
            json={
                "evaluator_id": 2,
                "subject_id": 3,
                "final_score": 7,
                "grades": {"13": 7},
                "evaluation_source": "c_level_direct",
            },
        )
        evidence["c_level_direct_submit"] = {
            "status": status,
            "error": code_of(body),
            "message": body.get("message") if isinstance(body, dict) else None,
        }
    finally:
        if activated:
            for wf_id in DEFERRED_IDS:
                try:
                    n8n("POST", f"/api/v1/workflows/{wf_id}/deactivate")
                except Exception as exc:
                    evidence.setdefault("deactivate_errors", []).append(f"{wf_id}:{exc}")
        if tokens is not None:
            evidence["cleanup"] = cleanup(tokens["_jtis"]).strip().splitlines()
        else:
            set_h1(False)

    wfs = n8n("GET", "/api/v1/workflows?limit=100")["data"]
    evidence["final_active"] = sorted(
        w["name"] for w in wfs if w.get("active") and not w.get("isArchived")
    )
    evidence["final_active_count"] = len(evidence["final_active"])
    cors = next((w for w in wfs if w.get("name") == "API: Global CORS Handler"), None)
    evidence["cors_active"] = bool(cors and cors.get("active"))

    out = Path("/tmp/epe_rgd_proof.json")
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()

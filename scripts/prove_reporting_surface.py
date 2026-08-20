#!/usr/bin/env python3
"""API proofs for the reporting-surface period bind and closed defects."""

from __future__ import annotations

import json
import os
import subprocess
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

OLD_ALL_EVAL_SQL = r"""
WITH latest_evaluations AS (
  SELECT DISTINCT ON (e.subject_id, e.is_self_evaluation, e.evaluation_source)
    e.id as evaluation_id, e.subject_id, e.evaluator_id, e.calculated_score,
    e.updated_at, e.is_self_evaluation, e.evaluation_source
  FROM performance_db.evaluations e
  ORDER BY e.subject_id, e.is_self_evaluation, e.evaluation_source, e.updated_at DESC
),
manager_evaluations_given AS (
  SELECT e.evaluator_id, e.subject_id as manager_id, mgr.full_name as manager_name,
         e.calculated_score, e.updated_at, e.id as evaluation_id
  FROM performance_db.evaluations e
  JOIN performance_db.users mgr ON e.subject_id = mgr.id
  WHERE e.evaluation_source = 'subordinate'
)
SELECT u.id
FROM performance_db.users u
LEFT JOIN manager_evaluations_given meg ON u.id = meg.evaluator_id
WHERE u.role NOT IN ('c_level', 'admin')
ORDER BY u.full_name
"""

UNBOUND_ANALYTICS_SQL = """
SELECT COALESCE(ROUND(AVG(e.calculated_score)::numeric, 2), 0)
FROM performance_db.evaluations e
WHERE e.calculated_score IS NOT NULL
"""


def n8n(method: str, path: str, payload: dict | None = None) -> dict:
    resp = requests.request(
        method,
        f"{N8N}{path}",
        headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"},
        json=payload,
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


def psql(query: str) -> str:
    completed = subprocess.run(
        SSH + [
            "docker", "exec", "-i", "postgres_n8n", "psql", "-U", "admin", "-d", "epe_2026",
            "-v", "ON_ERROR_STOP=1", "-At",
        ],
        input=query,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout)[-4000:])
    return completed.stdout.strip()


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
docker exec -e SECRET="$SECRET" -e SPECS="$SPECS" -e EXPIRED_JTI="$EXPIRED_JTI" \\
  -e NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@9.0.2/node_modules \\
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


def set_h1(active: bool) -> None:
    if active:
        psql(
            "UPDATE performance_db.evaluation_periods SET is_active=false WHERE id<>2;"
            "UPDATE performance_db.evaluation_periods SET is_active=true, status='active' WHERE id=2;"
        )
    else:
        psql(
            "UPDATE performance_db.evaluation_periods SET is_active=false, status='draft' WHERE id=2;"
        )


def insert_proof_rows() -> None:
    psql(
        """
INSERT INTO performance_db.evaluations
  (subject_id, evaluator_id, evaluation_source, is_self_evaluation, evaluation_type,
   period_id, calculated_score, status, updated_at)
VALUES
  (3, 3, 'manager', true, 'self', 1, 8.00, 'completed', now()),
  (3, 1, 'manager', false, 'manager', 1, 10.00, 'completed', now()),
  (1, 3, 'subordinate', false, 'manager', 1, 9.00, 'completed', now()),
  (3, 3, 'manager', true, 'self', 2, 6.00, 'completed', now()),
  (3, 1, 'manager', false, 'manager', 2, 4.00, 'completed', now()),
  (1, 3, 'subordinate', false, 'manager', 2, 5.00, 'completed', now());
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value)
SELECT e.id, 13, e.calculated_score::int
FROM performance_db.evaluations e
WHERE e.period_id IN (1, 2) AND e.calculated_score IS NOT NULL;
"""
    )


def cleanup_proof_rows() -> dict[str, str]:
    counts = {
        "scores": psql("DELETE FROM performance_db.evaluation_scores; SELECT count(*) FROM performance_db.evaluation_scores;"),
        "evaluations": psql("DELETE FROM performance_db.evaluations; SELECT count(*) FROM performance_db.evaluations;"),
        "corrections": psql("DELETE FROM performance_db.score_corrections; SELECT count(*) FROM performance_db.score_corrections;"),
    }
    set_h1(False)
    return counts


def auth_block(path: str, method: str, admin, c_level, hr, employee, expired, **kwargs):
    return {
        "no_token": call(method, path, **kwargs)[0],
        "forged": call(method, path, FORGED, **kwargs)[0],
        "expired": call(method, path, expired, **kwargs)[0],
        "employee": call(method, path, employee, **kwargs)[0],
        "hr": call(method, path, hr, **kwargs)[0],
        "admin": call(method, path, admin, **kwargs)[0],
        "c_level": call(method, path, c_level, **kwargs)[0],
    }


def main() -> None:
    evidence: dict = {}
    tokens = mint_tokens()
    admin, c_level, manager, employee, hr, expired = (
        tokens["admin"], tokens["c_level"], tokens["manager"],
        tokens["employee"], tokens["hr"], tokens["expired"],
    )

    evidence["draft"] = {
        "all-evaluations": call("GET", "/api/admin/all-evaluations", admin)[1],
        "analytics": call("GET", "/api/analytics", admin)[1],
        "details": call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3})[1],
        "manager-matrix": call("GET", "/api/manager-subordinates-matrix", admin)[1],
        "criteria": call("POST", "/manage-criteria", admin, json={"action": "get"})[1],
        "update-admin-data": call("POST", "/update-admin-data", admin, json={"grades": []})[0],
    }

    evidence["auth"] = {
        "all-evaluations": auth_block("/api/admin/all-evaluations", "GET", admin, c_level, hr, employee, expired),
        "analytics": auth_block("/api/analytics", "GET", admin, c_level, hr, employee, expired),
        "details": auth_block(
            "/api/admin/evaluation-details-by-user", "GET",
            admin, c_level, hr, employee, expired, params={"user_id": 3, "detail_type": "all"},
        ),
        "manager-matrix": auth_block(
            "/api/manager-subordinates-matrix", "GET",
            admin, c_level, hr, employee, expired, params={"manager_id": 18},
        ),
        "manage-criteria": auth_block("/manage-criteria", "POST", admin, c_level, hr, employee, expired, json={"action": "get"}),
        "update-admin-data": {
            "no_token": call("POST", "/update-admin-data", json={"grades": []})[0],
            "hr": call("POST", "/update-admin-data", hr, json={"grades": []})[0],
            "c_level": call("POST", "/update-admin-data", c_level, json={"grades": []})[0],
            "admin": call("POST", "/update-admin-data", admin, json={"grades": []})[0],
        },
    }
    evidence["manager_first_line"] = call("GET", "/api/manager-subordinates-matrix", manager)[0]

    set_h1(True)
    evidence["h1"] = psql("SELECT status||','||is_active::text FROM performance_db.evaluation_periods WHERE id=2;")
    insert_proof_rows()
    evidence["inserted"] = psql("SELECT count(*)||','||count(*) FILTER (WHERE period_id=1)||','||count(*) FILTER (WHERE period_id=2) FROM performance_db.evaluations;")

    old_count = psql(f"SELECT count(*) FROM ({OLD_ALL_EVAL_SQL}) q;")
    old_alina = psql(f"SELECT count(*) FROM ({OLD_ALL_EVAL_SQL}) q WHERE id=3;")
    ae_status, ae = call("GET", "/api/admin/all-evaluations", admin)
    rows = (ae or {}).get("data") or []
    evidence["row_multiplication"] = {
        "old_sql_rows": int(old_count),
        "old_sql_alina_rows": int(old_alina),
        "new_api_http": ae_status,
        "new_api_rows": len(rows),
        "new_api_alina_rows": sum(1 for r in rows if r.get("id") == 3),
        "period": (ae or {}).get("period"),
        "alina": next((r for r in rows if r.get("id") == 3), None),
    }

    an_status, an = call("GET", "/api/analytics", admin)
    unbound = psql(UNBOUND_ANALYTICS_SQL)
    p1 = psql("SELECT COALESCE(ROUND(AVG(calculated_score)::numeric,2),0) FROM performance_db.evaluations WHERE period_id=1;")
    p2 = psql("SELECT COALESCE(ROUND(AVG(calculated_score)::numeric,2),0) FROM performance_db.evaluations WHERE period_id=2;")
    evidence["analytics"] = {
        "http": an_status,
        "period": (an or {}).get("period"),
        "overall": ((an or {}).get("data") or {}).get("overall"),
        "trends": ((an or {}).get("data") or {}).get("period_trends"),
        "unbound_avg": unbound,
        "period1_avg": p1,
        "period2_avg": p2,
    }
    inspect = call("GET", "/api/analytics?period_id=1", admin)
    evidence["analytics_period1"] = {
        "http": inspect[0],
        "period": (inspect[1] or {}).get("period"),
        "overall": ((inspect[1] or {}).get("data") or {}).get("overall"),
    }

    details_all = call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3, "detail_type": "all"})
    details_self = call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3, "detail_type": "self"})
    details_mgr = call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3, "detail_type": "received_from_manager"})
    details_up = call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3, "detail_type": "gave_to_manager"})
    details_bad = call("GET", "/api/admin/evaluation-details-by-user", admin, params={"user_id": 3, "detail_type": "nope"})
    evidence["detail_type"] = {
        "all": {
            "http": details_all[0],
            "has_self": bool(((details_all[1] or {}).get("data") or {}).get("self_evaluation")),
            "manager_n": len(((details_all[1] or {}).get("data") or {}).get("manager_evaluations") or []),
            "to_manager": bool(((details_all[1] or {}).get("data") or {}).get("evaluation_to_manager")),
            "period": (details_all[1] or {}).get("period"),
            "detail_type": (details_all[1] or {}).get("detail_type"),
        },
        "self": {
            "http": details_self[0],
            "has_self": bool(((details_self[1] or {}).get("data") or {}).get("self_evaluation")),
            "manager_n": len(((details_self[1] or {}).get("data") or {}).get("manager_evaluations") or []),
            "to_manager": bool(((details_self[1] or {}).get("data") or {}).get("evaluation_to_manager")),
        },
        "received_from_manager": {
            "http": details_mgr[0],
            "has_self": bool(((details_mgr[1] or {}).get("data") or {}).get("self_evaluation")),
            "manager_n": len(((details_mgr[1] or {}).get("data") or {}).get("manager_evaluations") or []),
        },
        "gave_to_manager": {
            "http": details_up[0],
            "to_manager": bool(((details_up[1] or {}).get("data") or {}).get("evaluation_to_manager")),
            "has_self": bool(((details_up[1] or {}).get("data") or {}).get("self_evaluation")),
        },
        "invalid": {"http": details_bad[0], "error": (details_bad[1] or {}).get("error")},
    }

    mm = call("GET", "/api/manager-subordinates-matrix", admin, params={"manager_id": 18})
    evidence["manager_matrix"] = {
        "http": mm[0],
        "period": (mm[1] or {}).get("period"),
        "rows": len((mm[1] or {}).get("data") or []),
        "sample_ids": [r.get("id") for r in ((mm[1] or {}).get("data") or [])[:8]],
        "first_line": evidence["manager_first_line"],
    }
    clev_mm = call("GET", "/api/manager-subordinates-matrix", c_level, params={"manager_id": 2})
    evidence["manager_matrix_clevel"] = {
        "http": clev_mm[0],
        "sample_ids": [r.get("id") for r in ((clev_mm[1] or {}).get("data") or [])[:8]],
    }

    crit = call("POST", "/manage-criteria", admin, json={"action": "get"})
    crit1 = ((crit[1] or {}).get("data") or [{}])[0]
    freeze_save = call("POST", "/manage-criteria", admin, json={"action": "save", "criteria": crit1})
    freeze_ua = call("POST", "/update-admin-data", admin, json={"grades": [{"id": 1, "coefficient": 1}]})
    evidence["freeze"] = {
        "criteria_get_http": crit[0],
        "criteria_count": len((crit[1] or {}).get("data") or []),
        "criteria_period": (crit[1] or {}).get("period"),
        "save": freeze_save[0],
        "save_error": (freeze_save[1] or {}).get("error"),
        "update_admin": freeze_ua[0],
        "update_admin_error": (freeze_ua[1] or {}).get("error"),
    }

    ae1 = call("GET", "/api/admin/all-evaluations?period_id=1", admin)
    evidence["all_eval_period1"] = {
        "http": ae1[0],
        "period": (ae1[1] or {}).get("period"),
        "alina": next((r for r in ((ae1[1] or {}).get("data") or []) if r.get("id") == 3), None),
    }

    print(json.dumps(evidence, indent=2, default=str))
    out = Path("backups/2026-08-20-reporting-surface")
    out.mkdir(parents=True, exist_ok=True)
    (out / "api_proofs.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    (out / "proof_jtis.json").write_text(json.dumps(tokens["_jtis"]) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Runtime proofs for submit-evaluation sources + activated evaluations-matrix."""

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


def sql(query: str) -> str:
    return ssh(
        f"docker exec postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -Atc {json.dumps(query)}"
    ).strip()


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


def eval_row(subject_id: int, source: str) -> str:
    return sql(
        "SELECT evaluator_id||','||subject_id||','||evaluation_source||','||period_id||','||"
        "calculated_score||','||is_self_evaluation "
        "FROM performance_db.evaluations "
        f"WHERE subject_id={subject_id} AND evaluation_source='{source}' "
        "ORDER BY id DESC LIMIT 1"
    )


def main() -> None:
    evidence: dict = {}
    tokens = mint_tokens()
    admin, c_level, manager, employee, hr, expired = (
        tokens["admin"],
        tokens["c_level"],
        tokens["manager"],
        tokens["employee"],
        tokens["hr"],
        tokens["expired"],
    )

    sql("UPDATE performance_db.evaluation_periods SET is_active=true, status='active' WHERE id=2")
    evidence["h1_after_activate"] = sql(
        "SELECT id||','||status||','||is_active FROM performance_db.evaluation_periods WHERE id=2"
    )

    path = "/api/submit-evaluation"
    auth = {}
    auth["no_token"] = call("POST", path, json={"subject_id": 3, "evaluation_source": "manager", "grades": {"3": 7}})[0]
    auth["forged"] = call("POST", path, FORGED, json={"subject_id": 3, "evaluation_source": "manager", "grades": {"3": 7}})[0]
    auth["expired"] = call("POST", path, expired, json={"subject_id": 3, "evaluation_source": "manager", "grades": {"3": 7}})[0]
    cld = {"subject_id": 3, "evaluation_source": "c_level_direct", "evaluator_id": 88, "grades": {"1": 6, "10": 8}, "final_score": 1}
    auth["c_level_direct_no_token"] = call("POST", path, json=cld)[0]
    auth["c_level_direct_forged"] = call("POST", path, FORGED, json=cld)[0]
    auth["c_level_direct_expired"] = call("POST", path, expired, json=cld)[0]
    auth["c_level_direct_employee"] = call("POST", path, employee, json=cld)
    auth["c_level_direct_manager"] = call("POST", path, manager, json=cld)
    auth["c_level_direct_hr"] = call("POST", path, hr, json=cld)
    evidence["auth"] = {
        k: (v if isinstance(v, int) else {"status": v[0], "error": (v[1] or {}).get("error") if isinstance(v[1], dict) else v[1]})
        for k, v in auth.items()
    }

    before = int(sql("SELECT count(*) FROM performance_db.evaluations"))

    out_of_scope = call(
        "POST",
        path,
        admin,
        json={"subject_id": 31, "evaluation_source": "c_level_direct", "evaluator_id": 88, "grades": {"1": 6, "10": 8}},
    )
    read_only = call(
        "POST",
        path,
        admin,
        json={"subject_id": 21, "evaluation_source": "c_level_direct", "evaluator_id": 88, "grades": {"1": 6, "10": 8}},
    )
    outside_graph = call(
        "POST",
        path,
        manager,
        json={"subject_id": 22, "evaluation_source": "manager", "evaluator_id": 88, "grades": {"3": 6, "4": 8, "12": 7}},
    )
    manager_esenova = call(
        "POST",
        path,
        manager,
        json={"subject_id": 31, "evaluation_source": "manager", "evaluator_id": 88, "grades": {"3": 6, "4": 8, "12": 7}},
    )
    upward_c_level = call(
        "POST",
        path,
        manager,
        json={"subject_id": 18, "evaluation_source": "subordinate", "evaluator_id": 88, "grades": {"2": 8}},
    )
    after_rejects = int(sql("SELECT count(*) FROM performance_db.evaluations"))
    evidence["rejects"] = {
        "c_level_direct_out_of_scope": {"status": out_of_scope[0], "error": (out_of_scope[1] or {}).get("error")},
        "c_level_direct_readonly": {"status": read_only[0], "error": (read_only[1] or {}).get("error")},
        "manager_outside_graph": {"status": outside_graph[0], "error": (outside_graph[1] or {}).get("error")},
        "manager_esenova": {"status": manager_esenova[0], "error": (manager_esenova[1] or {}).get("error")},
        "upward_to_c_level": {"status": upward_c_level[0], "error": (upward_c_level[1] or {}).get("error")},
        "evaluations_before": before,
        "evaluations_after": after_rejects,
    }

    manager_ok = call(
        "POST",
        path,
        manager,
        json={
            "subject_id": 3,
            "evaluator_id": 88,
            "evaluation_source": "manager",
            "final_score": 1.0,
            "grades": {"3": 6, "4": 8, "12": 7},
        },
    )
    upward_ok = call(
        "POST",
        path,
        employee,
        json={
            "subject_id": 1,
            "evaluator_id": 88,
            "evaluation_source": "subordinate",
            "final_score": 1.0,
            "grades": {"2": 8},
        },
    )
    cld_ok = call(
        "POST",
        path,
        admin,
        json={
            "subject_id": 10,
            "evaluator_id": 18,
            "evaluation_source": "c_level_direct",
            "final_score": 1.0,
            "grades": {"1": 6, "10": 8},
        },
    )
    cld_clevel_ok = call(
        "POST",
        path,
        c_level,
        json={
            "subject_id": 39,
            "evaluator_id": 2,
            "evaluation_source": "c_level_direct",
            "final_score": 1.0,
            "grades": {"1": 5, "10": 7},
        },
    )
    dup = call(
        "POST",
        path,
        manager,
        json={"subject_id": 3, "evaluation_source": "manager", "grades": {"3": 6, "4": 8, "12": 7}},
    )
    evidence["writes"] = {
        "manager": {"status": manager_ok[0], "body": manager_ok[1], "row": eval_row(3, "manager")},
        "upward": {"status": upward_ok[0], "body": upward_ok[1], "row": eval_row(1, "subordinate")},
        "c_level_direct_admin": {"status": cld_ok[0], "body": cld_ok[1], "row": eval_row(10, "c_level_direct")},
        "c_level_direct_c_level": {"status": cld_clevel_ok[0], "body": cld_clevel_ok[1], "row": eval_row(39, "c_level_direct")},
        "duplicate_manager": {"status": dup[0], "error": (dup[1] or {}).get("error")},
    }

    matrix_admin = call("GET", "/api/admin/evaluations-matrix", admin)
    matrix_clevel = call("GET", "/api/admin/evaluations-matrix", c_level)
    matrix_employee = call("GET", "/api/admin/evaluations-matrix", employee)
    corr = call(
        "POST",
        "/api/admin/score-correction",
        admin,
        json={"subject_id": 3, "criteria_id": 13, "correction_score": 7, "evaluator_id": 2},
    )
    evidence["matrix"] = {
        "admin": {"status": matrix_admin[0], "keys": list((matrix_admin[1] or {}).keys()) if isinstance(matrix_admin[1], dict) else type(matrix_admin[1]).__name__, "rows": len((matrix_admin[1] or {}).get("data") or []) if isinstance(matrix_admin[1], dict) else None},
        "c_level": matrix_clevel[0],
        "employee": matrix_employee[0],
        "score_correction_inactive": {"status": corr[0], "body": corr[1] if not isinstance(corr[1], dict) else {k: corr[1].get(k) for k in ("message", "error", "code")}},
    }

    print(json.dumps(evidence, indent=2, default=str))
    out = Path("backups/2026-08-20-clevel-direct/submit_proofs.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()

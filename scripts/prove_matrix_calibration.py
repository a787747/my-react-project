#!/usr/bin/env python3
"""Runtime proofs for matrix period bind, update path, and active-only corrections."""

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


def sql(query: str) -> str:
    return ssh(
        "docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -At",
        # reused below
    )  # pragma: no cover


def psql(query: str) -> str:
    completed = subprocess.run(
        SSH + ["docker", "exec", "-i", "postgres_n8n", "psql", "-U", "admin", "-d", "epe_2026",
               "-v", "ON_ERROR_STOP=1", "-At"],
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
            "UPDATE performance_db.evaluation_periods SET is_active=false, status='draft' WHERE id=2;"
            "UPDATE performance_db.evaluation_periods SET is_active=true, status='active' WHERE id=2;"
        )
    else:
        psql(
            "UPDATE performance_db.evaluation_periods SET is_active=false, status='draft' WHERE id=2;"
        )


def clevel_grades(score_a: int, score_b: int) -> dict:
    return {"1": score_a, "10": score_b}


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

    evidence["draft_matrix"] = call("GET", "/api/admin/evaluations-matrix", admin)
    evidence["draft_correction"] = call(
        "POST",
        "/api/admin/score-correction",
        admin,
        json={"subject_id": 3, "criteria_id": 13, "correction_score": 7},
    )
    evidence["draft_correction_count"] = psql("SELECT count(*) FROM performance_db.score_corrections;")

    evidence["auth"] = {
        "matrix_no_token": call("GET", "/api/admin/evaluations-matrix")[0],
        "matrix_forged": call("GET", "/api/admin/evaluations-matrix", FORGED)[0],
        "matrix_expired": call("GET", "/api/admin/evaluations-matrix", expired)[0],
        "matrix_employee": call("GET", "/api/admin/evaluations-matrix", employee)[0],
        "corr_no_token": call("POST", "/api/admin/score-correction", json={"subject_id": 3, "criteria_id": 13, "correction_score": 7})[0],
        "corr_employee": call("POST", "/api/admin/score-correction", employee, json={"subject_id": 3, "criteria_id": 13, "correction_score": 7})[0],
    }

    set_h1(True)
    evidence["h1_after_activate"] = psql(
        "SELECT status||','||is_active::text FROM performance_db.evaluation_periods WHERE id=2;"
    )

    status, matrix = call("GET", "/api/admin/evaluations-matrix", admin)
    evidence["active_matrix_status"] = status
    evidence["active_matrix_period"] = {
        "period": (matrix or {}).get("period"),
        "campaign_active": (matrix or {}).get("campaign_active"),
        "rows": len((matrix or {}).get("data") or []),
    }

    rows = (matrix or {}).get("data") or []
    by_id = {row["id"]: row for row in rows}

    def star_ok(row):
        return (
            bool(row.get("is_in_scope"))
            and bool(row.get("can_be_evaluated"))
            and row.get("role") not in ("admin", "c_level")
        )

    evidence["stars"] = {
        "writable": sum(1 for row in rows if star_ok(row)),
        "blocked": sum(1 for row in rows if not star_ok(row)),
        "jemal_47": {
            "role": (by_id.get(47) or {}).get("role"),
            "can_be_evaluated": (by_id.get(47) or {}).get("can_be_evaluated"),
            "is_in_scope": (by_id.get(47) or {}).get("is_in_scope"),
            "star": star_ok(by_id.get(47) or {}),
        },
        "cem_21": {"star": star_ok(by_id.get(21) or {}), "can_be_evaluated": (by_id.get(21) or {}).get("can_be_evaluated")},
        "esenova_31": {"star": star_ok(by_id.get(31) or {}), "is_in_scope": (by_id.get(31) or {}).get("is_in_scope")},
        "alina_3": {"star": star_ok(by_id.get(3) or {})},
    }

    mgr_status, _ = call(
        "POST",
        "/api/submit-evaluation",
        manager,
        json={"subject_id": 3, "grades": {"13": 6, "2": 8, "5": 7}, "evaluation_source": "manager", "final_score": 1},
    )
    up_status, _ = call(
        "POST",
        "/api/submit-evaluation",
        employee,
        json={"subject_id": 1, "grades": {"13": 9}, "evaluation_source": "subordinate", "final_score": 9},
    )
    evidence["manager_and_upward"] = {"manager_http": mgr_status, "upward_http": up_status}

    _, matrix2 = call("GET", "/api/admin/evaluations-matrix", admin)
    alina = next((row for row in (matrix2.get("data") or []) if row["id"] == 3), {})
    akmyrat = next((row for row in (matrix2.get("data") or []) if row["id"] == 1), {})
    alina_c13 = next((c for c in alina.get("criteria") or [] if c["criteria_id"] == 13), {})
    akm_c13 = next((c for c in akmyrat.get("criteria") or [] if c["criteria_id"] == 13), {})
    evidence["manager_score_source"] = {
        "alina_13_manager_score": alina_c13.get("manager_score"),
        "akmyrat_13_manager_score": akm_c13.get("manager_score"),
        "akmyrat_13_subordinate_avg": akm_c13.get("subordinate_avg_score"),
    }

    first = call(
        "POST",
        "/api/submit-evaluation",
        admin,
        json={
            "subject_id": 10,
            "grades": clevel_grades(6, 8),
            "evaluation_source": "c_level_direct",
            "final_score": 1,
        },
    )
    evidence["clevel_submit"] = {"http": first[0], "body": first[1]}
    eval_row = psql(
        "SELECT id||','||evaluator_id||','||subject_id||','||evaluation_source||','||period_id||','||calculated_score "
        "FROM performance_db.evaluations WHERE subject_id=10 AND evaluation_source='c_level_direct' ORDER BY id DESC LIMIT 1;"
    )
    evidence["clevel_row"] = eval_row
    eval_id = int(eval_row.split(",")[0]) if eval_row else None
    dup = call(
        "POST",
        "/api/submit-evaluation",
        admin,
        json={
            "subject_id": 10,
            "grades": clevel_grades(4, 4),
            "evaluation_source": "c_level_direct",
            "final_score": 1,
        },
    )
    evidence["clevel_duplicate"] = {"http": dup[0], "error": (dup[1] or {}).get("error")}
    update = call(
        "POST",
        "/api/update-evaluation",
        admin,
        json={"evaluation_id": eval_id, "grades": clevel_grades(5, 7), "final_score": 1},
    )
    evidence["clevel_update"] = {"http": update[0], "body": update[1]}
    evidence["clevel_after_update"] = psql(
        "SELECT calculated_score FROM performance_db.evaluations WHERE id=" + str(eval_id) + ";"
    )
    _, matrix3 = call("GET", "/api/admin/evaluations-matrix", admin)
    asadbek = next((row for row in (matrix3.get("data") or []) if row["id"] == 10), {})
    evidence["clevel_reopen"] = {
        "actor_eval_id": asadbek.get("actor_c_level_evaluation_id"),
        "matches": asadbek.get("actor_c_level_evaluation_id") == eval_id,
    }

    corr = call(
        "POST",
        "/api/admin/score-correction",
        admin,
        json={"subject_id": 3, "criteria_id": 13, "correction_score": 10, "correction_level": "mid_level"},
    )
    evidence["correction_admin"] = {"http": corr[0], "body": corr[1]}
    evidence["correction_stored"] = psql(
        "SELECT evaluator_id||','||correction_level||','||period_id||','||correction_score "
        "FROM performance_db.score_corrections WHERE subject_id=3 AND criteria_id=13;"
    )
    first_line = call(
        "POST",
        "/api/admin/score-correction",
        manager,
        json={"subject_id": 3, "criteria_id": 13, "correction_score": 4},
    )
    evidence["correction_first_line"] = {"http": first_line[0], "error": (first_line[1] or {}).get("error")}

    psql(
        "INSERT INTO performance_db.score_corrections "
        "(subject_id, evaluator_id, criteria_id, correction_score, correction_level, period_id, updated_at) "
        "VALUES (3, 1, 13, 8, 'mid_level', 2, now());"
    )
    _, matrix4 = call("GET", "/api/admin/evaluations-matrix", admin)
    alina4 = next((row for row in (matrix4.get("data") or []) if row["id"] == 3), {})
    c13 = next((c for c in alina4.get("criteria") or [] if c["criteria_id"] == 13), {})
    manager_score = float(c13.get("manager_score"))
    mid = float(c13.get("mid_level_correction"))
    clev = float(c13.get("c_level_correction"))
    displayed = (manager_score + mid + clev) / 3
    evidence["final_cell"] = {
        "manager_score": manager_score,
        "mid_level_correction": mid,
        "c_level_correction": clev,
        "average": displayed,
        "formula": f"({manager_score} + {mid} + {clev}) / 3 = {displayed}",
    }

    requested = call("GET", "/api/admin/evaluations-matrix?period_id=1", admin)
    evidence["period_param_closed"] = {
        "http": requested[0],
        "period": (requested[1] or {}).get("period"),
        "campaign_active": (requested[1] or {}).get("campaign_active"),
        "alina_13_manager": next(
            (
                c.get("manager_score")
                for row in ((requested[1] or {}).get("data") or [])
                if row["id"] == 3
                for c in row.get("criteria") or []
                if c["criteria_id"] == 13
            ),
            "missing",
        ),
    }

    print(json.dumps(evidence, indent=2, default=str))
    Path("backups/2026-08-20-matrix-calibration/api_proofs.json").write_text(
        json.dumps(evidence, indent=2, default=str) + "\n"
    )
    Path("backups/2026-08-20-matrix-calibration/proof_jtis.json").write_text(
        json.dumps(tokens["_jtis"]) + "\n"
    )


if __name__ == "__main__":
    main()

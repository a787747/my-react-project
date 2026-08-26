#!/usr/bin/env python3
"""ROLE_ACCESS_HR_CLEVEL — the role × route matrix, exercised for real.

Runs every cell of the acceptance matrix against a RUNNING system (throwaway
stand or live) and writes a JSON proof artifact:

  * positive AND negative read cells for admin / c_level / hr / manager /
    employee on every surface this brief touches;
  * every write route called as c_level and as hr, each refusal recorded
    one by one, plus the ordinary-manager and ordinary-employee refusals;
  * the compensation walk: the ACTUAL response keys per role, recursively
    scanned for salary/compensation fields (must find none), with the exact
    key sets of admin-users-data users[] and options.grades[] recorded.

CAMPAIGN-SAFE BY CONSTRUCTION:
  * no evaluation, score, correction, user, scope, period or coefficient row
    is written — write routes are called ONLY with actors their guard refuses,
    or (score-correction as manager) with a c_level_only criterion the route
    refuses 422 before any write;
  * password-reset routes are NOT called: they are unauthenticated self-service
    account recovery (no role dimension exists to refuse), and the request
    route sends mail — D-0820-8 forbids that outside alexander@;
  * minted probe sessions are deleted in a finally; the four data-table counts
    are read before and after and must be identical (any drift aborts loudly —
    on live during the open campaign a drift can also be a real submit, the
    artifact records both figures either way).

Stand example (containers/db from the stand setup script):
  python3 scripts/prove_role_access.py \
    --base http://127.0.0.1:5299/webhook \
    --pg-container epe-roleaccess-pg --n8n-container epe-roleaccess-n8n \
    --db epe_roleaccess
Live example (through the tunnel host, AFTER the stand proof and the deploy):
  python3 scripts/prove_role_access.py --base https://epe.sedamedical.com/webhook
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import uuid
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent

# Live actor ids (see HANDOVER §3): admin Alexander; c_level read-only Cem
# Durukan (can_evaluate=false) and writer Bayram Urayev (can_evaluate=true) —
# the writer proves that the correction refusal is BY ROLE, not by capability.
DEFAULT_ACTORS = {
    "admin": 2,
    "c_level": 21,
    "c_level_writer": 18,
    "hr": 52,
    "manager": 1,
    "employee": 3,
}

COMP_KEY_RE = re.compile(r"salary|compens|зарплат", re.IGNORECASE)

# ── The matrix ───────────────────────────────────────────────────────────────
# (method, path, body, {role: expected}) — "200" etc. are the contract this
# brief establishes; the artifact records the ACTUAL status beside it.
ROLES = ["admin", "c_level", "c_level_writer", "hr", "manager", "employee"]

READ_CELLS = [
    ("GET", "/api/admin-users-data", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 200,
      "manager": 403, "employee": 403}),
    ("GET", "/api/score-coefficients", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("POST", "/manage-criteria", {"action": "get"},
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/admin/evaluations-matrix", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/admin/all-evaluations", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/analytics", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/admin/evaluation-details-by-user", {"_params": {"user_id": "3"}},
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/periods", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 200,
      "manager": 403, "employee": 403}),
    ("GET", "/api/periods/annual-rollup", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 403,
      "manager": 403, "employee": 403}),
    ("GET", "/api/hr/evaluation-status", None,
     {"admin": 200, "c_level": 200, "c_level_writer": 200, "hr": 200,
      "manager": 403, "employee": 403}),
    # Admin-only reads that back the roster page's admin-only affordances:
    ("GET", "/api/admin/employee-events", {"_params": {"user_id": "3"}},
     {"admin": 200, "c_level": 403, "c_level_writer": 403, "hr": 403,
      "manager": 403, "employee": 403}),
]

# Write routes: called ONLY with refused actors (or with a body the route
# refuses before any write, for the one role+capability the design admits).
# Never called as admin — an accepted admin write on live is campaign data.
WRITE_CELLS = [
    ("POST", "/admin/save-user", {"id": 3},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/admin/terminate-employee", {"user_id": 3, "termination_date": "2026-08-26"},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/admin/reinstate-employee", {"user_id": 3},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/admin/exclude-participant", {"user_id": 3, "period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/admin/include-participant", {"user_id": 3, "period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/create", {"name": "never"},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/activate", {"period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/start-evaluation", {"period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/rename", {"period_id": 2, "name": "never"},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/reparent", {"period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/periods/close", {"period_id": 2},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/manage-criteria", {"action": "save", "criteria": {"title": "never"}},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/manage-criteria", {"action": "delete", "criteria": {"id": 1}},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/score-coefficients",
     {"criteria": [{"id": 1, "weight": 5.0, "score_coefficients": {str(i): 1.0 for i in range(1, 11)}}]},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/update-admin-data", {"grades": [{"id": 1, "coefficient": 1.0}]},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    ("POST", "/api/admin/create-invite", {},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": 403, "employee": 403}),
    # criterion 1 is c_level_only: the route 422s it before the period gate and
    # before ownership, so even the role+capability the design admits (a
    # skip-level manager) cannot store this probe. c_level — including the
    # can_evaluate writer — must be refused 403 BY ROLE at the guard. The
    # manager cell reads 422 CRITERIA_NOT_APPLICABLE when the actor can
    # evaluate, 403 CAPABILITY_FORBIDDEN when not — refused without a write
    # either way, so both are accepted.
    ("POST", "/api/admin/score-correction",
     {"subject_id": 3, "criteria_id": 1, "correction_score": 5},
     {"c_level": 403, "c_level_writer": 403, "hr": 403, "manager": (422, 403), "employee": 403}),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True,
                   help="Webhook base, e.g. https://epe.sedamedical.com/webhook or the stand's")
    p.add_argument("--ssh-host", default="root@92.51.45.147")
    p.add_argument("--pg-container", default="postgres_n8n")
    p.add_argument("--n8n-container", default="n8n-n8n-1")
    p.add_argument("--db", default="epe_2026")
    p.add_argument("--actors", default=None,
                   help='JSON overriding actor ids, e.g. {"hr": 53}')
    p.add_argument("--out", default=None, help="Proof artifact path")
    return p.parse_args()


def ssh(args: argparse.Namespace, script: str) -> str:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.ssh_host, "bash", "-s"],
        input=script, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout)[-4000:])
    return completed.stdout


def data_counts(args: argparse.Namespace) -> str:
    return ssh(args, f"""
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -tA -c "
SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
       (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
       (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
       (SELECT count(*) FROM performance_db.period_results)"
""").strip()


def mint_tokens(args: argparse.Namespace, actors: dict[str, int]) -> dict:
    jtis = {name: str(uuid.uuid4()) for name in actors}
    specs = json.dumps(
        {name: {"sub": str(uid), "jti": jtis[name]} for name, uid in actors.items()},
        separators=(",", ":"))
    values = ",\n  ".join(
        f"('{jtis[name]}', {uid})" for name, uid in actors.items())
    script = f"""
set -euo pipefail
SECRET=$(docker exec {args.n8n_container} printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec {args.n8n_container} sh -c \
  "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
SPECS={json.dumps(specs)}
docker exec -e SECRET="$SECRET" -e SPECS="$SPECS" -e NODE_PATH="$JWTDIR" \
  {args.n8n_container} node -e '
const jwt = require("jsonwebtoken");
const now = Math.floor(Date.now()/1000);
const specs = JSON.parse(process.env.SPECS);
const out = {{}};
for (const [name, spec] of Object.entries(specs)) {{
  out[name] = jwt.sign(
    {{ sub: spec.sub, iss: "epe", aud: "epe-api", iat: now, exp: now + 3600, jti: spec.jti }},
    process.env.SECRET, {{ algorithm: "HS256" }});
}}
process.stdout.write(JSON.stringify(out) + "\\n");
'
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -c "
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
SELECT v.jti::uuid, v.user_id, u.token_version, now(), now() + interval '1 hour'
FROM (VALUES
  {values}
) AS v(jti, user_id)
JOIN performance_db.users u ON u.id = v.user_id;"
"""
    raw = ssh(args, script)
    tokens = json.loads(raw.strip().splitlines()[0])
    tokens["_jtis"] = list(jtis.values())
    return tokens


def cleanup_sessions(args: argparse.Namespace, jtis: list[str]) -> None:
    listed = ",".join(f"'{j}'::uuid" for j in jtis)
    ssh(args, f"""
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -c "
DELETE FROM performance_db.auth_sessions WHERE jti IN ({listed});"
""")


def call(base: str, method: str, path: str, token: str, body):
    headers = {"Authorization": f"Bearer {token}"}
    params = None
    payload = None
    if isinstance(body, dict) and "_params" in body:
        params = body["_params"]
    elif body is not None:
        payload = body
    resp = requests.request(method, f"{base}{path}", headers=headers,
                            params=params, json=payload, timeout=90)
    try:
        parsed = resp.json()
    except Exception:
        parsed = resp.text[:300]
    return resp.status_code, parsed


def walk_keys(value, found: set[str], prefix: str = "") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{prefix}.{k}" if prefix else k
            if COMP_KEY_RE.search(str(k)):
                found.add(path)
            walk_keys(v, found, path)
    elif isinstance(value, list):
        for item in value[:5]:
            walk_keys(item, found, prefix + "[]")


def main() -> None:
    args = parse_args()
    base = args.base.rstrip("/")
    actors = dict(DEFAULT_ACTORS)
    if args.actors:
        actors.update({k: int(v) for k, v in json.loads(args.actors).items()})

    counts_before = data_counts(args)
    tokens = mint_tokens(args, actors)
    jtis = tokens.pop("_jtis")

    matrix: list[dict] = []
    comp_walk: dict[str, dict] = {}
    failures: list[str] = []
    try:
        for method, path, body, expected in READ_CELLS + WRITE_CELLS:
            for role, want in expected.items():
                status, parsed = call(base, method, path, tokens[role], body)
                code = parsed.get("error") if isinstance(parsed, dict) else None
                wanted = want if isinstance(want, tuple) else (want,)
                cell = {"method": method, "path": path, "role": role,
                        "expected": list(wanted), "status": status, "code": code}
                matrix.append(cell)
                if status not in wanted:
                    failures.append(f"{role} {method} {path}: expected {wanted}, got {status} {code}")
                # Compensation walk on every 200 a non-admin role receives.
                if status == 200 and role != "admin":
                    found: set[str] = set()
                    walk_keys(parsed, found)
                    entry = comp_walk.setdefault(f"{role} {method} {path}", {})
                    entry["compensation_keys"] = sorted(found)
                    if found:
                        failures.append(f"{role} {method} {path}: compensation keys {sorted(found)}")
                    if path == "/api/admin-users-data" and isinstance(parsed, dict):
                        users = parsed.get("users") or []
                        grades = (parsed.get("options") or {}).get("grades") or []
                        entry["users0_keys"] = sorted(users[0].keys()) if users else []
                        entry["grades0_keys"] = sorted(grades[0].keys()) if grades else []
                        if role == "hr" and grades and set(grades[0]) != {"id", "code"}:
                            failures.append(f"hr grades keys leak: {sorted(grades[0])}")
                        if role in ("c_level", "c_level_writer") and grades \
                                and "coefficient" not in grades[0]:
                            failures.append("c_level grades lost coefficient — money screens would break")
            time.sleep(0.05)
    finally:
        cleanup_sessions(args, jtis)

    counts_after = data_counts(args)
    if counts_before != counts_after:
        failures.append(
            f"DATA COUNTS MOVED during the probe run: {counts_before} -> {counts_after}. "
            f"The probes write nothing — on live this can be a real submit landing in the "
            f"window; identify the rows before trusting this artifact.")

    artifact = {
        "base": base,
        "actors": actors,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "cells": matrix,
        "compensation_walk": comp_walk,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }
    out = Path(args.out) if args.out else (
        REPO / "backups" / "2026-08-26-role-access" /
        f"prove_role_access_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verdict": artifact["verdict"], "cells": len(matrix),
                      "failures": failures, "artifact": str(out)},
                     ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

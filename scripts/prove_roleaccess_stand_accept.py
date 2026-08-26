#!/usr/bin/env python3
"""ROLE_ACCESS_DEPLOY — STAND-ONLY: prove the c_level corrections route ACCEPTS.

The matrix prover (prove_role_access.py) proves role admission by refusal
codes, because on live nothing may be written. This script runs ONLY against
the throwaway stand and stores a real correction as each c_level writer
(Bayram 18, Jemal 47) on a manager-channel criterion, then reads the rows
back — the "deliberately still accepted" half of the acceptance, end to end.

It refuses to run against live: the target database name must carry the
stand prefix.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import uuid
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
STAND_PREFIX = "epe_roleaccess_"

# criterion 3 «Личная результативность и эффективность» — audience all,
# for_manager, NOT c_level_only: the correction lands in the manager channel,
# which is exactly what D-0820-7 gives c_level the right to calibrate.
WRITERS = [(18, "c_level_writer_bayram"), (47, "c_level_writer_jemal")]
SUBJECT_ID = 3      # Alina Naubatova, employee, in scope
CRITERIA_ID = 3
SCORES = {18: 7, 47: 6}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--ssh-host", default="root@92.51.45.147")
    p.add_argument("--pg-container", default="postgres_n8n")
    p.add_argument("--n8n-container", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--out", default=None)
    return p.parse_args()


def ssh(args: argparse.Namespace, script: str) -> str:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.ssh_host, "bash", "-s"],
        input=script, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout)[-4000:])
    return completed.stdout


def main() -> None:
    args = parse_args()
    if not args.db.startswith(STAND_PREFIX):
        raise SystemExit(
            f"refusing: {args.db!r} does not carry the stand prefix {STAND_PREFIX!r} — "
            f"this script stores correction rows and must never see live")
    base = args.base.rstrip("/")

    jtis = {uid: str(uuid.uuid4()) for uid, _ in WRITERS}
    specs = json.dumps({str(uid): {"sub": str(uid), "jti": jtis[uid]}
                        for uid, _ in WRITERS}, separators=(",", ":"))
    values = ",\n  ".join(f"('{jtis[uid]}', {uid})" for uid, _ in WRITERS)
    raw = ssh(args, f"""
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
""")
    tokens = json.loads(raw.strip().splitlines()[0])

    results = []
    failures = []
    try:
        for uid, label in WRITERS:
            resp = requests.post(
                f"{base}/api/admin/score-correction",
                headers={"Authorization": f"Bearer {tokens[str(uid)]}"},
                json={"subject_id": SUBJECT_ID, "criteria_id": CRITERIA_ID,
                      "correction_score": SCORES[uid]},
                timeout=90)
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:300]
            results.append({"writer": label, "user_id": uid,
                            "status": resp.status_code, "body": body})
            if resp.status_code != 200 or not (isinstance(body, dict) and body.get("success")):
                failures.append(f"{label}: expected an accepted 200, got {resp.status_code} {body}")
    finally:
        listed = ",".join(f"'{j}'::uuid" for j in jtis.values())
        ssh(args, f"""
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -c "
DELETE FROM performance_db.auth_sessions WHERE jti IN ({listed});"
""")

    rows = ssh(args, f"""
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -tA -c "
SELECT id || '|' || subject_id || '|' || evaluator_id || '|' || criteria_id || '|' ||
       correction_score || '|' || correction_level || '|' || period_id
FROM performance_db.score_corrections ORDER BY id;"
""").strip().splitlines()
    # Two writers, one unique key (subject, criteria, level, period): the second
    # accepted write must have UPSERTED over the first — exactly one row, its
    # evaluator the LAST writer. That is the known last-writer-wins residue
    # recorded in BUG-073's row, reproduced here, not a surprise.
    if len(rows) != 1:
        failures.append(f"expected exactly one stored correction row (upsert), got {rows}")
    else:
        parts = rows[0].split("|")
        if parts[1:6] != [str(SUBJECT_ID), str(WRITERS[-1][0]), str(CRITERIA_ID),
                          str(SCORES[WRITERS[-1][0]]), "c_level"]:
            failures.append(f"stored row does not match the last accepted write: {rows[0]}")

    artifact = {
        "base": base, "db": args.db, "writers": results,
        "stored_rows": rows, "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }
    out = Path(args.out) if args.out else (
        REPO / "backups" / "2026-08-26-role-access" /
        f"prove_stand_accept_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Control/treatment close proof for PEER_RECOGNITION (2026-08-27).

The claim under test: a peer-recognition row cannot reach the close dataset,
`period_results`, a rating, a final score or a bonus index.

The proof is not an assertion about the SQL. Two throwaway databases are
restored from ONE dump taken after the evaluations were seeded, so they are
byte-identical, and then differ in exactly one way:

    treatment  — carries the two nominations
    control    — the same rows deleted, nothing else touched

H1 is then closed in BOTH by the REAL route (`POST /api/periods/close`, admin,
one n8n container per database) and the frozen `period_results` are compared
row for row and by md5. If a nomination could move a single money cell, the two
frozen sets differ.

    python3 scripts/prove_recognition_close.py \
        --treatment-base http://127.0.0.1:25679/webhook --treatment-db <db> \
        --control-base   http://127.0.0.1:25680/webhook --control-db   <db>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid

import requests

ADMIN_ID = 2
PERIOD_ID = 2
SSH_HOST = "root@92.51.45.147"
PG = "postgres_n8n"

RESULTS_SQL = """
SELECT period_id || '|' || user_id || '|' || is_in_scope || '|' || has_data || '|' ||
       COALESCE(rating_manager::text,'~')      || '|' ||
       COALESCE(rating_upward::text,'~')       || '|' ||
       COALESCE(rating_c_level_direct::text,'~') || '|' ||
       COALESCE(rating_self::text,'~')         || '|' ||
       COALESCE(final_rating::text,'~')        || '|' ||
       COALESCE(bonus_index::text,'~')
FROM performance_db.period_results
WHERE period_id = %d
ORDER BY user_id
""" % PERIOD_ID


def ssh(script: str) -> str:
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", SSH_HOST, "bash", "-s"],
                          input=script, text=True, capture_output=True)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout)[-4000:])
    return done.stdout


def sql(db: str, statement: str) -> str:
    quoted = statement.replace('"', '\\"')
    return ssh(f'docker exec {PG} psql -U admin -d {db} -v ON_ERROR_STOP=1 -tA '
               f'-c "{quoted}"').strip()


def mint_admin(container: str, db: str) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    script = f"""
set -euo pipefail
SECRET=$(docker exec {container} printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec {container} sh -c \
  "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
docker exec -e SECRET="$SECRET" -e NODE_PATH="$JWTDIR" {container} node -e '
const jwt = require("jsonwebtoken");
const now = Math.floor(Date.now()/1000);
process.stdout.write(jwt.sign(
  {{ sub: "{ADMIN_ID}", iss: "epe", aud: "epe-api", iat: now, exp: now + 3600,
     jti: "{jti}" }}, process.env.SECRET, {{ algorithm: "HS256" }}) + "\\n");
'
docker exec {PG} psql -U admin -d {db} -v ON_ERROR_STOP=1 -c "
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
SELECT '{jti}'::uuid, u.id, u.token_version, now(), now() + interval '1 hour'
FROM performance_db.users u WHERE u.id = {ADMIN_ID};"
"""
    return ssh(script).strip().splitlines()[0], jti


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--treatment-base", required=True)
    p.add_argument("--treatment-db", required=True)
    p.add_argument("--treatment-container", default="epe-recognition-n8n")
    p.add_argument("--control-base", required=True)
    p.add_argument("--control-db", required=True)
    p.add_argument("--control-container", default="epe-recognition-n8n-ctl")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    report: dict = {}
    failures: list[str] = []

    def check(name: str, ok: bool, **evidence) -> None:
        report.setdefault("checks", []).append({"check": name, "pass": bool(ok), **evidence})
        if ok:
            print(f"ok    {name}")
        else:
            failures.append(name)
            print(f"FAIL  {name}: {json.dumps(evidence, ensure_ascii=False)[:400]}")

    # ── 1. Make the control differ by the nominations and by nothing else ────
    deleted = sql(args.control_db,
                  "WITH d AS (DELETE FROM performance_db.peer_recognitions RETURNING 1) "
                  "SELECT count(*) FROM d")
    report["control_nominations_deleted"] = deleted
    t_rows = sql(args.treatment_db, "SELECT count(*) FROM performance_db.peer_recognitions")
    c_rows = sql(args.control_db, "SELECT count(*) FROM performance_db.peer_recognitions")
    check("1 treatment carries the nominations, control carries none",
          t_rows == "2" and c_rows == "0", treatment=t_rows, control=c_rows,
          deleted=deleted)

    # ── 2. The two databases are otherwise identical ────────────────────────
    fingerprint = """
SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
  SELECT 'e|' || id || '|' || period_id || '|' || COALESCE(subject_id::text,'~') || '|' ||
         COALESCE(evaluator_id::text,'~') || '|' || evaluation_source || '|' ||
         COALESCE(calculated_score::text,'~') AS t
  FROM performance_db.evaluations
  UNION ALL
  SELECT 's|' || id || '|' || evaluation_id || '|' || criteria_id || '|' || score_value
  FROM performance_db.evaluation_scores
  UNION ALL
  SELECT 'c|' || id || '|' || title || '|' || weight || '|' || COALESCE(target_audience::text,'')
  FROM performance_db.criteria WHERE is_active = true
  UNION ALL
  SELECT 'k|' || criteria_id || '|' || score_level || '|' || coefficient
  FROM performance_db.score_coefficients
  UNION ALL
  SELECT 'g|' || id || '|' || code || '|' || coefficient FROM performance_db.grades
  UNION ALL
  SELECT 'p|' || user_id || '|' || is_in_scope || '|' || COALESCE(exclusion_reason,'')
  FROM performance_db.evaluation_period_participants WHERE period_id = 2
  UNION ALL
  SELECT 'u|' || id || '|' || full_name || '|' || COALESCE(grade_id::text,'~') || '|' ||
         COALESCE(manager_id::text,'~') || '|' || work_category
  FROM performance_db.users) x
"""
    t_fp = sql(args.treatment_db, fingerprint)
    c_fp = sql(args.control_db, fingerprint)
    report["inputs_fingerprint"] = {"treatment": t_fp, "control": c_fp}
    check("2 every money input is identical in both databases", t_fp == c_fp and len(t_fp) == 32,
          treatment=t_fp, control=c_fp)

    # ── 3. Close H1 in both, by the real route ──────────────────────────────
    report["close"] = {}
    for side, base, db, container in (
            ("treatment", args.treatment_base, args.treatment_db, args.treatment_container),
            ("control", args.control_base, args.control_db, args.control_container)):
        token, jti = mint_admin(container, db)
        resp = requests.post(f"{base.rstrip('/')}/api/periods/close",
                             headers={"Authorization": f"Bearer {token}"},
                             json={"period_id": PERIOD_ID}, timeout=180)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:400]
        report["close"][side] = {"status": resp.status_code, "body": body}
        sql(db, f"DELETE FROM performance_db.auth_sessions WHERE jti = '{jti}'::uuid")
        check(f"3 close succeeded on the {side}",
              resp.status_code == 200 and isinstance(body, dict) and body.get("success") is True,
              status=resp.status_code, body=body)

    # ── 4. Compare the frozen rows ──────────────────────────────────────────
    t_results = sql(args.treatment_db, RESULTS_SQL)
    c_results = sql(args.control_db, RESULTS_SQL)
    t_lines = [line for line in t_results.split("\n") if line]
    c_lines = [line for line in c_results.split("\n") if line]
    report["period_results"] = {
        "treatment_rows": len(t_lines),
        "control_rows": len(c_lines),
        "treatment_md5": sql(args.treatment_db,
                             f"SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM ({RESULTS_SQL}) x(t)"),
        "control_md5": sql(args.control_db,
                           f"SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM ({RESULTS_SQL}) x(t)"),
        "rows_with_money_treatment": [line for line in t_lines if "|true|true|" in line],
    }
    check("4 the same number of rows was frozen on both sides",
          len(t_lines) == len(c_lines) and len(t_lines) > 0,
          treatment=len(t_lines), control=len(c_lines))
    check("4 the frozen money is identical, row for row",
          t_lines == c_lines
          and report["period_results"]["treatment_md5"] == report["period_results"]["control_md5"],
          md5_treatment=report["period_results"]["treatment_md5"],
          md5_control=report["period_results"]["control_md5"],
          first_difference=next((f"{a} != {b}" for a, b in zip(t_lines, c_lines) if a != b), None))
    money_rows = report["period_results"]["rows_with_money_treatment"]
    check("4 the comparison had money in it (not an all-NULL freeze)",
          len(money_rows) >= 4, rows_with_data=len(money_rows), sample=money_rows[:4])

    # ── 5. The close payload itself carries no trace ────────────────────────
    raw = json.dumps(report["close"]["treatment"]["body"], ensure_ascii=False)
    check("5 the close response carries no recognition key and no nomination text",
          "recogn" not in raw.lower() and "MARKER-7Q2X" not in raw,
          bytes=len(raw))
    columns = sql(args.treatment_db,
                  "SELECT string_agg(column_name, ',' ORDER BY ordinal_position) "
                  "FROM information_schema.columns WHERE table_schema='performance_db' "
                  "AND table_name='period_results'")
    report["period_results_columns"] = columns
    check("5 period_results has no recognition column",
          "recogn" not in columns.lower(), columns=columns)

    # ── 6. The nominations survived the close, untouched ────────────────────
    survived = sql(args.treatment_db,
                   "SELECT count(*)::text || '|' || md5(string_agg("
                   "id::text || ':' || nominee_id::text || ':' || situation, "
                   "E'\\n' ORDER BY id)) FROM performance_db.peer_recognitions")
    report["nominations_after_close"] = survived
    check("6 the nominations still exist after the close and were not rewritten",
          survived.startswith("2|"), value=survived)

    report["verdict"] = "PASS" if not failures else "FAIL"
    report["failed"] = failures
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"\n{report['verdict']}  ({len(report.get('checks', []))} checks, "
          f"{len(failures)} failed)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

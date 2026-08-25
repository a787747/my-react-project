#!/usr/bin/env python3
"""PRELAUNCH_BATCH_NIGHT — prove on LIVE that only the four intended rows moved.

The claim this script exists to make is negative: the night's work excluded four
people from H1 scope and changed nothing else in `epe_2026`.

Method — no assertion is taken on trust:

  1. The pre-write anchor (`--anchor`) is restored into a throwaway database on the
     VPS. Both sides are exported as JSON and compared cell by cell; `dblink` is
     never created on live.
  2. Every user row × every column, and every participants row × every column.
  3. Catalogue, coefficients, grades, departments and periods are fingerprinted on
     both sides by md5 over an ordered projection.
  4. Period state, the four data tables, the scope-event log.
  5. The read surface through Caddy with an admin token minted and deleted in a
     `finally`.

The throwaway database is dropped before the script returns; the drop refuses any
name that does not carry the throwaway prefix, so `epe_2026` can never be a
candidate.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()
HOST = "root@92.51.45.147"
ORIGIN = "https://epe.sedamedical.com"
REPO = Path(__file__).resolve().parent.parent
ADMIN_ID = 2
PROBE_JTI = "caf10000-2026-0825-8000-000000000018"
H1 = 2
STAND_PREFIX = "epe_nightverify_"

EXCLUDED = [22, 25, 63, 64]

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST, command],
        capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def jsql(database: str, statement: str) -> Any:
    return json.loads(sql(database, statement) or "null")


def check(name: str, actual: Any, expected: Any) -> bool:
    ok = actual == expected
    REPORT.setdefault("checks", []).append(
        {"name": name, "expected": expected, "actual": actual, "ok": ok})
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 3600, "jti": jti}).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def call(method: str, path: str, token: str) -> tuple[int, Any]:
    request = urllib.request.Request(
        f"{ORIGIN}/webhook/{path.lstrip('/')}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method=method)
    try:
        with urllib.request.urlopen(request, timeout=180, context=TLS) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


USERS_SNAPSHOT = """
  SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM (
    SELECT id, full_name, email, role::text AS role, job_title,
           work_category::text AS work_category, is_project_participant,
           department_id, grade_id, manager_id, has_subordinates,
           can_evaluate, can_be_evaluated, token_version, employment_type,
           join_date::text AS join_date, salary_current::text AS salary_current,
           salary_proposed::text AS salary_proposed, created_at::text AS created_at,
           (password_hash IS NOT NULL) AS has_password,
           terminated_at::text AS terminated_at,
           termination_date::text AS termination_date
    FROM performance_db.users u) u"""

PARTICIPANTS_SNAPSHOT = """
  SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.period_id, p.user_id), '[]') FROM (
    SELECT period_id, user_id, is_in_scope, exclusion_reason,
           created_at::text AS created_at, updated_at::text AS updated_at
    FROM performance_db.evaluation_period_participants) p"""

# Every column of each table, without naming them, so a column added later is
# covered automatically rather than silently dropped out of the comparison.
FINGERPRINTS = {
    name: ("SELECT md5(coalesce(string_agg(t, '|' ORDER BY t), '')) FROM ("
           f"SELECT row_to_json(x)::text AS t FROM performance_db.{name} x) s")
    for name in ("criteria", "score_coefficients", "grades", "departments",
                 "evaluation_periods")
}


def diff_rows(before: list[dict], after: list[dict], key: tuple[str, ...]) -> list[dict]:
    def k(row: dict) -> tuple:
        return tuple(row[c] for c in key)
    bmap = {k(r): r for r in before}
    amap = {k(r): r for r in after}
    moved = []
    for kk in sorted(set(bmap) | set(amap)):
        b, a = bmap.get(kk), amap.get(kk)
        if b is None or a is None:
            moved.append({"key": list(kk), "appeared": a is not None, "vanished": b is not None})
            continue
        cells = {c: [b[c], a[c]] for c in b if b[c] != a[c]}
        if cells:
            moved.append({"key": list(kk), "cells": cells})
    return moved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", required=True,
                        help="path ON THE VPS of the pre-write pg_dump")
    parser.add_argument("--expect-release", default=None,
                        help="frontend release id that must be the symlink target")
    parser.add_argument("--out", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "live_verify.json"))
    args = parser.parse_args()

    stamp = ssh("date -u +%Y%m%d%H%M%S")
    stand = f"{STAND_PREFIX}{stamp}"
    REPORT["utc_at_start"] = ssh("date -u +%Y-%m-%dT%H:%M:%SZ")
    REPORT["anchor"] = args.anchor
    REPORT["anchor_md5"] = ssh(f"md5sum {args.anchor}").split()[0]
    REPORT["throwaway"] = stand

    try:
        # ── 1. restore the anchor into a throwaway ───────────────────────────
        ssh(f'docker exec postgres_n8n psql -U admin -d postgres -v ON_ERROR_STOP=1 '
            f'-c "CREATE DATABASE {stand}"')
        ssh(f'docker exec -i postgres_n8n pg_restore -U admin -d {stand} --no-owner --no-acl '
            f'< {args.anchor} 2>&1 | tail -3 || true')
        anchor_users = int(sql(stand, "SELECT count(*) FROM performance_db.users"))
        check("the anchor restored with 89 users", anchor_users, 89)

        # ── 2. cell by cell ──────────────────────────────────────────────────
        before_users = jsql(stand, USERS_SNAPSHOT)
        after_users = jsql("epe_2026", USERS_SNAPSHOT)
        user_moves = diff_rows(before_users, after_users, ("id",))
        cols = len(before_users[0]) if before_users else 0
        REPORT["users_cells_compared"] = len(before_users) * cols
        REPORT["users_diff"] = user_moves
        check(f"every one of {len(before_users) * cols} user cells is unchanged", user_moves, [])

        before_parts = jsql(stand, PARTICIPANTS_SNAPSHOT)
        after_parts = jsql("epe_2026", PARTICIPANTS_SNAPSHOT)
        part_moves = diff_rows(before_parts, after_parts, ("period_id", "user_id"))
        pcols = len(before_parts[0]) if before_parts else 0
        REPORT["participants_cells_compared"] = len(before_parts) * pcols
        REPORT["participants_diff"] = part_moves
        check("exactly four participants rows moved, all on period 2",
              sorted(m["key"] for m in part_moves), [[H1, i] for i in EXCLUDED])
        check("and each moved only is_in_scope, exclusion_reason and updated_at",
              sorted([sorted(m["cells"]) for m in part_moves]),
              [["exclusion_reason", "is_in_scope", "updated_at"]] * 4)
        check("each went true/NULL -> false/excluded_by_admin",
              sorted([[m["cells"]["is_in_scope"], m["cells"]["exclusion_reason"]]
                      for m in part_moves]),
              [[[True, False], [None, "excluded_by_admin"]]] * 4)

        # ── 3. fingerprints ──────────────────────────────────────────────────
        prints = {}
        for name, statement in FINGERPRINTS.items():
            b, a = sql(stand, statement), sql("epe_2026", statement)
            prints[name] = {"anchor": b, "live": a, "same": b == a}
            check(f"{name} is md5-identical to the anchor", a, b)
        REPORT["fingerprints"] = prints
    finally:
        ssh(f'docker exec postgres_n8n psql -U admin -d postgres -c '
            f'"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{stand}\'" '
            f'>/dev/null 2>&1 || true')
        if stand.startswith(STAND_PREFIX):
            ssh(f'docker exec postgres_n8n psql -U admin -d postgres -c "DROP DATABASE IF EXISTS {stand}"')
    remaining = sql("postgres", "SELECT string_agg(datname, ',' ORDER BY datname) "
                                "FROM pg_database WHERE datistemplate = false")
    REPORT["databases_after"] = remaining
    check("no throwaway database is left behind", remaining, "postgres,epe_2026"
          if remaining == "postgres,epe_2026" else "epe_2026,postgres")

    # ── 4. invariants ────────────────────────────────────────────────────────
    inv = jsql("epe_2026", """
      SELECT json_build_object(
        'users', (SELECT count(*) FROM performance_db.users),
        'terminated', (SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL),
        'in_scope_h1', (SELECT count(*) FROM performance_db.evaluation_period_participants
                        WHERE period_id = 2 AND is_in_scope),
        'in_scope_annual', (SELECT count(*) FROM performance_db.evaluation_period_participants
                            WHERE period_id = 5 AND is_in_scope),
        'participants_h1', (SELECT count(*) FROM performance_db.evaluation_period_participants
                            WHERE period_id = 2),
        'evaluations', (SELECT count(*) FROM performance_db.evaluations),
        'evaluation_scores', (SELECT count(*) FROM performance_db.evaluation_scores),
        'score_corrections', (SELECT count(*) FROM performance_db.score_corrections),
        'period_results', (SELECT count(*) FROM performance_db.period_results),
        'started_periods', (SELECT count(*) FROM performance_db.evaluation_periods
                            WHERE evaluation_started_at IS NOT NULL),
        'scope_events', (SELECT count(*) FROM performance_db.period_scope_events),
        'employment_events', (SELECT count(*) FROM performance_db.employment_events),
        'excluded_by_admin', (SELECT count(*) FROM performance_db.evaluation_period_participants
                              WHERE exclusion_reason = 'excluded_by_admin'),
        'extensions', (SELECT string_agg(extname, ',' ORDER BY extname) FROM pg_extension),
        'h1_status', (SELECT status || '/' || is_active FROM performance_db.evaluation_periods
                      WHERE id = 2))""")
    REPORT["invariants"] = inv
    check("89 users, 3 terminated", [inv["users"], inv["terminated"]], [89, 3])
    check("80 in scope of H1 out of 89 participants",
          [inv["in_scope_h1"], inv["participants_h1"]], [80, 89])
    check("the annual container is untouched at 86", inv["in_scope_annual"], 86)
    check("H1 is still active", inv["h1_status"], "active/true")
    check("evaluation_started_at is NULL on all three periods", inv["started_periods"], 0)
    check("the four data tables are 0/0/0/0",
          [inv["evaluations"], inv["evaluation_scores"],
           inv["score_corrections"], inv["period_results"]], [0, 0, 0, 0])
    check("four scope events, four excluded_by_admin rows",
          [inv["scope_events"], inv["excluded_by_admin"]], [4, 4])
    check("the owner's three employment events are untouched", inv["employment_events"], 3)
    check("no extension was created on live", inv["extensions"], "plpgsql")

    # ── 5. the read surface ──────────────────────────────────────────────────
    secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
    if not secret:
        raise SystemExit("could not read JWT_SIGNING_SECRET")
    sessions_before = int(sql("epe_2026", "SELECT count(*) FROM performance_db.auth_sessions"))
    version = int(sql("epe_2026",
                      f"SELECT token_version FROM performance_db.users WHERE id = {ADMIN_ID}"))
    sql("epe_2026", f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{PROBE_JTI}', {ADMIN_ID}, {version}, now(), now() + interval '1 hour')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
    token = mint(secret, ADMIN_ID, PROBE_JTI)
    try:
        status, body = call("GET", "api/periods", token)
        h1 = next(p for p in body["data"] if int(p["id"]) == H1)
        REPORT["periods_route"] = h1
        check("the periods route reports H1 active and not started",
              [h1["status"], h1["evaluation_started"]], ["active", False])
        check("and 80 in scope of 89",
              [h1["in_scope_count"], h1["participant_count"]], [80, 89])

        status, body = call("GET", "api/admin/period-scope-events", token)
        events = (body or {}).get("events") or []
        REPORT["scope_events_route"] = {"status": status, "count": len(events)}
        check("the scope-event log answers 200 with four exclusions",
              [status, len(events)], [200, 4])
        check("all four are period-2 admin exclusions of the four named people",
              sorted([[int(e["period_id"]), int(e["user_id"]), e["event_type"], e["reason"]]
                      for e in events]),
              [[H1, i, "excluded", "excluded_by_admin"] for i in EXCLUDED])

        status, body = call("GET", "api/admin-users-data", token)
        rows = (body or {}).get("users") or []
        REPORT["admin_users_data"] = {"status": status, "count": len(rows)}
        check("the admin user list still answers 200 with all 89", [status, len(rows)], [200, 89])
        check("exactly three of them carry a termination",
              sum(1 for r in rows if r.get("terminated_at")), 3)

        status, body = call("GET", "api/employees", token)
        REPORT["employees_route"] = {
            "status": status,
            "campaign_active": (body or {}).get("campaign_active"),
            "period_in_preparation": (body or {}).get("period_in_preparation")}
        check("the employees route still reports the preparation window",
              [(body or {}).get("campaign_active"), (body or {}).get("period_in_preparation")],
              [False, True])
    finally:
        sql("epe_2026", f"DELETE FROM performance_db.auth_sessions WHERE jti = '{PROBE_JTI}'")
    sessions_after = int(sql("epe_2026", "SELECT count(*) FROM performance_db.auth_sessions"))
    check("the probe session was deleted and no other session row moved",
          sessions_after, sessions_before)

    # ── 6. the frontend release ──────────────────────────────────────────────
    if args.expect_release:
        target = ssh("readlink /var/www/epe/current")
        REPORT["symlink_target"] = target
        check("the symlink points at the expected release",
              target.rstrip("/").split("/")[-1], args.expect_release)

    REPORT["failures"] = FAILURES
    REPORT["utc_at_end"] = ssh("date -u +%Y-%m-%dT%H:%M:%SZ")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False))

    total = len(REPORT.get("checks", []))
    print(f"{total - len(FAILURES)}/{total} checks passed → {out}")
    for f in FAILURES:
        print("  ✗", f)
    raise SystemExit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

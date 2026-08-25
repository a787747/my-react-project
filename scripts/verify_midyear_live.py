#!/usr/bin/env python3
"""Verify the MID_YEAR_HIRES_SCOPE deployment on LIVE — read-only (2026-08-25).

This session deploys the capability and excludes NOBODY. The point of this
script is therefore the negative claim: prove that adding the capability moved
no person's data, no money input and no period state. The anchor for this run
was taken AFTER the owner's three terminations, so those are part of the
baseline, not drift.

  1. Drift, cell by cell. The pre-deployment anchor is restored into a
     throwaway database and every column of every user is compared against
     live. dblink is never created on live (a previous brief did that by
     accident and had to undo it); both sides are exported as JSON instead.
  2. The frozen columns are checked by name, on all 89.
  3. Period state, the four data tables, catalogue and coefficient
     fingerprints, and the criteria-count distribution.
  4. The read surface, through Caddy with a real admin token that is minted
     and deleted in a finally.

The probe deletes its own session row and creates nothing else. The throwaway
database is dropped before the script returns.
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
    # Same as the sibling scripts: the system Python has no CA bundle of its
    # own, so the trust store is named explicitly rather than disabled.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent
ORIGIN = "https://epe.sedamedical.com"
ADMIN_ID = 2
PROBE_JTI = "caf10000-2026-0825-8000-000000000016"
VPS_TMP = "/root/epe_stand_tmp"

FROZEN_COLUMNS = ["salary_current", "salary_proposed", "join_date", "password_hash",
                  "can_evaluate", "can_be_evaluated", "token_version",
                  "employment_type", "created_at"]
NEW_COLUMNS: list[str] = []   # migration 016 adds a TABLE, not a users column

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, command],
        capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST,
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
        with urllib.request.urlopen(request, timeout=120, context=TLS) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


USERS_SQL_BASE = """
  SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM (
    SELECT id, full_name, email, role::text AS role, job_title, work_category,
           is_project_participant, department_id, grade_id, manager_id,
           has_subordinates, can_evaluate, can_be_evaluated, token_version,
           employment_type, join_date::text AS join_date,
           salary_current::text AS salary_current,
           salary_proposed::text AS salary_proposed,
           created_at::text AS created_at,
           (password_hash IS NOT NULL) AS password_hash
    FROM performance_db.users) u"""


def users(database: str, with_new_columns: bool) -> dict[str, dict[str, Any]]:
    statement = USERS_SQL_BASE
    if with_new_columns:
        statement = statement.replace(
            "(password_hash IS NOT NULL) AS password_hash",
            "(password_hash IS NOT NULL) AS password_hash,\n"
            "           terminated_at::text AS terminated_at,\n"
            "           termination_date::text AS termination_date")
    return {str(r["id"]): r for r in jsql(database, statement)}


def criteria_distribution(database: str) -> dict[str, int]:
    rows = jsql(database, """
      SELECT COALESCE(json_agg(json_build_object('c', crit, 'n', n)), '[]') FROM (
        SELECT crit, count(*)::int AS n FROM (
          SELECT (SELECT count(*) FROM performance_db.criteria c
                   WHERE c.is_active = true AND c.c_level_only = false
                     AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)
                     AND (c.target_audience <> 'managers_only' OR u.has_subordinates = true)) AS crit
          FROM performance_db.users u) t
        GROUP BY crit) x""")
    return {str(r["c"]): r["n"] for r in sorted(rows, key=lambda r: r["c"])}


def category_split(database: str) -> dict[str, int]:
    rows = jsql(database, """
      SELECT COALESCE(json_agg(json_build_object('k', work_category, 'n', n)), '[]') FROM (
        SELECT work_category, count(*)::int AS n FROM performance_db.users
        GROUP BY work_category) x""")
    return {r["k"]: r["n"] for r in sorted(rows, key=lambda r: r["k"])}


def fingerprints(database: str) -> dict[str, str]:
    raw = jsql(database, """
      SELECT json_build_object(
        'criteria', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT row_to_json(c)::text AS t FROM performance_db.criteria c) a),
        'score_coefficients', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT concat_ws(':',criteria_id,score_level,coefficient) AS t
                      FROM performance_db.score_coefficients) b),
        'grades', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT row_to_json(g)::text AS t FROM performance_db.grades g) c),
        'departments', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT row_to_json(d)::text AS t FROM performance_db.departments d) d),
        'periods', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT row_to_json(p)::text AS t FROM performance_db.evaluation_periods p) e),
        'participants', (SELECT md5(string_agg(t,'|' ORDER BY t)) FROM
                     (SELECT concat_ws(':',period_id,user_id,is_in_scope,coalesce(exclusion_reason,''),
                                       created_at,updated_at) AS t
                      FROM performance_db.evaluation_period_participants) f))""")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", required=True,
                        help="Anchor dump filename inside /root/epe_stand_tmp")
    parser.add_argument("--out", default=str(REPO / "backups/2026-08-25-midyear-scope/live_verify.json"))
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    throwaway = f"epe_midverify_{stamp}"
    REPORT["anchor"] = args.anchor
    REPORT["throwaway"] = throwaway

    live_users = users("epe_2026", with_new_columns=True)
    REPORT["live_user_count"] = len(live_users)
    check("live still has 89 people", len(live_users), 89)

    # ── 1. the anchor, restored and diffed ──────────────────────────────────
    ssh(f"docker exec postgres_n8n createdb -U admin {throwaway}")
    try:
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", HOST,
             f"docker exec -i postgres_n8n pg_restore -U admin -d {throwaway} --no-owner "
             f"< {VPS_TMP}/{args.anchor}"], capture_output=True)
        anchor_users = users(throwaway, with_new_columns=True)
        check("the anchor holds the same 89 people", len(anchor_users), 89)

        columns = sorted(set(next(iter(anchor_users.values()))))
        changed: list[str] = []
        compared = 0
        for uid in sorted(set(anchor_users) | set(live_users), key=int):
            before, after = anchor_users.get(uid), live_users.get(uid)
            if before is None or after is None:
                changed.append(f"{uid}: row {'added' if before is None else 'removed'}")
                continue
            for column in columns:
                compared += 1
                if before.get(column) != after.get(column):
                    changed.append(f"{uid}.{column}: {before.get(column)!r} -> {after.get(column)!r}")
        REPORT["cells_compared"] = compared
        REPORT["cells_changed"] = changed
        check("no cell of any user moved", changed, [])
        check("89 people x every column were compared",
              compared, 89 * len(columns))

        # 2. the frozen columns, by name.
        frozen_moved = [c for c in changed if any(f".{col}:" in c for col in FROZEN_COLUMNS)]
        check("no frozen column moved on anybody", frozen_moved, [])

        # Migration 016 adds a table, not a users column: the anchor and live
        # therefore have the SAME column list, and the diff above covers all of
        # it including terminated_at / termination_date.
        check("the anchor and live share every users column",
              sorted(set(next(iter(anchor_users.values())))
                     ^ set(next(iter(live_users.values())))), [])
        terminated = sorted(int(uid) for uid, row in live_users.items()
                            if row.get("terminated_at") is not None)
        REPORT["terminated_on_live"] = terminated
        check("the owner's three terminations are still exactly three, unchanged by this brief",
              len(terminated), 3)

        # 3. everything else, both sides.
        before_fp, after_fp = fingerprints(throwaway), fingerprints("epe_2026")
        REPORT["fingerprints"] = {"anchor": before_fp, "live": after_fp}
        for key in ("criteria", "score_coefficients", "grades", "departments",
                    "periods", "participants"):
            check(f"{key} md5 identical to the anchor", after_fp[key], before_fp[key])

        REPORT["criteria_distribution"] = {
            "anchor": criteria_distribution(throwaway),
            "live": criteria_distribution("epe_2026")}
        check("criteria-count distribution unchanged",
              REPORT["criteria_distribution"]["live"],
              REPORT["criteria_distribution"]["anchor"])
        REPORT["category_split"] = {
            "anchor": category_split(throwaway),
            "live": category_split("epe_2026")}
        check("general/project split unchanged",
              REPORT["category_split"]["live"], REPORT["category_split"]["anchor"])
    finally:
        ssh(f"docker exec postgres_n8n dropdb -U admin --force {throwaway}")
    remaining = sql("postgres", "SELECT string_agg(datname, ',' ORDER BY datname) "
                                "FROM pg_database WHERE datistemplate = false")
    REPORT["databases_after"] = remaining
    check("only the live database and postgres remain", remaining, "epe_2026,postgres")

    # ── period state and the data tables ────────────────────────────────────
    period = jsql("epe_2026", """
      SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.id), '[]') FROM (
        SELECT id, name, period_type, status, is_active,
               (evaluation_started_at IS NULL) AS gate_unpressed,
               evaluation_started_by
        FROM performance_db.evaluation_periods) p""")
    REPORT["periods"] = period
    h1 = next(p for p in period if p["id"] == 2)
    check("H1 is still active", [h1["status"], h1["is_active"]], ["active", True])
    check("the second gate is still unpressed", h1["gate_unpressed"], True)
    check("no period has been started at all",
          [p["gate_unpressed"] for p in period], [True, True, True])

    counts = sql("epe_2026", """
      SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
             (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
             (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
             (SELECT count(*) FROM performance_db.period_results)""")
    REPORT["data_tables"] = counts
    check("the four data tables are still empty", counts, "0/0/0/0")

    check("the employment event log holds only the owner's three terminations",
          int(sql("epe_2026", "SELECT count(*) FROM performance_db.employment_events")), 3)
    check("THE SCOPE EVENT LOG IS EMPTY — nobody was excluded by this brief",
          int(sql("epe_2026", "SELECT count(*) FROM performance_db.period_scope_events")), 0)
    check("migration 016 is on live",
          int(sql("epe_2026", "SELECT count(*) FROM information_schema.tables "
                              "WHERE table_schema='performance_db' "
                              "AND table_name='period_scope_events'")), 1)
    check("and nobody carries the new exclusion reason",
          int(sql("epe_2026", "SELECT count(*) FROM performance_db.evaluation_period_participants "
                              "WHERE exclusion_reason = 'excluded_by_admin'")), 0)
    check("no extension was created on live",
          sql("epe_2026", "SELECT string_agg(extname, ',' ORDER BY extname) FROM pg_extension"),
          "plpgsql")

    # ── 4. the read surface, with a real token ──────────────────────────────
    secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
    if not secret:
        raise SystemExit("could not read JWT_SIGNING_SECRET from the live container")
    sessions_before = int(sql("epe_2026", "SELECT count(*) FROM performance_db.auth_sessions"))
    REPORT["auth_sessions_before"] = sessions_before
    version = int(sql("epe_2026", f"SELECT token_version FROM performance_db.users WHERE id = {ADMIN_ID}"))
    sql("epe_2026", f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{PROBE_JTI}', {ADMIN_ID}, {version}, now(), now() + interval '1 hour')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
    token = mint(secret, ADMIN_ID, PROBE_JTI)
    try:
        status, body = call("GET", "api/admin-users-data", token)
        REPORT["admin_users_data"] = {"status": status, "count": len(body.get("users", []))
                                      if isinstance(body, dict) else None}
        check("the admin list answers 200", status, 200)
        rows = body["users"]
        check("with all 89 people", len(rows), 89)
        check("every row still carries the termination columns",
              sorted({("terminated_at" in r) and ("termination_date" in r) for r in rows}), [True])
        check("exactly three of them are set — the owner's, untouched",
              sum(1 for r in rows if r["terminated_at"] is not None), 3)
        check("no terminated person is filtered out of the payload — the page filters, not the route",
              len(rows), 89)
        managers = body["options"]["managers"]
        REPORT["manager_options"] = len(managers)
        check("the manager option list is non-empty", len(managers) > 0, True)

        status, body = call("GET", "api/admin/employment-events", token)
        REPORT["employment_events"] = {"status": status,
                                       "count": len((body or {}).get("events") or [])}
        check("the employment event log route answers 200", status, 200)
        check("and holds the owner's three terminations",
              len((body or {}).get("events") or []), 3)

        status, body = call("GET", "api/admin/period-scope-events", token)
        REPORT["period_scope_events_route"] = {"status": status, "body": body}
        check("the NEW scope event route answers 200", status, 200)
        check("and is empty — nobody was excluded", (body or {}).get("events"), [])

        status, body = call("GET", "api/periods", token)
        h1 = next(p for p in body["data"] if int(p["id"]) == 2)
        REPORT["periods_route"] = h1
        check("the periods route still reports H1 active", h1["status"], "active")
        check("still not started", h1["evaluation_started"], False)
        check("84 in scope of 89 — 87 minus the owner's three terminations",
              [h1["in_scope_count"], h1["participant_count"]], [84, 89])

        status, body = call("GET", "api/employees", token)
        REPORT["employees_route"] = {"status": status,
                                     "campaign_active": (body or {}).get("campaign_active"),
                                     "period_in_preparation": (body or {}).get("period_in_preparation")}
        check("the employees route answers 200", status, 200)
        check("campaign is still not running", (body or {}).get("campaign_active"), False)
        check("and the period reads as in preparation",
              (body or {}).get("period_in_preparation"), True)

        # The three new routes, unauthenticated, through Caddy.
        unauth = {}
        for method, path in (("POST", "api/admin/exclude-participant"),
                             ("POST", "api/admin/include-participant"),
                             ("GET", "api/admin/period-scope-events")):
            code, payload = call(method, path, "not-a-token")
            unauth[path] = {"status": code, "error": (payload or {}).get("error")
                            if isinstance(payload, dict) else None}
        REPORT["new_routes_unauthenticated"] = unauth
        check("all three new routes refuse a bad token",
              sorted({v["status"] for v in unauth.values()}), [401])
    finally:
        sql("epe_2026", f"DELETE FROM performance_db.auth_sessions WHERE jti = '{PROBE_JTI}'")
        sessions_after = int(sql("epe_2026", "SELECT count(*) FROM performance_db.auth_sessions"))
        REPORT["auth_sessions_after"] = sessions_after
        check("the probe session was removed", sessions_after, sessions_before)

    REPORT["failures"] = FAILURES
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n")
    passed = sum(1 for c in REPORT["checks"] if c["ok"])
    print(f"\nchecks: {passed}/{len(REPORT['checks'])} passed")
    print(f"report: {out}")
    if FAILURES:
        print("\nFAILURES:")
        for failure in FAILURES:
            print("  -", failure)
        raise SystemExit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()

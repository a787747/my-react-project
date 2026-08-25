#!/usr/bin/env python3
"""D-0825-11 — take the four post-31-March hires out of H1-2026 scope (2026-08-25).

The owner's decision: a person hired after 2026-03-31 is out of scope of H1-2026,
because less than three months of the period worked is too little to judge. By the
marking sheet that is exactly four people — 25, 64, 22, 63.

This script does NOT decide who. It verifies that live agrees with the sheet, and
refuses to write if it does not. Every write goes through the real
`POST /api/admin/exclude-participant` route built by D-0825-10; no SQL write of any
kind is issued here.

Preconditions asserted before the first write (any failure aborts before writing):

  * H1 (id 2) is `active`, `evaluation_started_at` is NULL on all three periods;
  * the four data tables are empty;
  * the four named people are in scope of period 2, reason NULL, not terminated,
    and each carries a join date strictly after 2026-03-31;
  * NOBODY ELSE in scope of period 2 carries a join date after 2026-03-31 — so the
    rule and the list of names agree, and the list is not a hand-picked subset;
  * `period_scope_events` is empty and nobody carries `excluded_by_admin`.

After the writes, a full cell-by-cell diff over every user row and every
participants row proves that only the four intended rows moved.

Read-only by default. Pass --apply to write.
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
PROBE_JTI = "caf10000-2026-0825-8000-000000000017"
H1 = 2
CUTOFF = "2026-03-31"

# The owner's four, from docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md.
TARGETS = [
    (25, "David Asatryan", "2026-04-09"),
    (64, "Mive Atayeva", "2026-04-27"),
    (22, "Muhammet-Ali Chariyev", "2026-05-01"),
    (63, "Merjen Jumayeva", "2026-05-01"),
]
NOTE = ("принят(а) после 31 марта 2026 — менее трёх месяцев в периоде H1; "
        "оценка со второго полугодия (D-0825-11)")

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


def call(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{ORIGIN}/webhook/{path.lstrip('/')}", data=data, headers=headers, method=method)
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


USERS_SNAPSHOT = """
  SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM (
    SELECT id, full_name, email, role::text AS role, job_title, work_category::text AS work_category,
           is_project_participant, department_id, grade_id, manager_id, has_subordinates,
           can_evaluate, can_be_evaluated, token_version, employment_type,
           join_date::text AS join_date, salary_current::text AS salary_current,
           salary_proposed::text AS salary_proposed, created_at::text AS created_at,
           (password_hash IS NOT NULL) AS has_password,
           terminated_at::text AS terminated_at, termination_date::text AS termination_date
    FROM performance_db.users u) u"""

PARTICIPANTS_SNAPSHOT = """
  SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.period_id, p.user_id), '[]') FROM (
    SELECT period_id, user_id, is_in_scope, exclusion_reason,
           created_at::text AS created_at, updated_at::text AS updated_at
    FROM performance_db.evaluation_period_participants) p"""


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
    parser.add_argument("--apply", action="store_true",
                        help="actually call the exclusion route (default: verify only)")
    parser.add_argument("--out", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "hiredate_exclusions.json"))
    args = parser.parse_args()

    REPORT["mode"] = "apply" if args.apply else "verify-only"
    REPORT["utc_at_start"] = ssh("date -u +%Y-%m-%dT%H:%M:%SZ")

    # ── 1. preconditions ────────────────────────────────────────────────────
    periods = jsql("epe_2026", """
      SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.id), '[]') FROM (
        SELECT id, name, status, is_active, evaluation_started_at::text AS started,
               start_date::text AS start_date, end_date::text AS end_date
        FROM performance_db.evaluation_periods) p""")
    REPORT["periods_before"] = periods
    h1 = next(p for p in periods if p["id"] == H1)
    check("H1 is the active period", [h1["status"], h1["is_active"]], ["active", True])
    check("the second gate is unpressed on every period",
          [p["started"] for p in periods], [None, None, None])
    check("H1 runs 2026-01-01..2026-06-30",
          [h1["start_date"], h1["end_date"]], ["2026-01-01", "2026-06-30"])

    counts = jsql("epe_2026", """
      SELECT json_build_object(
        'evaluations', (SELECT count(*) FROM performance_db.evaluations),
        'evaluation_scores', (SELECT count(*) FROM performance_db.evaluation_scores),
        'score_corrections', (SELECT count(*) FROM performance_db.score_corrections),
        'period_results', (SELECT count(*) FROM performance_db.period_results),
        'scope_events', (SELECT count(*) FROM performance_db.period_scope_events),
        'excluded_by_admin', (SELECT count(*) FROM performance_db.evaluation_period_participants
                              WHERE exclusion_reason = 'excluded_by_admin'),
        'users', (SELECT count(*) FROM performance_db.users),
        'terminated', (SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL),
        'in_scope_h1', (SELECT count(*) FROM performance_db.evaluation_period_participants
                        WHERE period_id = 2 AND is_in_scope))""")
    REPORT["counts_before"] = counts
    check("the four data tables are empty",
          [counts["evaluations"], counts["evaluation_scores"],
           counts["score_corrections"], counts["period_results"]], [0, 0, 0, 0])
    check("nobody has been excluded by hand yet",
          [counts["scope_events"], counts["excluded_by_admin"]], [0, 0])
    check("89 users, 3 terminated, 84 in scope of H1",
          [counts["users"], counts["terminated"], counts["in_scope_h1"]], [89, 3, 84])

    # The rule, computed on live — not the list of names.
    by_rule = jsql("epe_2026", f"""
      SELECT COALESCE(json_agg(json_build_object('id', u.id, 'name', u.full_name,
                                                 'join_date', u.join_date::text)
                               ORDER BY u.join_date, u.id), '[]')
      FROM performance_db.users u
      JOIN performance_db.evaluation_period_participants p
        ON p.user_id = u.id AND p.period_id = {H1} AND p.is_in_scope
      WHERE u.join_date > '{CUTOFF}'::date""")
    REPORT["rule_yields"] = by_rule
    check("the hire-date rule yields exactly the owner's four, by id",
          sorted(r["id"] for r in by_rule), sorted(t[0] for t in TARGETS))
    check("and their names and hire dates match the marking sheet",
          sorted((r["id"], r["name"], r["join_date"]) for r in by_rule),
          sorted(TARGETS))

    targets_now = jsql("epe_2026", f"""
      SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.id), '[]') FROM (
        SELECT u.id, u.full_name, u.join_date::text AS join_date,
               u.terminated_at::text AS terminated_at, p.is_in_scope, p.exclusion_reason
        FROM performance_db.users u
        JOIN performance_db.evaluation_period_participants p
          ON p.user_id = u.id AND p.period_id = {H1}
        WHERE u.id IN ({','.join(str(t[0]) for t in TARGETS)})) t""")
    REPORT["targets_before"] = targets_now
    check("all four are in scope, reason NULL, employed",
          [[t["is_in_scope"], t["exclusion_reason"], t["terminated_at"]] for t in targets_now],
          [[True, None, None]] * 4)

    # The six other 2026 hires that must NOT move.
    untouched = jsql("epe_2026", f"""
      SELECT COALESCE(json_agg(json_build_object('id', u.id, 'name', u.full_name,
               'join_date', u.join_date::text, 'in_scope', p.is_in_scope,
               'reason', p.exclusion_reason) ORDER BY u.id), '[]')
      FROM performance_db.users u
      JOIN performance_db.evaluation_period_participants p
        ON p.user_id = u.id AND p.period_id = {H1}
      WHERE u.join_date >= '2026-01-01' AND u.join_date <= '{CUTOFF}'::date""")
    REPORT["other_2026_hires"] = untouched
    check("seven other people were hired in 2026 on or before the cutoff",
          len(untouched), 7)
    check("six of them are in H1 scope; the seventh is the owner's terminated leaver",
          [sum(1 for r in untouched if r["in_scope"]),
           sorted(r["reason"] for r in untouched if not r["in_scope"])],
          [6, ["terminated"]])

    users_before = jsql("epe_2026", USERS_SNAPSHOT)
    parts_before = jsql("epe_2026", PARTICIPANTS_SNAPSHOT)
    REPORT["snapshot_sizes"] = {"users": len(users_before), "participants": len(parts_before)}

    if FAILURES:
        print("PRECONDITIONS FAILED — nothing was written:")
        for f in FAILURES:
            print("  ✗", f)
        raise SystemExit(1)

    if not args.apply:
        print("preconditions all pass; re-run with --apply to write")
        REPORT["applied"] = False
    else:
        # ── 2. the writes, through the real route ───────────────────────────
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
        responses = []
        try:
            for uid, name, join in TARGETS:
                status, body = call("POST", "api/admin/exclude-participant", token,
                                    {"period_id": H1, "user_id": uid, "note": NOTE})
                responses.append({"id": uid, "name": name, "status": status, "body": body})
                check(f"exclude {uid} {name} answers 200", status, 200)
        finally:
            sql("epe_2026", f"DELETE FROM performance_db.auth_sessions WHERE jti = '{PROBE_JTI}'")
        REPORT["responses"] = responses
        sessions_after = int(sql("epe_2026", "SELECT count(*) FROM performance_db.auth_sessions"))
        check("the probe session was cleaned up", sessions_after, sessions_before)
        REPORT["applied"] = True

        # ── 3. drift, cell by cell ──────────────────────────────────────────
        users_after = jsql("epe_2026", USERS_SNAPSHOT)
        parts_after = jsql("epe_2026", PARTICIPANTS_SNAPSHOT)
        user_moves = diff_rows(users_before, users_after, ("id",))
        REPORT["user_cell_diff"] = user_moves
        REPORT["user_cells_compared"] = len(users_before) * (len(users_before[0]) if users_before else 0)
        check("not one cell of the users table moved", user_moves, [])

        part_moves = diff_rows(parts_before, parts_after, ("period_id", "user_id"))
        REPORT["participants_cell_diff"] = part_moves
        REPORT["participant_cells_compared"] = (
            len(parts_before) * (len(parts_before[0]) if parts_before else 0))
        check("exactly four participants rows moved",
              sorted(m["key"] for m in part_moves),
              sorted([H1, t[0]] for t in TARGETS))
        check("and every one of them moved only period 2",
              sorted({m["key"][0] for m in part_moves}), [H1])
        check("each moved row went in-scope -> excluded_by_admin, and moved nothing else",
              sorted([sorted(m["cells"].keys()) for m in part_moves]),
              sorted([["exclusion_reason", "is_in_scope", "updated_at"]] * 4))
        check("the new value of every one is (false, excluded_by_admin)",
              sorted([[m["cells"]["is_in_scope"][1], m["cells"]["exclusion_reason"][1]]
                      for m in part_moves]),
              [[False, "excluded_by_admin"]] * 4)

        # ── 4. invariants after ─────────────────────────────────────────────
        after = jsql("epe_2026", """
          SELECT json_build_object(
            'evaluations', (SELECT count(*) FROM performance_db.evaluations),
            'evaluation_scores', (SELECT count(*) FROM performance_db.evaluation_scores),
            'score_corrections', (SELECT count(*) FROM performance_db.score_corrections),
            'period_results', (SELECT count(*) FROM performance_db.period_results),
            'scope_events', (SELECT count(*) FROM performance_db.period_scope_events),
            'users', (SELECT count(*) FROM performance_db.users),
            'terminated', (SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL),
            'in_scope_h1', (SELECT count(*) FROM performance_db.evaluation_period_participants
                            WHERE period_id = 2 AND is_in_scope),
            'in_scope_annual', (SELECT count(*) FROM performance_db.evaluation_period_participants
                                WHERE period_id = 5 AND is_in_scope),
            'started', (SELECT count(*) FROM performance_db.evaluation_periods
                        WHERE evaluation_started_at IS NOT NULL))""")
        REPORT["counts_after"] = after
        check("H1 in scope is now 80", after["in_scope_h1"], 80)
        check("the annual container is untouched at 86", after["in_scope_annual"], 86)
        check("still 89 users and 3 terminated",
              [after["users"], after["terminated"]], [89, 3])
        check("the four data tables are still empty",
              [after["evaluations"], after["evaluation_scores"],
               after["score_corrections"], after["period_results"]], [0, 0, 0, 0])
        check("four scope events were appended", after["scope_events"], 4)
        check("the second gate is still unpressed", after["started"], 0)

        events = jsql("epe_2026", """
          SELECT COALESCE(json_agg(row_to_json(e) ORDER BY e.id), '[]') FROM (
            SELECT id, period_id, user_id, event_type, reason, actor_id, note
            FROM performance_db.period_scope_events) e""")
        REPORT["scope_events"] = events
        check("every event is an exclusion of period 2 by the admin, with the reason",
              sorted([[e["period_id"], e["event_type"], e["reason"], e["actor_id"]]
                      for e in events]),
              sorted([[H1, "excluded", "excluded_by_admin", ADMIN_ID]] * 4))
        check("each carries the owner's note", sorted({e["note"] for e in events}), [NOTE])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    REPORT["failures"] = FAILURES
    REPORT["utc_at_end"] = ssh("date -u +%Y-%m-%dT%H:%M:%SZ")
    out.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False))

    passed = sum(1 for c in REPORT.get("checks", []) if c["ok"])
    total = len(REPORT.get("checks", []))
    print(f"{passed}/{total} checks passed → {out}")
    for f in FAILURES:
        print("  ✗", f)
    raise SystemExit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

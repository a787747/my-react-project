#!/usr/bin/env python3
"""HIRE_DATE_AND_SCOPE_TOGGLE stand proof, including the two real closes."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent
ADMIN = 1601
PERIOD = 2
FAILURES: list[str] = []
REPORT: dict[str, Any] = {"checks": []}
MONEY_COLUMNS = [
    "is_in_scope", "has_data", "rating_manager", "rating_upward",
    "rating_c_level_direct", "rating_self", "final_rating", "bonus_index",
]


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} "
         "-v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def jsql(database: str, statement: str) -> Any:
    return json.loads(sql(database, statement) or "null")


def check(name: str, actual: Any, expected: Any) -> None:
    ok = actual == expected
    REPORT["checks"].append(
        {"name": name, "actual": actual, "expected": expected, "ok": ok})
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(database: str, secret: str, port: int, user_id: int) -> str:
    jti = str(uuid.uuid5(uuid.NAMESPACE_URL, f"hire-scope/{port}/{user_id}"))
    version = int(sql(
        database,
        f"SELECT token_version FROM performance_db.users WHERE id={user_id}"))
    sql(database, f"""
      INSERT INTO performance_db.auth_sessions
        (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{jti}', {user_id}, {version}, now(), now() + interval '3 hours')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '3 hours'
    """)
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 7200, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def call(port: int, token: str, method: str, path: str,
         body: dict[str, Any] | None = None) -> tuple[int, Any]:
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhook/{path.lstrip('/')}",
        data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def fresh_payload(database: str, user_id: int, **changes: Any) -> dict[str, Any]:
    row = jsql(database, f"""
      SELECT row_to_json(u) FROM (
        SELECT id, full_name, email, job_title, role, work_category,
               department_id, grade_id, manager_id,
               to_char(join_date, 'YYYY-MM-DD') AS join_date
        FROM performance_db.users WHERE id={user_id}
      ) u
    """)
    row.update(changes)
    return row


def participant(database: str, user_id: int, period_id: int = PERIOD) -> dict[str, Any]:
    return jsql(database, f"""
      SELECT row_to_json(x) FROM (
        SELECT is_in_scope, exclusion_reason, scope_override
        FROM performance_db.evaluation_period_participants
        WHERE period_id={period_id} AND user_id={user_id}
      ) x
    """)


def save_date(port: int, database: str, token: str, user_id: int,
              join_date: str | None) -> tuple[int, Any]:
    return call(
        port, token, "POST", "admin/save-user",
        fresh_payload(database, user_id, join_date=join_date or ""))


def close(port: int, token: str) -> tuple[int, Any]:
    return call(port, token, "POST", "api/periods/close", {"period_id": PERIOD})


RESULTS_SQL = """
  SELECT COALESCE(json_agg(row_to_json(r) ORDER BY r.user_id), '[]') FROM (
    SELECT user_id, is_in_scope, has_data,
           rating_manager::text, rating_upward::text,
           rating_c_level_direct::text, rating_self::text,
           final_rating::text, bonus_index::text
    FROM performance_db.period_results
    WHERE period_id = 2
  ) r
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        default=str(REPO / "backups/2026-08-26-hiredate-scope/throwaway_env.json"))
    parser.add_argument(
        "--out",
        default=str(REPO / "backups/2026-08-26-hiredate-scope/proof.json"))
    args = parser.parse_args()
    env = json.loads(Path(args.env).read_text())
    ctl, trt = env["database_control"], env["database_treatment"]
    old_port, new_port = env["port_old"], env["port_new"]
    secret = env["jwt_secret"]
    token_ctl = mint(ctl, secret, old_port, ADMIN)
    token_trt = mint(trt, secret, new_port, ADMIN)

    check("both stands start with migration 017",
          [sql(ctl, "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='performance_db' "
                    "AND table_name='employee_card_events'"),
           sql(trt, "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='performance_db' "
                    "AND table_name='employee_card_events'")],
          ["1", "1"])
    check("stand gate is pressed, live-like campaign route is open",
          sql(trt, "SELECT evaluation_started_at IS NOT NULL "
                   "FROM performance_db.evaluation_periods WHERE id=2"), "t")

    # A partial body can no longer demote a manager or move their category.
    before_1602 = fresh_payload(trt, 1602)
    status, body = call(new_port, token_trt, "POST", "admin/save-user", {
        "id": 1602, "full_name": before_1602["full_name"],
        "email": before_1602["email"],
    })
    check("partial whole-row update is refused", [status, body.get("error")],
          [422, "INCOMPLETE_USER_ROW"])
    check("partial refusal leaves the row byte-identical",
          fresh_payload(trt, 1602), before_1602)

    # Wrong date -> H1 out, Annual unchanged; empty -> both open periods out;
    # restored date -> both in. Every response names every period.
    status, first = save_date(new_port, trt, token_trt, 1613, "2026-04-09")
    REPORT["no_date_to_late"] = {"status": status, "body": first}
    check("wrong date save succeeds", status, 200)
    outcomes = {row["period_id"]: row["outcome"] for row in first["scope_results"]}
    check("wrong date states the result for H1, Annual 2026 and closed Annual 2025",
          outcomes,
          {1: "closed_untouched", 2: "excluded_by_date", 5: "unchanged_in_scope"})
    check("H1 follows the late date",
          participant(trt, 1613),
          {"is_in_scope": False, "exclusion_reason": "insufficient_tenure",
           "scope_override": None})

    status, emptied = save_date(new_port, trt, token_trt, 1613, None)
    REPORT["late_to_empty"] = {"status": status, "body": emptied}
    check("date can be set empty", status, 200)
    check("empty date is explicit on the card",
          sql(trt, "SELECT join_date IS NULL FROM performance_db.users WHERE id=1613"), "t")
    check("empty date moves Annual 2026 out too",
          participant(trt, 1613, 5),
          {"is_in_scope": False, "exclusion_reason": "join_date_missing",
           "scope_override": None})

    status, restored = save_date(new_port, trt, token_trt, 1613, "2025-03-01")
    REPORT["empty_to_restored"] = {"status": status, "body": restored}
    check("date can be restored", status, 200)
    check("restored date brings H1 and Annual 2026 in",
          [participant(trt, 1613), participant(trt, 1613, 5)],
          [{"is_in_scope": True, "exclusion_reason": None, "scope_override": None},
           {"is_in_scope": True, "exclusion_reason": None, "scope_override": None}])

    # Manual off/on on a no-data person. Inclusion leaves a durable manual mark.
    status_off, off = call(new_port, token_trt, "POST",
                           "api/admin/exclude-participant",
                           {"user_id": 1608, "period_id": 2})
    status_on, on = call(new_port, token_trt, "POST",
                         "api/admin/include-participant",
                         {"user_id": 1608, "period_id": 2})
    REPORT["manual_toggle"] = {
        "off": {"status": status_off, "body": off},
        "on": {"status": status_on, "body": on},
    }
    check("manual toggle off and on both succeed", [status_off, status_on], [200, 200])
    check("manual on is durable state, not an unmarked default",
          participant(trt, 1608),
          {"is_in_scope": True, "exclusion_reason": None,
           "scope_override": "included_by_admin"})

    # Existing evaluation means hard refusal: there is no confirmation escape.
    before_1603 = participant(trt, 1603)
    status, refused = call(new_port, token_trt, "POST",
                           "api/admin/exclude-participant",
                           {"user_id": 1603, "period_id": 2,
                            "confirm_existing_evaluations": True})
    REPORT["manual_refusal"] = {"status": status, "body": refused}
    check("even a legacy confirmation flag cannot bypass the refusal",
          [status, refused.get("error")], [409, "HAS_EVALUATIONS"])
    check("refusal lists received/self/given/corrections",
          [refused.get("evaluations_received"), refused.get("self_reviews"),
           refused.get("evaluations_given"), refused.get("corrections_about")],
          [2, 1, 1, 0])
    check("refusal changes no scope state", participant(trt, 1603), before_1603)

    # A manually excluded person stays excluded even when the date says IN.
    status, manual = save_date(new_port, trt, token_trt, 1614, "2025-01-01")
    REPORT["manual_precedence"] = {"status": status, "body": manual}
    manual_outcomes = {row["period_id"]: row["outcome"]
                       for row in manual["scope_results"]}
    check("manual exclusion is named as preserved", manual_outcomes[2],
          "manual_preserved")
    check("manual exclusion remains byte-for-byte in scope state",
          participant(trt, 1614),
          {"is_in_scope": False, "exclusion_reason": "excluded_by_admin",
           "scope_override": None})
    # Restore the card value; it must still preserve the manual mark.
    save_date(new_port, trt, token_trt, 1614, "2026-04-09")

    # Money treatment: date-derived OUT + stored score -> corrected date brings
    # IN (allowed; destroys nothing). Control remains OUT.
    status, money = save_date(new_port, trt, token_trt, 1607, "2025-03-01")
    REPORT["money_recompute"] = {"status": status, "body": money}
    check("bringing a scored person into scope is allowed", status, 200)
    check("money subject is now in H1 by date",
          participant(trt, 1607),
          {"is_in_scope": True, "exclusion_reason": None, "scope_override": None})
    check("control subject stays date-derived out",
          participant(ctl, 1607),
          {"is_in_scope": False, "exclusion_reason": "hired_after_period_end",
           "scope_override": None})

    # Unified event reader: all actions have actor and time.
    status, event_body = call(
        new_port, token_trt, "GET", "api/admin/employee-events?user_id=1613")
    REPORT["events_1613"] = {"status": status, "body": event_body}
    check("unified event reader answers", status, 200)
    check("three card edits are readable", len([
        event for event in event_body["events"] if event["source"] == "card"
    ]), 3)
    check("every returned action carries actor and time",
          all(event.get("actor_id") == ADMIN and event.get("occurred_at")
              for event in event_body["events"]), True)

    # Evaluations themselves never moved.
    fp_sql = """
      SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (
        SELECT concat_ws(':', e.id, e.subject_id, e.evaluator_id, e.period_id,
          e.calculated_score, e.evaluation_source, e.is_self_evaluation,
          s.criteria_id, s.score_value, s.comment) AS t
        FROM performance_db.evaluations e
        LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id=e.id
      ) x
    """
    check("evaluation rows remain byte-identical before close",
          sql(trt, fp_sql), sql(ctl, fp_sql))

    status_ctl, close_ctl = close(old_port, token_ctl)
    status_trt, close_trt = close(new_port, token_trt)
    REPORT["closes"] = {
        "control": {"status": status_ctl, "body": close_ctl},
        "treatment": {"status": status_trt, "body": close_trt},
    }
    check("both real close routes succeed", [status_ctl, status_trt], [200, 200])

    rows_ctl = {int(row["user_id"]): row for row in jsql(ctl, RESULTS_SQL)}
    rows_trt = {int(row["user_id"]): row for row in jsql(trt, RESULTS_SQL)}
    check("both closes freeze the same people", sorted(rows_ctl), sorted(rows_trt))

    moved = []
    for user_id in sorted(rows_ctl):
        cells = {
            column: [rows_ctl[user_id][column], rows_trt[user_id][column]]
            for column in MONEY_COLUMNS
            if rows_ctl[user_id][column] != rows_trt[user_id][column]
        }
        if cells:
            moved.append({"user_id": user_id, "cells": cells})
    REPORT["money_cells_compared"] = len(rows_ctl) * len(MONEY_COLUMNS)
    REPORT["moved_rows"] = moved
    check("only the date-corrected money subject moves",
          [row["user_id"] for row in moved], [1607])
    check("affected frozen row equals hand arithmetic",
          rows_trt[1607],
          {"user_id": 1607, "is_in_scope": True, "has_data": True,
           "rating_manager": "6.00", "rating_upward": None,
           "rating_c_level_direct": None, "rating_self": None,
           "final_rating": "6.0000", "bonus_index": "5.9400"})
    check("control freezes the same person out with no number",
          rows_ctl[1607],
          {"user_id": 1607, "is_in_scope": False, "has_data": False,
           "rating_manager": None, "rating_upward": None,
           "rating_c_level_direct": None, "rating_self": None,
           "final_rating": None, "bonus_index": None})
    pool_ctl = sum(Decimal(row["bonus_index"]) for row in rows_ctl.values()
                   if row["bonus_index"] is not None)
    pool_trt = sum(Decimal(row["bonus_index"]) for row in rows_trt.values()
                   if row["bonus_index"] is not None)
    check("pool difference is exactly the hand index",
          str(pool_trt - pool_ctl), "5.9400")

    REPORT["failures"] = FAILURES
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
    passed = len(REPORT["checks"]) - len(FAILURES)
    print(f"{passed}/{len(REPORT['checks'])} checks passed -> {output}")
    for failure in FAILURES:
        print("  x", failure)
    raise SystemExit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

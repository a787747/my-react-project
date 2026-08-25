#!/usr/bin/env python3
"""Prove the TERMINATED_EMPLOYEES build on the throwaway stand (D-0825-7).

Everything below runs against the two stand databases built by
scripts/setup_termination_throwaway.sh. Live epe_2026 is never contacted.

What this proves, in order:

  A. The state before: who is in scope, who has which task, what the counters
     read, and a byte-level fingerprint of every evaluation row.
  B. The refusals, each by name — direct reports (with the message the owner
     will see), self-termination, unknown user, bad date, non-admin caller,
     reinstating somebody who was never terminated.
  C. Termination: the person leaves every list, cannot log in, cannot be let
     back in by the shared invite, is out of scope with a reason and a date,
     their evaluators' task lists lose them, and the campaign counter drops.
  D. Every evaluation row is byte-identical before and after.
  E. Reinstatement restores the state exactly — including NOT clobbering an
     exclusion that was there for a different reason.
  F. The money: the same period closed twice from two copies of one dump, one
     with the termination and one without. The ratings of the people the
     terminated person evaluated must match to the digit; their own result and
     their share of the pool must be gone.

A proof artifact records the compared values, never a slogan: every check
below stores what it saw on both sides, and a run that compared nothing fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
SSH_ID = str(Path.home() / ".ssh/id_ed25519")
REPO = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:25679/webhook"
CONTAINER = "epe-term-n8n"
FIXTURE_PASSWORD = "Term2026-Portal!"

ADMIN, MANAGER, LEAVER = 1501, 1502, 1503
STAYER_A, STAYER_B, CLEVEL = 1504, 1505, 1506
NEWCOMER, UNREG_LEAVER, UNREG_STAYER = 1507, 1508, 1509
PERIOD = 2
TERMINATION_DATE = "2026-08-20"

FROZEN_COLUMNS = ["employment_type", "join_date", "salary_current", "salary_proposed",
                  "created_at", "password_hash", "can_evaluate", "can_be_evaluated"]

FAILURES: list[str] = []
PROOF: dict[str, Any] = {}


# ── plumbing ────────────────────────────────────────────────────────────────

def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", SSH_ID, HOST, command],
        capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", SSH_ID, HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def jsql(database: str, statement: str) -> Any:
    return json.loads(sql(database, statement) or "null")


def call(method: str, path: str, token: str | None = None,
         body: Any = None, query: str = "") -> tuple[int, Any]:
    url = f"{BASE}/{path.lstrip('/')}{query}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def login(email: str) -> tuple[int, str | None, Any]:
    status, body = call("POST", "auth/login",
                        body={"email": email, "password": FIXTURE_PASSWORD})
    token = body.get("token") if status == 200 and isinstance(body, dict) else None
    return status, token, body


def check(name: str, actual: Any, expected: Any) -> bool:
    ok = actual == expected
    PROOF.setdefault("checks", []).append(
        {"name": name, "expected": expected, "actual": actual, "ok": ok})
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


# ── stand readers ───────────────────────────────────────────────────────────

def evaluations_fingerprint(database: str) -> dict[str, Any]:
    """Every evaluation and every score row, as data and as one md5."""
    rows = jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(t) ORDER BY t.evaluation_id, t.criteria_id), '[]') FROM (
        SELECT e.id AS evaluation_id, e.subject_id, e.evaluator_id, e.period_id,
               e.calculated_score::text, e.weighted_score::text, e.evaluation_source,
               e.is_self_evaluation, e.status, e.general_comment,
               e.updated_at::text,
               s.id AS score_id, s.criteria_id, s.score_value, s.comment
        FROM performance_db.evaluations e
        LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) t""")
    blob = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    return {"md5": hashlib.md5(blob.encode()).hexdigest(),
            "row_count": len(rows), "rows": rows}


def users_snapshot(database: str) -> dict[str, dict[str, Any]]:
    rows = jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM (
        SELECT id, full_name, email, role::text AS role, job_title, work_category,
               is_project_participant, department_id, grade_id, manager_id,
               has_subordinates, can_evaluate, can_be_evaluated, token_version,
               employment_type, join_date::text AS join_date,
               salary_current::text AS salary_current,
               salary_proposed::text AS salary_proposed,
               created_at::text AS created_at,
               (password_hash IS NOT NULL) AS password_hash,
               terminated_at::text AS terminated_at,
               termination_date::text AS termination_date
        FROM performance_db.users) u""")
    return {str(r["id"]): r for r in rows}


def participants(database: str) -> dict[str, dict[str, Any]]:
    rows = jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.period_id, p.user_id), '[]') FROM (
        SELECT period_id, user_id, is_in_scope, exclusion_reason
        FROM performance_db.evaluation_period_participants) p""")
    return {f"{r['period_id']}:{r['user_id']}": r for r in rows}


def employment_events(database: str) -> list[dict[str, Any]]:
    return jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(e) ORDER BY e.id), '[]') FROM (
        SELECT id, user_id, event_type, effective_date::text AS effective_date,
               period_id, actor_id, occurred_at::text AS occurred_at, note
        FROM performance_db.employment_events) e""")


def period_results(database: str) -> dict[str, dict[str, Any]]:
    rows = jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(r) ORDER BY r.user_id), '[]') FROM (
        SELECT period_id, user_id, is_in_scope, has_data,
               rating_manager::text, rating_upward::text,
               rating_c_level_direct::text, rating_self::text,
               final_rating::text, bonus_index::text
        FROM performance_db.period_results) r""")
    return {str(r["user_id"]): r for r in rows}


def diff_users(before: dict, after: dict) -> list[str]:
    changed = []
    for uid in sorted(set(before) | set(after), key=int):
        b, a = before.get(uid), after.get(uid)
        if b is None or a is None:
            changed.append(f"{uid}: row {'added' if b is None else 'removed'}")
            continue
        for column in sorted(set(b) | set(a)):
            if b.get(column) != a.get(column):
                changed.append(f"{uid}.{column}: {b.get(column)!r} -> {a.get(column)!r}")
    return changed


def repoint_stand(database: str, pgpass: str) -> None:
    """Point the stand n8n at another throwaway database and restart it."""
    credential = json.dumps([{
        "id": "VNbfkY8IKbEzn88B", "name": "EPE 2026 Postgres", "type": "postgres",
        "data": {"host": "postgres_n8n", "port": 5432, "database": database,
                 "user": "admin", "password": pgpass, "ssl": "disable",
                 "allowUnauthorizedCerts": False, "sshTunnel": False},
    }])
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-i", SSH_ID, HOST,
         f"docker exec -i {CONTAINER} sh -c 'cat > /tmp/cred.json'"],
        input=credential.encode(), check=True, capture_output=True)
    ssh(f"docker exec {CONTAINER} n8n import:credentials --input=/tmp/cred.json")
    ssh(f"docker exec {CONTAINER} rm -f /tmp/cred.json")
    ssh(f"docker restart {CONTAINER}")
    for _ in range(60):
        probe = ssh(f"docker exec {CONTAINER} sh -c "
                    f"'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null' || true")
        if "ok" in probe:
            time.sleep(3)
            return
        time.sleep(2)
    raise SystemExit("stand n8n did not come back up after repointing")


# ── the proof ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-db", required=True)
    parser.add_argument("--treatment-db", required=True)
    parser.add_argument("--out", default=str(REPO / "backups/2026-08-25-termination/termination_proof.json"))
    args = parser.parse_args()
    ctl, trt = args.control_db, args.treatment_db
    for name in (ctl, trt):
        if not name.startswith("epe_term_"):
            raise SystemExit(f"Refusing to run against a non-stand database: {name}")
    pgpass = ssh("docker exec postgres_n8n env | grep '^POSTGRES_PASSWORD=' | cut -d= -f2-")

    PROOF["stand"] = {"control_db": ctl, "treatment_db": trt, "base": BASE}

    # ── A. before ───────────────────────────────────────────────────────────
    evals_before = evaluations_fingerprint(trt)
    users_before = users_snapshot(trt)
    epp_before = participants(trt)
    PROOF["A_before"] = {
        "evaluations_md5": evals_before["md5"],
        "evaluation_row_count": evals_before["row_count"],
        "leaver_in_scope": epp_before[f"{PERIOD}:{LEAVER}"],
        "newcomer_in_scope": epp_before[f"{PERIOD}:{NEWCOMER}"],
    }
    check("A: leaver starts in scope", epp_before[f"{PERIOD}:{LEAVER}"]["is_in_scope"], True)
    check("A: newcomer starts excluded for hire date",
          epp_before[f"{PERIOD}:{NEWCOMER}"]["exclusion_reason"], "hired_after_period_end")
    check("A: no employment events yet", employment_events(trt), [])

    status, admin_token, _ = login("tm.admin@sedamedical.com")
    check("A: admin logs in", status, 200)
    status, manager_token, _ = login("tm.manager@sedamedical.com")
    check("A: manager logs in", status, 200)
    status, leaver_token, leaver_login = login("tm.leaver@sedamedical.com")
    check("A: leaver logs in before termination", status, 200)

    _, employees_before = call("GET", "api/employees", manager_token)
    manager_list_before = sorted(e["id"] for e in (employees_before or {}).get("data", []))
    PROOF["A_before"]["manager_task_list"] = manager_list_before
    check("A: manager's task list contains the leaver", LEAVER in manager_list_before, True)

    _, leaver_scope_before = call("GET", "api/employees", leaver_token)
    check("A: leaver is in scope on their own read",
          (leaver_scope_before or {}).get("actor_is_in_scope"), True)
    _, leaver_self_before = call("GET", "api/check-self-review", leaver_token)
    check("A: leaver has a self-review",
          (leaver_self_before or {}).get("has_self_review"), True)

    _, periods_before = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_before["data"] if int(p["id"]) == PERIOD)
    in_scope_before = int(row["in_scope_count"])
    PROOF["A_before"]["periods_in_scope_count"] = in_scope_before

    _, hr_before = call("GET", "api/hr/evaluation-status", admin_token)
    hr_rows_before = hr_before.get("employees") or []
    hr_ids_before = sorted(r["id"] for r in hr_rows_before)
    hr_count_before = int(hr_before["in_scope_count"])
    PROOF["A_before"]["hr_in_scope_count"] = hr_count_before
    check("A: HR status lists the leaver", LEAVER in hr_ids_before, True)

    _, admin_users_before = call("GET", "api/admin-users-data", admin_token)
    leaver_row_before = next(u for u in admin_users_before["users"] if u["id"] == LEAVER)
    check("A: admin list shows the leaver as employed",
          leaver_row_before["terminated_at"], None)
    managers_before = sorted(m["id"] for m in admin_users_before["options"]["managers"])
    check("A: the c_level fixture is offered as a manager", CLEVEL in managers_before, True)

    # ── B. refusals ─────────────────────────────────────────────────────────
    refusals = {}

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": MANAGER, "termination_date": TERMINATION_DATE})
    refusals["has_direct_reports"] = {"status": status, "body": body}
    check("B: terminating a person with direct reports is refused", status, 422)
    check("B: refusal names the reason", (body or {}).get("error"), "HAS_DIRECT_REPORTS")
    reported = sorted(r["id"] for r in (body or {}).get("reports", []))
    check("B: refusal lists the actual reports", reported, [LEAVER, STAYER_A, STAYER_B])
    PROOF["B_owner_message_direct_reports"] = (body or {}).get("message")

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": ADMIN, "termination_date": TERMINATION_DATE})
    refusals["self"] = {"status": status, "error": (body or {}).get("error")}
    check("B: self-termination is refused", (body or {}).get("error"), "CANNOT_TERMINATE_SELF")

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": 999999, "termination_date": TERMINATION_DATE})
    refusals["unknown_user"] = {"status": status, "error": (body or {}).get("error")}
    check("B: unknown user is a 404", status, 404)

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": LEAVER, "termination_date": "2026-02-31"})
    refusals["impossible_date"] = {"status": status, "error": (body or {}).get("error")}
    check("B: an impossible date is refused", (body or {}).get("error"), "INVALID_TERMINATION_DATE")

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": LEAVER})
    refusals["missing_date"] = {"status": status, "error": (body or {}).get("error")}
    check("B: a missing date is refused", (body or {}).get("error"), "INVALID_TERMINATION_DATE")

    status, body = call("POST", "api/admin/terminate-employee", manager_token,
                        {"user_id": STAYER_A, "termination_date": TERMINATION_DATE})
    refusals["non_admin"] = {"status": status, "error": (body or {}).get("error")}
    check("B: a manager cannot terminate anybody", status, 403)

    status, body = call("POST", "api/admin/terminate-employee", None,
                        {"user_id": STAYER_A, "termination_date": TERMINATION_DATE})
    refusals["no_token"] = {"status": status, "error": (body or {}).get("error")}
    check("B: an unauthenticated call is refused", status, 401)

    status, body = call("POST", "api/admin/reinstate-employee", admin_token,
                        {"user_id": STAYER_A})
    refusals["reinstate_not_terminated"] = {"status": status, "error": (body or {}).get("error")}
    check("B: reinstating somebody who was never terminated is refused",
          (body or {}).get("error"), "NOT_TERMINATED")

    PROOF["B_refusals"] = refusals
    check("B: nothing was written by any refusal",
          evaluations_fingerprint(trt)["md5"], evals_before["md5"])
    check("B: no refusal produced an employment event", employment_events(trt), [])
    check("B: no refusal changed a user row", diff_users(users_before, users_snapshot(trt)), [])

    # ── C. terminate ────────────────────────────────────────────────────────
    status, terminate_body = call("POST", "api/admin/terminate-employee", admin_token,
                                  {"user_id": LEAVER, "termination_date": TERMINATION_DATE,
                                   "note": "stand proof"})
    PROOF["C_terminate_response"] = {"status": status, "body": terminate_body}
    check("C: termination succeeds", status, 200)
    check("C: the live session was revoked",
          (terminate_body or {}).get("sessions_revoked", 0) >= 1, True)
    check("C: scoped out of both open periods",
          sorted((terminate_body or {}).get("scoped_out_period_ids", [])), [2, 5])

    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": LEAVER, "termination_date": TERMINATION_DATE})
    check("C: a second termination is refused, not repeated",
          (body or {}).get("error"), "ALREADY_TERMINATED")

    # D. the evaluation rows did not move.
    evals_after = evaluations_fingerprint(trt)
    PROOF["D_evaluations"] = {
        "md5_before": evals_before["md5"], "md5_after": evals_after["md5"],
        "row_count_before": evals_before["row_count"],
        "row_count_after": evals_after["row_count"],
    }
    check("D: every evaluation row is byte-identical after termination",
          evals_after["md5"], evals_before["md5"])
    check("D: no evaluation row was added or removed",
          evals_after["row_count"], evals_before["row_count"])

    # The person cannot get in.
    status, body = call("GET", "api/employees", leaver_token)
    PROOF["C_old_token"] = {"status": status, "error": (body or {}).get("error")}
    check("C: the token minted before termination is dead", status, 401)

    status, _, relogin = login("tm.leaver@sedamedical.com")
    # The control: a real account with a wrong password. The two refusals must
    # be the same words, or the login form becomes an oracle for who was fired.
    wrong_status, wrong_body = call("POST", "auth/login",
                                    body={"email": "tm.stayer.a@sedamedical.com",
                                          "password": "definitely-not-the-password"})
    PROOF["C_login"] = {"terminated": {"status": status, "body": relogin},
                        "wrong_password": {"status": wrong_status, "body": wrong_body}}
    check("C: a terminated employee cannot log in", status, 401)
    check("C: the refusal is indistinguishable from a wrong password",
          (relogin or {}).get("message"), (wrong_body or {}).get("message"))

    # Out of scope, with a reason, and nobody else's reason touched.
    epp_after = participants(trt)
    PROOF["C_scope"] = {
        "leaver_period_2": epp_after[f"{PERIOD}:{LEAVER}"],
        "leaver_period_5": epp_after.get(f"5:{LEAVER}"),
        "newcomer_period_2": epp_after[f"{PERIOD}:{NEWCOMER}"],
    }
    check("C: the leaver is out of scope on the active period",
          epp_after[f"{PERIOD}:{LEAVER}"]["is_in_scope"], False)
    check("C: with 'terminated' as the reason",
          epp_after[f"{PERIOD}:{LEAVER}"]["exclusion_reason"], "terminated")
    check("C: and out of scope on the draft container too",
          epp_after[f"5:{LEAVER}"]["exclusion_reason"], "terminated")
    check("C: the newcomer's own exclusion reason is untouched",
          epp_after[f"{PERIOD}:{NEWCOMER}"], epp_before[f"{PERIOD}:{NEWCOMER}"])
    other_scope_moved = [k for k in epp_before
                         if k not in (f"{PERIOD}:{LEAVER}", f"5:{LEAVER}")
                         and epp_before[k] != epp_after.get(k)]
    check("C: no other person's scope moved", other_scope_moved, [])

    # Their evaluators' lists lose them, and the counters drop.
    _, employees_after = call("GET", "api/employees", manager_token)
    manager_list_after = sorted(e["id"] for e in (employees_after or {}).get("data", []))
    PROOF["C_manager_task_list"] = {"before": manager_list_before, "after": manager_list_after}
    check("C: the manager's task list lost the leaver", LEAVER in manager_list_after, False)
    check("C: and lost exactly one person",
          len(manager_list_before) - len(manager_list_after), 1)
    check("C: the other reports are still there",
          manager_list_after, sorted(set(manager_list_before) - {LEAVER}))

    _, periods_after = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_after["data"] if int(p["id"]) == PERIOD)
    in_scope_after = int(row["in_scope_count"])
    PROOF["C_counters"] = {"periods_in_scope_before": in_scope_before,
                           "periods_in_scope_after": in_scope_after,
                           "participant_count": int(row["participant_count"])}
    check("C: the campaign counter drops by exactly one",
          in_scope_before - in_scope_after, 1)
    check("C: the participant count does not move — nothing was deleted",
          int(row["participant_count"]), len(users_before))

    _, hr_after = call("GET", "api/hr/evaluation-status", admin_token)
    hr_rows_after = hr_after.get("employees") or []
    hr_ids_after = sorted(r["id"] for r in hr_rows_after)
    hr_count_after = int(hr_after["in_scope_count"])
    PROOF["C_counters"]["hr_in_scope_before"] = hr_count_before
    PROOF["C_counters"]["hr_in_scope_after"] = hr_count_after
    check("C: HR completion counts against the smaller population",
          hr_count_before - hr_count_after, 1)
    check("C: the leaver is gone from the HR status list", LEAVER in hr_ids_after, False)
    manager_row = next(r for r in hr_rows_after if r["id"] == MANAGER)
    manager_row_before = next(r for r in hr_rows_before if r["id"] == MANAGER)
    PROOF["C_counters"]["manager_total_subordinates"] = {
        "before": int(manager_row_before["total_subordinates"]),
        "after": int(manager_row["total_subordinates"])}
    check("C: the manager is no longer expected to evaluate the leaver",
          int(manager_row_before["total_subordinates"]) - int(manager_row["total_subordinates"]), 1)

    # The record.
    events = employment_events(trt)
    PROOF["C_event"] = events
    check("C: exactly one event was recorded", len(events), 1)
    check("C: the event names the actor", events[0]["actor_id"], ADMIN)
    check("C: the event names the period", events[0]["period_id"], PERIOD)
    check("C: the event carries the owner's date", events[0]["effective_date"], TERMINATION_DATE)
    check("C: the event says what happened", events[0]["event_type"], "terminated")

    # The password path.
    reset_before = int(sql(trt, f"SELECT count(*) FROM performance_db.password_reset_tokens "
                                f"WHERE user_id = {LEAVER}"))
    status, body = call("POST", "api/request-password-reset",
                        body={"email": "tm.leaver@sedamedical.com"})
    reset_after = int(sql(trt, f"SELECT count(*) FROM performance_db.password_reset_tokens "
                               f"WHERE user_id = {LEAVER}"))
    status_ok, body_ok = call("POST", "api/request-password-reset",
                              body={"email": "tm.stayer.b@sedamedical.com"})
    reset_control = int(sql(trt, f"SELECT count(*) FROM performance_db.password_reset_tokens "
                                 f"WHERE user_id = {STAYER_B}"))
    PROOF["C_password_reset"] = {
        "terminated": {"status": status, "body": body,
                       "tokens_before": reset_before, "tokens_after": reset_after},
        "control": {"status": status_ok, "tokens_after": reset_control}}
    check("C: the reset request answers the same generic 200", status, 200)
    check("C: but no reset token is created for a terminated employee",
          reset_after, reset_before)
    check("C: an employed colleague still gets one — the route is not simply broken",
          reset_control, 1)

    # The shared-invite door.
    invite = sql(trt, "SELECT token FROM performance_db.invite_tokens "
                      "WHERE expires_at > now() ORDER BY id DESC LIMIT 1")
    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": UNREG_LEAVER, "termination_date": TERMINATION_DATE})
    check("C: the never-registered employee is terminated", status, 200)
    for uid, email in ((UNREG_LEAVER, "tm.unreg.leaver@sedamedical.com"),
                       (UNREG_STAYER, "tm.unreg.stayer@sedamedical.com")):
        sql(trt, f"""
          DELETE FROM performance_db.email_verification_codes WHERE lower(email) = '{email}';
          INSERT INTO performance_db.email_verification_codes
            (email, code, expires_at, is_verified, verified_at)
          VALUES ('{email}', '424242', now() + interval '1 hour', true, now());""")
    status_t, body_t = call("POST", "api/register",
                            body={"token": invite, "email": "tm.unreg.leaver@sedamedical.com",
                                  "password": "StandProof2026!", "verification_code": "424242"})
    status_c, body_c = call("POST", "api/register",
                            body={"token": invite, "email": "tm.unreg.stayer@sedamedical.com",
                                  "password": "StandProof2026!", "verification_code": "424242"})
    hash_t = sql(trt, f"SELECT (password_hash IS NOT NULL) FROM performance_db.users WHERE id = {UNREG_LEAVER}")
    hash_c = sql(trt, f"SELECT (password_hash IS NOT NULL) FROM performance_db.users WHERE id = {UNREG_STAYER}")
    PROOF["C_shared_invite"] = {
        "terminated": {"status": status_t, "body": body_t, "now_registered": hash_t},
        "control": {"status": status_c, "now_registered": hash_c}}
    check("C: the shared invite cannot register a terminated employee", status_t, 400)
    check("C: and no password was set for them", hash_t, "f")
    check("C: the same invite still works for an employed colleague", status_c, 200)
    check("C: whose password was set", hash_c, "t")

    # A terminated person is never offered as somebody's manager.
    status, _ = call("POST", "api/admin/terminate-employee", admin_token,
                     {"user_id": CLEVEL, "termination_date": TERMINATION_DATE})
    check("C: the c_level fixture is terminated", status, 200)
    _, admin_users_mid = call("GET", "api/admin-users-data", admin_token)
    managers_after = sorted(m["id"] for m in admin_users_mid["options"]["managers"])
    PROOF["C_manager_options"] = {"before": managers_before, "after": managers_after}
    check("C: a terminated person is no longer offered as a manager",
          CLEVEL in managers_after, False)
    check("C: and nobody else was dropped from the list",
          managers_after, sorted(set(managers_before) - {CLEVEL}))
    leaver_row_mid = next(u for u in admin_users_mid["users"] if u["id"] == LEAVER)
    PROOF["C_admin_row"] = leaver_row_mid
    check("C: the admin list still returns the terminated row, marked",
          leaver_row_mid["termination_date"], TERMINATION_DATE)

    # Nothing else on the user table moved.
    users_after = users_snapshot(trt)
    changed = diff_users(users_before, users_after)
    PROOF["C_user_drift"] = changed
    expected_changed_ids = {str(LEAVER), str(CLEVEL), str(UNREG_LEAVER), str(UNREG_STAYER)}
    stray = [c for c in changed if c.split(".")[0].split(":")[0] not in expected_changed_ids]
    check("C: no user outside the terminated set changed", stray, [])
    frozen_moved = [c for c in changed if any(f".{col}:" in c for col in FROZEN_COLUMNS)
                    and not c.startswith(f"{UNREG_STAYER}.password_hash")]
    check("C: no frozen column moved on anybody", frozen_moved, [])
    check("C: token_version was bumped for the terminated person",
          int(users_after[str(LEAVER)]["token_version"]) - int(users_before[str(LEAVER)]["token_version"]), 1)

    # ── E. reinstate ────────────────────────────────────────────────────────
    status, reinstate_body = call("POST", "api/admin/reinstate-employee", admin_token,
                                  {"user_id": LEAVER, "note": "stand proof: undo"})
    PROOF["E_reinstate_response"] = {"status": status, "body": reinstate_body}
    check("E: reinstatement succeeds", status, 200)
    check("E: back in scope on both open periods",
          sorted((reinstate_body or {}).get("scoped_in_period_ids", [])), [2, 5])

    epp_reinstated = participants(trt)
    check("E: the scope rows are exactly what they were before termination",
          {k: v for k, v in epp_reinstated.items() if k.endswith(f":{LEAVER}")},
          {k: v for k, v in epp_before.items() if k.endswith(f":{LEAVER}")})
    check("E: the newcomer's reason survived the round trip",
          epp_reinstated[f"{PERIOD}:{NEWCOMER}"], epp_before[f"{PERIOD}:{NEWCOMER}"])

    users_reinstated = users_snapshot(trt)
    check("E: the terminated marks are cleared",
          [users_reinstated[str(LEAVER)]["terminated_at"],
           users_reinstated[str(LEAVER)]["termination_date"]], [None, None])
    leaver_diff = [c for c in diff_users(users_before, users_reinstated)
                   if c.startswith(f"{LEAVER}.")]
    PROOF["E_leaver_residual_diff"] = leaver_diff
    check("E: the only trace left on the row is the bumped token_version",
          leaver_diff, [f"{LEAVER}.token_version: 0 -> 1"])

    status, leaver_token_2, _ = login("tm.leaver@sedamedical.com")
    check("E: the reinstated employee can log in again", status, 200)
    _, employees_reinstated = call("GET", "api/employees", manager_token)
    check("E: the manager's task list has them back",
          sorted(e["id"] for e in (employees_reinstated or {}).get("data", [])),
          manager_list_before)
    # Two other fixtures (the c_level writer and the never-registered employee)
    # are still terminated at this point, so the counter is short by exactly
    # those two — not by the person just reinstated.
    _, periods_reinstated = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_reinstated["data"] if int(p["id"]) == PERIOD)
    check("E: reinstating the leaver returns their place in the counter",
          int(row["in_scope_count"]), in_scope_before - 2)
    check("E: and no evaluation row moved during any of it",
          evaluations_fingerprint(trt)["md5"], evals_before["md5"])

    # Put the stand into its final shape for the money proof: only the leaver
    # is terminated, everybody else is back.
    for uid in (CLEVEL, UNREG_LEAVER):
        status, _ = call("POST", "api/admin/reinstate-employee", admin_token, {"user_id": uid})
        check(f"E: fixture {uid} reinstated for the money run", status, 200)

    _, periods_all_back = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_all_back["data"] if int(p["id"]) == PERIOD)
    check("E: with everybody reinstated the counter is exactly where it started",
          int(row["in_scope_count"]), in_scope_before)
    check("E: and the whole participant list is byte-identical to the start",
          participants(trt), epp_before)
    status, _ = call("POST", "api/admin/terminate-employee", admin_token,
                     {"user_id": LEAVER, "termination_date": TERMINATION_DATE,
                      "note": "stand proof: final state for the close"})
    check("E: the leaver is terminated again for the close", status, 200)

    events = employment_events(trt)
    leaver_events = [e for e in events if e["user_id"] == LEAVER]
    PROOF["E_event_history"] = leaver_events
    check("E: the log holds the whole history, not just the current state",
          [e["event_type"] for e in leaver_events],
          ["terminated", "reinstated", "terminated"])

    # ── F. the money ────────────────────────────────────────────────────────
    evals_final = evaluations_fingerprint(trt)
    check("F: evaluations are still byte-identical going into the close",
          evals_final["md5"], evals_before["md5"])

    status, close_trt = call("POST", "api/periods/close", admin_token,
                             {"period_id": PERIOD, "confirm_name": "H1-2026",
                              "name": "H1-2026"})
    PROOF["F_close_treatment"] = {"status": status, "body": close_trt}
    check("F: the treatment period closes", status, 200)

    repoint_stand(ctl, pgpass)
    status, admin_token_ctl, _ = login("tm.admin@sedamedical.com")
    check("F: admin logs in on the control stand", status, 200)
    check("F: nobody is terminated on the control stand",
          int(sql(ctl, "SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL")), 0)
    status, close_ctl = call("POST", "api/periods/close", admin_token_ctl,
                             {"period_id": PERIOD, "confirm_name": "H1-2026",
                              "name": "H1-2026"})
    PROOF["F_close_control"] = {"status": status, "body": close_ctl}
    check("F: the control period closes", status, 200)

    results_ctl = period_results(ctl)
    results_trt = period_results(trt)
    PROOF["F_period_results"] = {
        "control": {k: results_ctl[k] for k in sorted(results_ctl, key=int)
                    if 1501 <= int(k) <= 1509},
        "treatment": {k: results_trt[k] for k in sorted(results_trt, key=int)
                      if 1501 <= int(k) <= 1509},
    }

    # The people the terminated person evaluated must not move by a digit.
    unchanged = []
    for uid in sorted(set(results_ctl) & set(results_trt), key=int):
        if uid == str(LEAVER):
            continue
        if results_ctl[uid] != results_trt[uid]:
            unchanged.append({"user_id": uid,
                              "control": results_ctl[uid], "treatment": results_trt[uid]})
    PROOF["F_rows_that_moved"] = unchanged
    check("F: no other person's stored result changed", unchanged, [])
    check("F: the manager they evaluated has the same upward rating to the digit",
          results_trt[str(MANAGER)]["rating_upward"], results_ctl[str(MANAGER)]["rating_upward"])
    check("F: and the same final rating",
          results_trt[str(MANAGER)]["final_rating"], results_ctl[str(MANAGER)]["final_rating"])
    check("F: and the same bonus index",
          results_trt[str(MANAGER)]["bonus_index"], results_ctl[str(MANAGER)]["bonus_index"])

    # The terminated person's own result and pool share are gone.
    PROOF["F_leaver"] = {"control": results_ctl[str(LEAVER)],
                         "treatment": results_trt[str(LEAVER)]}
    check("F: the leaver had a result without the termination",
          results_ctl[str(LEAVER)]["has_data"], True)
    check("F: with a real bonus index",
          results_ctl[str(LEAVER)]["bonus_index"] not in (None, "", "0.0000"), True)
    check("F: with the termination they are out of scope", results_trt[str(LEAVER)]["is_in_scope"], False)
    check("F: carry no data", results_trt[str(LEAVER)]["has_data"], False)
    check("F: and no bonus index at all", results_trt[str(LEAVER)]["bonus_index"], None)
    check("F: no rating of any kind",
          [results_trt[str(LEAVER)][k] for k in
           ("rating_manager", "rating_upward", "rating_c_level_direct", "rating_self", "final_rating")],
          [None, None, None, None, None])
    check("F: and the row still exists — nothing was deleted",
          results_trt[str(LEAVER)]["user_id"], LEAVER)

    pool_ctl = sum(float(r["bonus_index"]) for r in results_ctl.values() if r["bonus_index"])
    pool_trt = sum(float(r["bonus_index"]) for r in results_trt.values() if r["bonus_index"])
    leaver_index = float(results_ctl[str(LEAVER)]["bonus_index"])
    PROOF["F_pool"] = {"control_total_index": round(pool_ctl, 4),
                       "treatment_total_index": round(pool_trt, 4),
                       "leaver_index": leaver_index,
                       "difference": round(pool_ctl - pool_trt, 4)}
    check("F: the pool shrinks by exactly the leaver's index and nothing else",
          round(pool_ctl - pool_trt, 4), round(leaver_index, 4))

    # A vacuous run must fail: assert the proof actually compared things.
    check("meta: the run compared a non-trivial number of values",
          len(PROOF.get("checks", [])) > 50, True)

    PROOF["failures"] = FAILURES
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(PROOF, ensure_ascii=False, indent=2) + "\n")

    passed = sum(1 for c in PROOF["checks"] if c["ok"])
    print(f"\nchecks: {passed}/{len(PROOF['checks'])} passed")
    print(f"proof:  {out}")
    if FAILURES:
        print("\nFAILURES:")
        for failure in FAILURES:
            print("  -", failure)
        raise SystemExit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()

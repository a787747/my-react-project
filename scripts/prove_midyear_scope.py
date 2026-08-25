#!/usr/bin/env python3
"""Prove the MID_YEAR_HIRES_SCOPE build on the throwaway stand (2026-08-25).

Everything below runs against the two stand databases built by
scripts/setup_midyear_throwaway.sh. Live epe_2026 is never contacted.

What this proves, in order:

  A. The state before: who is in scope, who has which task, what the counters
     read, and a byte-level fingerprint of every evaluation row.
  B. The refusals, each by name — non-admin, unauthenticated, unknown user,
     unknown period, closed period, a person with no participants row, a
     person already excluded for another reason, and the mandatory
     confirmation gate for a person who already has evaluation data. None of
     them writes anything.
  C. Exclusion: the person leaves their manager's task list and the HR
     completion count, cannot be evaluated and cannot evaluate, KEEPS their
     login, and a never-registered colleague excluded the same way can still
     register through the shared invite. Scope on the other period is untouched.
  D. Every evaluation row and every users row is byte-identical before and
     after. Not one column of the person's own row moves — not the capability
     flags, not token_version, not the employment columns.
  E. The two reasons side by side: a real leaver terminated through the real
     employment route, and the two reverse actions proven not to cross.
  F. The reverse action is exact: the participants table returns to its
     starting values and the task lists to their starting membership.
  G. "No row" versus "row with is_in_scope=false", measured on two fixtures
     across the whole read surface — the answer the brief asked for, and the
     one place where the two differ.
  H. The money: the same period closed twice from two copies of one dump, one
     with the exclusion and one without. Everyone else's stored result must
     match cell for cell; the excluded person's own result and their share of
     the pool must be gone.

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
CONTAINER = "epe-mid-n8n"
FIXTURE_PASSWORD = "Mid2026-Portal!"

ADMIN, MANAGER, SUBJECT = 1601, 1602, 1603
STAYER_A, STAYER_B, CLEVEL = 1604, 1605, 1606
NEWCOMER, UNREG_EXCLUDED, UNREG_CONTROL = 1607, 1608, 1609
NOROW, LEAVER = 1610, 1611
PERIOD = 2
CONTAINER_PERIOD = 5
CLOSED_PERIOD = 1
REASON = "excluded_by_admin"

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
    # A second fingerprint over the CONTENT only. The control and the treatment
    # were seeded by two separate runs of one file, so their evaluations carry
    # now() timestamps microseconds apart and their surrogate ids can differ.
    # Neither is a scored value, and every (subject, source, criterion) here is
    # unique, so the matrix's ORDER BY updated_at picks the same row on both
    # sides. This is the fingerprint that can honestly be compared ACROSS the
    # two stands; the full one above is for before/after inside one stand.
    content = [{k: v for k, v in r.items()
                if k not in ("updated_at", "evaluation_id", "score_id")} for r in rows]
    content_blob = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return {"md5": hashlib.md5(blob.encode()).hexdigest(),
            "content_md5": hashlib.md5(content_blob.encode()).hexdigest(),
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


def scope_events(database: str) -> list[dict[str, Any]]:
    return jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(e) ORDER BY e.id), '[]') FROM (
        SELECT id, period_id, user_id, event_type, reason, actor_id,
               occurred_at::text AS occurred_at, note
        FROM performance_db.period_scope_events) e""")


def employment_events(database: str) -> list[dict[str, Any]]:
    """Employment events for the FIXTURE range only.

    The stand is a restored copy of live, and live already carries real
    termination rows from the owner's own work. Asserting an empty table would
    be asserting a fact about live, not about this build.
    """
    return jsql(database, """
      SELECT COALESCE(json_agg(row_to_json(e) ORDER BY e.id), '[]') FROM (
        SELECT id, user_id, event_type, effective_date::text AS effective_date,
               period_id, actor_id, note
        FROM performance_db.employment_events
        WHERE user_id BETWEEN 1601 AND 1611) e""")


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


def task_list(token: str) -> list[int]:
    _, body = call("GET", "api/employees", token)
    return sorted(e["id"] for e in (body or {}).get("data", []))


# ── the proof ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-db", required=True)
    parser.add_argument("--treatment-db", required=True)
    parser.add_argument("--out",
                        default=str(REPO / "backups/2026-08-25-midyear-scope/midyear_scope_proof.json"))
    args = parser.parse_args()
    ctl, trt = args.control_db, args.treatment_db
    for name in (ctl, trt):
        if not name.startswith("epe_mid_"):
            raise SystemExit(f"Refusing to run against a non-stand database: {name}")
    pgpass = ssh("docker exec postgres_n8n env | grep '^POSTGRES_PASSWORD=' | cut -d= -f2-")

    PROOF["stand"] = {"control_db": ctl, "treatment_db": trt, "base": BASE,
                      "reason_written": REASON}

    # ── A. before ───────────────────────────────────────────────────────────
    evals_before = evaluations_fingerprint(trt)
    users_before = users_snapshot(trt)
    epp_before = participants(trt)
    PROOF["A_before"] = {
        "evaluations_md5": evals_before["md5"],
        "evaluations_content_md5": evals_before["content_md5"],
        "evaluation_row_count": evals_before["row_count"],
        "subject_period_2": epp_before[f"{PERIOD}:{SUBJECT}"],
        "subject_period_5": epp_before[f"{CONTAINER_PERIOD}:{SUBJECT}"],
        "newcomer_period_2": epp_before[f"{PERIOD}:{NEWCOMER}"],
        "norow_period_2_present": f"{PERIOD}:{NOROW}" in epp_before,
        "norow_period_5": epp_before.get(f"{CONTAINER_PERIOD}:{NOROW}"),
    }
    check("A: the subject starts in scope of the active period",
          epp_before[f"{PERIOD}:{SUBJECT}"]["is_in_scope"], True)
    check("A: the newcomer starts excluded for hire date",
          epp_before[f"{PERIOD}:{NEWCOMER}"]["exclusion_reason"], "hired_after_period_end")
    check("A: the no-row fixture genuinely has no participants row on period 2",
          f"{PERIOD}:{NOROW}" in epp_before, False)
    check("A: but does have one on the container period",
          epp_before[f"{CONTAINER_PERIOD}:{NOROW}"]["is_in_scope"], True)
    check("A: no scope events yet", scope_events(trt), [])
    check("A: no employment event on any fixture yet", employment_events(trt), [])

    status, admin_token, _ = login("my.admin@sedamedical.com")
    check("A: admin logs in", status, 200)
    status, manager_token, _ = login("my.manager@sedamedical.com")
    check("A: manager logs in", status, 200)
    status, subject_token, _ = login("my.latestart@sedamedical.com")
    check("A: the subject logs in before exclusion", status, 200)
    status, norow_token, _ = login("my.norow@sedamedical.com")
    check("A: the no-row fixture logs in", status, 200)

    manager_list_before = task_list(manager_token)
    PROOF["A_before"]["manager_task_list"] = manager_list_before
    check("A: the manager's task list contains the subject",
          SUBJECT in manager_list_before, True)
    check("A: and never contained the no-row fixture",
          NOROW in manager_list_before, False)

    _, subject_scope_before = call("GET", "api/employees", subject_token)
    check("A: the subject is in scope on their own read",
          (subject_scope_before or {}).get("actor_is_in_scope"), True)
    _, norow_scope_before = call("GET", "api/employees", norow_token)
    PROOF["A_before"]["norow_actor_is_in_scope"] = (norow_scope_before or {}).get("actor_is_in_scope")
    check("A: the no-row fixture already reads as out of scope",
          (norow_scope_before or {}).get("actor_is_in_scope"), False)

    _, subject_self_before = call("GET", "api/check-self-review", subject_token)
    check("A: the subject has a self-review on record",
          (subject_self_before or {}).get("has_self_review"), True)

    _, periods_before = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_before["data"] if int(p["id"]) == PERIOD)
    in_scope_before = int(row["in_scope_count"])
    participant_count_before = int(row["participant_count"])
    PROOF["A_before"]["periods_in_scope_count"] = in_scope_before
    PROOF["A_before"]["periods_participant_count"] = participant_count_before

    _, hr_before = call("GET", "api/hr/evaluation-status", admin_token)
    hr_rows_before = hr_before.get("employees") or []
    hr_ids_before = sorted(r["id"] for r in hr_rows_before)
    hr_count_before = int(hr_before["in_scope_count"])
    PROOF["A_before"]["hr_in_scope_count"] = hr_count_before
    check("A: HR status lists the subject", SUBJECT in hr_ids_before, True)
    check("A: HR status never listed the no-row fixture", NOROW in hr_ids_before, False)

    _, matrix_before = call("GET", "api/admin/evaluations-matrix", admin_token)
    matrix_rows_before = {int(e["id"]): e for e in (matrix_before or {}).get("data", [])}
    PROOF["A_before"]["matrix_subject_in_scope"] = matrix_rows_before.get(SUBJECT, {}).get("is_in_scope")
    PROOF["A_before"]["matrix_norow_in_scope"] = matrix_rows_before.get(NOROW, {}).get("is_in_scope")
    check("A: the matrix shows the subject as in scope",
          matrix_rows_before[SUBJECT]["is_in_scope"], True)
    check("A: the matrix already emits the no-row fixture as a row",
          NOROW in matrix_rows_before, True)
    check("A: marked out of scope",
          matrix_rows_before[NOROW]["is_in_scope"], False)

    # ── B. refusals ─────────────────────────────────────────────────────────
    refusals: dict[str, Any] = {}

    status, body = call("POST", "api/admin/exclude-participant", None,
                        {"user_id": STAYER_A, "period_id": PERIOD})
    refusals["no_token"] = {"status": status, "error": (body or {}).get("error")}
    check("B: an unauthenticated exclusion is refused", status, 401)

    status, body = call("POST", "api/admin/exclude-participant", manager_token,
                        {"user_id": STAYER_A, "period_id": PERIOD})
    refusals["non_admin"] = {"status": status, "error": (body or {}).get("error")}
    check("B: a manager cannot exclude anybody", status, 403)

    status, body = call("POST", "api/admin/include-participant", manager_token,
                        {"user_id": STAYER_A, "period_id": PERIOD})
    refusals["non_admin_include"] = {"status": status, "error": (body or {}).get("error")}
    check("B: a manager cannot put anybody back either", status, 403)

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": 999999, "period_id": PERIOD})
    refusals["unknown_user"] = {"status": status, "error": (body or {}).get("error")}
    check("B: an unknown user is a 404", status, 404)
    check("B: named USER_NOT_FOUND", (body or {}).get("error"), "USER_NOT_FOUND")

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": STAYER_A, "period_id": 999999})
    refusals["unknown_period"] = {"status": status, "error": (body or {}).get("error")}
    check("B: an unknown period is a 404", status, 404)
    check("B: named PERIOD_NOT_FOUND", (body or {}).get("error"), "PERIOD_NOT_FOUND")

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": STAYER_A, "period_id": CLOSED_PERIOD})
    refusals["closed_period"] = {"status": status, "body": body}
    check("B: a closed period is refused", status, 422)
    check("B: named PERIOD_CLOSED", (body or {}).get("error"), "PERIOD_CLOSED")

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": NOROW, "period_id": PERIOD})
    refusals["no_participant_row"] = {"status": status, "body": body}
    check("B: a person with no participants row is refused", status, 404)
    check("B: named NOT_A_PARTICIPANT", (body or {}).get("error"), "NOT_A_PARTICIPANT")

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": NEWCOMER, "period_id": PERIOD})
    refusals["already_excluded_other_reason"] = {"status": status, "body": body}
    check("B: excluding somebody already out of scope is refused", status, 409)
    check("B: named ALREADY_EXCLUDED", (body or {}).get("error"), "ALREADY_EXCLUDED")
    check("B: and the refusal names the reason that is already there",
          (body or {}).get("current_reason"), "hired_after_period_end")

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": SUBJECT, "period_id": "not-a-number"})
    refusals["bad_period_id"] = {"status": status, "error": (body or {}).get("error")}
    check("B: a non-numeric period id is a 422", status, 422)

    status, body = call("POST", "api/admin/include-participant", admin_token,
                        {"user_id": STAYER_A, "period_id": PERIOD})
    refusals["include_somebody_in_scope"] = {"status": status, "body": body}
    check("B: putting back somebody who is already in scope is refused", status, 409)
    check("B: named NOT_EXCLUDED_BY_ADMIN",
          (body or {}).get("error"), "NOT_EXCLUDED_BY_ADMIN")

    status, body = call("POST", "api/admin/include-participant", admin_token,
                        {"user_id": NEWCOMER, "period_id": PERIOD})
    refusals["include_hire_date_exclusion"] = {"status": status, "body": body}
    check("B: the reverse action refuses to cancel a hire-date exclusion", status, 409)
    check("B: and says which reason it will not touch",
          (body or {}).get("current_reason"), "hired_after_period_end")

    # The mandatory confirmation gate.
    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": SUBJECT, "period_id": PERIOD})
    refusals["has_evaluations_unconfirmed"] = {"status": status, "body": body}
    check("B: a person with evaluation data is refused without confirmation", status, 409)
    check("B: named HAS_EVALUATIONS", (body or {}).get("error"), "HAS_EVALUATIONS")
    check("B: the refusal counts what they RECEIVED",
          (body or {}).get("evaluations_received"), 2)
    check("B: their self-review", (body or {}).get("self_reviews"), 1)
    check("B: and what they GAVE", (body or {}).get("evaluations_given"), 1)
    PROOF["B_owner_message_has_evaluations"] = (body or {}).get("message")

    # The direct-reports warning, on somebody who actually has reports. This is
    # a warning and NOT a refusal (see the report): a manager who really started
    # in the second half of the year must be excludable. The route names the
    # people who would be left with an evaluator who has no task list, and the
    # caller decides.
    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": MANAGER, "period_id": PERIOD})
    refusals["manager_with_reports_unconfirmed"] = {"status": status, "body": body}
    check("B: excluding a manager with reports is gated on data, not on the reports",
          (body or {}).get("error"), "HAS_EVALUATIONS")
    check("B: and the answer NAMES the in-scope reports left without an evaluator",
          sorted(r["id"] for r in (body or {}).get("reports_in_scope", [])),
          [SUBJECT, STAYER_A, STAYER_B])
    check("B: the no-row fixture is not among them — they were never in scope",
          NOROW in [r["id"] for r in (body or {}).get("reports_in_scope", [])], False)

    PROOF["B_refusals"] = refusals
    check("B: nothing was written by any refusal",
          evaluations_fingerprint(trt)["md5"], evals_before["md5"])
    check("B: no refusal produced a scope event", scope_events(trt), [])
    check("B: no refusal changed a user row", diff_users(users_before, users_snapshot(trt)), [])
    check("B: no refusal changed a participants row", participants(trt), epp_before)

    # ── C. exclude ──────────────────────────────────────────────────────────
    status, exclude_body = call("POST", "api/admin/exclude-participant", admin_token,
                                {"user_id": SUBJECT, "period_id": PERIOD,
                                 "confirm_existing_evaluations": True,
                                 "note": "вышел на работу в сентябре"})
    PROOF["C_exclude_response"] = {"status": status, "body": exclude_body}
    check("C: exclusion succeeds once confirmed", status, 200)
    check("C: and reports the reason it wrote",
          (exclude_body or {}).get("exclusion_reason"), REASON)

    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": SUBJECT, "period_id": PERIOD,
                         "confirm_existing_evaluations": True})
    check("C: a second exclusion is refused, not repeated",
          (body or {}).get("error"), "ALREADY_EXCLUDED")

    epp_after = participants(trt)
    PROOF["C_scope"] = {
        "subject_period_2": epp_after[f"{PERIOD}:{SUBJECT}"],
        "subject_period_5": epp_after[f"{CONTAINER_PERIOD}:{SUBJECT}"],
        "newcomer_period_2": epp_after[f"{PERIOD}:{NEWCOMER}"],
    }
    check("C: the subject is out of scope of the named period",
          epp_after[f"{PERIOD}:{SUBJECT}"]["is_in_scope"], False)
    check("C: with a reason that is not a leaver's",
          epp_after[f"{PERIOD}:{SUBJECT}"]["exclusion_reason"], REASON)
    check("C: the OTHER period is untouched — this is not a termination",
          epp_after[f"{CONTAINER_PERIOD}:{SUBJECT}"],
          epp_before[f"{CONTAINER_PERIOD}:{SUBJECT}"])
    check("C: the newcomer's own exclusion reason is untouched",
          epp_after[f"{PERIOD}:{NEWCOMER}"], epp_before[f"{PERIOD}:{NEWCOMER}"])
    other_scope_moved = [k for k in epp_before
                         if k != f"{PERIOD}:{SUBJECT}" and epp_before[k] != epp_after.get(k)]
    check("C: no other person's scope moved", other_scope_moved, [])

    # The record.
    events = scope_events(trt)
    PROOF["C_event"] = events
    check("C: exactly one scope event was recorded", len(events), 1)
    check("C: the event names the actor", events[0]["actor_id"], ADMIN)
    check("C: the event names the period", events[0]["period_id"], PERIOD)
    check("C: the event names the person", events[0]["user_id"], SUBJECT)
    check("C: the event says what happened", events[0]["event_type"], "excluded")
    check("C: the event carries the machine reason", events[0]["reason"], REASON)
    check("C: and the owner's words", events[0]["note"], "вышел на работу в сентябре")
    check("C: no employment event was written — nobody was terminated",
          employment_events(trt), [])

    # Lists and counters.
    manager_list_after = task_list(manager_token)
    PROOF["C_manager_task_list"] = {"before": manager_list_before, "after": manager_list_after}
    check("C: the manager's task list lost the subject",
          SUBJECT in manager_list_after, False)
    check("C: and lost exactly one person",
          len(manager_list_before) - len(manager_list_after), 1)
    check("C: the other reports are still there",
          manager_list_after, sorted(set(manager_list_before) - {SUBJECT}))

    _, periods_after = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_after["data"] if int(p["id"]) == PERIOD)
    PROOF["C_counters"] = {
        "periods_in_scope_before": in_scope_before,
        "periods_in_scope_after": int(row["in_scope_count"]),
        "participant_count_before": participant_count_before,
        "participant_count_after": int(row["participant_count"]),
    }
    check("C: the campaign counter drops by exactly one",
          in_scope_before - int(row["in_scope_count"]), 1)
    check("C: the participant count does not move — nothing was deleted",
          int(row["participant_count"]), participant_count_before)

    _, hr_after = call("GET", "api/hr/evaluation-status", admin_token)
    hr_ids_after = sorted(r["id"] for r in (hr_after.get("employees") or []))
    hr_count_after = int(hr_after["in_scope_count"])
    PROOF["C_counters"]["hr_in_scope_before"] = hr_count_before
    PROOF["C_counters"]["hr_in_scope_after"] = hr_count_after
    check("C: the HR completion count drops by exactly one",
          hr_count_before - hr_count_after, 1)
    check("C: the subject is gone from the HR status list",
          SUBJECT in hr_ids_after, False)
    manager_row_after = next(r for r in (hr_after.get("employees") or []) if r["id"] == MANAGER)
    manager_row_before = next(r for r in hr_rows_before if r["id"] == MANAGER)
    PROOF["C_counters"]["manager_total_subordinates"] = {
        "before": int(manager_row_before["total_subordinates"]),
        "after": int(manager_row_after["total_subordinates"])}
    check("C: the manager is no longer expected to evaluate them",
          int(manager_row_before["total_subordinates"])
          - int(manager_row_after["total_subordinates"]), 1)

    # Cannot be evaluated, cannot evaluate.
    status, body = call("POST", "api/submit-evaluation", manager_token,
                        {"subject_id": SUBJECT, "evaluation_source": "manager",
                         "grades": {"3": 7, "4": 7, "12": 7, "14": 7}})
    PROOF["C_cannot_be_evaluated"] = {"status": status, "body": body}
    check("C: their manager can no longer evaluate them", status, 403)
    check("C: named SCOPE_MISMATCH", (body or {}).get("error"), "SCOPE_MISMATCH")

    status, body = call("POST", "api/submit-evaluation", admin_token,
                        {"subject_id": SUBJECT, "evaluation_source": "c_level_direct",
                         "grades": {"1": 7, "10": 7}})
    PROOF["C_cannot_be_evaluated_clevel"] = {"status": status, "error": (body or {}).get("error")}
    check("C: c_level_direct on them is refused too", status, 403)

    status, subject_token_2, subject_login = login("my.latestart@sedamedical.com")
    PROOF["C_login_after_exclusion"] = {"status": status,
                                        "has_token": bool(subject_token_2)}
    check("C: THE EXCLUDED PERSON CAN STILL LOG IN", status, 200)
    check("C: and gets a working session", bool(subject_token_2), True)

    status, body = call("GET", "api/employees", subject_token)
    PROOF["C_old_token_still_valid"] = {"status": status}
    check("C: the session they already held is NOT revoked", status, 200)
    check("C: but it now reads as out of scope",
          (body or {}).get("actor_is_in_scope"), False)

    status, body = call("POST", "api/self-review-submit", subject_token_2,
                        {"final_score": 7, "grades": {"3": 7, "4": 7, "12": 7}})
    PROOF["C_cannot_self_review"] = {"status": status, "body": body}
    check("C: they cannot submit a self-review", status, 403)
    check("C: named NOT_IN_SCOPE", (body or {}).get("error"), "NOT_IN_SCOPE")

    status, body = call("POST", "api/submit-evaluation", subject_token_2,
                        {"subject_id": MANAGER, "evaluation_source": "subordinate",
                         "grades": {"2": 7, "3": 7, "4": 7, "12": 7, "14": 7}})
    PROOF["C_cannot_evaluate_upward"] = {"status": status, "body": body}
    check("C: and they cannot evaluate their manager", status, 403)

    # The shared-invite door — the difference from termination.
    invite = sql(trt, "SELECT token FROM performance_db.invite_tokens "
                      "WHERE expires_at > now() ORDER BY id DESC LIMIT 1")
    status, body = call("POST", "api/admin/exclude-participant", admin_token,
                        {"user_id": UNREG_EXCLUDED, "period_id": PERIOD,
                         "note": "never registered, excluded by hand"})
    PROOF["C_exclude_unregistered"] = {"status": status, "body": body}
    check("C: a never-registered employee is excluded without a confirmation flag",
          status, 200)
    for email in ("my.unreg.excluded@sedamedical.com", "my.unreg.control@sedamedical.com"):
        sql(trt, f"""
          DELETE FROM performance_db.email_verification_codes WHERE lower(email) = '{email}';
          INSERT INTO performance_db.email_verification_codes
            (email, code, expires_at, is_verified, verified_at)
          VALUES ('{email}', '424242', now() + interval '1 hour', true, now());""")
    status_e, body_e = call("POST", "api/register",
                            body={"token": invite, "email": "my.unreg.excluded@sedamedical.com",
                                  "password": "StandProof2026!", "verification_code": "424242"})
    status_c, body_c = call("POST", "api/register",
                            body={"token": invite, "email": "my.unreg.control@sedamedical.com",
                                  "password": "StandProof2026!", "verification_code": "424242"})
    hash_e = sql(trt, f"SELECT (password_hash IS NOT NULL) FROM performance_db.users WHERE id = {UNREG_EXCLUDED}")
    hash_c = sql(trt, f"SELECT (password_hash IS NOT NULL) FROM performance_db.users WHERE id = {UNREG_CONTROL}")
    PROOF["C_shared_invite"] = {
        "excluded": {"status": status_e, "body": body_e, "now_registered": hash_e},
        "control": {"status": status_c, "now_registered": hash_c}}
    check("C: AN EXCLUDED EMPLOYEE CAN STILL REGISTER through the shared invite",
          status_e, 200)
    check("C: and their password is set", hash_e, "t")
    check("C: the same invite works for the control colleague", status_c, 200)
    check("C: whose password is also set", hash_c, "t")

    # A password reset still works for them, unlike a leaver.
    status, body = call("POST", "api/request-password-reset",
                        body={"email": "my.latestart@sedamedical.com"})
    reset_tokens = int(sql(trt, "SELECT count(*) FROM performance_db.password_reset_tokens "
                                f"WHERE user_id = {SUBJECT}"))
    PROOF["C_password_reset"] = {"status": status, "tokens_created": reset_tokens}
    check("C: a reset link is still created for an excluded employee", reset_tokens, 1)

    # ── D. nothing moved ────────────────────────────────────────────────────
    evals_after = evaluations_fingerprint(trt)
    PROOF["D_evaluations"] = {
        "md5_before": evals_before["md5"], "md5_after": evals_after["md5"],
        "row_count_before": evals_before["row_count"],
        "row_count_after": evals_after["row_count"]}
    check("D: every evaluation row is byte-identical after the exclusion",
          evals_after["md5"], evals_before["md5"])
    check("D: no evaluation row was added or removed",
          evals_after["row_count"], evals_before["row_count"])

    users_after = users_snapshot(trt)
    changed = diff_users(users_before, users_after)
    # The only user rows that may move are the two that deliberately registered
    # through the shared invite in the step above.
    allowed = {f"{UNREG_EXCLUDED}.password_hash", f"{UNREG_CONTROL}.password_hash"}
    stray = [c for c in changed if c.split(":")[0] not in allowed]
    PROOF["D_user_drift"] = {"all": changed, "unexpected": stray}
    check("D: no user row moved except the two deliberate registrations", stray, [])
    subject_diff = [c for c in changed if c.startswith(f"{SUBJECT}.")]
    PROOF["D_subject_row_diff"] = subject_diff
    check("D: NOT ONE COLUMN of the excluded person's own row changed",
          subject_diff, [])
    check("D: their employment columns are still empty",
          [users_after[str(SUBJECT)]["terminated_at"],
           users_after[str(SUBJECT)]["termination_date"]], [None, None])
    check("D: their capability flags are untouched",
          [users_after[str(SUBJECT)]["can_evaluate"],
           users_after[str(SUBJECT)]["can_be_evaluated"]],
          [users_before[str(SUBJECT)]["can_evaluate"],
           users_before[str(SUBJECT)]["can_be_evaluated"]])
    check("D: and token_version was NOT bumped — the login is untouched",
          users_after[str(SUBJECT)]["token_version"],
          users_before[str(SUBJECT)]["token_version"])

    # ── E. the two reasons side by side ─────────────────────────────────────
    status, body = call("POST", "api/admin/terminate-employee", admin_token,
                        {"user_id": LEAVER, "termination_date": "2026-06-01",
                         "note": "stand: a real leaver"})
    check("E: the leaver is terminated through the real employment route", status, 200)
    epp_both = participants(trt)
    PROOF["E_two_reasons"] = {
        "excluded_by_admin": epp_both[f"{PERIOD}:{SUBJECT}"],
        "terminated": epp_both[f"{PERIOD}:{LEAVER}"],
        "hired_after_period_end": epp_both[f"{PERIOD}:{NEWCOMER}"]}
    check("E: the three populations carry three different reasons",
          sorted({epp_both[f"{PERIOD}:{SUBJECT}"]["exclusion_reason"],
                  epp_both[f"{PERIOD}:{LEAVER}"]["exclusion_reason"],
                  epp_both[f"{PERIOD}:{NEWCOMER}"]["exclusion_reason"]}),
          ["excluded_by_admin", "hired_after_period_end", "terminated"])
    check("E: the leaver is out of BOTH periods — termination is company-wide",
          [epp_both[f"{PERIOD}:{LEAVER}"]["is_in_scope"],
           epp_both[f"{CONTAINER_PERIOD}:{LEAVER}"]["is_in_scope"]], [False, False])
    check("E: the excluded person is out of ONE — exclusion is period-bound",
          [epp_both[f"{PERIOD}:{SUBJECT}"]["is_in_scope"],
           epp_both[f"{CONTAINER_PERIOD}:{SUBJECT}"]["is_in_scope"]], [False, True])

    status, body = call("POST", "api/admin/include-participant", admin_token,
                        {"user_id": LEAVER, "period_id": PERIOD})
    PROOF["E_include_refuses_leaver"] = {"status": status, "body": body}
    check("E: the scope route refuses to put a leaver back", status, 409)
    check("E: naming the reason it will not touch",
          (body or {}).get("current_reason"), "terminated")

    status, _ = call("POST", "api/admin/reinstate-employee", admin_token,
                     {"user_id": LEAVER, "note": "stand: undo"})
    check("E: the employment route reinstates the leaver", status, 200)
    epp_post_reinstate = participants(trt)
    check("E: and reinstatement did NOT put the excluded person back",
          epp_post_reinstate[f"{PERIOD}:{SUBJECT}"]["exclusion_reason"], REASON)
    check("E: while the leaver is back in scope of both periods",
          [epp_post_reinstate[f"{PERIOD}:{LEAVER}"]["is_in_scope"],
           epp_post_reinstate[f"{CONTAINER_PERIOD}:{LEAVER}"]["is_in_scope"]], [True, True])

    # ── F. the reverse action ───────────────────────────────────────────────
    status, include_body = call("POST", "api/admin/include-participant", admin_token,
                                {"user_id": SUBJECT, "period_id": PERIOD,
                                 "note": "stand: undo"})
    PROOF["F_include_response"] = {"status": status, "body": include_body}
    check("F: the reverse action succeeds", status, 200)

    status, _ = call("POST", "api/admin/include-participant", admin_token,
                     {"user_id": UNREG_EXCLUDED, "period_id": PERIOD})
    check("F: the never-registered fixture is put back too", status, 200)

    epp_restored = participants(trt)
    PROOF["F_participants_restored"] = {
        "identical_to_start": epp_restored == epp_before,
        "differences": [k for k in set(epp_before) | set(epp_restored)
                        if epp_before.get(k) != epp_restored.get(k)]}
    check("F: the participants table is back to its exact starting values",
          epp_restored, epp_before)

    check("F: the manager's task list is back to its starting membership",
          task_list(manager_token), manager_list_before)
    _, periods_restored = call("GET", "api/periods", admin_token)
    row = next(p for p in periods_restored["data"] if int(p["id"]) == PERIOD)
    check("F: and the campaign counter is exactly where it started",
          int(row["in_scope_count"]), in_scope_before)
    check("F: no evaluation row moved during any of it",
          evaluations_fingerprint(trt)["md5"], evals_before["md5"])

    all_events = scope_events(trt)
    subject_events = [e for e in all_events if e["user_id"] == SUBJECT]
    PROOF["F_event_history"] = all_events
    check("F: the log holds the history, not just the current state",
          [e["event_type"] for e in subject_events], ["excluded", "included"])
    check("F: an inclusion carries no machine reason",
          subject_events[1]["reason"], None)

    status, events_body = call("GET", "api/admin/period-scope-events", admin_token,
                               query=f"?user_id={SUBJECT}")
    PROOF["F_events_route"] = {"status": status, "body": events_body}
    check("F: the record is readable through its own route", status, 200)
    check("F: filtered to the person asked for",
          sorted({e["user_id"] for e in (events_body or {}).get("events", [])}), [SUBJECT])
    status, _ = call("GET", "api/admin/period-scope-events", manager_token)
    check("F: and is admin-only", status, 403)

    # Final shape for the money proof: exactly one difference from the control.
    status, _ = call("POST", "api/admin/exclude-participant", admin_token,
                     {"user_id": SUBJECT, "period_id": PERIOD,
                      "confirm_existing_evaluations": True,
                      "note": "stand: final state for the close"})
    check("F: the subject is excluded again for the close", status, 200)

    # ── G. "no row" versus "row with is_in_scope=false" ─────────────────────
    _, norow_scope = call("GET", "api/employees", norow_token)
    _, subject_scope = call("GET", "api/employees", subject_token_2)
    _, hr_g = call("GET", "api/hr/evaluation-status", admin_token)
    hr_ids_g = sorted(r["id"] for r in (hr_g.get("employees") or []))
    _, matrix_g = call("GET", "api/admin/evaluations-matrix", admin_token)
    matrix_g_rows = {int(e["id"]): e for e in (matrix_g or {}).get("data", [])}
    manager_list_g = task_list(manager_token)
    status_norow_self, body_norow_self = call("POST", "api/self-review-submit", norow_token,
                                              {"final_score": 7, "grades": {"3": 7, "4": 7, "12": 7}})
    status_subj_self, body_subj_self = call("POST", "api/self-review-submit", subject_token_2,
                                            {"final_score": 7, "grades": {"3": 7, "4": 7, "12": 7}})
    status_norow_eval, _ = call("POST", "api/submit-evaluation", manager_token,
                                {"subject_id": NOROW, "evaluation_source": "manager",
                                 "grades": {"3": 7, "4": 7, "12": 7, "14": 7}})
    status_subj_eval, _ = call("POST", "api/submit-evaluation", manager_token,
                               {"subject_id": SUBJECT, "evaluation_source": "manager",
                                "grades": {"3": 7, "4": 7, "12": 7, "14": 7}})
    comparison = {
        "manager_task_list": {"no_row": NOROW in manager_list_g,
                              "excluded": SUBJECT in manager_list_g},
        "own_actor_is_in_scope": {"no_row": (norow_scope or {}).get("actor_is_in_scope"),
                                  "excluded": (subject_scope or {}).get("actor_is_in_scope")},
        "hr_status_listed": {"no_row": NOROW in hr_ids_g, "excluded": SUBJECT in hr_ids_g},
        "matrix_row_emitted": {"no_row": NOROW in matrix_g_rows,
                               "excluded": SUBJECT in matrix_g_rows},
        "matrix_is_in_scope": {"no_row": matrix_g_rows.get(NOROW, {}).get("is_in_scope"),
                               "excluded": matrix_g_rows.get(SUBJECT, {}).get("is_in_scope")},
        "self_review_submit": {"no_row": [status_norow_self, (body_norow_self or {}).get("error")],
                               "excluded": [status_subj_self, (body_subj_self or {}).get("error")]},
        "being_evaluated": {"no_row": status_norow_eval, "excluded": status_subj_eval},
    }
    PROOF["G_no_row_vs_excluded"] = comparison
    for key, pair in comparison.items():
        check(f"G: '{key}' behaves the same for no-row and for excluded",
              pair["no_row"], pair["excluded"])

    # ── H. the money ────────────────────────────────────────────────────────
    epp_final_trt = participants(trt)
    epp_final_ctl = participants(ctl)
    scope_delta = {k: {"control": epp_final_ctl.get(k), "treatment": epp_final_trt.get(k)}
                   for k in set(epp_final_ctl) | set(epp_final_trt)
                   if epp_final_ctl.get(k) != epp_final_trt.get(k)}
    PROOF["H_scope_delta_going_into_close"] = scope_delta
    check("H: the two stands differ in exactly one participants row going in",
          sorted(scope_delta), [f"{PERIOD}:{SUBJECT}"])

    evals_final = evaluations_fingerprint(trt)
    check("H: evaluations are still byte-identical going into the close",
          evals_final["md5"], evals_before["md5"])
    ctl_fp = evaluations_fingerprint(ctl)
    PROOF["H_cross_stand_evaluations"] = {
        "control_content_md5": ctl_fp["content_md5"],
        "treatment_content_md5": evals_final["content_md5"],
        "control_row_count": ctl_fp["row_count"],
        "treatment_row_count": evals_final["row_count"]}
    check("H: and the control's evaluations are the same data as the treatment's",
          ctl_fp["content_md5"], evals_final["content_md5"])
    check("H: with the same number of rows", ctl_fp["row_count"], evals_final["row_count"])

    status, close_trt = call("POST", "api/periods/close", admin_token,
                             {"period_id": PERIOD, "confirm_name": "H1-2026",
                              "name": "H1-2026"})
    PROOF["H_close_treatment"] = {"status": status, "body": close_trt}
    check("H: the treatment period closes", status, 200)

    repoint_stand(ctl, pgpass)
    status, admin_token_ctl, _ = login("my.admin@sedamedical.com")
    check("H: admin logs in on the control stand", status, 200)
    check("H: nobody is excluded by admin on the control stand",
          int(sql(ctl, "SELECT count(*) FROM performance_db.evaluation_period_participants "
                       f"WHERE exclusion_reason = '{REASON}'")), 0)
    status, close_ctl = call("POST", "api/periods/close", admin_token_ctl,
                             {"period_id": PERIOD, "confirm_name": "H1-2026",
                              "name": "H1-2026"})
    PROOF["H_close_control"] = {"status": status, "body": close_ctl}
    check("H: the control period closes", status, 200)

    results_ctl = period_results(ctl)
    results_trt = period_results(trt)
    PROOF["H_period_results_fixtures"] = {
        "control": {k: results_ctl[k] for k in sorted(results_ctl, key=int)
                    if 1601 <= int(k) <= 1611},
        "treatment": {k: results_trt[k] for k in sorted(results_trt, key=int)
                      if 1601 <= int(k) <= 1611},
    }
    PROOF["H_row_counts"] = {"control": len(results_ctl), "treatment": len(results_trt)}

    moved = []
    for uid in sorted(set(results_ctl) & set(results_trt), key=int):
        if uid == str(SUBJECT):
            continue
        if results_ctl[uid] != results_trt[uid]:
            moved.append({"user_id": uid,
                          "control": results_ctl[uid], "treatment": results_trt[uid]})
    PROOF["H_rows_that_moved"] = moved
    check("H: NOBODY ELSE'S STORED RESULT CHANGED — cell by cell", moved, [])
    check("H: the two closes produced the same number of rows",
          len(results_trt), len(results_ctl))
    check("H: nobody appears in one close and not the other",
          sorted(set(results_ctl) ^ set(results_trt)), [])

    check("H: the manager they evaluated keeps the same upward rating to the digit",
          results_trt[str(MANAGER)]["rating_upward"], results_ctl[str(MANAGER)]["rating_upward"])
    check("H: the same final rating",
          results_trt[str(MANAGER)]["final_rating"], results_ctl[str(MANAGER)]["final_rating"])
    check("H: and the same bonus index",
          results_trt[str(MANAGER)]["bonus_index"], results_ctl[str(MANAGER)]["bonus_index"])

    PROOF["H_subject"] = {"control": results_ctl[str(SUBJECT)],
                          "treatment": results_trt[str(SUBJECT)]}
    check("H: without the exclusion the subject had a result",
          results_ctl[str(SUBJECT)]["has_data"], True)
    check("H: with a real bonus index",
          results_ctl[str(SUBJECT)]["bonus_index"] not in (None, "", "0.0000"), True)
    check("H: with the exclusion they are out of scope",
          results_trt[str(SUBJECT)]["is_in_scope"], False)
    check("H: carry no data", results_trt[str(SUBJECT)]["has_data"], False)
    check("H: and no bonus index at all", results_trt[str(SUBJECT)]["bonus_index"], None)
    check("H: no rating of any kind",
          [results_trt[str(SUBJECT)][k] for k in
           ("rating_manager", "rating_upward", "rating_c_level_direct",
            "rating_self", "final_rating")],
          [None, None, None, None, None])
    check("H: and the row still exists — nothing was deleted",
          results_trt[str(SUBJECT)]["user_id"], SUBJECT)

    # The one asymmetry, measured: a person with no participants row gets no
    # frozen row at all, in either close.
    PROOF["H_no_row_at_close"] = {
        "control_has_row": str(NOROW) in results_ctl,
        "treatment_has_row": str(NOROW) in results_trt,
        "excluded_has_row": str(SUBJECT) in results_trt}
    check("H: the no-row fixture gets NO frozen result in the control",
          str(NOROW) in results_ctl, False)
    check("H: nor in the treatment", str(NOROW) in results_trt, False)
    check("H: while the excluded person DOES get one, marked out of scope",
          str(SUBJECT) in results_trt, True)

    pool_ctl = sum(float(r["bonus_index"]) for r in results_ctl.values() if r["bonus_index"])
    pool_trt = sum(float(r["bonus_index"]) for r in results_trt.values() if r["bonus_index"])
    subject_index = float(results_ctl[str(SUBJECT)]["bonus_index"])
    PROOF["H_pool"] = {"control_total_index": round(pool_ctl, 4),
                       "treatment_total_index": round(pool_trt, 4),
                       "subject_index": subject_index,
                       "difference": round(pool_ctl - pool_trt, 4)}
    check("H: the pool shrinks by exactly the excluded person's index and nothing else",
          round(pool_ctl - pool_trt, 4), round(subject_index, 4))

    # A vacuous run must fail: assert the proof actually compared things.
    check("meta: the run compared a non-trivial number of values",
          len(PROOF.get("checks", [])) > 80, True)

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

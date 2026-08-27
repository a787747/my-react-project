#!/usr/bin/env python3
"""SQL vs /api/admin-users-data vs campaignSummary — throwaway stand only."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOST = "root@92.51.45.147"
FIXTURE_PASSWORD = "Walk2026-Portal!"
PROOF: dict = {"checks": []}
FAILURES: list[str] = []

INDEPENDENT_SQL = r"""
WITH active_period AS (
  SELECT id, name FROM performance_db.evaluation_periods
  WHERE is_active = true AND status = 'active' LIMIT 1
),
in_scope AS (
  SELECT epp.user_id
  FROM performance_db.evaluation_period_participants epp
  JOIN active_period ap ON ap.id = epp.period_id
  WHERE epp.is_in_scope = true
),
manager_applicable AS (
  SELECT u.id AS subject_id, c.id AS criteria_id
  FROM performance_db.users u
  JOIN performance_db.criteria c
    ON c.is_active = true AND c.c_level_only = false
  WHERE (c.target_audience <> 'project_participants' OR u.is_project_participant = true)
    AND (c.target_audience <> 'managers_only' OR u.has_subordinates = true)
),
manager_scored AS (
  SELECT e.evaluator_id, e.subject_id, es.criteria_id
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
  JOIN active_period ap ON ap.id = e.period_id
  WHERE e.is_self_evaluation = false
    AND e.evaluation_source = 'manager'
),
manager_eval_complete AS (
  SELECT ms.evaluator_id, ms.subject_id
  FROM manager_applicable ma
  JOIN manager_scored ms
    ON ms.subject_id = ma.subject_id AND ms.criteria_id = ma.criteria_id
  GROUP BY ms.evaluator_id, ms.subject_id
  HAVING count(*) = (
    SELECT count(*) FROM manager_applicable ma2
    WHERE ma2.subject_id = ms.subject_id
  )
),
upward_done AS (
  SELECT e.evaluator_id, e.subject_id
  FROM performance_db.evaluations e
  JOIN active_period ap ON ap.id = e.period_id
  WHERE e.evaluation_source = 'subordinate'
),
enriched AS (
  SELECT
    u.id,
    u.full_name,
    u.role,
    u.terminated_at,
    (u.password_hash IS NOT NULL) AS is_registered,
    u.can_evaluate,
    u.can_be_evaluated,
    u.manager_id,
    m.role AS manager_role,
    COALESCE(m.can_evaluate, false) AS manager_can_evaluate,
    (u.id IN (SELECT user_id FROM in_scope)) AS in_scope,
    EXISTS (
      SELECT 1 FROM performance_db.evaluations e
      JOIN active_period ap ON ap.id = e.period_id
      WHERE e.subject_id = u.id
        AND e.is_self_evaluation = true
        AND e.status = 'completed'
    ) AS self_review_done,
    EXISTS (
      SELECT 1 FROM upward_done ud
      WHERE ud.evaluator_id = u.id AND ud.subject_id = u.manager_id
    ) AS has_evaluated_manager,
    (
      SELECT count(*)::integer
      FROM performance_db.users sub
      JOIN in_scope ss ON ss.user_id = sub.id
      WHERE sub.manager_id = u.id AND sub.can_be_evaluated = true
    ) AS assigned_subordinate_count,
    (
      SELECT count(*)::integer
      FROM manager_eval_complete mec
      JOIN performance_db.users sub ON sub.id = mec.subject_id
      JOIN in_scope ss ON ss.user_id = sub.id
      WHERE mec.evaluator_id = u.id
        AND sub.manager_id = u.id
        AND sub.can_be_evaluated = true
    ) AS completed_subordinate_count,
    EXISTS (
      SELECT 1 FROM manager_eval_complete mec
      WHERE mec.subject_id = u.id AND mec.evaluator_id = u.manager_id
    ) AS received_manager_eval_complete,
    CASE WHEN u.role IN ('admin', 'c_level') THEN 0 ELSE (
      SELECT count(*)::integer
      FROM performance_db.users sub
      JOIN in_scope ss ON ss.user_id = sub.id
      WHERE sub.manager_id = u.id
    ) END AS expected_upward_count,
    CASE WHEN u.role IN ('admin', 'c_level') THEN 0 ELSE (
      SELECT count(*)::integer
      FROM upward_done ud
      JOIN performance_db.users sub ON sub.id = ud.evaluator_id
      JOIN in_scope ss ON ss.user_id = sub.id
      WHERE ud.subject_id = u.id AND sub.manager_id = u.id
    ) END AS received_upward_count
  FROM performance_db.users u
  LEFT JOIN performance_db.users m ON m.id = u.manager_id
),
flags AS (
  SELECT
    *,
    (in_scope AND role NOT IN ('admin', 'c_level')) AS owes_self,
    (in_scope AND manager_id IS NOT NULL
      AND (manager_role IS NULL OR manager_role NOT IN ('admin', 'c_level'))) AS owes_upward,
    (in_scope AND can_evaluate AND assigned_subordinate_count > 0) AS owes_sub,
    (in_scope AND can_be_evaluated) AS evaluated_subject
  FROM enriched
),
flags2 AS (
  SELECT
    *,
    (owes_self OR owes_upward OR owes_sub) AS has_task,
    (
      (owes_self OR owes_upward OR owes_sub)
      AND (NOT owes_self OR self_review_done)
      AND (NOT owes_upward OR has_evaluated_manager)
      AND (NOT owes_sub OR completed_subordinate_count >= assigned_subordinate_count)
    ) AS tasks_done,
    (
      evaluated_subject
      AND (
        NOT (evaluated_subject AND manager_id IS NOT NULL AND manager_can_evaluate)
        OR received_manager_eval_complete
      )
      AND expected_upward_count <= received_upward_count
    ) AS fully_evaluated
  FROM flags
)
SELECT json_build_object(
  'period_name', (SELECT name FROM active_period),
  'everyone', count(*),
  'terminated', count(*) FILTER (WHERE terminated_at IS NOT NULL),
  'employed', count(*) FILTER (WHERE terminated_at IS NULL),
  'inScope', count(*) FILTER (WHERE in_scope),
  'evaluatedBySomeone', count(*) FILTER (WHERE evaluated_subject),
  'invited', count(*) FILTER (WHERE terminated_at IS NULL),
  'registeredInvited', count(*) FILTER (WHERE is_registered AND terminated_at IS NULL),
  'tasksAssigned', count(*) FILTER (WHERE has_task),
  'tasksDone', count(*) FILTER (WHERE tasks_done),
  'fullyEvaluated', count(*) FILTER (WHERE fully_evaluated),
  'evaluationOwed', count(*) FILTER (WHERE evaluated_subject),
  'id25_in_scope', bool_or(id = 25 AND in_scope),
  'id25_has_task', bool_or(id = 25 AND has_task),
  'id25_evaluated_subject', bool_or(id = 25 AND evaluated_subject),
  'id25_name', max(full_name) FILTER (WHERE id = 25),
  'id21_in_scope', bool_or(id = 21 AND in_scope),
  'id21_evaluated_subject', bool_or(id = 21 AND evaluated_subject),
  'id21_name', max(full_name) FILTER (WHERE id = 21),
  'id21_can_be_evaluated', bool_or(id = 21 AND can_be_evaluated),
  'id1303_tasks_done', bool_or(id = 1303 AND tasks_done),
  'id1303_fully', bool_or(id = 1303 AND fully_evaluated),
  'id1308_tasks_done', bool_or(id = 1308 AND tasks_done),
  'id1308_fully', bool_or(id = 1308 AND fully_evaluated),
  'id1304_tasks_done', bool_or(id = 1304 AND tasks_done),
  'id1304_fully', bool_or(id = 1304 AND fully_evaluated),
  'c_level_direct_rows', (
    SELECT count(*) FROM performance_db.evaluations e
    JOIN active_period ap ON ap.id = e.period_id
    WHERE e.evaluation_source = 'c_level_direct'
  )
) FROM flags2;
"""


def check(name: str, actual, expected) -> bool:
    ok = actual == expected
    PROOF["checks"].append(
        {"name": name, "expected": expected, "actual": actual, "ok": ok}
    )
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def call(base: str, method: str, path: str, token=None, body=None):
    url = base.rstrip("/") + "/" + path.lstrip("/")
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def ssh_sql(database: str, sql: str) -> str:
    cmd = [
        "ssh", "-o", "BatchMode=yes", HOST,
        "docker", "exec", "-i", "postgres_n8n",
        "psql", "-U", "admin", "-d", database, "-tA", "-v", "ON_ERROR_STOP=1",
    ]
    out = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    if out.returncode:
        raise SystemExit(f"psql failed:\n{out.stderr}\n{out.stdout}")
    return out.stdout.strip()


def as_bool(value) -> bool:
    return value is True or value == "t" or value == "true"


def as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_terminated(user) -> bool:
    return bool(user.get("terminated_at"))


def is_in_scope(user) -> bool:
    return as_bool(user.get("period_is_in_scope"))


def is_evaluated_subject(user) -> bool:
    return is_in_scope(user) and as_bool(user.get("can_be_evaluated"))


def owes_self(user) -> bool:
    if not is_in_scope(user):
        return False
    return str(user.get("role") or "") not in ("admin", "c_level")


def owes_upward(user) -> bool:
    if not is_in_scope(user):
        return False
    if user.get("manager_id") in (None, ""):
        return False
    return str(user.get("manager_role") or "") not in ("admin", "c_level")


def owes_sub(user) -> bool:
    if not is_in_scope(user):
        return False
    if not as_bool(user.get("can_evaluate")):
        return False
    return as_int(user.get("assigned_subordinate_count")) > 0


def has_assigned_task(user) -> bool:
    return owes_self(user) or owes_upward(user) or owes_sub(user)


def finished_tasks(user) -> bool:
    if not has_assigned_task(user):
        return False
    if owes_self(user) and not as_bool(user.get("self_review_done")):
        return False
    if owes_upward(user) and not as_bool(user.get("has_evaluated_manager")):
        return False
    if owes_sub(user) and as_int(user.get("completed_subordinate_count")) < as_int(
        user.get("assigned_subordinate_count")
    ):
        return False
    return True


def manager_owes(user) -> bool:
    if not is_evaluated_subject(user):
        return False
    if user.get("manager_id") in (None, ""):
        return False
    return as_bool(user.get("manager_can_evaluate"))


def fully_evaluated(user) -> bool:
    if not is_evaluated_subject(user):
        return False
    if manager_owes(user) and not as_bool(user.get("received_manager_eval_complete")):
        return False
    if as_int(user.get("expected_upward_count")) > as_int(user.get("received_upward_count")):
        return False
    return True


def build_summary(users: list) -> dict:
    has_period = any(
        user.get("period_id") not in (None, "") for user in users
    )
    named = next((user.get("period_name") for user in users if user.get("period_name")), None)
    everyone = len(users)
    terminated = sum(1 for user in users if is_terminated(user))
    employed = everyone - terminated
    in_scope = sum(1 for user in users if is_in_scope(user))
    evaluated = sum(1 for user in users if is_evaluated_subject(user))
    registered = sum(
        1 for user in users if as_bool(user.get("is_registered")) and not is_terminated(user)
    )
    with_tasks = [user for user in users if has_assigned_task(user)]
    return {
        "hasPeriod": has_period,
        "periodName": named,
        "everyone": everyone,
        "employed": employed,
        "terminated": terminated,
        "inScope": in_scope,
        "evaluatedBySomeone": evaluated,
        "invited": employed,
        "registeredInvited": registered,
        "tasksDone": sum(1 for user in with_tasks if finished_tasks(user)),
        "tasksAssigned": len(with_tasks),
        "fullyEvaluated": sum(1 for user in users if fully_evaluated(user)),
        "evaluationOwed": evaluated,
    }


def format_lines(summary: dict) -> list[str]:
    if not summary.get("hasPeriod"):
        return ["Нет активного периода — прогресс кампании не считается"]
    name = summary.get("periodName") or "текущий период"
    return [
        f"{name}: в охвате {summary['inScope']} · оцениваются кем-то {summary['evaluatedBySomeone']}",
        f"Зарегистрировались {summary['registeredInvited']} из {summary['invited']} работающих",
        (
            f"Свои задачи закрыли {summary['tasksDone']} из {summary['tasksAssigned']}"
            f" · их оценили все, кто должен {summary['fullyEvaluated']} из {summary['evaluationOwed']}"
        ),
    ]


def login(base: str, email: str):
    status, body = call(
        base, "POST", "auth/login", body={"email": email, "password": FIXTURE_PASSWORD}
    )
    token = body.get("token") if status == 200 and isinstance(body, dict) else None
    return status, token, body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--db", required=True)
    parser.add_argument(
        "--out",
        default=str(REPO / "backups/2026-08-27-admin-users-summary/prove.json"),
    )
    args = parser.parse_args()

    if not args.db.startswith("epe_adminusers_"):
        print("refusing to prove against a non-stand database", args.db, file=sys.stderr)
        return 1

    sql_raw = ssh_sql(args.db, INDEPENDENT_SQL)
    sql = json.loads(sql_raw)
    PROOF["sql"] = sql

    applicable = ssh_sql(args.db, """
      WITH manager_applicable AS (
        SELECT u.id AS subject_id, c.id AS criteria_id
        FROM performance_db.users u
        JOIN performance_db.criteria c
          ON c.is_active = true AND c.c_level_only = false
        WHERE u.id IN (1303, 1304, 1308)
          AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)
          AND (c.target_audience <> 'managers_only' OR u.has_subordinates = true)
      )
      SELECT json_agg(json_build_object(
        'subject_id', subject_id,
        'criteria', (
          SELECT string_agg(criteria_id::text, ',' ORDER BY criteria_id)
          FROM manager_applicable m2 WHERE m2.subject_id = m.subject_id
        )
      ) ORDER BY subject_id)
      FROM (SELECT DISTINCT subject_id FROM manager_applicable) m;
    """)
    PROOF["applicable_manager_criteria"] = json.loads(applicable) if applicable else []

    status, token, body = login(args.base, "wt.admin@sedamedical.com")
    check("admin login", status, 200)
    if not token:
        print("login failed", body, file=sys.stderr)
        return 1
    PROOF["admin_login"] = {"status": status, "user_id": (body or {}).get("user", {}).get("id")}

    status, payload = call(args.base, "GET", "api/admin-users-data", token)
    check("admin-users-data status", status, 200)
    users = (payload or {}).get("users") if isinstance(payload, dict) else None
    if not isinstance(users, list) or not users:
        print("empty roster", payload, file=sys.stderr)
        return 1
    PROOF["roster_size"] = len(users)

    js = build_summary(users)
    PROOF["js"] = js
    PROOF["rendered_lines"] = format_lines(js)

    keys = [
        "everyone", "terminated", "employed", "inScope", "evaluatedBySomeone",
        "invited", "registeredInvited", "tasksAssigned", "tasksDone",
        "fullyEvaluated", "evaluationOwed",
    ]
    side_by_side = []
    for key in keys:
        row = {"counter": key, "sql": sql[key], "js": js[key]}
        side_by_side.append(row)
        check(f"sql==js {key}", sql[key], js[key])
    PROOF["side_by_side"] = side_by_side

    by_id = {int(u["id"]): u for u in users}
    u25 = by_id.get(25)
    u21 = by_id.get(21)
    u1303 = by_id.get(1303)
    u1308 = by_id.get(1308)
    u1304 = by_id.get(1304)
    PROOF["id25"] = {
        "name": (u25 or {}).get("full_name"),
        "period_is_in_scope": (u25 or {}).get("period_is_in_scope"),
        "can_be_evaluated": (u25 or {}).get("can_be_evaluated"),
        "has_task": has_assigned_task(u25 or {}),
        "evaluated_subject": is_evaluated_subject(u25 or {}),
    }
    PROOF["id21"] = {
        "name": (u21 or {}).get("full_name"),
        "period_is_in_scope": (u21 or {}).get("period_is_in_scope"),
        "can_be_evaluated": (u21 or {}).get("can_be_evaluated"),
        "evaluated_subject": is_evaluated_subject(u21 or {}),
    }

    check("id 25 is out of scope (SQL)", sql["id25_in_scope"], False)
    check("id 25 not in tasks denominator (SQL)", sql["id25_has_task"], False)
    check("id 25 not in evaluated-BY denominator (SQL)", sql["id25_evaluated_subject"], False)
    check("id 25 out of scope (API)", is_in_scope(u25 or {}), False)
    check("id 25 not a completion subject (API)", is_evaluated_subject(u25 or {}), False)
    check("id 25 not in tasks (API)", has_assigned_task(u25 or {}), False)

    check("id 21 is in scope (SQL)", sql["id21_in_scope"], True)
    check("id 21 is not an evaluated subject (SQL)", sql["id21_evaluated_subject"], False)
    check("id 21 can_be_evaluated false (SQL)", sql["id21_can_be_evaluated"], False)
    check("id 21 in scope (API)", is_in_scope(u21 or {}), True)
    check("id 21 not evaluated-BY (API)", is_evaluated_subject(u21 or {}), False)

    check("two populations differ (inScope > evaluatedBySomeone)", sql["inScope"] > sql["evaluatedBySomeone"], True)
    check("two directions differ as people (1303 vs 1308)", True, True)
    check("1303 tasks not done (SQL)", sql["id1303_tasks_done"], False)
    check("1303 fully evaluated (SQL)", sql["id1303_fully"], True)
    check("1308 tasks done (SQL)", sql["id1308_tasks_done"], True)
    check("1308 not fully evaluated (SQL)", sql["id1308_fully"], False)
    check("1304 both directions (SQL tasks)", sql["id1304_tasks_done"], True)
    check("1304 both directions (SQL fully)", sql["id1304_fully"], True)
    check("1303 tasks not done (API)", finished_tasks(u1303 or {}), False)
    check("1303 fully evaluated (API)", fully_evaluated(u1303 or {}), True)
    check("1308 tasks done (API)", finished_tasks(u1308 or {}), True)
    check("1308 not fully evaluated (API)", fully_evaluated(u1308 or {}), False)
    check("c_level_direct is seeded and ignored by Welcome counters", sql["c_level_direct_rows"] >= 1, True)
    check("c_level_direct did not finish 1303's assigned tasks", sql["id1303_tasks_done"], False)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(PROOF, ensure_ascii=False, indent=2) + "\n")
    print("RENDERED LINES:")
    for line in PROOF["rendered_lines"]:
        print(f"  {line}")
    print("SIDE BY SIDE:")
    for row in side_by_side:
        print(f"  {row['counter']:22} sql={row['sql']}  js={row['js']}")
    if FAILURES:
        print("FAIL", *FAILURES, sep="\n", file=sys.stderr)
        return 1
    print("PASS", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

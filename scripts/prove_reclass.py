#!/usr/bin/env python3
"""Acceptance proof for live reclassification (brief 2026-08-24, D-0822-3).

Runs against the isolated stand from setup_reclass_throwaway.sh:
n8n on 127.0.0.1:25679 (tunneled), throwaway DB epe_reclass_* on the VPS.

Every check records the COMPARED VALUES, not a verdict string: a run that
compared nothing fails loudly instead of writing the same slogan as a run
that compared everything.

Proves, per the brief:
  - BUG-043: with no active leaf period /api/employees answers "none", never
    the annual container id 5; the preparation window still names H1
  - weight floor 0.1: 0 / 0.05 / 0.09 rejected 422, 0.1 accepted and stored
  - role x route regression on every touched route
  - P (project, coef 2.20) evaluated on the full applicable set -> index I1;
    P -> general: matrix excludes 8/13 AND their corrections (I2 < I1) while
    every score row survives in the database; ordinary edit keeps the
    excluded rows; P -> project again restores I1 to the digit
  - G (general, coef 0.60) evaluated on 3 criteria -> flag done; G -> project
    reopens the manager flag naming [8, 13]; the additive submit adds exactly
    those; calculated_score equals an independent average over all five
    surviving rows; re-adding an already-scored criterion is refused
  - write validation: a project criterion for a general subject is 422 on
    submit, additive, update and self-review, with row counts unchanged
  - close regression: persisted period_results equal an independent replay of
    the client matrix pipeline under the new emission filter; the frozen rows
    do not move when the classification is switched after close
  - BUG-041 runtime repro: the pre-fix statement (RECON §7.2 text) executed
    against a zero-row header DELETES score rows; the deployed statement
    executed under identical conditions deletes nothing (row counts shown)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent

ACTORS = {
    "admin":            (1301, "33333333-3333-4333-8333-333333333301"),
    "manager":          (1302, "33333333-3333-4333-8333-333333333302"),
    "employee_g":       (1303, "33333333-3333-4333-8333-333333333303"),
    "employee_p":       (1304, "33333333-3333-4333-8333-333333333304"),
    "c_level":          (1305, "33333333-3333-4333-8333-333333333305"),
    "c_level_readonly": (1306, "33333333-3333-4333-8333-333333333306"),
    "hr":               (1307, "33333333-3333-4333-8333-333333333307"),
    "employee_n":       (1308, "33333333-3333-4333-8333-333333333308"),
    "employee_r":       (1309, "33333333-3333-4333-8333-333333333309"),
}

H1 = 2            # half_year leaf, draft in the restored dump
ANNUAL_2026 = 5   # container (parent of H1)
MANAGER = 1302
G, P, N, R = 1303, 1304, 1308, 1309

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 4 * 3600, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def call(base: str, method: str, path: str, *, token: str | None = None,
         body: dict[str, Any] | None = None) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def sql(database: str, statement: str) -> str:
    if not database.startswith("epe_reclass_"):
        raise SystemExit(f"Refusing non-throwaway database: {database}")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


CHECKS_RUN = 0


def check(name: str, actual: Any, expected: Any) -> bool:
    global CHECKS_RUN
    CHECKS_RUN += 1
    ok = actual == expected
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def record(section: str, key: str, value: Any) -> None:
    REPORT.setdefault(section, {})[key] = value


# ── independent client-pipeline replica (formula #1 cell + formula #3 index) ──

def criterion_final(crit: dict[str, Any]) -> float | None:
    if crit.get("c_level_only"):
        return float(crit["c_level_score"]) if crit.get("c_level_score") is not None else None
    if crit.get("manager_score") is None:
        return None
    scores = [float(crit["manager_score"])]
    if crit.get("mid_level_correction") is not None:
        scores.append(float(crit["mid_level_correction"]))
    if crit.get("c_level_correction") is not None:
        scores.append(float(crit["c_level_correction"]))
    return sum(scores) / len(scores)


def client_pipeline(matrix_rows: list[dict], coefficients: list[dict],
                    grade_map: dict[str, float]) -> dict[int, dict[str, Any]]:
    coef_map = {int(c["id"]): c for c in coefficients}
    out: dict[int, dict[str, Any]] = {}
    for emp in matrix_rows:
        finals: list[float] = []
        weighted_sum = 0.0
        cell_ids: list[int] = []
        for crit in emp.get("criteria") or []:
            cell_ids.append(int(crit["criteria_id"]))
            raw = criterion_final(crit)
            if raw is None:
                continue
            finals.append(raw)
            coefs = coef_map.get(int(crit["criteria_id"]))
            if not coefs:
                weighted_sum += raw
                continue
            weight = float(coefs.get("weight") or 1.0)
            level = max(0, min(10, int(raw + 0.5)))
            level_map = coefs.get("levels") or {}
            level_value = level_map.get(str(level), level_map.get(level))
            coefficient = 1.0 if level_value is None else float(level_value)
            weighted_sum += raw * coefficient * weight
        grade_coefficient = grade_map.get(emp.get("grade_code") or "", 1.0)
        out[int(emp["id"])] = {
            "final": round(sum(finals) / len(finals), 6) if finals else None,
            "index": round(weighted_sum * grade_coefficient, 6) if finals else None,
            "cells": sorted(cell_ids),
        }
    return out


def fetch_matrix(base: str, token: str, period_id: int | None = None) -> list[dict]:
    path = "api/admin/evaluations-matrix"
    if period_id is not None:
        path += f"?period_id={period_id}"
    status, body = call(base, "GET", path, token=token)
    if status != 200:
        raise SystemExit(f"matrix fetch failed: {status} {body}")
    return (body or {}).get("data") or []


def matrix_fixture_rows(base: str, token: str, period_id: int | None = None) -> list[dict]:
    return [r for r in fetch_matrix(base, token, period_id) if 1301 <= int(r["id"]) <= 1310]


def extract_update_sql(evaluation_id: int, actor_id: int, score_rows: str) -> str:
    """The DEPLOYED update statement, byte-sourced from the tracked artifact."""
    wf = json.loads((REPO / "n8n_workflows/route_guard_h1/update-evaluation.json").read_text())
    node = next(n for n in wf["nodes"] if n["name"] == "Build Update SQL")
    js = node["parameters"]["jsCode"]
    match = re.search(r"sql: `\n(WITH score_rows[\s\S]*?FROM updated_header uh)\n\s*`", js)
    if not match:
        raise SystemExit("could not extract the update SQL template from the tracked artifact")
    template = match.group(1)
    return (template
            .replace("${scoreRows.join(', ')}", score_rows)
            .replace("${generalCommentSql}", "NULL")
            .replace("${evalId}", str(evaluation_id))
            .replace("${actorId}", str(actor_id)))


# The PRE-FIX statement, verbatim from docs/RECON_RECLASS_COEFF_2026-08-2x.md §7.2
# (live before 2026-08-22): the reassertion was "period is not closed", and
# removed_scores was gated on nothing but the evaluation id.
PRE_FIX_UPDATE_SQL = """
WITH score_rows(crit_id, score_val, cmt) AS ( VALUES {score_rows} ),
updated_header AS (
  UPDATE performance_db.evaluations
  SET calculated_score = (SELECT AVG(score_val::numeric) FROM score_rows),
      general_comment = NULL, updated_at = now()
  WHERE id = {eval_id}
    AND evaluator_id = {actor_id}
    AND (SELECT status FROM performance_db.evaluation_periods WHERE id = period_id) != 'closed'
  RETURNING id, calculated_score
),
upserted_scores AS (
  INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
  SELECT uh.id, sr.crit_id, sr.score_val, sr.cmt
  FROM updated_header uh CROSS JOIN score_rows sr
  ON CONFLICT (evaluation_id, criteria_id) DO UPDATE
    SET score_value = EXCLUDED.score_value, comment = EXCLUDED.comment
  RETURNING criteria_id
),
removed_scores AS (
  DELETE FROM performance_db.evaluation_scores
  WHERE evaluation_id = {eval_id}
    AND criteria_id NOT IN (SELECT crit_id FROM score_rows)
  RETURNING criteria_id
)
SELECT uh.id AS evaluation_id, uh.calculated_score AS final_score,
       (SELECT count(*)::integer FROM upserted_scores) AS scores_saved
FROM updated_header uh
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--env-file", type=Path,
                        default=REPO / "backups/2026-08-24-reclass/throwaway_env.json")
    parser.add_argument("--output", type=Path,
                        default=REPO / "backups/2026-08-24-reclass/reclass_proof.json")
    args = parser.parse_args()

    env = json.loads(args.env_file.read_text())
    db = env["database"]
    secret = env["jwt_secret"]
    base = args.base_url
    tok = {name: mint(secret, uid, jti) for name, (uid, jti) in ACTORS.items()}

    record("stand", "database", db)
    record("stand", "base_url", base)

    # ── catalogue + grade coefficients used by every recomputation ────────────
    catalogue = json.loads(sql(db, """
      SELECT COALESCE(json_agg(json_build_object(
        'id', c.id, 'weight', c.weight, 'target_audience', c.target_audience,
        'levels', COALESCE((SELECT json_object_agg(sc.score_level::text, sc.coefficient)
                            FROM performance_db.score_coefficients sc
                            WHERE sc.criteria_id = c.id), '{}'::json)
      ) ORDER BY c.id), '[]'::json)
      FROM performance_db.criteria c WHERE c.is_active = true"""))
    grade_map = {code: float(coef) for code, coef in
                 (line.split("|") for line in sql(
                     db, "SELECT code || '|' || coefficient FROM performance_db.grades").splitlines())}
    project_ids = sorted(int(c["id"]) for c in catalogue
                         if c["target_audience"] == "project_participants")
    record("catalogue", "project_criteria_ids", project_ids)
    check("catalogue: project criteria are 8 and 13", project_ids, [8, 13])

    def employees_view(actor: str) -> dict[str, Any]:
        status, body = call(base, "GET", "api/employees", token=tok[actor])
        if status != 200:
            raise SystemExit(f"employees fetch failed for {actor}: {status} {body}")
        return body

    def employee_row(actor: str, subject: int) -> dict[str, Any] | None:
        rows = employees_view(actor).get("data") or []
        return next((r for r in rows if int(r["id"]) == subject), None)

    def score_rows_in_db(subject: int, evaluator: int = MANAGER,
                         source: str = "manager") -> list[int]:
        raw = sql(db, f"""
          SELECT COALESCE(json_agg(es.criteria_id ORDER BY es.criteria_id), '[]'::json)
          FROM performance_db.evaluations e
          JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
          WHERE e.subject_id = {subject} AND e.evaluator_id = {evaluator}
            AND e.evaluation_source = '{source}' AND e.period_id = {H1}
            AND e.is_self_evaluation = false""")
        return json.loads(raw)

    def calculated_score_in_db(subject: int, evaluator: int = MANAGER) -> float | None:
        raw = sql(db, f"""
          SELECT calculated_score FROM performance_db.evaluations
          WHERE subject_id = {subject} AND evaluator_id = {evaluator}
            AND evaluation_source = 'manager' AND period_id = {H1}
            AND is_self_evaluation = false""")
        return float(raw) if raw else None

    # =========================================================================
    # 0. BUG-043 — draft state: the current period is "none", never id 5
    # =========================================================================
    for actor in ("admin", "manager", "employee_g", "hr"):
        view = employees_view(actor)
        record("bug043_draft", actor, {
            "current_period_id": view.get("current_period_id"),
            "current_period_status": view.get("current_period_status"),
            "campaign_active": view.get("campaign_active"),
            "period_in_preparation": view.get("period_in_preparation"),
            "actor_is_in_scope": view.get("actor_is_in_scope"),
        })
        check(f"bug043 draft/{actor}: current period is none", view.get("current_period_id"), None)
        check(f"bug043 draft/{actor}: container id 5 never current",
              view.get("current_period_id") == ANNUAL_2026, False)
        check(f"bug043 draft/{actor}: scope is null with no period",
              view.get("actor_is_in_scope"), None)
        check(f"bug043 draft/{actor}: no preparation flag without an active period",
              view.get("period_in_preparation"), False)

    # =========================================================================
    # 1. Activate (preparation window) and start
    # =========================================================================
    status, body = call(base, "POST", "api/periods/activate", token=tok["admin"],
                        body={"period_id": H1})
    check("activate H1", status, 200)
    view = employees_view("employee_g")
    record("preparation", "employee_view", {
        "current_period_id": view.get("current_period_id"),
        "period_in_preparation": view.get("period_in_preparation"),
        "actor_is_in_scope": view.get("actor_is_in_scope"),
        "campaign_active": view.get("campaign_active"),
    })
    check("preparation: current period is the H1 leaf", view.get("current_period_id"), H1)
    check("preparation: in-preparation flag", view.get("period_in_preparation"), True)
    check("preparation: scope is real", view.get("actor_is_in_scope"), True)

    status, body = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                        body={"period_id": H1})
    check("start H1", status, 200)

    # =========================================================================
    # 2. Weight floor 0.1 (criterion 12; original weight restored afterwards)
    # =========================================================================
    crit12 = next(c for c in catalogue if int(c["id"]) == 12)
    original_weight = float(crit12["weight"])
    levels12 = {str(i): float(crit12["levels"][str(i)]) for i in range(1, 11)}

    def weight_save(weight: float) -> tuple[int, Any]:
        return call(base, "POST", "api/score-coefficients", token=tok["admin"], body={
            "criteria": [{"id": 12, "weight": weight, "score_coefficients": levels12}],
        })

    floor_results = {}
    for value in (0, 0.05, 0.09):
        status, body = weight_save(value)
        stored = float(sql(db, "SELECT weight FROM performance_db.criteria WHERE id = 12"))
        floor_results[str(value)] = {"status": status, "error": (body or {}).get("error"),
                                     "stored_after": stored}
        check(f"weight floor: {value} rejected", (status, (body or {}).get("error")),
              (422, "INVALID_WEIGHT"))
        check(f"weight floor: {value} did not change the stored weight", stored, original_weight)
    status, body = weight_save(0.1)
    stored = float(sql(db, "SELECT weight FROM performance_db.criteria WHERE id = 12"))
    floor_results["0.1"] = {"status": status, "stored_after": stored}
    check("weight floor: 0.1 accepted", status, 200)
    check("weight floor: 0.1 stored", stored, 0.1)
    status, _ = weight_save(original_weight)
    check("weight floor: original weight restored", status, 200)
    check("weight floor: stored back to original",
          float(sql(db, "SELECT weight FROM performance_db.criteria WHERE id = 12")), original_weight)
    record("weight_floor", "results", floor_results)

    # =========================================================================
    # 3. Role x route regression on every touched route (non-mutating bodies)
    # =========================================================================
    role_matrix: dict[str, dict[str, Any]] = {}
    probes = [
        ("GET",  "api/employees",                 None,                       "employees"),
        ("GET",  "api/check-evaluated",           None,                       "check_evaluated"),
        ("GET",  "api/check-self-review",         None,                       "check_self_review"),
        ("GET",  "api/get-my-manager",            None,                       "get_my_manager"),
        ("GET",  "api/admin/evaluations-matrix",  None,                       "matrix"),
        ("POST", "api/submit-evaluation",         {},                         "submit"),
        ("POST", "api/update-evaluation",         {},                         "update"),
        ("POST", "api/self-review-submit",        {},                         "self_review"),
        ("POST", "admin/save-user",               {},                         "save_user"),
        ("POST", "api/score-coefficients",        {},                         "save_coefficients"),
        ("POST", "api/admin/score-correction",    {},                         "score_correction"),
        ("POST", "api/periods/close",             {"period_id": 999999},      "close_unknown"),
    ]
    for actor in ("admin", "manager", "employee_g", "c_level", "c_level_readonly", "hr"):
        row: dict[str, Any] = {}
        for method, path, body_probe, label in probes:
            status, body = call(base, method, path, token=tok[actor], body=body_probe)
            row[label] = {"status": status, "error": (body or {}).get("error")
                          if isinstance(body, dict) else None}
        role_matrix[actor] = row
    record("role_route_matrix", "results", role_matrix)
    expect = [
        ("admin",            "matrix", 200, None),
        ("c_level",          "matrix", 200, None),
        ("c_level_readonly", "matrix", 200, None),
        ("hr",               "matrix", 403, "ROLE_FORBIDDEN"),
        ("manager",          "matrix", 403, "ROLE_FORBIDDEN"),
        ("employee_g",       "matrix", 403, "ROLE_FORBIDDEN"),
        ("admin",            "submit", 422, "INVALID_SUBJECT"),
        ("manager",          "submit", 422, "INVALID_SUBJECT"),
        ("hr",               "submit", 403, "CAPABILITY_FORBIDDEN"),
        ("c_level_readonly", "submit", 403, "CAPABILITY_FORBIDDEN"),
        ("manager",          "update", 422, "INVALID_EVALUATION_ID"),
        ("hr",               "update", 403, "CAPABILITY_FORBIDDEN"),
        ("c_level_readonly", "update", 403, "CAPABILITY_FORBIDDEN"),
        ("admin",            "self_review", 403, "ROLE_FORBIDDEN"),
        ("c_level",          "self_review", 403, "ROLE_FORBIDDEN"),
        ("employee_g",       "self_review", 422, "INVALID_SCORE"),
        ("hr",               "self_review", 422, "INVALID_SCORE"),
        ("admin",            "save_user", 422, "INVALID_NAME"),
        ("manager",          "save_user", 403, "ROLE_FORBIDDEN"),
        ("c_level",          "save_user", 403, "ROLE_FORBIDDEN"),
        ("hr",               "save_user", 403, "ROLE_FORBIDDEN"),
        ("admin",            "save_coefficients", 422, "INVALID_BODY"),
        ("c_level",          "save_coefficients", 403, "ROLE_FORBIDDEN"),
        ("hr",               "save_coefficients", 403, "ROLE_FORBIDDEN"),
        ("admin",            "score_correction", 422, "INVALID_BODY"),
        ("c_level",          "score_correction", 422, "INVALID_BODY"),
        ("c_level_readonly", "score_correction", 403, "CAPABILITY_FORBIDDEN"),
        ("hr",               "score_correction", 403, "ROLE_FORBIDDEN"),
        ("admin",            "close_unknown", 404, "PERIOD_NOT_FOUND"),
        ("manager",          "close_unknown", 403, "ROLE_FORBIDDEN"),
        ("employee_g",       "employees", 200, None),
        ("hr",               "employees", 200, None),
    ]
    for actor, label, want_status, want_error in expect:
        got = role_matrix[actor][label]
        check(f"role matrix {actor}/{label}", (got["status"], got["error"]),
              (want_status, want_error))

    # =========================================================================
    # 4. P: full applicable set -> I1; corrections attach to criterion 13
    # =========================================================================
    p_grades = {"3": 8, "4": 6, "8": 9, "12": 7, "13": 10}
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": P, "grades": p_grades})
    check("P: full-set submit", status, 200)
    check("P: calculated_score is the plain average of 5 rows",
          calculated_score_in_db(P), 8.0)

    row = employee_row("manager", P)
    check("P: evaluated_by_actor true on the full set", row.get("evaluated_by_actor"), True)
    check("P: no missing criteria", row.get("missing_criteria_ids"), [])

    # corrections + c_level_direct rows (also exercises the close branches
    # BUG-039 named as never executed end-to-end)
    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": P, "criteria_id": 13, "correction_score": 6})
    check("P: c_level correction on criterion 13", status, 200)
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["c_level"],
                        body={"subject_id": P, "evaluation_source": "c_level_direct",
                              "grades": {"1": 7, "10": 8}})
    check("P: c_level_direct scores for criteria 1 and 10", status, 200)

    pipeline_1 = client_pipeline(matrix_fixture_rows(base, tok["admin"]), catalogue, grade_map)
    i1 = pipeline_1[P]
    record("p_flow", "I1_project_with_corrections", i1)
    check("P/I1: matrix emits every active cell for a project person",
          i1["cells"], [1, 2, 3, 4, 8, 10, 12, 13])

    # =========================================================================
    # 5. Write validation: project criterion for a general subject -> 422
    # =========================================================================
    rows_before = sql(db, f"SELECT count(*) FROM performance_db.evaluations WHERE subject_id = {N}")
    scores_before = sql(db, "SELECT count(*) FROM performance_db.evaluation_scores")
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": N, "grades": {"8": 5}})
    rows_after = sql(db, f"SELECT count(*) FROM performance_db.evaluations WHERE subject_id = {N}")
    scores_after = sql(db, "SELECT count(*) FROM performance_db.evaluation_scores")
    record("write_validation", "submit_project_criterion_for_general", {
        "status": status, "error": (body or {}).get("error"),
        "evaluations_before": rows_before, "evaluations_after": rows_after,
        "scores_before": scores_before, "scores_after": scores_after,
    })
    check("submit: project criterion for general subject is 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))
    check("submit 422: no evaluation row written", rows_after, rows_before)
    check("submit 422: no score row written", scores_after, scores_before)

    status, body = call(base, "POST", "api/self-review-submit", token=tok["employee_n"],
                        body={"final_score": 5, "grades": {"3": 5, "8": 5}})
    check("self-review: project criterion for a general actor is 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))

    # N gets a clean 3-criteria evaluation, then an additive attempt with a
    # project criterion while N is still general: applicability precedes the
    # additive branch.
    status, _ = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                     body={"subject_id": N, "grades": {"3": 6, "4": 6, "12": 6}})
    check("N: 3-criteria submit", status, 200)
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": N, "grades": {"8": 5}})
    check("N: additive with a project criterion while general is still 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))

    # =========================================================================
    # 6. P -> general: soft exclusion everywhere, nothing deleted
    # =========================================================================
    def save_user_category(subject: int, category: str) -> tuple[int, Any]:
        user_row = json.loads(sql(db, f"""
          SELECT row_to_json(u) FROM (
            SELECT id, full_name, email, role, job_title, department_id, grade_id, manager_id
            FROM performance_db.users WHERE id = {subject}) u"""))
        return call(base, "POST", "admin/save-user", token=tok["admin"], body={
            "id": subject, "full_name": user_row["full_name"], "email": user_row["email"],
            "role": user_row["role"], "job_title": user_row["job_title"],
            "department_id": user_row["department_id"], "grade_id": user_row["grade_id"],
            "manager_id": user_row["manager_id"], "work_category": category,
        })

    status, body = save_user_category(P, "general")
    record("p_flow", "switch_to_general", {"status": status,
                                           "user": (body or {}).get("user", {}).get("work_category")})
    check("P -> general: save-user accepts mid-campaign (no freeze)", status, 200)
    check("P -> general: is_project_participant derived false",
          sql(db, f"SELECT is_project_participant FROM performance_db.users WHERE id = {P}"), "f")

    db_rows_general = score_rows_in_db(P)
    pipeline_2 = client_pipeline(matrix_fixture_rows(base, tok["admin"]), catalogue, grade_map)
    i2 = pipeline_2[P]
    record("p_flow", "I2_general", i2)
    record("p_flow", "db_rows_while_general", db_rows_general)
    check("P/I2: matrix cells exclude 8 and 13 (the correction on 13 goes with its cell)",
          i2["cells"], [1, 2, 3, 4, 10, 12])
    check("P/I2: index dropped", i2["index"] < i1["index"], True)
    check("P/I2: DB still holds all five manager rows", db_rows_general, [3, 4, 8, 12, 13])

    row = employee_row("manager", P)
    check("P general: flag stays done (all currently-applicable covered)",
          row.get("evaluated_by_actor"), True)
    check("P general: nothing missing", row.get("missing_criteria_ids"), [])

    # ordinary edit while P is general: 422 for an excluded criterion; a clean
    # edit of the applicable set keeps the excluded rows
    eval_p = int(sql(db, f"""
      SELECT id FROM performance_db.evaluations
      WHERE subject_id = {P} AND evaluator_id = {MANAGER}
        AND evaluation_source = 'manager' AND period_id = {H1}"""))
    status, body = call(base, "POST", "api/update-evaluation", token=tok["manager"],
                        body={"evaluation_id": eval_p,
                              "grades": {"3": 8, "4": 6, "12": 7, "8": 9}})
    check("update: excluded criterion in the payload is 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))
    check("update 422: rows untouched", score_rows_in_db(P), [3, 4, 8, 12, 13])

    status, body = call(base, "POST", "api/update-evaluation", token=tok["manager"],
                        body={"evaluation_id": eval_p, "grades": {"3": 8, "4": 6, "12": 7}})
    record("p_flow", "ordinary_edit_while_general",
           {"status": status, "final_score": (body or {}).get("final_score"),
            "rows_after": score_rows_in_db(P)})
    check("update: ordinary edit of the applicable set succeeds", status, 200)
    check("update: the excluded rows 8 and 13 SURVIVE the edit",
          score_rows_in_db(P), [3, 4, 8, 12, 13])
    check("update: calculated_score averages the applicable set only",
          (body or {}).get("final_score"), 7.0)

    # =========================================================================
    # 7. P -> project again: I1 restored to the digit
    # =========================================================================
    status, _ = save_user_category(P, "project")
    check("P -> project again", status, 200)
    pipeline_3 = client_pipeline(matrix_fixture_rows(base, tok["admin"]), catalogue, grade_map)
    i3 = pipeline_3[P]
    record("p_flow", "I3_project_again", i3)
    check("P restored: index equals I1 to the digit", i3["index"], i1["index"])
    check("P restored: final equals I1 final", i3["final"], i1["final"])
    check("P restored: cells match I1", i3["cells"], i1["cells"])

    # =========================================================================
    # 8. G: 3 criteria -> done; G -> project reopens; additive adds 8/13 only
    # =========================================================================
    g_grades = {"3": 8, "4": 6, "12": 9}
    status, _ = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                     body={"subject_id": G, "grades": g_grades})
    check("G: 3-criteria submit", status, 200)
    row = employee_row("manager", G)
    check("G general: flag done", row.get("evaluated_by_actor"), True)
    check("G general: nothing missing", row.get("missing_criteria_ids"), [])

    status, _ = save_user_category(G, "project")
    check("G -> project", status, 200)
    row = employee_row("manager", G)
    record("g_flow", "after_switch", {
        "evaluated_by_actor": row.get("evaluated_by_actor"),
        "missing_criteria_ids": row.get("missing_criteria_ids"),
    })
    check("G project: manager flag REOPENS", row.get("evaluated_by_actor"), False)
    check("G project: the missing criteria are named", row.get("missing_criteria_ids"), [8, 13])

    scores_before = int(sql(db, "SELECT count(*) FROM performance_db.evaluation_scores"))
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": G, "grades": {"8": 9, "13": 7},
                              "final_score": 999.99})
    scores_after = int(sql(db, "SELECT count(*) FROM performance_db.evaluation_scores"))
    record("g_flow", "additive", {"status": status, "body": body,
                                  "scores_added_rows": scores_after - scores_before})
    check("G additive: accepted", status, 200)
    check("G additive: response says extended", (body or {}).get("scores_added"), 2)
    check("G additive: exactly two rows added", scores_after - scores_before, 2)
    check("G additive: DB rows are the five", score_rows_in_db(G), [3, 4, 8, 12, 13])

    independent_avg = round((8 + 6 + 9 + 9 + 7) / 5, 6)
    stored_calc = calculated_score_in_db(G)
    db_avg = float(sql(db, f"""
      SELECT ROUND(AVG(es.score_value::numeric), 6)
      FROM performance_db.evaluations e
      JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
      WHERE e.subject_id = {G} AND e.evaluator_id = {MANAGER}
        AND e.evaluation_source = 'manager' AND e.period_id = {H1}"""))
    record("g_flow", "calculated_score", {"stored": stored_calc,
                                          "independent_python": independent_avg,
                                          "independent_sql": db_avg,
                                          "client_sent": 999.99})
    check("G additive: calculated_score equals the independent 5-row average",
          round(stored_calc, 6), independent_avg)
    check("G additive: SQL average agrees", db_avg, independent_avg)

    row = employee_row("manager", G)
    check("G project: flag closes after the additive write",
          row.get("evaluated_by_actor"), True)
    check("G project: nothing missing any more", row.get("missing_criteria_ids"), [])

    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": G, "grades": {"8": 5}})
    check("G: re-adding an already-scored criterion is refused",
          (status, (body or {}).get("error")), (409, "CRITERIA_ALREADY_SCORED"))
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": G, "grades": {"3": 1, "4": 1, "8": 1, "12": 1, "13": 1}})
    check("G: a full re-submit is refused by the same rule",
          (status, (body or {}).get("error")), (409, "CRITERIA_ALREADY_SCORED"))
    check("G: the refused attempts changed nothing",
          round(calculated_score_in_db(G), 6), independent_avg)

    # =========================================================================
    # 9. Self-review + upward (row-existence flags unchanged) and R for BUG-041
    # =========================================================================
    status, _ = call(base, "POST", "api/self-review-submit", token=tok["employee_g"],
                     body={"final_score": 7.67, "grades": {"3": 8, "4": 6, "12": 9}})
    check("G: self-review accepted", status, 200)
    status, _ = call(base, "POST", "api/submit-evaluation", token=tok["employee_g"],
                     body={"subject_id": MANAGER, "evaluation_source": "subordinate",
                           "grades": {"2": 9}})
    check("G: upward evaluation accepted", status, 200)
    row = employee_row("manager", G)
    check("G: has_self_review stays row-existence", row.get("has_self_review"), True)
    check("G: has_evaluated_manager stays row-existence", row.get("has_evaluated_manager"), True)

    status, _ = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                     body={"subject_id": R, "grades": {"3": 5, "4": 5, "12": 5}})
    check("R: BUG-041 carrier evaluation", status, 200)
    eval_r = int(sql(db, f"""
      SELECT id FROM performance_db.evaluations
      WHERE subject_id = {R} AND evaluator_id = {MANAGER}
        AND evaluation_source = 'manager' AND period_id = {H1}"""))

    # =========================================================================
    # 10. Close regression: persisted results equal the replica under the
    #     new emission filter (P is GENERAL at close: 8/13 must be excluded
    #     from the frozen numbers too)
    # =========================================================================
    status, _ = save_user_category(P, "general")
    check("P -> general before close", status, 200)
    pre_close_rows = matrix_fixture_rows(base, tok["admin"])
    pre_close = client_pipeline(pre_close_rows, catalogue, grade_map)
    record("close", "pre_close_pipeline", {str(k): v for k, v in pre_close.items()})

    status, body = call(base, "POST", "api/periods/close", token=tok["admin"],
                        body={"period_id": H1})
    record("close", "response", {"status": status,
                                 "results_stored": (body or {}).get("results_stored")})
    check("close of the started period succeeds", status, 200)

    persisted = json.loads(sql(db, f"""
      SELECT COALESCE(json_agg(json_build_object(
        'user_id', pr.user_id, 'final_rating', pr.final_rating,
        'bonus_index', pr.bonus_index, 'has_data', pr.has_data) ORDER BY pr.user_id), '[]'::json)
      FROM performance_db.period_results pr
      WHERE pr.period_id = {H1} AND pr.user_id BETWEEN 1301 AND 1310"""))
    compared = []
    for row_p in persisted:
        uid = int(row_p["user_id"])
        expected = pre_close.get(uid, {"final": None, "index": None})
        stored_final = None if row_p["final_rating"] is None else round(float(row_p["final_rating"]), 4)
        stored_index = None if row_p["bonus_index"] is None else round(float(row_p["bonus_index"]), 4)
        want_final = None if expected["final"] is None else round(expected["final"], 4)
        want_index = None if expected["index"] is None else round(expected["index"], 4)
        compared.append({"user_id": uid, "persisted_final": stored_final,
                         "replica_final": want_final, "persisted_index": stored_index,
                         "replica_index": want_index})
        check(f"close/{uid}: persisted final equals the replica", stored_final, want_final)
        check(f"close/{uid}: persisted index equals the replica", stored_index, want_index)
    record("close", "compared", compared)
    check("close: P's frozen index is the EXCLUDED one (I2 shape, not I1)",
          round(float(next(r for r in persisted if int(r["user_id"]) == P)["bonus_index"]), 4)
          < round(i1["index"], 4), True)

    # the frozen rows do not move when the classification changes after close
    fingerprint_before = sql(db, f"""
      SELECT md5(string_agg(pr.user_id || ':' || COALESCE(pr.final_rating::text, 'x')
                 || ':' || COALESCE(pr.bonus_index::text, 'x'), ',' ORDER BY pr.user_id))
      FROM performance_db.period_results pr WHERE pr.period_id = {H1}""")
    status, _ = save_user_category(P, "project")
    check("post-close: classification switch still allowed", status, 200)
    fingerprint_after = sql(db, f"""
      SELECT md5(string_agg(pr.user_id || ':' || COALESCE(pr.final_rating::text, 'x')
                 || ':' || COALESCE(pr.bonus_index::text, 'x'), ',' ORDER BY pr.user_id))
      FROM performance_db.period_results pr WHERE pr.period_id = {H1}""")
    record("close", "fingerprints", {"before": fingerprint_before, "after": fingerprint_after})
    check("post-close: period_results byte-identical after the switch",
          fingerprint_after, fingerprint_before)

    # ...while the live-joined read view restores I1 for the read-only inspect
    inspect = client_pipeline(matrix_fixture_rows(base, tok["admin"], period_id=H1),
                              catalogue, grade_map)
    record("close", "post_close_inspect_P", inspect[P])
    check("post-close inspect: live-joined matrix restores I1 to the digit",
          inspect[P]["index"], i1["index"])

    # BUG-043 after close: nothing active again -> the answer is none
    view = employees_view("employee_g")
    check("bug043 post-close: current period is none again",
          view.get("current_period_id"), None)

    # =========================================================================
    # 11. BUG-041 runtime repro (statement-level, on the closed period)
    #     The RECON's race: "the period was closed ... in the window between
    #     Execute Ownership Check and Execute Update". Here the period IS
    #     closed, so the header matches zero rows — exactly the state the
    #     racing statement executes in.
    # =========================================================================
    score_rows_literal = "(3::integer, 6::integer, NULL::text)"
    rows_before = score_rows_in_db(R)
    check("bug041: carrier holds three rows", rows_before, [3, 4, 12])

    # the HTTP route refuses pre-DML on a closed period, changing nothing
    status, body = call(base, "POST", "api/update-evaluation", token=tok["manager"],
                        body={"evaluation_id": eval_r, "grades": {"3": 6}})
    record("bug041", "route_level_post_close", {"status": status,
                                                "error": (body or {}).get("error"),
                                                "rows_after": score_rows_in_db(R)})
    check("bug041 route: closed period refused before any DML",
          (status, (body or {}).get("error")), (403, "PERIOD_CLOSED"))
    check("bug041 route: rows untouched", score_rows_in_db(R), [3, 4, 12])

    # PRE-FIX statement (RECON §7.2 verbatim): header matches zero rows, and
    # the ungated DELETE still fires — the destructive race, demonstrated.
    pre_fix = PRE_FIX_UPDATE_SQL.format(score_rows=score_rows_literal,
                                        eval_id=eval_r, actor_id=MANAGER)
    returned = sql(db, pre_fix)
    rows_after_prefix = score_rows_in_db(R)
    record("bug041", "pre_fix_statement", {
        "header_rows_returned": returned, "rows_before": rows_before,
        "rows_after": rows_after_prefix,
    })
    check("bug041 pre-fix: the header matched zero rows (403 path)", returned, "")
    check("bug041 pre-fix: the DELETE fired anyway — rows 4 and 12 are GONE",
          rows_after_prefix, [3])

    # restore the destroyed rows
    sql(db, f"""
      INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value)
      VALUES ({eval_r}, 4, 5), ({eval_r}, 12, 5)""")
    check("bug041: rows restored for the post-fix run", score_rows_in_db(R), [3, 4, 12])

    # POST-FIX statement (byte-sourced from the deployed artifact): identical
    # conditions, zero rows returned, zero rows deleted.
    post_fix = extract_update_sql(eval_r, MANAGER, score_rows_literal)
    returned = sql(db, post_fix)
    rows_after_postfix = score_rows_in_db(R)
    record("bug041", "post_fix_statement", {
        "header_rows_returned": returned, "rows_before": [3, 4, 12],
        "rows_after": rows_after_postfix,
    })
    check("bug041 post-fix: the header matched zero rows (403 path)", returned, "")
    check("bug041 post-fix: ZERO rows deleted", rows_after_postfix, [3, 4, 12])

    # ── verdict ───────────────────────────────────────────────────────────────
    REPORT["failures"] = FAILURES
    REPORT["checks_run"] = CHECKS_RUN
    if CHECKS_RUN < 100:
        FAILURES.append(f"vacuous run: only {CHECKS_RUN} checks executed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"report: {args.output}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for failure in FAILURES:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()

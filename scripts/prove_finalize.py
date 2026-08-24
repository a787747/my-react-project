#!/usr/bin/env python3
"""Acceptance proof for the finalization batch (brief 2026-08-24).

Runs against the isolated stand from setup_finalize_throwaway.sh:
n8n on 127.0.0.1:25679 (tunneled), throwaway DB epe_final_* on the VPS.

Every check records the COMPARED VALUES, not a verdict string: a run that
compared nothing fails loudly instead of writing the same slogan as a run
that compared everything.

Proves, per the brief:
  1. Corrections applicability (approved decision): POST score-correction
     answers 422 CRITERIA_NOT_APPLICABLE for a project criterion aimed at a
     currently-general subject — c_level and mid_level writers both — with
     the corrections row count unchanged; applicable writes (project
     criterion for a project subject, 'all' criterion for anyone) stay 200.
  2. BUG-046: the middle-manager matrix stops emitting soft-excluded project
     cells (scores AND their corrections) after a project->general switch,
     with every database row intact and the cells returning on switch-back;
     the admin matrix agrees on the emitted set.
  3. New-criterion path end-to-end: a criterion shaped exactly as Alexander
     will create (all / self off / manager on / c_level off, 10 level texts)
     through the same admin route the UI calls; Manage Criteria seeds NO
     score_coefficients rows and cannot set a weight (DB default 1.0);
     GET /api/score-coefficients renders the unseeded criterion (all-1.0
     fill) so /admin/scoring can save real values via the existing upsert;
     /api/employees, both matrices, the additive flow and close all pick the
     criterion up; the money paths compute a silent 1.0-fallback index while
     coefficient rows are absent — shown as two different close numbers for
     the same scores, before and after the explicit save.
  4. Role x route regression on the two touched workflows.
"""

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
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent

ACTORS = {
    "admin":            (1301, "44444444-4444-4444-8444-444444444401"),
    "manager":          (1302, "44444444-4444-4444-8444-444444444402"),
    "employee_g":       (1303, "44444444-4444-4444-8444-444444444403"),
    "employee_p":       (1304, "44444444-4444-4444-8444-444444444404"),
    "c_level":          (1305, "44444444-4444-4444-8444-444444444405"),
    "c_level_readonly": (1306, "44444444-4444-4444-8444-444444444406"),
    "hr":               (1307, "44444444-4444-4444-8444-444444444407"),
    "employee_n":       (1308, "44444444-4444-4444-8444-444444444408"),
    "employee_r":       (1309, "44444444-4444-4444-8444-444444444409"),
    "midmanager":       (1310, "44444444-4444-4444-8444-444444444410"),
}

H1 = 2            # half_year leaf, draft in the restored dump
MANAGER = 1302
MID = 1310
G, P, N, R = 1303, 1304, 1308, 1309

NEW_TITLE = "FN Критерий 9 (acceptance)"
NEW_WEIGHT = 1.8          # the explicit weight saved via /admin/scoring
NEW_LEVEL_COEF = 1.05     # the explicit level coefficient (all 10 levels)

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}
CHECKS_RUN = 0


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
    if not database.startswith("epe_final_"):
        raise SystemExit(f"Refusing non-throwaway database: {database}")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--env-file", type=Path,
                        default=REPO / "backups/2026-08-24-finalize/throwaway_env.json")
    parser.add_argument("--output", type=Path,
                        default=REPO / "backups/2026-08-24-finalize/finalize_proof.json")
    args = parser.parse_args()

    env = json.loads(args.env_file.read_text())
    db = env["database"]
    secret = env["jwt_secret"]
    base = args.base_url
    tok = {name: mint(secret, uid, jti) for name, (uid, jti) in ACTORS.items()}

    record("stand", "database", db)
    record("stand", "base_url", base)

    def read_catalogue() -> list[dict]:
        return json.loads(sql(db, """
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
    catalogue = read_catalogue()
    project_ids = sorted(int(c["id"]) for c in catalogue
                         if c["target_audience"] == "project_participants")
    record("catalogue", "project_criteria_ids", project_ids)
    check("catalogue: project criteria are 8 and 13", project_ids, [8, 13])
    base_active_ids = sorted(int(c["id"]) for c in catalogue)
    check("catalogue: 8 active criteria in the restored dump",
          base_active_ids, [1, 2, 3, 4, 8, 10, 12, 13])

    def employee_row(actor: str, subject: int) -> dict[str, Any] | None:
        status, body = call(base, "GET", "api/employees", token=tok[actor])
        if status != 200:
            raise SystemExit(f"employees fetch failed for {actor}: {status} {body}")
        rows = (body or {}).get("data") or []
        return next((r for r in rows if int(r["id"]) == subject), None)

    def fetch_matrix(actor: str) -> list[dict]:
        status, body = call(base, "GET", "api/admin/evaluations-matrix", token=tok[actor])
        if status != 200:
            raise SystemExit(f"admin matrix fetch failed: {status} {body}")
        return [r for r in ((body or {}).get("data") or []) if 1301 <= int(r["id"]) <= 1310]

    def fetch_mm_matrix(actor: str) -> tuple[int, Any]:
        return call(base, "GET", "api/manager-subordinates-matrix", token=tok[actor])

    def corrections_count(subject: int | None = None) -> int:
        where = f"WHERE subject_id = {subject}" if subject else ""
        return int(sql(db, f"SELECT count(*) FROM performance_db.score_corrections {where}"))

    def score_rows_in_db(subject: int) -> list[int]:
        raw = sql(db, f"""
          SELECT COALESCE(json_agg(es.criteria_id ORDER BY es.criteria_id), '[]'::json)
          FROM performance_db.evaluations e
          JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
          WHERE e.subject_id = {subject} AND e.evaluator_id = {MANAGER}
            AND e.evaluation_source = 'manager' AND e.period_id = {H1}
            AND e.is_self_evaluation = false""")
        return json.loads(raw)

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

    # =========================================================================
    # 1. New criterion, created in DRAFT state exactly as Alexander will:
    #    the same POST manage-criteria {action:'save'} the UI sends
    #    (useCriteria.saveCriterion), no id -> INSERT. The editor has no
    #    weight field and the INSERT names no weight column.
    # =========================================================================
    levels = {f"level_{i}_desc": f"Уровень {i}: описание критерия 9 ({i}/10)"
              for i in range(1, 11)}
    status, body = call(base, "POST", "manage-criteria", token=tok["admin"], body={
        "action": "save",
        "criteria": {
            "title": NEW_TITLE,
            "description": "Приёмочный критерий девятой формы (аудитория все, без самооценки)",
            "target_audience": "all",
            "is_active": True,
            "selfassesment": False,
            "for_manager": True,
            "c_level_only": False,
            **levels,
        },
    })
    check("new criterion: manage-criteria save accepted", status, 200)
    new_id = int(sql(db, f"SELECT id FROM performance_db.criteria WHERE title = '{NEW_TITLE}'"))
    record("new_criterion", "id", new_id)

    created = json.loads(sql(db, f"""
      SELECT row_to_json(c) FROM (
        SELECT weight, target_audience, is_active, selfassesment, for_manager, c_level_only,
               (level_1_desc IS NOT NULL AND level_10_desc IS NOT NULL) AS levels_present,
               (SELECT count(*) FROM performance_db.score_coefficients sc
                 WHERE sc.criteria_id = {new_id}) AS coefficient_rows
        FROM performance_db.criteria WHERE id = {new_id}) c"""))
    record("new_criterion", "created_row", created)
    check("new criterion: NO score_coefficients rows are seeded",
          int(created["coefficient_rows"]), 0)
    check("new criterion: weight is the DB default 1.00 (the editor cannot set one)",
          float(created["weight"]), 1.0)
    check("new criterion: shape as sent (all / self off / manager on / c_level off)",
          (created["target_audience"], created["selfassesment"],
           created["for_manager"], created["c_level_only"], created["levels_present"]),
          ("all", False, True, False, True))

    # /admin/scoring renders from GET api/score-coefficients: the unseeded
    # criterion must come back with the all-1.0 fill so the save can create
    # the real rows via the existing upsert.
    status, body = call(base, "GET", "api/score-coefficients", token=tok["admin"])
    check("scoring GET: 200 for admin", status, 200)
    row = next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == new_id), None)
    record("new_criterion", "scoring_get_unseeded", row)
    check("scoring GET: the unseeded criterion is rendered", row is not None, True)
    if row:
        check("scoring GET: unseeded weight reads 1.0", float(row["weight"]), 1.0)
        check("scoring GET: all ten levels filled with 1.0",
              sorted(set(float(v) for v in row["score_coefficients"].values())), [1.0])
        check("scoring GET: exactly levels 1..10",
              sorted(int(k) for k in row["score_coefficients"]), list(range(1, 11)))

    # the catalogue read every form uses picks it up too (weight admin-only)
    status, body = call(base, "GET", "api/criteria", token=tok["manager"])
    check("criteria GET: 200 for manager", status, 200)
    crow = next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == new_id), None)
    check("criteria GET: new criterion visible to the manager form", crow is not None, True)
    if crow:
        record("new_criterion", "criteria_get_manager",
               {k: crow.get(k) for k in ("id", "target_audience", "selfassesment",
                                         "for_manager", "c_level_only", "weight")})
        check("criteria GET: weight stripped for a non-admin", crow.get("weight"), None)
        check("criteria GET: self off / manager on as the form filters need",
              (crow.get("selfassesment"), crow.get("for_manager")), (False, True))

    # =========================================================================
    # 2. Activate + start the campaign (the criterion predates the start,
    #    which is the only order production allows — the catalogue freezes
    #    on start with 409 EVALUATION_STARTED).
    # =========================================================================
    status, _ = call(base, "POST", "api/periods/activate", token=tok["admin"],
                     body={"period_id": H1})
    check("activate H1", status, 200)
    status, _ = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                     body={"period_id": H1})
    check("start H1", status, 200)

    # =========================================================================
    # 3. Role x route regression on the two touched workflows
    # =========================================================================
    role_matrix: dict[str, dict[str, Any]] = {}
    for actor in ("admin", "manager", "midmanager", "employee_g",
                  "c_level", "c_level_readonly", "hr"):
        row_probe: dict[str, Any] = {}
        for method, path, body_probe, label in [
            ("POST", "api/admin/score-correction", {}, "score_correction"),
            ("GET", "api/manager-subordinates-matrix", None, "mm_matrix"),
        ]:
            status, body = call(base, method, path, token=tok[actor], body=body_probe)
            row_probe[label] = {"status": status, "error": (body or {}).get("error")
                                if isinstance(body, dict) else None}
        role_matrix[actor] = row_probe
    record("role_route_matrix", "results", role_matrix)
    for actor, label, want_status, want_error in [
        ("admin",            "score_correction", 422, "INVALID_BODY"),
        ("manager",          "score_correction", 422, "INVALID_BODY"),
        ("midmanager",       "score_correction", 422, "INVALID_BODY"),
        ("c_level",          "score_correction", 422, "INVALID_BODY"),
        ("c_level_readonly", "score_correction", 403, "CAPABILITY_FORBIDDEN"),
        ("hr",               "score_correction", 403, "ROLE_FORBIDDEN"),
        ("employee_g",       "score_correction", 403, "ROLE_FORBIDDEN"),
        ("admin",            "mm_matrix", 200, None),
        # 1302's reports are all non-managers: the route is for managers of managers
        ("manager",          "mm_matrix", 403, "OWNERSHIP_FORBIDDEN"),
        ("midmanager",       "mm_matrix", 200, None),
        ("c_level",          "mm_matrix", 200, None),
        ("c_level_readonly", "mm_matrix", 200, None),
        ("hr",               "mm_matrix", 403, "ROLE_FORBIDDEN"),
        ("employee_g",       "mm_matrix", 403, "ROLE_FORBIDDEN"),
    ]:
        got = role_matrix[actor][label]
        check(f"role matrix {actor}/{label}", (got["status"], got["error"]),
              (want_status, want_error))

    # =========================================================================
    # 4. Corrections applicability — negative tests both ways, both writer
    #    levels, with row counts around every write
    # =========================================================================
    corr: dict[str, Any] = {}
    count_0 = corrections_count()
    check("corrections: table starts empty", count_0, 0)

    #  (a) c_level writer (admin), project criterion, GENERAL subject -> 422
    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": N, "criteria_id": 8, "correction_score": 6})
    corr["clevel_project_criterion_general_subject"] = {
        "status": status, "error": (body or {}).get("error"),
        "count_before": count_0, "count_after": corrections_count()}
    check("corr: admin, criterion 8 for general N -> 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))
    check("corr: refused write stored nothing", corrections_count(), count_0)

    #  (b) mid_level writer, project criterion, GENERAL subject -> 422
    status, body = call(base, "POST", "api/admin/score-correction", token=tok["midmanager"],
                        body={"subject_id": N, "criteria_id": 13, "correction_score": 6})
    corr["mid_project_criterion_general_subject"] = {
        "status": status, "error": (body or {}).get("error"),
        "count_after": corrections_count()}
    check("corr: mid-manager, criterion 13 for general N -> 422",
          (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))
    check("corr: still nothing stored", corrections_count(), count_0)

    #  (c) the other way: applicable writes succeed
    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": P, "criteria_id": 8, "correction_score": 6})
    corr["clevel_project_criterion_project_subject"] = {
        "status": status, "level": ((body or {}).get("data") or {}).get("correction_level")}
    check("corr: admin, criterion 8 for project P -> 200 c_level",
          (status, ((body or {}).get("data") or {}).get("correction_level")),
          (200, "c_level"))

    status, body = call(base, "POST", "api/admin/score-correction", token=tok["midmanager"],
                        body={"subject_id": P, "criteria_id": 13, "correction_score": 6})
    corr["mid_project_criterion_project_subject"] = {
        "status": status, "level": ((body or {}).get("data") or {}).get("correction_level")}
    check("corr: mid-manager (skip-level), criterion 13 for project P -> 200 mid_level",
          (status, ((body or {}).get("data") or {}).get("correction_level")),
          (200, "mid_level"))

    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": R, "criteria_id": 3, "correction_score": 7})
    corr["clevel_all_criterion_general_subject"] = {"status": status}
    check("corr: an 'all' criterion for a general subject stays writable", status, 200)
    check("corr: exactly the three applicable writes stored", corrections_count(), count_0 + 3)
    record("corrections_applicability", "writes", corr)

    # =========================================================================
    # 5. Evaluations: the flag counts the new criterion for every subject
    # =========================================================================
    #  P (project): the FULL applicable set now includes the new criterion
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": P, "grades": {"3": 8, "4": 6, "8": 9,
                                                          "12": 7, "13": 10, str(new_id): 7}})
    check("P: full-set submit incl. the new criterion", status, 200)
    row = employee_row("manager", P)
    check("P: flag done on the full set", row.get("evaluated_by_actor"), True)
    check("P: nothing missing", row.get("missing_criteria_ids"), [])

    #  N (general): the old 3-criteria set is no longer complete
    status, _ = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                     body={"subject_id": N, "grades": {"3": 6, "4": 6, "12": 6}})
    check("N: old-set submit accepted", status, 200)
    row = employee_row("manager", N)
    record("new_criterion", "flag_after_old_set", {
        "evaluated_by_actor": row.get("evaluated_by_actor"),
        "missing_criteria_ids": row.get("missing_criteria_ids")})
    check("N: the flag counts the new criterion — task stays open",
          row.get("evaluated_by_actor"), False)
    check("N: the missing criterion is named", row.get("missing_criteria_ids"), [new_id])

    #  additive flow picks it up
    scores_before = int(sql(db, "SELECT count(*) FROM performance_db.evaluation_scores"))
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": N, "grades": {str(new_id): 7}})
    scores_after = int(sql(db, "SELECT count(*) FROM performance_db.evaluation_scores"))
    record("new_criterion", "additive", {"status": status,
                                         "scores_added": (body or {}).get("scores_added"),
                                         "rows_added": scores_after - scores_before})
    check("N additive: the new criterion is accepted", status, 200)
    check("N additive: exactly one row added", scores_after - scores_before, 1)
    row = employee_row("manager", N)
    check("N additive: flag closes", row.get("evaluated_by_actor"), True)
    check("N additive: nothing missing", row.get("missing_criteria_ids"), [])
    check("N: DB rows are the four", score_rows_in_db(N), [3, 4, 12, new_id])

    # =========================================================================
    # 6. Both matrices pick the new criterion up for every subject
    # =========================================================================
    admin_rows = fetch_matrix("admin")
    cells_by_user = {int(r["id"]): sorted(int(c["criteria_id"]) for c in r.get("criteria") or [])
                     for r in admin_rows}
    record("new_criterion", "admin_matrix_cells", {str(k): v for k, v in cells_by_user.items()})
    check("admin matrix: new criterion cell for the general subject N",
          new_id in cells_by_user.get(N, []), True)
    check("admin matrix: new criterion cell for the project subject P",
          new_id in cells_by_user.get(P, []), True)
    check("admin matrix: new criterion cell for the unevaluated subject G",
          new_id in cells_by_user.get(G, []), True)
    check("admin matrix: P sees every active cell",
          cells_by_user.get(P), sorted([1, 2, 3, 4, 8, 10, 12, 13, new_id]))
    check("admin matrix: general N excludes 8/13 only",
          cells_by_user.get(N), sorted([1, 2, 3, 4, 10, 12, new_id]))

    status, body = fetch_mm_matrix("midmanager")
    check("mm matrix: 200 for the middle manager", status, 200)
    mm_rows = (body or {}).get("data") or []
    mm_by_user = {int(r["id"]): {int(c["criteria_id"]): c for c in r.get("criteria") or []}
                  for r in mm_rows}
    record("bug046", "before_switch_users", sorted(mm_by_user))
    check("mm matrix: the span is 1302's four reports",
          sorted(mm_by_user), [G, P, N, R])
    check("mm matrix: new criterion cell present for N",
          new_id in mm_by_user.get(N, {}), True)
    p_cells = mm_by_user.get(P, {})
    record("bug046", "P_cells_before", {
        "ids": sorted(p_cells),
        "cell8": {k: p_cells[8].get(k) for k in ("manager_score", "c_level_correction")} if 8 in p_cells else None,
        "cell13": {k: p_cells[13].get(k) for k in ("manager_score", "mid_level_correction")} if 13 in p_cells else None,
    })
    check("mm matrix before: P carries cells 8 and 13",
          sorted(p_cells), sorted([2, 3, 4, 8, 12, 13, new_id]))
    check("mm matrix before: cell 8 carries score and c_level correction",
          (p_cells[8].get("manager_score"), p_cells[8].get("c_level_correction")), (9, 6))
    check("mm matrix before: cell 13 carries score and mid_level correction",
          (p_cells[13].get("manager_score"), p_cells[13].get("mid_level_correction")), (10, 6))

    # =========================================================================
    # 7. BUG-046: P -> general; the middle-manager matrix stops emitting the
    #    excluded cells (scores AND corrections), rows intact; switch back
    # =========================================================================
    db_rows_before = score_rows_in_db(P)
    corr_p_before = corrections_count(P)
    status, _ = save_user_category(P, "general")
    check("P -> general mid-campaign", status, 200)

    status, body = fetch_mm_matrix("midmanager")
    check("mm matrix after switch: still 200", status, 200)
    mm_by_user = {int(r["id"]): {int(c["criteria_id"]): c for c in r.get("criteria") or []}
                  for r in ((body or {}).get("data") or [])}
    p_cells_general = mm_by_user.get(P, {})
    record("bug046", "P_cells_while_general", sorted(p_cells_general))
    check("BUG-046: cells 8 and 13 are GONE from the middle-manager matrix",
          sorted(p_cells_general), sorted([2, 3, 4, 12, new_id]))
    check("BUG-046: no emitted cell carries the excluded corrections",
          [cid for cid, cell in p_cells_general.items()
           if cell.get("mid_level_correction") is not None
           or cell.get("c_level_correction") is not None], [])

    admin_cells_general = {int(r["id"]): sorted(int(c["criteria_id"])
                                                for c in r.get("criteria") or [])
                           for r in fetch_matrix("admin")}
    check("BUG-046: the admin matrix emits the same criteria set for P",
          [c for c in admin_cells_general.get(P, []) if c not in (1, 10)],
          sorted(p_cells_general))

    db_rows_general = score_rows_in_db(P)
    corr_p_general = corrections_count(P)
    record("bug046", "db_rows", {"scores_before": db_rows_before,
                                 "scores_while_general": db_rows_general,
                                 "corrections_before": corr_p_before,
                                 "corrections_while_general": corr_p_general})
    check("BUG-046: every score row survives in the database",
          db_rows_general, db_rows_before)
    check("BUG-046: both correction rows survive in the database",
          (corr_p_before, corr_p_general), (2, 2))

    status, _ = save_user_category(P, "project")
    check("P -> project again", status, 200)
    status, body = fetch_mm_matrix("midmanager")
    mm_by_user = {int(r["id"]): {int(c["criteria_id"]): c for c in r.get("criteria") or []}
                  for r in ((body or {}).get("data") or [])}
    p_cells_back = mm_by_user.get(P, {})
    record("bug046", "P_cells_after_switch_back", sorted(p_cells_back))
    check("BUG-046: the cells return on switch-back",
          sorted(p_cells_back), sorted([2, 3, 4, 8, 12, 13, new_id]))
    check("BUG-046: correction values return unchanged",
          (p_cells_back[8].get("c_level_correction"),
           p_cells_back[13].get("mid_level_correction")), (6, 6))

    # =========================================================================
    # 8. Money: close #1 with the coefficient rows ABSENT — the silent 1.0
    #    fallback, persisted; then the explicit save; then close #2 —
    #    two different numbers for the same scores.
    # =========================================================================
    catalogue_1 = read_catalogue()
    new_cat_1 = next(c for c in catalogue_1 if int(c["id"]) == new_id)
    check("money: the new criterion still has no level rows at close #1",
          new_cat_1["levels"], {})
    replica_1 = client_pipeline(fetch_matrix("admin"), catalogue_1, grade_map)
    record("money", "replica_close1", {str(k): v for k, v in replica_1.items()})

    status, body = call(base, "POST", "api/periods/close", token=tok["admin"],
                        body={"period_id": H1})
    check("close #1 succeeds", status, 200)

    def persisted_results() -> dict[int, dict[str, Any]]:
        rows = json.loads(sql(db, f"""
          SELECT COALESCE(json_agg(json_build_object(
            'user_id', pr.user_id, 'final_rating', pr.final_rating,
            'bonus_index', pr.bonus_index, 'has_data', pr.has_data) ORDER BY pr.user_id), '[]'::json)
          FROM performance_db.period_results pr
          WHERE pr.period_id = {H1} AND pr.user_id BETWEEN 1301 AND 1310"""))
        return {int(r["user_id"]): r for r in rows}

    stored_1 = persisted_results()
    record("money", "persisted_close1", {str(k): v for k, v in stored_1.items()})
    for uid in (P, N):
        want = replica_1.get(uid, {})
        check(f"close #1/{uid}: persisted final equals the replica",
              round(float(stored_1[uid]["final_rating"]), 4), round(want["final"], 4))
        check(f"close #1/{uid}: persisted index equals the replica",
              round(float(stored_1[uid]["bonus_index"]), 4), round(want["index"], 4))
    index_fallback = round(float(stored_1[N]["bonus_index"]), 4)

    # stand-only surgery: reopen the throwaway's period so the SAME scores can
    # be closed again after the explicit save (live close stays irreversible)
    sql(db, f"""
      BEGIN;
      DELETE FROM performance_db.period_results WHERE period_id = {H1};
      UPDATE performance_db.evaluation_periods
        SET status = 'active', is_active = true WHERE id = {H1};
      COMMIT;""")
    record("money", "stand_reset",
           "period_results wiped + H1 re-activated by SQL on the throwaway only")

    # the mandatory save: /admin/scoring's existing upsert creates the rows
    status, body = call(base, "POST", "api/score-coefficients", token=tok["admin"], body={
        "criteria": [{"id": new_id, "weight": NEW_WEIGHT,
                      "score_coefficients": {str(i): NEW_LEVEL_COEF for i in range(1, 11)}}],
    })
    check("scoring save: explicit weight + coefficients accepted", status, 200)
    check("scoring save: exactly ten rows created",
          int(sql(db, f"SELECT count(*) FROM performance_db.score_coefficients WHERE criteria_id = {new_id}")), 10)
    check("scoring save: stored weight",
          float(sql(db, f"SELECT weight FROM performance_db.criteria WHERE id = {new_id}")), NEW_WEIGHT)
    status, body = call(base, "GET", "api/score-coefficients", token=tok["admin"])
    row = next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == new_id), None)
    check("scoring GET after save: the explicit values come back",
          (float(row["weight"]), sorted(set(float(v) for v in row["score_coefficients"].values()))),
          (NEW_WEIGHT, [NEW_LEVEL_COEF]))

    catalogue_2 = read_catalogue()
    replica_2 = client_pipeline(fetch_matrix("admin"), catalogue_2, grade_map)
    status, body = call(base, "POST", "api/periods/close", token=tok["admin"],
                        body={"period_id": H1})
    check("close #2 succeeds", status, 200)
    stored_2 = persisted_results()
    record("money", "persisted_close2", {str(k): v for k, v in stored_2.items()})
    for uid in (P, N):
        want = replica_2.get(uid, {})
        check(f"close #2/{uid}: persisted final equals the replica",
              round(float(stored_2[uid]["final_rating"]), 4), round(want["final"], 4))
        check(f"close #2/{uid}: persisted index equals the replica",
              round(float(stored_2[uid]["bonus_index"]), 4), round(want["index"], 4))
    index_explicit = round(float(stored_2[N]["bonus_index"]), 4)

    # the worked example, to the digit: only the new criterion's term moved
    grade_n = grade_map["S2"]
    term_fallback = 7 * 1.0 * 1.0
    term_explicit = 7 * NEW_LEVEL_COEF * NEW_WEIGHT
    expected_delta = round((term_explicit - term_fallback) * grade_n, 4)
    record("money", "worked_example_N", {
        "grades": {"3": 6, "4": 6, "12": 6, str(new_id): 7},
        "grade_coefficient_S2": grade_n,
        "index_with_fallback_1.0": index_fallback,
        "index_with_explicit_coefficients": index_explicit,
        "new_criterion_term_fallback": f"7 x 1.0 x 1.0 = {term_fallback}",
        "new_criterion_term_explicit": f"7 x {NEW_LEVEL_COEF} x {NEW_WEIGHT} = {term_explicit}",
        "delta_expected": expected_delta,
        "delta_observed": round(index_explicit - index_fallback, 4),
    })
    check("money: the two closes persisted DIFFERENT indices for the same scores",
          index_explicit != index_fallback, True)
    check("money: the delta is exactly the new criterion's term",
          round(index_explicit - index_fallback, 4), expected_delta)
    check("money: N's final rating did not move (ratings ignore coefficients)",
          round(float(stored_2[N]["final_rating"]), 4),
          round(float(stored_1[N]["final_rating"]), 4))

    # ── verdict ───────────────────────────────────────────────────────────────
    REPORT["failures"] = FAILURES
    REPORT["checks_run"] = CHECKS_RUN
    if CHECKS_RUN < 70:
        FAILURES.append(f"vacuous run: only {CHECKS_RUN} checks executed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"report: {args.output}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for failure in FAILURES:
            print(f"  - {failure}")
        raise SystemExit(1)
    print(f"ALL {CHECKS_RUN} CHECKS PASSED")


if __name__ == "__main__":
    main()

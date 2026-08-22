#!/usr/bin/env python3
"""Acceptance proof for the two-gate lifecycle + coefficient privacy (2026-08-22).

Runs against the isolated stand from setup_lifecycle_throwaway.sh:
n8n on 127.0.0.1:25679 (tunneled), throwaway DB epe_lifecycle_* on the VPS.

Every check records the COMPARED VALUES, not a verdict string: a run that
compared nothing fails loudly instead of writing the same slogan as a run that
compared everything.

Proves, per the brief:
  - role x route probe matrix for GET/POST score-coefficients, GET criteria
    (weight present/absent per role), update-admin-data, manage-criteria
  - ordered E2E: activate -> criteria 200 / weight 200 / zero tasks / submit
    refused;  start -> criteria 409 / weight 200 / tasks appear / submit 200;
    start again -> explicit already-started with zero state change;
    start on draft / closed / container / annual -> refused by precondition;
    close of a started period -> unchanged semantics (close proof re-run)
  - self-review: the employee never receives coefficients, and the stored
    weighted_score equals an independent recomputation with the subject's REAL
    grade coefficient, for two subjects whose coefficients differ
  - BUG-029: weight 0 and coefficient 0 rejected on both write paths, with the
    stored values re-read afterwards to show nothing changed
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

ACTORS = {
    "admin":            (1201, "22222222-2222-4222-8222-222222222201"),
    "manager":          (1202, "22222222-2222-4222-8222-222222222202"),
    "employee_a":       (1203, "22222222-2222-4222-8222-222222222203"),
    "employee_b":       (1204, "22222222-2222-4222-8222-222222222204"),
    "c_level":          (1205, "22222222-2222-4222-8222-222222222205"),
    "c_level_readonly": (1206, "22222222-2222-4222-8222-222222222206"),
    "hr":               (1207, "22222222-2222-4222-8222-222222222207"),
}

H1 = 2            # half_year leaf, draft in the restored dump
ANNUAL_2026 = 5   # container (parent of H1)

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
    if not database.startswith("epe_lifecycle_"):
        raise SystemExit(f"Refusing non-throwaway database: {database}")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def check(name: str, actual: Any, expected: Any) -> bool:
    ok = actual == expected
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def record(section: str, key: str, value: Any) -> None:
    REPORT.setdefault(section, {})[key] = value


# ── client pipeline replica: formula #2, independent of the server code ──────

def recompute_weighted(grades: dict[int, int], catalogue: list[dict],
                       grade_coefficient: float) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    by_id = {int(c["id"]): c for c in catalogue}
    for criteria_id, score in grades.items():
        crit = by_id.get(int(criteria_id))
        weight = float(crit["weight"]) if crit else 1.0
        if crit:
            level = max(0, min(10, int(score + 0.5)))
            level_map = crit["levels"]
            raw = level_map.get(str(level), level_map.get(level))
            coefficient = 1.0 if raw is None else float(raw)
        else:
            coefficient = 1.0
        weighted_sum += score * coefficient * weight
        total_weight += weight
    return round((weighted_sum / total_weight) * grade_coefficient, 2)


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
                    grades: list[dict]) -> dict[int, dict[str, float | None]]:
    coef_map = {c["id"]: c for c in coefficients}
    grade_map = {g["code"]: float(g.get("coefficient") or 1.0) for g in grades}
    out: dict[int, dict[str, float | None]] = {}
    for emp in matrix_rows:
        finals: list[float] = []
        weighted_sum = 0.0
        for crit in emp.get("criteria") or []:
            raw = criterion_final(crit)
            if raw is None:
                continue
            finals.append(raw)
            coefs = coef_map.get(crit["criteria_id"])
            if not coefs:
                weighted_sum += raw
                continue
            weight = float(coefs.get("weight") or 1.0)
            level = max(0, min(10, int(raw + 0.5) if raw >= 0 else round(raw)))
            level_map = coefs.get("score_coefficients") or {}
            level_value = level_map.get(str(level), level_map.get(level))
            coefficient = 1.0 if level_value is None else float(level_value)
            weighted_sum += raw * coefficient * weight
        grade_coefficient = grade_map.get(emp.get("grade_code"), 1.0)
        out[emp["id"]] = {
            "final": round(sum(finals) / len(finals), 6) if finals else None,
            "index": round(weighted_sum * grade_coefficient, 6) if finals else None,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--env-file", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "backups/2026-08-22-lifecycle-coeff/throwaway_env.json")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "backups/2026-08-22-lifecycle-coeff/lifecycle_proof.json")
    args = parser.parse_args()

    env = json.loads(args.env_file.read_text())
    db = env["database"]
    secret = env["jwt_secret"]
    base = args.base_url
    tok = {name: mint(secret, uid, jti) for name, (uid, jti) in ACTORS.items()}

    record("stand", "database", db)
    record("stand", "base_url", base)

    # ── catalogue snapshot used by every recomputation ────────────────────────
    catalogue = json.loads(sql(db, """
      SELECT COALESCE(json_agg(json_build_object(
        'id', c.id, 'weight', c.weight, 'selfassesment', c.selfassesment,
        'levels', COALESCE((SELECT json_object_agg(sc.score_level::text, sc.coefficient)
                            FROM performance_db.score_coefficients sc
                            WHERE sc.criteria_id = c.id), '{}'::json)
      ) ORDER BY c.id), '[]'::json)
      FROM performance_db.criteria c WHERE c.is_active = true"""))
    record("catalogue", "active_criteria", [
        {"id": c["id"], "weight": float(c["weight"]), "self": c["selfassesment"]} for c in catalogue])

    grade_coefficients = dict(
        line.split("|") for line in sql(db, """
          SELECT u.id || '|' || g.coefficient
          FROM performance_db.users u JOIN performance_db.grades g ON g.id = u.grade_id
          WHERE u.id IN (1203, 1204)""").splitlines())
    gc_a = float(grade_coefficients["1203"])
    gc_b = float(grade_coefficients["1204"])
    record("subjects", "grade_coefficients", {"1203": gc_a, "1204": gc_b})
    check("two subjects must have different grade coefficients", gc_a != gc_b, True)

    # =====================================================================
    # 0. DRAFT: start refused, catalogue and coefficients editable
    # =====================================================================
    status, body = call(base, "POST", "api/periods/start-evaluation",
                        token=tok["admin"], body={"period_id": H1})
    record("draft", "start_on_draft", {"status": status, "error": (body or {}).get("error")})
    check("draft: start refused", (status, (body or {}).get("error")), (422, "PERIOD_NOT_ACTIVE"))

    def criteria_save(actor: str = "admin") -> tuple[int, Any]:
        return call(base, "POST", "manage-criteria", token=tok[actor], body={
            "action": "save",
            "criteria": {"id": 12, "title": "Профессиональное развитие и обмен знаниями",
                         "description": "", "target_audience": "all", "weight": 1.0,
                         "is_active": True, "selfassesment": True, "for_manager": True,
                         "c_level_only": False},
        })

    def weight_save(weight: float = 1.0, coefficient: float | None = None,
                    actor: str = "admin") -> tuple[int, Any]:
        levels = {str(i): (coefficient if coefficient is not None
                           else float(next(c for c in catalogue if int(c["id"]) == 12)["levels"][str(i)]))
                  for i in range(1, 11)}
        return call(base, "POST", "api/score-coefficients", token=tok[actor], body={
            "criteria": [{"id": 12, "weight": weight, "score_coefficients": levels}]})

    def grade_save(coefficient: float, actor: str = "admin") -> tuple[int, Any]:
        grade_id = int(sql(db, "SELECT id FROM performance_db.grades WHERE code = 'S1'"))
        return call(base, "POST", "update-admin-data", token=tok[actor],
                    body={"grades": [{"id": grade_id, "coefficient": coefficient}]})

    s, _ = criteria_save()
    record("draft", "criteria_save_status", s)
    check("draft: criteria editable", s, 200)
    s, _ = weight_save()
    record("draft", "weight_save_status", s)
    check("draft: weights editable", s, 200)

    # =====================================================================
    # 1. ACTIVATE -> preparation window
    # =====================================================================
    status, body = call(base, "POST", "api/periods/activate", token=tok["admin"],
                        body={"period_id": H1})
    check("activate H1", status, 200)
    periods = {p["id"]: p for p in call(base, "GET", "api/periods", token=tok["admin"])[1]["data"]}
    record("preparation", "h1_state", {
        "status": periods[H1]["status"], "is_active": periods[H1]["is_active"],
        "evaluation_started": periods[H1]["evaluation_started"],
        "evaluation_started_at": periods[H1]["evaluation_started_at"]})
    check("activation does not start the evaluation",
          (periods[H1]["status"], periods[H1]["is_active"], periods[H1]["evaluation_started"]),
          ("active", True, False))

    s, _ = criteria_save()
    record("preparation", "criteria_save_status", s)
    check("preparation: criteria still editable", s, 200)
    s, _ = weight_save()
    record("preparation", "weight_save_status", s)
    check("preparation: weights still editable", s, 200)
    s, _ = grade_save(0.60)
    record("preparation", "grade_save_status", s)
    check("preparation: grade coefficients still editable", s, 200)

    _, emp_a = call(base, "GET", "api/employees", token=tok["employee_a"])
    _, emp_mgr = call(base, "GET", "api/employees", token=tok["manager"])
    record("preparation", "employees_employee_a", {
        "campaign_active": emp_a["campaign_active"],
        "period_in_preparation": emp_a["period_in_preparation"],
        "actor_is_in_scope": emp_a["actor_is_in_scope"],
        "rows": len(emp_a["data"])})
    record("preparation", "employees_manager", {
        "campaign_active": emp_mgr["campaign_active"],
        "period_in_preparation": emp_mgr["period_in_preparation"],
        "actor_is_in_scope": emp_mgr["actor_is_in_scope"],
        "rows": len(emp_mgr["data"])})
    check("preparation: no campaign for the employee",
          (emp_a["campaign_active"], emp_a["period_in_preparation"], emp_a["actor_is_in_scope"],
           len(emp_a["data"])), (False, True, True, 0))
    check("preparation: the manager sees zero subordinates",
          (emp_mgr["campaign_active"], len(emp_mgr["data"])), (False, 0))

    _, mymgr = call(base, "GET", "api/get-my-manager", token=tok["employee_a"])
    record("preparation", "has_evaluated_manager", mymgr["manager"]["has_evaluated_manager"])
    _, chkev = call(base, "GET", "api/check-evaluated?evaluator_id=1202", token=tok["manager"])
    record("preparation", "check_evaluated_rows", len(chkev.get("details") or []))
    check("preparation: check-evaluated is empty", len(chkev.get("details") or []), 0)

    status, body = call(base, "POST", "api/self-review-submit", token=tok["employee_a"],
                        body={"final_score": 7, "grades": {"3": 7}, "comments": {}})
    record("preparation", "self_review_submit", {"status": status, "error": (body or {}).get("error")})
    check("preparation: self-review refused",
          (status, (body or {}).get("error")), (409, "PERIOD_NOT_STARTED"))

    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": 1203, "evaluation_source": "manager",
                              "grades": {"3": 7}, "comments": {}})
    record("preparation", "submit_evaluation", {"status": status, "error": (body or {}).get("error")})
    check("preparation: manager submit refused",
          (status, (body or {}).get("error")), (409, "PERIOD_NOT_STARTED"))

    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": 1203, "criteria_id": 3, "correction_score": 6})
    record("preparation", "score_correction", {"status": status, "error": (body or {}).get("error")})
    check("preparation: correction refused",
          (status, (body or {}).get("error")), (409, "NO_ACTIVE_PERIOD"))

    # ── role x route probe matrix, taken in the preparation window ────────────
    probe: dict[str, dict[str, Any]] = {}
    for role in ("admin", "c_level", "c_level_readonly", "hr", "manager", "employee_a"):
        row: dict[str, Any] = {}
        s, b = call(base, "GET", "api/score-coefficients", token=tok[role])
        row["GET /api/score-coefficients"] = {"status": s, "error": (b or {}).get("error")}
        s, b = call(base, "POST", "api/score-coefficients", token=tok[role],
                    body={"criteria": [{"id": 12, "weight": 1.0,
                                        "score_coefficients": {str(i): 1.0 for i in range(1, 11)}}]})
        row["POST /api/score-coefficients"] = {"status": s, "error": (b or {}).get("error")}
        s, b = call(base, "GET", "api/criteria", token=tok[role])
        rows = (b or {}).get("data") or []
        row["GET /api/criteria"] = {
            "status": s,
            "criteria_returned": len(rows),
            "weight_present_on_any": any("weight" in c for c in rows),
            "sample_keys_have_weight": ("weight" in rows[0]) if rows else None,
        }
        s, b = call(base, "POST", "update-admin-data", token=tok[role], body={"grades": []})
        row["POST /update-admin-data"] = {"status": s, "error": (b or {}).get("error")}
        s, b = call(base, "POST", "manage-criteria", token=tok[role], body={"action": "get"})
        row["POST /manage-criteria (get)"] = {"status": s, "error": (b or {}).get("error")}
        probe[role] = row
    REPORT["role_route_probe"] = probe

    for role in ("c_level", "c_level_readonly", "hr", "manager", "employee_a"):
        check(f"{role}: GET score-coefficients forbidden",
              probe[role]["GET /api/score-coefficients"]["status"], 403)
        check(f"{role}: criteria carry no weight",
              probe[role]["GET /api/criteria"]["weight_present_on_any"], False)
        check(f"{role}: POST score-coefficients forbidden",
              probe[role]["POST /api/score-coefficients"]["status"], 403)
        check(f"{role}: update-admin-data forbidden",
              probe[role]["POST /update-admin-data"]["status"], 403)
        check(f"{role}: manage-criteria forbidden",
              probe[role]["POST /manage-criteria (get)"]["status"], 403)
    check("admin: GET score-coefficients allowed",
          probe["admin"]["GET /api/score-coefficients"]["status"], 200)
    check("admin: criteria carry weight",
          probe["admin"]["GET /api/criteria"]["weight_present_on_any"], True)

    # =====================================================================
    # 2. START -> campaign running
    # =====================================================================
    status, body = call(base, "POST", "api/periods/start-evaluation",
                        token=tok["employee_a"], body={"period_id": H1})
    record("start", "start_by_employee", {"status": status, "error": (body or {}).get("error")})
    check("start is admin-only", status, 403)

    status, body = call(base, "POST", "api/periods/start-evaluation",
                        token=tok["admin"], body={"period_id": H1})
    record("start", "start_by_admin", {"status": status, "already_started": (body or {}).get("already_started"),
                                       "started_at": ((body or {}).get("data") or {}).get("evaluation_started_at")})
    check("start succeeds for admin", (status, (body or {}).get("already_started")), (200, False))
    started_at_1 = sql(db, f"SELECT evaluation_started_at FROM performance_db.evaluation_periods WHERE id = {H1}")
    started_by = sql(db, f"SELECT evaluation_started_by FROM performance_db.evaluation_periods WHERE id = {H1}")
    record("start", "db_started_at", started_at_1)
    record("start", "db_started_by", started_by)
    check("started_by is the admin actor", started_by, "1201")

    s, b = criteria_save()
    record("started", "criteria_save", {"status": s, "error": (b or {}).get("error")})
    check("started: criteria frozen", (s, (b or {}).get("error")), (409, "EVALUATION_STARTED"))
    s, b = call(base, "POST", "manage-criteria", token=tok["admin"],
                body={"action": "delete", "criteria": {"id": 12}})
    record("started", "criteria_delete", {"status": s, "error": (b or {}).get("error")})
    check("started: criteria delete frozen", (s, (b or {}).get("error")), (409, "EVALUATION_STARTED"))

    s, _ = weight_save()
    record("started", "weight_save_status", s)
    check("started: weights still editable", s, 200)
    s, _ = grade_save(0.60)
    record("started", "grade_save_status", s)
    check("started: grade coefficients still editable", s, 200)

    _, emp_a2 = call(base, "GET", "api/employees", token=tok["employee_a"])
    _, emp_mgr2 = call(base, "GET", "api/employees", token=tok["manager"])
    record("started", "employees_employee_a", {
        "campaign_active": emp_a2["campaign_active"],
        "period_in_preparation": emp_a2["period_in_preparation"],
        "actor_is_in_scope": emp_a2["actor_is_in_scope"]})
    record("started", "employees_manager_rows",
           sorted(e["id"] for e in emp_mgr2["data"]))
    check("started: campaign is live for the employee",
          (emp_a2["campaign_active"], emp_a2["period_in_preparation"]), (True, False))
    check("started: the manager sees both subordinates",
          sorted(e["id"] for e in emp_mgr2["data"]), [1203, 1204])

    # =====================================================================
    # 3. SELF-REVIEW: server-computed weighted_score, two grade coefficients
    # =====================================================================
    self_ids = [int(c["id"]) for c in catalogue if c["selfassesment"]]
    sr_cases = {
        "employee_a": (1203, gc_a, {self_ids[0]: 8, self_ids[1]: 6, self_ids[2]: 9}),
        "employee_b": (1204, gc_b, {self_ids[0]: 5, self_ids[1]: 10, self_ids[2]: 4}),
    }
    sr_tuples = []
    for actor, (uid, gc, grades) in sr_cases.items():
        avg = round(sum(grades.values()) / len(grades), 2)
        status, body = call(base, "POST", "api/self-review-submit", token=tok[actor], body={
            "user_id": uid, "final_score": avg,
            # a hostile client still sending a weighted_score must not be believed
            "weighted_score": 999.99,
            "grades": {str(k): v for k, v in grades.items()}, "comments": {}})
        check(f"{actor}: self-review accepted after start", status, 200)
        stored = sql(db, f"""SELECT weighted_score || '|' || calculated_score
                             FROM performance_db.evaluations
                             WHERE subject_id = {uid} AND is_self_evaluation = true""")
        stored_weighted, stored_calculated = stored.split("|")
        expected = recompute_weighted(grades, catalogue, gc)
        sr_tuples.append({
            "actor": actor, "user_id": uid, "grade_coefficient": gc,
            "grades": grades, "client_sent_weighted_score": 999.99,
            "stored_weighted_score": float(stored_weighted),
            "independent_recomputation": expected,
            "stored_calculated_score": float(stored_calculated),
            "match": float(stored_weighted) == expected,
        })
        check(f"{actor}: stored weighted_score equals the independent recomputation",
              float(stored_weighted), expected)
        check(f"{actor}: the client-sent 999.99 was ignored",
              float(stored_weighted) != 999.99, True)
    REPORT["self_review"] = {"tuples": sr_tuples}
    check("the two subjects produced different weighted scores (real coefficients used)",
          sr_tuples[0]["stored_weighted_score"] != sr_tuples[1]["stored_weighted_score"], True)

    # =====================================================================
    # 4. MANAGER SUBMIT + UPDATE + CORRECTION while started
    # =====================================================================
    mgr_grades = {"3": 8, "4": 7, "12": 9}
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": 1203, "evaluation_source": "manager",
                              "grades": mgr_grades, "comments": {},
                              "general_comment": "lifecycle proof"})
    record("started", "submit_evaluation_status", status)
    check("started: manager submit accepted", status, 200)
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["manager"],
                        body={"subject_id": 1204, "evaluation_source": "manager",
                              "grades": {"3": 6, "4": 5, "12": 7, "8": 8, "13": 9}, "comments": {}})
    check("started: manager submit for B accepted", status, 200)

    eval_id = int(sql(db, """SELECT id FROM performance_db.evaluations
                             WHERE subject_id = 1203 AND evaluator_id = 1202
                               AND is_self_evaluation = false"""))
    status, body = call(base, "POST", "api/update-evaluation", token=tok["manager"],
                        body={"evaluation_id": eval_id, "grades": {"3": 9, "4": 7, "12": 9},
                              "comments": {}, "general_comment": "updated"})
    record("started", "update_evaluation_status", status)
    check("started: update accepted", status, 200)

    status, body = call(base, "POST", "api/admin/score-correction", token=tok["admin"],
                        body={"subject_id": 1203, "criteria_id": 3, "correction_score": 7})
    record("started", "score_correction_status", status)
    check("started: correction accepted", status, 200)

    # Upward evaluation, so get-my-manager's has_evaluated_manager has something
    # to report — the flag is period-bound and must follow the start gate.
    status, body = call(base, "POST", "api/submit-evaluation", token=tok["employee_a"],
                        body={"subject_id": 1202, "evaluation_source": "subordinate",
                              "grades": {"2": 8}, "comments": {}})
    record("started", "submit_upward_status", status)
    check("started: upward submit accepted", status, 200)
    _, mymgr2 = call(base, "GET", "api/get-my-manager", token=tok["employee_a"])
    record("started", "has_evaluated_manager", mymgr2["manager"]["has_evaluated_manager"])
    check("started: has_evaluated_manager is true",
          mymgr2["manager"]["has_evaluated_manager"], True)

    _, chkev2 = call(base, "GET", "api/check-evaluated?evaluator_id=1202", token=tok["manager"])
    record("started", "check_evaluated_subjects",
           sorted(d["subject_id"] for d in (chkev2.get("details") or [])))
    check("started: check-evaluated reports both subjects",
          sorted(d["subject_id"] for d in (chkev2.get("details") or [])), [1203, 1204])

    _, chksr = call(base, "GET", "api/check-self-review?user_id=1203", token=tok["employee_a"])
    record("started", "check_self_review_a", {"has_self_review": chksr.get("has_self_review")})
    check("started: check-self-review sees the row", chksr.get("has_self_review"), True)

    # =====================================================================
    # 4b. The read surface really keys on STARTED, while reporting keys on ACTIVE
    #     Stand-only manipulation: clear the start mark by SQL with the same
    #     rows in place, re-read both surfaces, then restore it. This is the only
    #     way to compare the two states over identical data.
    # =====================================================================
    keyed: dict[str, Any] = {}
    saved_started_at = sql(db, f"SELECT evaluation_started_at FROM performance_db.evaluation_periods WHERE id = {H1}")
    saved_started_by = sql(db, f"SELECT evaluation_started_by FROM performance_db.evaluation_periods WHERE id = {H1}")

    def read_surface(label: str) -> dict[str, Any]:
        _, e = call(base, "GET", "api/employees", token=tok["manager"])
        _, sr = call(base, "GET", "api/check-self-review?user_id=1203", token=tok["employee_a"])
        _, ce = call(base, "GET", "api/check-evaluated?evaluator_id=1202", token=tok["manager"])
        _, mm = call(base, "GET", "api/get-my-manager", token=tok["employee_a"])
        _, mx = call(base, "GET", "api/admin/evaluations-matrix", token=tok["admin"])
        return {
            "label": label,
            "employees.campaign_active": e["campaign_active"],
            "employees.period_in_preparation": e["period_in_preparation"],
            "employees.actor_is_in_scope": e["actor_is_in_scope"],
            "employees.subordinate_rows": len(e["data"]),
            "employees.evaluated_by_actor_1203":
                next((r.get("evaluated_by_actor") for r in e["data"] if r["id"] == 1203), None),
            "check_self_review.has_self_review": sr.get("has_self_review"),
            "check_evaluated.rows": len(ce.get("details") or []),
            "get_my_manager.has_evaluated_manager": (mm.get("manager") or {}).get("has_evaluated_manager"),
            "matrix.campaign_active": mx.get("campaign_active"),
            "matrix.period_id": (mx.get("period") or {}).get("id"),
            "matrix.employee_rows": len(mx.get("data") or []),
        }

    keyed["with_start_mark"] = read_surface("evaluation_started_at set")
    sql(db, f"UPDATE performance_db.evaluation_periods SET evaluation_started_by = NULL, evaluation_started_at = NULL WHERE id = {H1}")
    keyed["without_start_mark"] = read_surface("evaluation_started_at cleared (same rows)")
    sql(db, f"""UPDATE performance_db.evaluation_periods
                SET evaluation_started_at = TIMESTAMPTZ '{saved_started_at}',
                    evaluation_started_by = {saved_started_by}
                WHERE id = {H1}""")
    keyed["restored"] = read_surface("evaluation_started_at restored")
    REPORT["read_surface_keying"] = keyed

    on, off = keyed["with_start_mark"], keyed["without_start_mark"]
    check("campaign surface goes dark without the start mark", [
        off["employees.campaign_active"], off["employees.period_in_preparation"],
        off["employees.subordinate_rows"], off["check_self_review.has_self_review"],
        off["check_evaluated.rows"], off["get_my_manager.has_evaluated_manager"],
    ], [False, True, 0, False, 0, False])
    check("the same surface is live with the mark", [
        on["employees.campaign_active"], on["employees.subordinate_rows"],
        on["check_self_review.has_self_review"], on["check_evaluated.rows"],
        on["get_my_manager.has_evaluated_manager"],
    ], [True, 2, True, 2, True])
    check("actor_is_in_scope is unaffected by the start mark",
          (on["employees.actor_is_in_scope"], off["employees.actor_is_in_scope"]), (True, True))
    check("the admin matrix is unaffected by the start mark",
          (on["matrix.campaign_active"], off["matrix.campaign_active"],
           on["matrix.period_id"], off["matrix.period_id"],
           on["matrix.employee_rows"], off["matrix.employee_rows"]),
          (True, True, H1, H1, on["matrix.employee_rows"], on["matrix.employee_rows"]))
    strip = lambda d: {k: v for k, v in d.items() if k != "label"}
    check("clearing and restoring the mark left it identical",
          strip(keyed["restored"]), strip(keyed["with_start_mark"]))

    # =====================================================================
    # 5. START AGAIN -> explicit already-started, zero state change
    # =====================================================================
    before = sql(db, f"""SELECT md5(evaluation_started_at::text || '|' || evaluation_started_by
                         || '|' || status || '|' || is_active)
                         FROM performance_db.evaluation_periods WHERE id = {H1}""")
    status, body = call(base, "POST", "api/periods/start-evaluation",
                        token=tok["admin"], body={"period_id": H1})
    after = sql(db, f"""SELECT md5(evaluation_started_at::text || '|' || evaluation_started_by
                        || '|' || status || '|' || is_active)
                        FROM performance_db.evaluation_periods WHERE id = {H1}""")
    record("start_again", "response", {"status": status,
                                       "already_started": (body or {}).get("already_started"),
                                       "message": (body or {}).get("message")})
    record("start_again", "row_fingerprint", {"before": before, "after": after})
    check("second start is an explicit no-op",
          (status, (body or {}).get("already_started")), (200, True))
    check("second start changed no state", after, before)

    # =====================================================================
    # 6. PRECONDITION REFUSALS
    # =====================================================================
    refusals: dict[str, Any] = {}
    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": ANNUAL_2026})
    refusals["container (Annual 2026, has a child)"] = {"status": s, "error": (b or {}).get("error")}
    check("container refused", (s, (b or {}).get("error")), (422, "CONTAINER_NOT_STARTABLE"))

    s, b = call(base, "POST", "api/periods/create", token=tok["admin"],
                body={"name": "LC Annual 2027", "start_date": "2027-01-01",
                      "end_date": "2027-12-31", "period_type": "annual"})
    annual_childless = b["data"]["id"]
    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": annual_childless})
    refusals["annual, childless"] = {"period_id": annual_childless, "status": s,
                                     "error": (b or {}).get("error")}
    check("childless annual refused", (s, (b or {}).get("error")), (422, "ANNUAL_PERIOD_NOT_STARTABLE"))

    s, b = call(base, "POST", "api/periods/create", token=tok["admin"],
                body={"name": "LC H2-2026 draft", "start_date": "2026-07-01",
                      "end_date": "2026-12-31", "period_type": "half_year"})
    draft_leaf = b["data"]["id"]
    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": draft_leaf})
    refusals["draft leaf"] = {"period_id": draft_leaf, "status": s, "error": (b or {}).get("error")}
    check("draft leaf refused", (s, (b or {}).get("error")), (422, "PERIOD_NOT_ACTIVE"))

    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": 999999})
    refusals["unknown id"] = {"status": s, "error": (b or {}).get("error")}
    check("unknown period refused", (s, (b or {}).get("error")), (404, "PERIOD_NOT_FOUND"))

    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": "not-a-number"})
    refusals["invalid id"] = {"status": s, "error": (b or {}).get("error")}
    check("invalid period id refused", (s, (b or {}).get("error")), (422, "INVALID_PERIOD_ID"))
    REPORT["refusals"] = refusals

    # =====================================================================
    # 7. BUG-029: zero weight / zero coefficient rejected on both write paths
    # =====================================================================
    bug029: dict[str, Any] = {}
    before_w = sql(db, "SELECT weight FROM performance_db.criteria WHERE id = 12")
    s, b = weight_save(weight=0)
    after_w = sql(db, "SELECT weight FROM performance_db.criteria WHERE id = 12")
    bug029["weight_zero"] = {"status": s, "error": (b or {}).get("error"),
                             "weight_before": before_w, "weight_after": after_w}
    check("weight 0 rejected", (s, (b or {}).get("error")), (422, "INVALID_WEIGHT"))
    check("weight 0 wrote nothing", after_w, before_w)

    before_c = sql(db, "SELECT coefficient FROM performance_db.score_coefficients WHERE criteria_id = 12 AND score_level = 5")
    s, b = weight_save(weight=1.0, coefficient=0)
    after_c = sql(db, "SELECT coefficient FROM performance_db.score_coefficients WHERE criteria_id = 12 AND score_level = 5")
    bug029["coefficient_zero"] = {"status": s, "error": (b or {}).get("error"),
                                  "coefficient_before": before_c, "coefficient_after": after_c}
    check("coefficient 0 rejected", (s, (b or {}).get("error")), (422, "INVALID_COEFFICIENT"))
    check("coefficient 0 wrote nothing", after_c, before_c)

    grade_id = int(sql(db, "SELECT id FROM performance_db.grades WHERE code = 'S1'"))
    before_g = sql(db, f"SELECT coefficient FROM performance_db.grades WHERE id = {grade_id}")
    s, b = grade_save(0)
    after_g = sql(db, f"SELECT coefficient FROM performance_db.grades WHERE id = {grade_id}")
    bug029["grade_coefficient_zero"] = {"status": s, "error": (b or {}).get("error"),
                                        "coefficient_before": before_g, "coefficient_after": after_g}
    check("grade coefficient 0 rejected", (s, (b or {}).get("error")), (422, "INVALID_GRADE_COEFFICIENT"))
    check("grade coefficient 0 wrote nothing", after_g, before_g)

    s, b = weight_save(weight=float("-1"))
    bug029["weight_negative"] = {"status": s, "error": (b or {}).get("error")}
    check("negative weight rejected", (s, (b or {}).get("error")), (422, "INVALID_WEIGHT"))

    s, b = call(base, "POST", "api/score-coefficients", token=tok["admin"], body={
        "criteria": [{"id": 12, "weight": 1.0,
                      "score_coefficients": {**{str(i): 1.0 for i in range(1, 11)}, "11": 1.0}}]})
    bug029["level_out_of_range"] = {"status": s, "error": (b or {}).get("error")}
    check("level 11 rejected", (s, (b or {}).get("error")), (422, "INVALID_COEFFICIENT_LEVEL"))
    REPORT["bug_029"] = bug029

    # =====================================================================
    # 8. CLOSE of a STARTED period: semantics unchanged (close proof re-run)
    # =====================================================================
    _, matrix = call(base, "GET", "api/admin/evaluations-matrix", token=tok["admin"])
    _, coefs = call(base, "GET", "api/score-coefficients", token=tok["admin"])
    _, users_data = call(base, "GET", "api/admin-users-data", token=tok["admin"])
    expected_pipeline = client_pipeline(
        matrix["data"], coefs["data"], users_data["options"]["grades"])

    results_before = sql(db, "SELECT count(*) FROM performance_db.period_results")
    status, body = call(base, "POST", "api/periods/close", token=tok["admin"],
                        body={"period_id": H1})
    record("close", "response", {"status": status, "results_stored": (body or {}).get("results_stored"),
                                 "in_scope": (body or {}).get("in_scope"),
                                 "no_data": (body or {}).get("no_data"),
                                 "already_closed": (body or {}).get("already_closed")})
    check("close of a started period succeeds", status, 200)

    persisted = {}
    for line in sql(db, f"""
        SELECT user_id || '|' || COALESCE(final_rating::text,'-') || '|'
               || COALESCE(bonus_index::text,'-') || '|' || has_data || '|' || is_in_scope
        FROM performance_db.period_results WHERE period_id = {H1} AND user_id IN (1203, 1204)
        ORDER BY user_id""").splitlines():
        uid, final, index, has_data, in_scope = line.split("|")
        persisted[int(uid)] = {"final_rating": None if final == "-" else float(final),
                               "bonus_index": None if index == "-" else float(index),
                               "has_data": has_data == "t", "is_in_scope": in_scope == "t"}
    close_tuples = []
    for uid in (1203, 1204):
        exp = expected_pipeline.get(uid, {})
        got = persisted.get(uid, {})
        close_tuples.append({
            "user_id": uid,
            "matrix_pipeline_final": exp.get("final"),
            "persisted_final_rating": got.get("final_rating"),
            "matrix_pipeline_index": exp.get("index"),
            "persisted_bonus_index": got.get("bonus_index"),
            "final_match": exp.get("final") is not None and got.get("final_rating") is not None
                           and abs(exp["final"] - got["final_rating"]) < 0.005,
            "index_match": exp.get("index") is not None and got.get("bonus_index") is not None
                           and abs(exp["index"] - got["bonus_index"]) < 0.005,
        })
        check(f"{uid}: persisted final matches the matrix pipeline",
              close_tuples[-1]["final_match"], True)
        check(f"{uid}: persisted index matches the matrix pipeline",
              close_tuples[-1]["index_match"], True)
    REPORT.setdefault("close", {})["tuples"] = close_tuples
    check("the close proof compared something", len(close_tuples), 2)

    fingerprint_1 = sql(db, f"""
      SELECT md5(string_agg(user_id || '|' || COALESCE(final_rating::text,'-') || '|'
             || COALESCE(bonus_index::text,'-'), E'\\n' ORDER BY user_id))
      FROM performance_db.period_results WHERE period_id = {H1}""")
    status, body = call(base, "POST", "api/periods/close", token=tok["admin"],
                        body={"period_id": H1})
    fingerprint_2 = sql(db, f"""
      SELECT md5(string_agg(user_id || '|' || COALESCE(final_rating::text,'-') || '|'
             || COALESCE(bonus_index::text,'-'), E'\\n' ORDER BY user_id))
      FROM performance_db.period_results WHERE period_id = {H1}""")
    record("close", "second_close", {"status": status, "already_closed": (body or {}).get("already_closed"),
                                     "fingerprint_before": fingerprint_1,
                                     "fingerprint_after": fingerprint_2,
                                     "results_before_first_close": results_before})
    check("second close is idempotent", (status, (body or {}).get("already_closed")), (200, True))
    check("second close changed no results", fingerprint_2, fingerprint_1)

    s, b = call(base, "POST", "api/periods/start-evaluation", token=tok["admin"],
                body={"period_id": H1})
    REPORT["refusals"]["closed period"] = {"status": s, "error": (b or {}).get("error")}
    check("closed period refused", (s, (b or {}).get("error")), (422, "PERIOD_CLOSED"))

    started_at_final = sql(db, f"SELECT evaluation_started_at FROM performance_db.evaluation_periods WHERE id = {H1}")
    record("close", "start_mark_survives_close", {"before": started_at_1, "after": started_at_final})
    check("the start mark survives close", started_at_final, started_at_1)

    # =====================================================================
    REPORT["failures"] = FAILURES
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str))
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURES")
        for f in FAILURES:
            print(f"  - {f}")
        raise SystemExit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()

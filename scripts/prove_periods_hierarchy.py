#!/usr/bin/env python3
"""Acceptance proof for periods hierarchy + close-time persistence (2026-08-21).

Runs against the isolated stand from setup_hierarchy_throwaway.sh:
n8n on 127.0.0.1:25679 (tunneled), throwaway DB epe_hier_* on the VPS.

Proves, per the brief:
  - container Annual-T with closed P1 + P2; A: finals 6/8 -> annual 7, index i1+i2
  - B in scope P2 only: annual 8.0 NOT 4.0 (anti-zero-fill), P1 out-of-scope,
    index = single term
  - C in scope P1, never evaluated: no-data marker, excluded from mean, visible
  - persisted final/index == client pipeline over the matrix API (cross-check)
  - weight edit after close changes nothing; second close changes zero rows
  - container activation refused (422); rename safe; reparent safe
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
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"

JTIS = {
    "admin": ("11111111-1111-4111-8111-111111111101", 1101),
    "manager": ("11111111-1111-4111-8111-111111111102", 1102),
    "employee_a": ("11111111-1111-4111-8111-111111111103", 1103),
    "c_level": ("11111111-1111-4111-8111-111111111106", 1106),
    "hr": ("11111111-1111-4111-8111-111111111107", 1107),
}


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint_token(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 4 * 3600, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    sig = b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


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
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", "replace")
        return exc.code, parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sql(database: str, statement: str) -> str:
    if not database.startswith("epe_hier_"):
        raise SystemExit(f"Refusing non-throwaway database: {database}")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def results_fingerprint(database: str, period_id: int | None = None) -> str:
    where = f"WHERE period_id = {period_id}" if period_id else ""
    return sql(database, f"""
      SELECT COALESCE(md5(string_agg(
        period_id || '|' || user_id || '|' || is_in_scope || '|' || has_data || '|' ||
        COALESCE(rating_manager::text,'-') || '|' || COALESCE(rating_upward::text,'-') || '|' ||
        COALESCE(rating_c_level_direct::text,'-') || '|' || COALESCE(rating_self::text,'-') || '|' ||
        COALESCE(final_rating::text,'-') || '|' || COALESCE(bonus_index::text,'-'),
        E'\\n' ORDER BY period_id, user_id)), 'empty')
      FROM performance_db.period_results {where}""")


# ── Client pipeline replica (matrixUtils + useFinalScoresMatrix, verbatim) ──

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
            # JS Math.round semantics (x.5 rounds up), not Python banker's rounding
            level = max(0, min(10, int(raw + 0.5) if raw >= 0 else round(raw)))
            level_map = coefs.get("score_coefficients") or {}
            level_value = level_map.get(str(level), level_map.get(level))
            coefficient = 1.0 if level_value is None else float(level_value)
            weighted_sum += raw * coefficient * weight
        grade_coefficient = grade_map.get(emp.get("grade_code"), 1.0)
        out[emp["id"]] = {
            "final": (sum(finals) / len(finals)) if finals else None,
            "index": (weighted_sum * grade_coefficient) if finals else None,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--env-file", type=Path,
                        default=Path("backups/2026-08-21-periods-hierarchy/throwaway_env.json"))
    parser.add_argument("--output", type=Path,
                        default=Path("backups/2026-08-21-periods-hierarchy/api_proof.json"))
    args = parser.parse_args()

    parsed_base = urllib.parse.urlparse(args.base_url)
    if parsed_base.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Proof base URL must be loopback")
    env = json.loads(args.env_file.read_text())
    database: str = env["database"]
    if not database.startswith("epe_hier_"):
        raise SystemExit("Proof database must use the epe_hier_ prefix")
    secret: str = env["jwt_secret"]

    tokens = {actor: mint_token(secret, uid, jti) for actor, (jti, uid) in JTIS.items()}
    evidence: dict[str, Any] = {"database": database}

    def record(name: str, method: str, path: str, *, actor: str | None = None,
               body: dict[str, Any] | None = None) -> tuple[int, Any]:
        status, payload = call(args.base_url, method, path,
                               token=tokens.get(actor) if actor else None, body=body)
        evidence[name] = {"status": status, "body": payload}
        return status, payload

    # ── 1. Create the container and children ─────────────────────────────
    status, annual = record("create_container", "POST", "api/periods/create", actor="admin",
                            body={"name": "Hier Annual-T", "start_date": "2026-01-01",
                                  "end_date": "2026-12-31", "period_type": "annual"})
    require(status == 200, f"container create failed: {annual}")
    annual_id = annual["data"]["id"]

    status, p1 = record("create_p1_with_parent", "POST", "api/periods/create", actor="admin",
                        body={"name": "Hier P1", "start_date": "2026-01-01",
                              "end_date": "2026-06-30", "period_type": "half_year",
                              "parent_period_id": annual_id})
    require(status == 200 and p1["data"]["parent_period_id"] == annual_id,
            f"P1 create-with-parent failed: {p1}")
    p1_id = p1["data"]["id"]

    status, p2 = record("create_p2", "POST", "api/periods/create", actor="admin",
                        body={"name": "Hier P2", "start_date": "2026-07-01",
                              "end_date": "2026-12-31", "period_type": "half_year"})
    require(status == 200, f"P2 create failed: {p2}")
    p2_id = p2["data"]["id"]

    status, attach = record("attach_p2", "POST", "api/periods/reparent", actor="admin",
                            body={"period_id": p2_id, "parent_period_id": annual_id})
    require(status == 200 and attach["data"]["parent_period_id"] == annual_id,
            f"P2 attach failed: {attach}")

    # ── 2. Container refusals ────────────────────────────────────────────
    status, refusal = record("container_activate_422", "POST", "api/periods/activate",
                             actor="admin", body={"period_id": annual_id})
    require(status == 422 and refusal.get("error") == "CONTAINER_NOT_ACTIVATABLE",
            f"container activation must 422: {status} {refusal}")

    status, refusal = record("container_close_422", "POST", "api/periods/close",
                             actor="admin", body={"period_id": annual_id})
    require(status == 422 and refusal.get("error") == "CONTAINER_NOT_CLOSABLE",
            f"container close must 422: {status} {refusal}")

    status, refusal = record("dates_outside_parent_422", "POST", "api/periods/create",
                             actor="admin",
                             body={"name": "Hier Bad Dates", "start_date": "2025-12-01",
                                   "end_date": "2026-03-31", "period_type": "half_year",
                                   "parent_period_id": annual_id})
    require(status == 422 and refusal.get("error") == "CHILD_DATES_OUTSIDE_PARENT",
            f"outside dates must 422: {status} {refusal}")

    status, refusal = record("nested_container_422", "POST", "api/periods/reparent",
                             actor="admin", body={"period_id": annual_id, "parent_period_id": p2_id})
    require(status == 422 and refusal.get("error") == "CHILD_IS_CONTAINER",
            f"nesting a container must 422: {status} {refusal}")

    # ── 3. P1 campaign: activate, seed evaluations, close ────────────────
    status, act = record("activate_p1", "POST", "api/periods/activate", actor="admin",
                         body={"period_id": p1_id})
    require(status == 200, f"P1 activation failed: {act}")

    # B out of scope in P1 (hired for H2 in the story)
    sql(database, f"""
      UPDATE performance_db.evaluation_period_participants
      SET is_in_scope = false, exclusion_reason = 'hier acceptance: out of scope P1'
      WHERE period_id = {p1_id} AND user_id = 1104;
    """)
    # Evaluations P1: manager->A 6/6/6; A self 5/5/5; A upward->manager 7
    sql(database, f"""
      INSERT INTO performance_db.evaluations
        (id, period_id, subject_id, evaluator_id, status, calculated_score, weighted_score,
         updated_at, evaluation_type, is_self_evaluation, evaluation_source)
      VALUES
        (2101, {p1_id}, 1103, 1102, 'completed', 6.00, NULL, now(), 'manager', false, 'manager'),
        (2102, {p1_id}, 1103, 1103, 'completed', 5.00, 5.00, now(), 'self', true, 'self'),
        (2103, {p1_id}, 1102, 1103, 'completed', 7.00, NULL, now(), 'manager', false, 'subordinate');
      INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
      VALUES
        (2101, 3, 6, NULL), (2101, 4, 6, NULL), (2101, 12, 6, NULL),
        (2102, 3, 5, NULL), (2102, 4, 5, NULL), (2102, 12, 5, NULL),
        (2103, 2, 7, NULL);
    """)

    status, close1 = record("close_p1", "POST", "api/periods/close", actor="admin",
                            body={"period_id": p1_id})
    require(status == 200 and close1.get("closed") is True, f"P1 close failed: {close1}")
    evidence["close_p1_counts"] = {k: close1.get(k) for k in ("results_stored", "in_scope", "no_data")}

    stored_p1 = sql(database, f"""
      SELECT user_id || '|' || is_in_scope || '|' || has_data || '|' ||
             COALESCE(rating_manager::text,'-') || '|' || COALESCE(rating_upward::text,'-') || '|' ||
             COALESCE(rating_self::text,'-') || '|' ||
             COALESCE(final_rating::text,'-') || '|' || COALESCE(bonus_index::text,'-')
      FROM performance_db.period_results
      WHERE period_id = {p1_id} AND user_id BETWEEN 1101 AND 1110 ORDER BY user_id""")
    evidence["stored_p1_fixture_rows"] = stored_p1.splitlines()
    rows_p1 = {int(line.split("|")[0]): line.split("|") for line in stored_p1.splitlines()}
    require(rows_p1[1103][6].startswith("6.0"), f"A final in P1 must be 6.0: {rows_p1[1103]}")
    require(rows_p1[1103][3] == "6.00", f"A manager rating must persist 6.00: {rows_p1[1103]}")
    require(rows_p1[1103][5] == "5.00", f"A self rating must persist 5.00: {rows_p1[1103]}")
    require(rows_p1[1102][4] == "7.00", f"manager upward rating must persist 7.00: {rows_p1[1102]}")
    require(rows_p1[1104][1] == "f" and rows_p1[1104][6] == "-" and rows_p1[1104][7] == "-",
            f"B out of scope in P1 must carry no numbers: {rows_p1[1104]}")
    require(rows_p1[1105][1] == "t" and rows_p1[1105][2] == "f" and rows_p1[1105][6] == "-",
            f"C must be explicit no-data, not zero: {rows_p1[1105]}")
    a_index_p1 = float(rows_p1[1103][7])

    # ── 4. P2 campaign ───────────────────────────────────────────────────
    status, act2 = record("activate_p2", "POST", "api/periods/activate", actor="admin",
                          body={"period_id": p2_id})
    require(status == 200, f"P2 activation failed: {act2}")
    sql(database, f"""
      INSERT INTO performance_db.evaluations
        (id, period_id, subject_id, evaluator_id, status, calculated_score, weighted_score,
         updated_at, evaluation_type, is_self_evaluation, evaluation_source)
      VALUES
        (2111, {p2_id}, 1103, 1102, 'completed', 8.00, NULL, now(), 'manager', false, 'manager'),
        (2112, {p2_id}, 1104, 1102, 'completed', 8.00, NULL, now(), 'manager', false, 'manager');
      INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
      VALUES
        (2111, 3, 8, NULL), (2111, 4, 8, NULL), (2111, 12, 8, NULL),
        (2112, 3, 8, NULL), (2112, 4, 8, NULL), (2112, 12, 8, NULL);
    """)
    status, close2 = record("close_p2", "POST", "api/periods/close", actor="admin",
                            body={"period_id": p2_id})
    require(status == 200 and close2.get("closed") is True, f"P2 close failed: {close2}")

    stored_p2 = sql(database, f"""
      SELECT user_id || '|' || is_in_scope || '|' || has_data || '|' ||
             COALESCE(final_rating::text,'-') || '|' || COALESCE(bonus_index::text,'-')
      FROM performance_db.period_results
      WHERE period_id = {p2_id} AND user_id BETWEEN 1101 AND 1110 ORDER BY user_id""")
    evidence["stored_p2_fixture_rows"] = stored_p2.splitlines()
    rows_p2 = {int(line.split("|")[0]): line.split("|") for line in stored_p2.splitlines()}
    require(rows_p2[1103][3].startswith("8.0"), f"A final in P2 must be 8.0: {rows_p2[1103]}")
    require(rows_p2[1104][3].startswith("8.0"), f"B final in P2 must be 8.0: {rows_p2[1104]}")
    a_index_p2 = float(rows_p2[1103][4])
    b_index_p2 = float(rows_p2[1104][4])

    # ── 5. Second close: zero rows changed ───────────────────────────────
    fp_before = results_fingerprint(database)
    count_before = sql(database, "SELECT count(*) FROM performance_db.period_results")
    status, again = record("close_p2_again", "POST", "api/periods/close", actor="admin",
                           body={"period_id": p2_id})
    require(status == 200 and again.get("already_closed") is True
            and again.get("results_stored") == 0,
            f"second close must be a zero-write no-op: {status} {again}")
    require(results_fingerprint(database) == fp_before, "second close changed stored rows")
    require(sql(database, "SELECT count(*) FROM performance_db.period_results") == count_before,
            "second close changed row count")

    # ── 6. Annual roll-up ────────────────────────────────────────────────
    status, rollup = record("rollup_admin", "GET",
                            f"api/periods/annual-rollup?container_id={annual_id}", actor="admin")
    require(status == 200, f"rollup failed: {rollup}")
    require(len(rollup["children"]) == 2, f"container must show 2 children: {rollup['children']}")
    people = {row["user_id"]: row for row in rollup["rows"]}

    a_row = people[1103]
    require(abs(float(a_row["annual_rating"]) - 7.0) < 1e-6,
            f"A annual rating must be mean(6,8)=7.0: {a_row['annual_rating']}")
    require(abs(float(a_row["annual_index"]) - (a_index_p1 + a_index_p2)) < 0.0001,
            f"A annual index must be i1+i2={a_index_p1 + a_index_p2}: {a_row['annual_index']}")

    b_row = people[1104]
    require(abs(float(b_row["annual_rating"]) - 8.0) < 1e-6,
            f"B annual rating must be 8.0 (out-of-scope excluded): {b_row['annual_rating']}")
    require(abs(float(b_row["annual_rating"]) - 4.0) > 1.0,
            "ANTI-ZERO-FILL: B must NOT be diluted to 4.0")
    require(b_row["results"].get(str(p1_id), {}).get("in_scope") is False,
            f"B P1 cell must be out-of-scope: {b_row['results']}")
    require(abs(float(b_row["annual_index"]) - b_index_p2) < 0.0001,
            f"B annual index must be its single P2 term: {b_row['annual_index']}")

    c_row = people.get(1105)
    require(c_row is not None, "C must be visible in the rollup")
    require(c_row["annual_rating"] is None, f"C has no data anywhere -> no mean: {c_row}")
    c_p1 = c_row["results"].get(str(p1_id), {})
    require(c_p1.get("in_scope") is True and c_p1.get("has_data") is False,
            f"C P1 cell must be explicit no-data: {c_p1}")

    # audience: c_level 200, hr 403, employee 403
    status, _ = record("rollup_c_level", "GET",
                       f"api/periods/annual-rollup?container_id={annual_id}", actor="c_level")
    require(status == 200, "c_level must read the rollup")
    status, _ = record("rollup_hr_403", "GET",
                       f"api/periods/annual-rollup?container_id={annual_id}", actor="hr")
    require(status == 403, "hr must not read the rollup (D-0820-11)")
    status, _ = record("rollup_employee_403", "GET",
                       f"api/periods/annual-rollup?container_id={annual_id}", actor="employee_a")
    require(status == 403, "employee must not read the rollup")

    # rollup of a leaf is refused
    status, refusal = record("rollup_leaf_422", "GET",
                             f"api/periods/annual-rollup?container_id={p1_id}", actor="admin")
    require(status == 422 and refusal.get("error") == "NOT_A_CONTAINER",
            f"leaf rollup must 422: {status} {refusal}")

    # ── 7. Cross-check vs the matrix / money-screen pipeline ─────────────
    status, coefs = record("score_coefficients", "GET", "api/score-coefficients", actor="admin")
    require(status == 200, f"score-coefficients failed: {coefs}")
    coef_rows = coefs.get("data") or coefs
    status, users_data = record("admin_users_data", "GET", "api/admin-users-data", actor="admin")
    require(status == 200, f"admin-users-data failed: {users_data}")
    grade_rows = (users_data.get("options") or {}).get("grades") or []

    for period_id, rows_stored in ((p1_id, rows_p1), (p2_id, rows_p2)):
        status, matrix = record(f"matrix_p{period_id}", "GET",
                                f"api/admin/evaluations-matrix?period_id={period_id}", actor="admin")
        require(status == 200, f"matrix failed for {period_id}: {matrix}")
        replica = client_pipeline(matrix["data"], coef_rows, grade_rows)
        for user_id in (1102, 1103, 1104, 1105):
            expected = replica.get(user_id)
            stored = rows_stored.get(user_id)
            if expected is None or stored is None:
                continue
            stored_final = None if stored[-2] == "-" else float(stored[-2])
            stored_index = None if stored[-1] == "-" else float(stored[-1])
            if not (stored[1] == "t" and stored[2] == "t"):
                continue  # out-of-scope/no-data rows carry no numbers by design
            if expected["final"] is None:
                require(stored_final is None,
                        f"user {user_id} period {period_id}: client no-final but stored {stored_final}")
                continue
            require(stored_final is not None and abs(stored_final - expected["final"]) < 0.005,
                    f"user {user_id} period {period_id}: stored final {stored_final} != client {expected['final']}")
            require(stored_index is not None and abs(stored_index - expected["index"]) < 0.005,
                    f"user {user_id} period {period_id}: stored index {stored_index} != client {expected['index']}")
    evidence["cross_check"] = "stored final/index match client matrix+money pipeline (<0.005)"

    # ── 8. Immutability: weight/grade edits change nothing after close ───
    fp_before = results_fingerprint(database)
    rollup_before = json.dumps(rollup["rows"], sort_keys=True)
    sql(database, """
      UPDATE performance_db.criteria SET weight = weight + 3 WHERE id = 3;
      UPDATE performance_db.grades SET coefficient = coefficient + 0.7
      WHERE id = (SELECT min(id) FROM performance_db.grades);
    """)
    status, rollup_after = record("rollup_after_weight_edit", "GET",
                                  f"api/periods/annual-rollup?container_id={annual_id}",
                                  actor="admin")
    require(status == 200, "rollup after weight edit failed")
    require(json.dumps(rollup_after["rows"], sort_keys=True) == rollup_before,
            "IMMUTABILITY: weight/grade edit must not change the annual view")
    require(results_fingerprint(database) == fp_before,
            "IMMUTABILITY: weight/grade edit must not change stored results")
    sql(database, """
      UPDATE performance_db.criteria SET weight = weight - 3 WHERE id = 3;
      UPDATE performance_db.grades SET coefficient = coefficient - 0.7
      WHERE id = (SELECT min(id) FROM performance_db.grades);
    """)

    # ── 9. Rename: label only, nothing keys on the name ──────────────────
    status, renamed = record("rename_p1", "POST", "api/periods/rename", actor="admin",
                             body={"period_id": p1_id, "name": "Hier P1 (переименован)"})
    require(status == 200 and renamed["data"]["name"] == "Hier P1 (переименован)",
            f"rename failed: {renamed}")
    status, dup = record("rename_duplicate_409", "POST", "api/periods/rename", actor="admin",
                         body={"period_id": p1_id, "name": "Hier P2"})
    require(status == 409 and dup.get("error") == "PERIOD_NAME_TAKEN",
            f"duplicate rename must 409: {status} {dup}")
    require(results_fingerprint(database) == fp_before, "rename must not touch stored results")
    status, rollup_renamed = record("rollup_after_rename", "GET",
                                    f"api/periods/annual-rollup?container_id={annual_id}",
                                    actor="admin")
    require(any(c["name"] == "Hier P1 (переименован)" for c in rollup_renamed["children"]),
            "rollup must show the new child name")
    require(json.dumps(rollup_renamed["rows"], sort_keys=True) == rollup_before,
            "rename must not change any number")

    # ── 10. Reparent is safe: detach and re-attach, numbers identical ────
    status, det = record("detach_p1", "POST", "api/periods/reparent", actor="admin",
                         body={"period_id": p1_id, "parent_period_id": None})
    require(status == 200 and det["data"]["parent_period_id"] is None, f"detach failed: {det}")
    status, rollup_det = record("rollup_after_detach", "GET",
                                f"api/periods/annual-rollup?container_id={annual_id}",
                                actor="admin")
    require(len(rollup_det["children"]) == 1, "detached child must leave the container")
    # While P1 is detached (top-level, has evaluations): it can never become a parent
    status, refusal = record("parent_has_evaluations_422", "POST", "api/periods/reparent",
                             actor="admin",
                             body={"period_id": p2_id, "parent_period_id": p1_id})
    require(status == 422 and refusal.get("error") == "PARENT_HAS_EVALUATIONS",
            f"period with evaluations as parent must 422: {status} {refusal}")
    status, reat = record("reattach_p1", "POST", "api/periods/reparent", actor="admin",
                          body={"period_id": p1_id, "parent_period_id": annual_id})
    require(status == 200 and reat["data"]["parent_period_id"] == annual_id,
            f"re-attach failed: {reat}")
    status, rollup_reat = record("rollup_after_reattach", "GET",
                                 f"api/periods/annual-rollup?container_id={annual_id}",
                                 actor="admin")
    require(json.dumps(rollup_reat["rows"], sort_keys=True) == rollup_before,
            "reparenting must not change any number")
    require(results_fingerprint(database) == fp_before, "reparenting must not touch stored results")

    # ── 11. Closed period cannot be re-activated ─────────────────────────
    status, refusal = record("activate_closed_422", "POST", "api/periods/activate",
                             actor="admin", body={"period_id": p1_id})
    require(status == 422 and refusal.get("error") == "PERIOD_CLOSED",
            f"closed period activation must 422: {status} {refusal}")

    # ── 12. GET periods catalogue shows the hierarchy ────────────────────
    status, catalogue = record("periods_catalogue", "GET", "api/periods", actor="admin")
    require(status == 200, "catalogue failed")
    by_id = {p["id"]: p for p in catalogue["data"]}
    require(by_id[annual_id]["child_count"] == 2, "container must report child_count=2")
    require(by_id[p1_id]["parent_period_id"] == annual_id, "P1 must report its parent")
    require(by_id[p1_id]["has_results"] is True, "P1 must report has_results")
    require(by_id[2]["status"] == "draft" and by_id[2]["is_active"] is False,
            "H1 (id=2) must stay draft/inactive on the stand")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str))
    print(f"ALL CHECKS PASSED — evidence in {args.output}")
    print(json.dumps({
        "annual_id": annual_id, "p1_id": p1_id, "p2_id": p2_id,
        "A_annual": people[1103]["annual_rating"], "A_index": people[1103]["annual_index"],
        "B_annual": people[1104]["annual_rating"], "B_index": people[1104]["annual_index"],
        "C_annual": people[1105]["annual_rating"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

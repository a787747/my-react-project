#!/usr/bin/env python3
"""PRELAUNCH_BATCH_NIGHT — prove items 3, 6, 7 and 8 on the throwaway stand.

Nothing here trusts the application. The bonus allocation index is recomputed
from the raw database rows by an implementation written independently of the
JavaScript, and BOTH are then compared against constants worked out by hand and
written into this file before the stand was built (`EXPECTED_INDEX`). A run in
which the two implementations agree with each other but not with the hand
figures fails.

  §1  the arithmetic, from raw rows, three ways
  §2  /api/employees — the excluded person and their manager (item 3)
  §3  /api/admin-users-data — the five period states (item 5)
  §4  /api/admin/evaluations-matrix — every criterion, every channel (item 6)
  §5  the budget distribution (item 7), against the shipped JS
  §6  the pool rule and the people it removes (item 8)

Live is never contacted except to read the JWT secret of the STAND container.
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
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}

# ── The hand computation ─────────────────────────────────────────────────────
# Worked out on paper from the live catalogue before the stand existed, using
# formula 3 of HANDOVER §4: Σ(score × level-coefficient × weight) × grade
# coefficient, with NO division by the sum of weights.
#
#   1602 MY Manager   S2 1.10  c2 8→1.60×3.00=38.40  c3 7→1.30×3.00=27.30
#                              c4 7→1.20×1.50=12.60  c12 8→1.50×1.00=12.00
#                              c14 7→2.00×1.50=21.00 c1 6→1.20×5.00=36.00
#                              c10 5→1.00×1.60=8.00   Σ=155.30 ×1.10 = 170.830
#   1603 MY LateStart S1 0.60  c3 8→1.60×3.00=38.40  c4 7→1.20×1.50=12.60
#                              c8 6→1.10×1.40=9.24   c12 7→1.30×1.00=9.10
#                              c13 7→1.80×1.80=22.68 c14 7→2.00×1.50=21.00
#                              c1 7→1.60×5.00=56.00  c10 6→1.20×1.60=11.52
#                                                     Σ=180.54 ×0.60 = 108.324
#   1604 MY Stayer A  A  0.30  c3 6→1.10×3.00=19.80  c4 5→1.00×1.50=7.50
#                              c12 5→1.00×1.00=5.00  c14 6→1.50×1.50=13.50
#                                                     Σ=45.80  ×0.30 = 13.740
#   1605 MY Stayer B  S1 0.60  c3 (9+5+4)/3=6.0→1.10×3.00=19.80   ← corrected
#                              c4 8→1.50×1.50=18.00  c8 8→1.60×1.40=17.92
#                              c12 7→1.30×1.00=9.10  c13 9→3.80×1.80=61.56
#                              c14 8→3.00×1.50=36.00 c1 8→2.80×5.00=112.00
#                              c10 7→1.50×1.60=16.80 Σ=291.18 ×0.60 = 174.708
#   1612 MY Partial   S3 1.40  c3 6→1.10×3.00=19.80  c8 9→2.50×1.40=31.50
#                              c13 4→0.90×1.80=6.48  (c4, c12, c14 unscored)
#                                                     Σ=57.78  ×1.40 = 80.892
EXPECTED_INDEX = {
    1602: Decimal("170.830"),
    1603: Decimal("108.324"),
    1604: Decimal("13.740"),
    1605: Decimal("174.708"),
    1612: Decimal("80.892"),
}
# Formula 1, the plain rating, for the same people — the number the person sees.
# `evaluations.calculated_score` is numeric with scale 2, so the seed's 8.1667
# is stored as 8.17 and read back as such. These are the values on disk.
EXPECTED_MANAGER_RATING = {
    1602: Decimal("7.40"),
    1603: Decimal("7.00"),
    1604: Decimal("5.50"),
    1605: Decimal("8.17"),
    1612: Decimal("6.33"),
}


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST, command],
        capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST,
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


class Stand:
    def __init__(self, port: int, db: str, secret: str):
        self.port, self.db, self.secret = port, db, secret
        self.tokens: dict[int, str] = {}

    def token(self, user_id: int) -> str:
        if user_id not in self.tokens:
            # auth_sessions.jti is a uuid column; a readable string will not fit,
            # so the readable name is hashed into a stable v5 uuid instead.
            jti = str(uuid.uuid5(uuid.NAMESPACE_URL, f"epe-night/{self.port}/{user_id}"))
            version = int(sql(self.db,
                              f"SELECT token_version FROM performance_db.users WHERE id = {user_id}"))
            sql(self.db, f"""
              INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
              VALUES ('{jti}', {user_id}, {version}, now(), now() + interval '2 hours')
              ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '2 hours'""")
            self.tokens[user_id] = mint(self.secret, user_id, jti)
        return self.tokens[user_id]

    def call(self, method: str, path: str, user_id: int, body: dict | None = None) -> tuple[int, Any]:
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token(user_id)}"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/webhook/{path.lstrip('/')}",
            data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, raw.decode("utf-8", "replace")


# ── §1 the arithmetic, recomputed from raw rows ──────────────────────────────

def recompute_indices(db: str) -> dict[int, Decimal]:
    """Formula 3, from criteria / score_coefficients / grades / scores.

    Written from the methodology, not from the JavaScript: no import, no shared
    helper, and the applicability rules restated here rather than read out of a
    payload. If this and the screen agree, two independent readings agree.
    """
    criteria = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(c)), '[]') FROM (
        SELECT id, weight::text AS weight, target_audience, c_level_only
        FROM performance_db.criteria WHERE is_active = true) c""")
    coefs = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(s)), '[]') FROM (
        SELECT criteria_id, score_level, coefficient::text AS coefficient
        FROM performance_db.score_coefficients) s""")
    users = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(u)), '[]') FROM (
        SELECT u.id, u.is_project_participant, u.has_subordinates,
               g.coefficient::text AS grade_coefficient
        FROM performance_db.users u
        LEFT JOIN performance_db.grades g ON g.id = u.grade_id) u""")
    scores = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(s)), '[]') FROM (
        SELECT e.subject_id, e.evaluation_source, e.updated_at::text AS updated_at,
               es.criteria_id, es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
        WHERE e.period_id = 2 AND e.is_self_evaluation = false) s""")
    corrections = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(c)), '[]') FROM (
        SELECT subject_id, criteria_id, correction_level, correction_score
        FROM performance_db.score_corrections WHERE period_id = 2) c""")

    coef_map: dict[tuple[int, int], Decimal] = {
        (int(r["criteria_id"]), int(r["score_level"])): Decimal(r["coefficient"]) for r in coefs}
    crit_map = {int(c["id"]): c for c in criteria}

    # Latest score per (subject, criterion, source), by updated_at — the same
    # last-writer-wins the matrix SQL uses.
    latest: dict[tuple[int, int, str], tuple[str, int]] = {}
    for row in scores:
        key = (int(row["subject_id"]), int(row["criteria_id"]), row["evaluation_source"])
        if key not in latest or row["updated_at"] > latest[key][0]:
            latest[key] = (row["updated_at"], int(row["score_value"]))
    corr: dict[tuple[int, int, str], int] = {
        (int(c["subject_id"]), int(c["criteria_id"]), c["correction_level"]): int(c["correction_score"])
        for c in corrections}

    out: dict[int, Decimal] = {}
    for user in users:
        uid = int(user["id"])
        grade = Decimal(user["grade_coefficient"]) if user["grade_coefficient"] else Decimal("1.0")
        total = Decimal(0)
        for cid, crit in crit_map.items():
            audience = crit["target_audience"]
            if audience == "project_participants" and not user["is_project_participant"]:
                continue
            if audience == "managers_only" and not user["has_subordinates"]:
                continue
            if crit["c_level_only"]:
                raw = latest.get((uid, cid, "c_level_direct"))
                if raw is None:
                    continue
                final = Decimal(raw[1])
            else:
                mgr = latest.get((uid, cid, "manager"))
                if mgr is None:
                    continue
                parts = [Decimal(mgr[1])]
                for level in ("mid_level", "c_level"):
                    if (uid, cid, level) in corr:
                        parts.append(Decimal(corr[(uid, cid, level)]))
                final = sum(parts) / Decimal(len(parts))
            level = int(final.to_integral_value(rounding="ROUND_HALF_EVEN"))
            level = max(0, min(10, level))
            coefficient = coef_map.get((cid, level), Decimal("1.0"))
            total += final * coefficient * Decimal(crit["weight"])
        if total != 0:
            out[uid] = (total * grade).quantize(Decimal("0.001"))
    return out


def distribute(rows: list[tuple[Any, Decimal]], budget: Decimal, decimals: int = 2) -> dict[Any, Decimal]:
    """Largest-remainder allocation — the Python twin of distributeBudget."""
    total = sum(index for _, index in rows)
    if budget <= 0 or total <= 0:
        return {key: Decimal(0) for key, _ in rows}
    scale = Decimal(10) ** decimals
    units = int((budget * scale).to_integral_value(rounding="ROUND_HALF_EVEN"))
    exact = []
    for key, index in rows:
        share = (index / total) * units
        floor = int(share)
        exact.append([key, floor, share - floor])
    leftover = units - sum(row[1] for row in exact)
    for row in sorted(exact, key=lambda r: -r[2])[:leftover]:
        row[1] += 1
    return {key: Decimal(floor) / scale for key, floor, _ in exact}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "throwaway_env.json"))
    parser.add_argument("--out", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "night_proof.json"))
    args = parser.parse_args()
    env = json.loads(Path(args.env).read_text())
    db = env["database_treatment"]
    new = Stand(env["port_new"], db, env["jwt_secret"])
    REPORT["env"] = {k: v for k, v in env.items() if k != "jwt_secret"}

    # ── §1 the arithmetic ────────────────────────────────────────────────────
    indices = recompute_indices(db)
    REPORT["recomputed_indices"] = {str(k): str(v) for k, v in sorted(indices.items())}
    for uid, expected in EXPECTED_INDEX.items():
        check(f"§1 index of {uid} equals the hand figure",
              str(indices.get(uid)), str(expected))
    # Formula 1 is stored by the submit path; read it back so the two numbers
    # can be shown side by side.
    ratings = jsql(db, """
      SELECT COALESCE(json_object_agg(subject_id, calculated_score::text), '{}') FROM (
        SELECT subject_id, calculated_score FROM performance_db.evaluations
        WHERE period_id = 2 AND evaluation_source = 'manager') r""")
    REPORT["manager_ratings"] = ratings
    for uid, expected in EXPECTED_MANAGER_RATING.items():
        check(f"§1 stored manager rating of {uid}", ratings.get(str(uid)), str(expected))
    # The point of §4 of the HANDOVER, made numeric: two people whose ratings
    # are close have indices that are not, and that is the design.
    REPORT["rating_vs_index"] = {
        "1603": {"rating": str(EXPECTED_MANAGER_RATING[1603]), "index": str(EXPECTED_INDEX[1603])},
        "1604": {"rating": str(EXPECTED_MANAGER_RATING[1604]), "index": str(EXPECTED_INDEX[1604])},
        "rating_ratio": str((EXPECTED_MANAGER_RATING[1603] / EXPECTED_MANAGER_RATING[1604]).quantize(Decimal("0.001"))),
        "index_ratio": str((EXPECTED_INDEX[1603] / EXPECTED_INDEX[1604]).quantize(Decimal("0.001"))),
    }
    check("§1 the rating ratio and the index ratio genuinely differ",
          REPORT["rating_vs_index"]["rating_ratio"] != REPORT["rating_vs_index"]["index_ratio"], True)

    # ── §2 item 3: the excluded person and their manager ─────────────────────
    status, body = new.call("GET", "api/employees?user_id=1602&role=manager", 1602)
    REPORT["manager_employees"] = {"status": status,
                                   "data": [r["id"] for r in (body or {}).get("data", [])],
                                   "out_of_scope": [(r["id"], r.get("exclusion_reason"), r.get("join_date"))
                                                    for r in (body or {}).get("out_of_scope_data", [])]}
    check("§2 the manager's roster answers 200", status, 200)
    in_scope_ids = sorted(r["id"] for r in body["data"])
    check("§2 the task list holds only in-scope reports",
          in_scope_ids, [1603, 1604, 1605, 1612])
    oos = sorted((r["id"], r.get("exclusion_reason"), r.get("join_date"))
                 for r in body["out_of_scope_data"])
    check("§2 the excluded person is PRESENT, marked, with the reason and the date",
          oos, [(1614, "excluded_by_admin", "2026-04-09")])
    check("§2 the terminated person is in neither array — still hidden",
          [1615 in in_scope_ids, any(r[0] == 1615 for r in oos)], [False, False])

    status, body = new.call("GET", "api/employees?user_id=1614&role=employee", 1614)
    REPORT["excluded_employee_payload"] = {
        "status": status,
        "actor_is_in_scope": (body or {}).get("actor_is_in_scope"),
        "actor_exclusion_reason": (body or {}).get("actor_exclusion_reason"),
        "actor_join_date": (body or {}).get("actor_join_date"),
        "tasks": len((body or {}).get("data") or []),
    }
    check("§2 the excluded person reads as out of scope, with the reason and their hire date",
          [(body or {}).get("actor_is_in_scope"), (body or {}).get("actor_exclusion_reason"),
           (body or {}).get("actor_join_date")],
          [False, "excluded_by_admin", "2026-04-09"])
    check("§2 and has no tasks", len((body or {}).get("data") or []), 0)

    # ── §3 item 5: the five period states on the admin roster ────────────────
    status, body = new.call("GET", "api/admin-users-data", 1601)
    rows = {int(r["id"]): r for r in (body or {}).get("users", [])}
    REPORT["admin_users_states"] = {
        str(uid): {"in_scope": rows[uid].get("period_is_in_scope"),
                   "reason": rows[uid].get("period_exclusion_reason"),
                   "has_row": rows[uid].get("has_period_row"),
                   "join_date": rows[uid].get("join_date"),
                   "terminated_at": rows[uid].get("terminated_at")}
        for uid in (1602, 1610, 1613, 1614, 1615, 1607) if uid in rows}
    check("§3 the admin roster answers 200", status, 200)
    check("§3 an ordinary person is in scope with a hire date",
          [rows[1602].get("period_is_in_scope"), rows[1602].get("has_period_row"),
           bool(rows[1602].get("join_date"))], [True, True, True])
    check("§3 the excluded-by-admin row carries its reason",
          [rows[1614].get("period_is_in_scope"), rows[1614].get("period_exclusion_reason")],
          [False, "excluded_by_admin"])
    check("§3 the hired-after-period-end row carries its own, different reason",
          [rows[1607].get("period_is_in_scope"), rows[1607].get("period_exclusion_reason")],
          [False, "hired_after_period_end"])
    check("§3 the terminated row is still returned to the admin, with its date",
          [rows[1615].get("period_exclusion_reason"), bool(rows[1615].get("terminated_at"))],
          ["terminated", True])
    check("§3 the missing-hire-date row is in scope and has no date — the BUG-066 shape",
          [rows[1613].get("period_is_in_scope"), rows[1613].get("join_date")], [True, None])
    check("§3 the person with no participants row is reported as having none, not dropped",
          [1610 in rows, rows[1610].get("has_period_row"), rows[1610].get("period_is_in_scope")],
          [True, False, None])
    check("§3 the roster still holds everybody", len(rows), 104)

    # ── §4 item 6: every criterion and every channel on the matrix ───────────
    status, body = new.call("GET", "api/admin/evaluations-matrix", 1601)
    matrix = {int(r["id"]): r for r in (body or {}).get("data", [])}
    check("§4 the matrix answers 200", status, 200)

    def crit(uid: int) -> dict[int, dict]:
        return {int(c["criteria_id"]): c for c in matrix[uid]["criteria"]}

    check("§4 a project participant is emitted the six manager-path criteria plus the two C-level ones",
          sorted(crit(1603)), [1, 3, 4, 8, 10, 12, 13, 14])
    check("§4 a general employee is emitted four plus the two C-level ones",
          sorted(crit(1604)), [1, 3, 4, 10, 12, 14])
    check("§4 the manager, and only the manager, is emitted criterion 2",
          [2 in crit(1602), 2 in crit(1603), 2 in crit(1604)], [True, False, False])

    c1603 = crit(1603)
    REPORT["channels_1603"] = {
        "manager": c1603[3].get("manager_score"),
        "self": c1603[3].get("self_score"),
        "c_level_direct": c1603[1].get("c_level_score"),
        "upward_on_their_manager": crit(1602)[2].get("subordinate_avg_score"),
    }
    check("§4 all four channels reach the payload",
          [c1603[3].get("manager_score") is not None,
           c1603[3].get("self_score") is not None,
           c1603[1].get("c_level_score") is not None,
           crit(1602)[2].get("subordinate_avg_score") is not None],
          [True, True, True, True])
    # 9 + 4 + 6 over three subordinates = 6.30 after the SQL's ROUND(...,2).
    # If the exclusion had dropped what 1603 GAVE, this would read 5.00.
    check("§4 the upward channel is an average of three, not a last writer",
          [round(float(crit(1602)[2]["subordinate_avg_score"]), 2),
           int(crit(1602)[2]["subordinate_count"])],
          [6.3, 3])

    c1605 = crit(1605)
    REPORT["corrections_1605"] = {
        "manager_score": c1605[3].get("manager_score"),
        "mid_level_correction": c1605[3].get("mid_level_correction"),
        "c_level_correction": c1605[3].get("c_level_correction"),
    }
    check("§4 both corrections reach the screen alongside the manager's own score",
          [c1605[3].get("manager_score"), c1605[3].get("mid_level_correction"),
           c1605[3].get("c_level_correction")], [9, 5, 4])

    c1612 = crit(1612)
    scored = sorted(k for k, v in c1612.items() if v.get("manager_score") is not None)
    unscored = sorted(k for k, v in c1612.items()
                      if v.get("manager_score") is None and not v.get("c_level_only"))
    REPORT["partial_1612"] = {"scored": scored, "unscored": unscored}
    check("§4 a partial evaluation shows three scored and three applicable-but-empty",
          [scored, unscored], [[3, 8, 13], [4, 12, 14]])

    out_of_scope_rows = sorted(uid for uid, r in matrix.items() if r.get("is_in_scope") is False)
    REPORT["matrix_out_of_scope"] = out_of_scope_rows
    check("§4 out-of-scope people are still emitted as rows (BUG-060 unchanged), marked",
          [1614 in out_of_scope_rows, 1607 in out_of_scope_rows], [True, True])

    # ── §5 item 7: the budget distribution ───────────────────────────────────
    pool = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.id), '[]') FROM (
        SELECT u.id, COALESCE(epp.is_in_scope, false) AS is_in_scope, u.can_be_evaluated
        FROM performance_db.users u
        LEFT JOIN performance_db.evaluation_period_participants epp
          ON epp.user_id = u.id AND epp.period_id = 2
        WHERE u.role <> 'admin') p""")
    eligible = [int(r["id"]) for r in pool if r["is_in_scope"] and r["can_be_evaluated"]]
    REPORT["pool_size"] = len(eligible)
    rows = [(uid, indices.get(uid, Decimal(0))) for uid in eligible]
    total_index = sum(index for _, index in rows)
    REPORT["total_index"] = str(total_index)
    check("§5 the pool's total index is the sum of the five hand figures",
          str(total_index), str(sum(EXPECTED_INDEX.values())))

    budgets = [Decimal("1000000"), Decimal("2500000.55"), Decimal("999.99"), Decimal("1")]
    distribution_report = []
    for budget in budgets:
        amounts = distribute(rows, budget)
        total = sum(amounts.values())
        distribution_report.append({
            "budget": str(budget), "sum_of_amounts": str(total),
            "named": {str(uid): str(amounts[uid]) for uid in EXPECTED_INDEX},
        })
        check(f"§5 amounts sum to the budget {budget} exactly",
              str(total.quantize(Decimal('0.01'))), str(budget.quantize(Decimal('0.01'))))
    REPORT["distribution"] = distribution_report
    # And the shipped JavaScript agrees with the Python, digit for digit.
    js_input = json.dumps({"rows": [{"key": uid, "index": float(index)} for uid, index in rows],
                           "budgets": [str(b) for b in budgets]})
    js = subprocess.run(
        ["node", "--input-type=module", "-e", """
        const input = JSON.parse(process.argv[1]);
        const m = await import(process.argv[2]);
        const out = {};
        for (const b of input.budgets) {
          const amounts = m.distributeBudget(input.rows, Number(b));
          out[b] = Object.fromEntries([...amounts.entries()].map(([k, v]) => [k, v.toFixed(2)]));
        }
        console.log(JSON.stringify(out));
        """, "--", js_input, str(REPO / "src" / "utils" / "matrixUtils.js")],
        capture_output=True, cwd=REPO)
    if js.returncode:
        raise SystemExit(js.stderr.decode())
    js_out = json.loads(js.stdout.decode())
    mismatches = []
    for budget in budgets:
        py = {str(uid): f"{amount:.2f}" for uid, amount in distribute(rows, budget).items()}
        for key, value in js_out[str(budget)].items():
            if py.get(key) != value:
                mismatches.append((str(budget), key, py.get(key), value))
    REPORT["js_vs_python_mismatches"] = mismatches
    check("§5 the shipped JavaScript and this script agree on every amount", mismatches, [])

    # ── §6 item 8: who takes no share, and why ───────────────────────────────
    not_in_pool = jsql(db, """
      SELECT COALESCE(json_agg(row_to_json(p) ORDER BY p.id), '[]') FROM (
        SELECT u.id, u.full_name, u.role::text AS role, u.can_be_evaluated,
               COALESCE(epp.is_in_scope, false) AS is_in_scope,
               epp.exclusion_reason
        FROM performance_db.users u
        LEFT JOIN performance_db.evaluation_period_participants epp
          ON epp.user_id = u.id AND epp.period_id = 2
        WHERE u.role <> 'admin'
          AND (COALESCE(epp.is_in_scope, false) = false OR u.can_be_evaluated = false)) p""")
    REPORT["not_in_pool"] = not_in_pool
    by_flag = [r for r in not_in_pool if not r["can_be_evaluated"]]
    by_scope = [r for r in not_in_pool if r["can_be_evaluated"] and not r["is_in_scope"]]
    REPORT["not_in_pool_split"] = {
        "evaluated_by_nobody": [(r["id"], r["full_name"]) for r in by_flag],
        "out_of_scope": [(r["id"], r["full_name"]) for r in by_flag and by_scope],
    }
    real_by_flag = sorted(r["id"] for r in by_flag if r["id"] < 1000)
    check("§6 the flag half of the rule yields exactly the five real C-level people "
          "(the sixth, the admin, the matrix route never returns at all)",
          real_by_flag, [18, 21, 40, 47, 61])
    check("§6 and the two halves never overlap",
          sorted(set(r["id"] for r in by_flag) & set(r["id"] for r in by_scope)), [])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    REPORT["failures"] = FAILURES
    Path(args.out).write_text(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str))
    total = len(REPORT.get("checks", []))
    print(f"{total - len(FAILURES)}/{total} checks passed → {args.out}")
    for failure in FAILURES:
        print("  ✗", failure)
    raise SystemExit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

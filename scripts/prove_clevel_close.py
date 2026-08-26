#!/usr/bin/env python3
"""CLEVEL_AVERAGING — the money claim, control against treatment, twice.

D-0826-1 changes ONE thing on a money path: the `c_level_direct` channel is now
the MEAN across every C-level evaluator of a cell, with the number of evaluators
beside it, instead of whichever row was touched last.

That claim needs two rounds, because it has two halves that a single comparison
cannot separate:

  ROUND 1 — one C-level evaluator on the subject.
            Control (workflow surface at HEAD) and treatment (working tree)
            close the same data. NOTHING may move. This is the no-regression
            half, and it is the half that would silently cost money if the
            averaging changed a value where there is nothing to average.

  ROUND 2 — a SECOND C-level evaluator on the same subject, same criteria,
            different scores. The two databases are identical again, and now
            the two closes must DISAGREE, in exactly one person's row, by
            exactly the hand-computed amount.

Between the rounds each stand is reset the same way: the frozen results are
deleted, period 2 is put back to `active`, and the one extra evaluation is
inserted identically on both sides. So round 1 and round 2 differ by a single
evaluation and by nothing else — which is what makes the second round's diff
attributable.

Every number the script asserts is written here as a constant with its working,
derived from the live coefficient snapshot, and is compared against a SECOND,
independent recomputation from the raw database rows.
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
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []
REPORT: dict[str, Any] = {}
MONEY_COLUMNS = ["is_in_scope", "has_data", "rating_manager", "rating_upward",
                 "rating_c_level_direct", "rating_self", "final_rating", "bonus_index"]

SUBJECT = 1605          # MY Stayer B — grade S1 (0.60), project participant
CLEVEL_ONE = 1606       # already scores criterion 1 = 8, criterion 10 = 7
CLEVEL_TWO = 1616       # added in round 2: criterion 1 = 4, criterion 10 = 9
ADMIN = 1601

# ── The hand figures, with their working ───────────────────────────────────
#
# 1605's applicable criteria are [1, 3, 4, 8, 10, 12, 13, 14] (project
# participant, no direct reports so criterion 2 is not applicable). Weights and
# level curves are the live values photographed in
# docs/coefficients/H1-2026_coefficients_20260826T044844Z.md.
#
#   crit  weight  final score      level coef   contribution
#    3     3.00   (9+5+4)/3 = 6.0     1.10        19.80
#    4     1.50    8                  1.50        18.00
#    8     1.40    8                  1.60        17.92
#   12     1.00    7                  1.30         9.10
#   13     1.80    9                  3.80        61.56
#   14     1.50    8                  3.00        36.00
#                                          fixed  162.38
#
# Criterion 1 (weight 5.00) and criterion 10 (weight 1.60) are the C-level
# channel, and they are the only thing that moves:
#
#   round 1, both sides       crit 1 = 8 → 8 × 2.80 × 5.00 = 112.00
#                             crit10 = 7 → 7 × 1.50 × 1.60 =  16.80   Σ = 291.18
#   round 2, OLD code         crit 1 = 4 → 4 × 0.70 × 5.00 =  14.00
#     (latest row wins,       crit10 = 9 → 9 × 2.20 × 1.60 =  31.68   Σ = 208.06
#      which is 1616's)
#   round 2, NEW code         crit 1 = 6 → 6 × 1.20 × 5.00 =  36.00
#     (mean of 8 and 4,       crit10 = 8 → 8 × 1.80 × 1.60 =  23.04   Σ = 221.42
#      and of 7 and 9)
#
# index = Σ × grade coefficient (S1 = 0.60):
FIXED_PART = 19.80 + 18.00 + 17.92 + 9.10 + 61.56 + 36.00     # 162.38
HAND = {
    "round1_sum":        FIXED_PART + 112.00 + 16.80,          # 291.18
    "round1_index":     (FIXED_PART + 112.00 + 16.80) * 0.60,  # 174.708
    "round2_old_sum":    FIXED_PART + 14.00 + 31.68,           # 208.06
    "round2_old_index": (FIXED_PART + 14.00 + 31.68) * 0.60,   # 124.836
    "round2_new_sum":    FIXED_PART + 36.00 + 23.04,           # 221.42
    "round2_new_index": (FIXED_PART + 36.00 + 23.04) * 0.60,   # 132.852
}
# final_rating is the plain mean of the eight cell values, unweighted:
#   round 1        [8, 6.0, 8, 8, 7, 7, 9, 8] → 61.0 / 8 = 7.625
#   round 2 OLD    [4, 6.0, 8, 8, 9, 7, 9, 8] → 59.0 / 8 = 7.375
#   round 2 NEW    [6, 6.0, 8, 8, 8, 7, 9, 8] → 60.0 / 8 = 7.500
HAND_RATING = {"round1": 7.625, "round2_old": 7.375, "round2_new": 7.500}


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


def token_for(db: str, secret: str, actor: int, tag: str) -> str:
    jti = str(uuid.uuid5(uuid.NAMESPACE_URL, f"epe-clevel/{db}/{actor}/{tag}"))
    version = int(sql(db, f"SELECT token_version FROM performance_db.users WHERE id = {actor}"))
    sql(db, f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{jti}', {actor}, {version}, now(), now() + interval '1 hour')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({"sub": str(actor), "iss": "epe", "aud": "epe-api",
                                 "iat": now, "exp": now + 3600, "jti": jti}).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def call(port: int, path: str, token: str, payload: dict | None = None,
         method: str = "GET") -> tuple[int, Any]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhook/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method=method)
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


RESULTS_SQL = """
  SELECT COALESCE(json_agg(row_to_json(r) ORDER BY r.user_id), '[]') FROM (
    SELECT pr.user_id, pr.is_in_scope, pr.has_data,
           pr.rating_manager::text AS rating_manager,
           pr.rating_upward::text AS rating_upward,
           pr.rating_c_level_direct::text AS rating_c_level_direct,
           pr.rating_self::text AS rating_self,
           pr.final_rating::text AS final_rating,
           pr.bonus_index::text AS bonus_index
    FROM performance_db.period_results pr
    WHERE pr.period_id = 2) r"""

FINGERPRINT_SQL = (
    "SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (SELECT concat_ws(':', e.id, e.subject_id,"
    " e.evaluator_id, e.period_id, e.calculated_score, e.evaluation_source,"
    " e.is_self_evaluation, s.criteria_id, s.score_value) AS t"
    " FROM performance_db.evaluations e"
    " LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) x")

# The second C-level evaluation, applied identically to both stands. `now()`
# is strictly later than the seeded row's, so the OLD reader's choice is
# deterministic and the report can name which score it picked.
SECOND_EVALUATION_SQL = f"""
BEGIN;
WITH e AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  VALUES ({SUBJECT}, {CLEVEL_TWO}, 2, 6.5000, 'c_level_direct', false, 'completed',
          'stand: SECOND c_level on stayer B', now() + interval '1 minute')
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT e.id, v.c, v.s, NULL FROM e, (VALUES (1,4),(10,9)) AS v(c,s);
COMMIT;
"""

# Reset between rounds. Stand-only: it undoes the close so the same route can
# be exercised again on the same database. Live has no such path — close is
# irreversible and recovery is a restore (HANDOVER §3).
REOPEN_SQL = """
BEGIN;
DELETE FROM performance_db.period_results WHERE period_id = 2;
UPDATE performance_db.evaluation_periods
SET status = 'active', is_active = true WHERE id = 2;
COMMIT;
"""


def matrix_cells(port: int, token: str, subject: int) -> dict[str, Any]:
    """The two c_level_only cells of one person, as the screen receives them."""
    status, body = call(port, "api/admin/evaluations-matrix", token)
    if status != 200:
        return {"http_status": status, "body": body}
    people = (body or {}).get("data") or []
    row = next((p for p in people if int(p["id"]) == subject), None)
    if row is None:
        return {"http_status": status, "found": False}
    cells = {}
    for crit in row.get("criteria") or []:
        if crit.get("c_level_only"):
            cells[str(crit["criteria_id"])] = {
                "c_level_score": crit.get("c_level_score"),
                "c_level_count": crit.get("c_level_count", "ABSENT"),
            }
    return {"http_status": status, "cells": cells}


def frozen(db: str) -> dict[int, dict]:
    return {int(r["user_id"]): r for r in jsql(db, RESULTS_SQL)}


def diff(rows_a: dict[int, dict], rows_b: dict[int, dict]) -> list[dict]:
    out = []
    for uid in sorted(set(rows_a) & set(rows_b)):
        cells = {c: [rows_a[uid][c], rows_b[uid][c]]
                 for c in MONEY_COLUMNS if rows_a[uid][c] != rows_b[uid][c]}
        if cells:
            out.append({"user_id": uid, "cells": cells})
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    base = REPO / "backups" / "2026-08-26-clevel-averaging"
    parser.add_argument("--env", default=str(base / "throwaway_env.json"))
    parser.add_argument("--out", default=str(base / "clevel_close_proof.json"))
    args = parser.parse_args()
    env = json.loads(Path(args.env).read_text())
    ctl_db, trt_db = env["database_control"], env["database_treatment"]
    port_old, port_new = env["port_old"], env["port_new"]
    secret = env["jwt_secret"]
    REPORT["hand_figures"] = HAND
    REPORT["stand"] = {"control_db": ctl_db, "treatment_db": trt_db}

    # ── ROUND 1 — one C-level evaluator ────────────────────────────────────
    fp_ctl, fp_trt = sql(ctl_db, FINGERPRINT_SQL), sql(trt_db, FINGERPRINT_SQL)
    REPORT["round1"] = {"fingerprint": {"control": fp_ctl, "treatment": fp_trt}}
    check("round 1: the two stands start byte-identical", fp_ctl, fp_trt)
    if FAILURES:
        raise SystemExit("stands diverged before round 1; refusing to compare")

    check("round 1: exactly one c_level_direct evaluation on the subject",
          int(sql(ctl_db, f"SELECT count(*) FROM performance_db.evaluations "
                          f"WHERE subject_id = {SUBJECT} AND period_id = 2 "
                          f"AND evaluation_source = 'c_level_direct'")), 1)

    tok_old = token_for(ctl_db, secret, ADMIN, "r1-old")
    tok_new = token_for(trt_db, secret, ADMIN, "r1-new")
    REPORT["round1"]["matrix_control"] = matrix_cells(port_old, tok_old, SUBJECT)
    REPORT["round1"]["matrix_treatment"] = matrix_cells(port_new, tok_new, SUBJECT)
    check("round 1: the payload's C-level cells are the same value on both sides",
          {k: v["c_level_score"] for k, v in REPORT["round1"]["matrix_treatment"]["cells"].items()},
          {k: v["c_level_score"] for k, v in REPORT["round1"]["matrix_control"]["cells"].items()})
    check("round 1: the new payload carries a count of 1 on both C-level cells",
          {k: v["c_level_count"] for k, v in REPORT["round1"]["matrix_treatment"]["cells"].items()},
          {"1": 1, "10": 1})
    check("round 1: the old payload carries no count field at all",
          sorted({v["c_level_count"] for v in REPORT["round1"]["matrix_control"]["cells"].values()}),
          ["ABSENT"])

    s_ctl, b_ctl = call(port_old, "api/periods/close", tok_old, {"period_id": 2}, "POST")
    s_trt, b_trt = call(port_new, "api/periods/close", tok_new, {"period_id": 2}, "POST")
    REPORT["round1"]["close"] = {"control": [s_ctl, b_ctl], "treatment": [s_trt, b_trt]}
    check("round 1: both closes answer 200", [s_ctl, s_trt], [200, 200])

    r1_ctl, r1_trt = frozen(ctl_db), frozen(trt_db)
    REPORT["round1"]["row_counts"] = {"control": len(r1_ctl), "treatment": len(r1_trt)}
    check("round 1: both froze the same rows", sorted(set(r1_ctl) ^ set(r1_trt)), [])
    r1_moved = diff(r1_ctl, r1_trt)
    REPORT["round1"]["moved"] = r1_moved
    REPORT["round1"]["cells_compared"] = len(r1_ctl) * len(MONEY_COLUMNS)
    check("round 1: NOT ONE frozen money cell moved — one evaluator is a no-op", r1_moved, [])
    check("round 1: the subject's index is the hand figure on both sides",
          [round(float(r1_ctl[SUBJECT]["bonus_index"]), 4),
           round(float(r1_trt[SUBJECT]["bonus_index"]), 4)],
          [round(HAND["round1_index"], 4), round(HAND["round1_index"], 4)])
    check("round 1: the subject's rating is the hand figure",
          round(float(r1_trt[SUBJECT]["final_rating"]), 4), HAND_RATING["round1"])
    pool1_ctl = sum(float(r["bonus_index"]) for r in r1_ctl.values() if r["bonus_index"])
    pool1_trt = sum(float(r["bonus_index"]) for r in r1_trt.values() if r["bonus_index"])
    REPORT["round1"]["pool"] = {"control": pool1_ctl, "treatment": pool1_trt}
    check("round 1: the pool is identical to the last digit", pool1_ctl, pool1_trt)

    # ── between the rounds ─────────────────────────────────────────────────
    for db in (ctl_db, trt_db):
        sql(db, REOPEN_SQL)
        sql(db, SECOND_EVALUATION_SQL)
    fp_ctl, fp_trt = sql(ctl_db, FINGERPRINT_SQL), sql(trt_db, FINGERPRINT_SQL)
    REPORT["round2"] = {"fingerprint": {"control": fp_ctl, "treatment": fp_trt}}
    check("round 2: the two stands are byte-identical again", fp_ctl, fp_trt)
    if FAILURES:
        raise SystemExit("stands diverged before round 2; refusing to compare")

    # Item 1's claim, measured rather than argued: BOTH rows are in the table.
    rows = jsql(ctl_db, f"""
      SELECT COALESCE(json_agg(row_to_json(x) ORDER BY x.evaluator_id), '[]') FROM (
        SELECT e.evaluator_id, es.criteria_id, es.score_value, e.updated_at::text
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON es.evaluation_id = e.id
        WHERE e.subject_id = {SUBJECT} AND e.period_id = 2
          AND e.evaluation_source = 'c_level_direct') x""")
    REPORT["round2"]["source_rows"] = rows
    check("round 2: both C-level evaluations survive in the database, four score rows",
          sorted((r["evaluator_id"], r["criteria_id"], r["score_value"]) for r in rows),
          [(CLEVEL_ONE, 1, 8), (CLEVEL_ONE, 10, 7), (CLEVEL_TWO, 1, 4), (CLEVEL_TWO, 10, 9)])
    check("round 2: two distinct evaluation rows, not one overwritten",
          int(sql(ctl_db, f"SELECT count(*) FROM performance_db.evaluations "
                          f"WHERE subject_id = {SUBJECT} AND period_id = 2 "
                          f"AND evaluation_source = 'c_level_direct'")), 2)

    tok_old = token_for(ctl_db, secret, ADMIN, "r2-old")
    tok_new = token_for(trt_db, secret, ADMIN, "r2-new")
    m_old = matrix_cells(port_old, tok_old, SUBJECT)
    m_new = matrix_cells(port_new, tok_new, SUBJECT)
    REPORT["round2"]["matrix_control"] = m_old
    REPORT["round2"]["matrix_treatment"] = m_new
    check("round 2: the OLD payload shows the LAST WRITER's scores — 4 and 9",
          {k: v["c_level_score"] for k, v in m_old["cells"].items()}, {"1": 4, "10": 9})
    check("round 2: the NEW payload shows the MEANS — 6 and 8",
          {k: float(v["c_level_score"]) for k, v in m_new["cells"].items()}, {"1": 6.0, "10": 8.0})
    check("round 2: and the count travels with them",
          {k: v["c_level_count"] for k, v in m_new["cells"].items()}, {"1": 2, "10": 2})

    s_ctl, b_ctl = call(port_old, "api/periods/close", tok_old, {"period_id": 2}, "POST")
    s_trt, b_trt = call(port_new, "api/periods/close", tok_new, {"period_id": 2}, "POST")
    REPORT["round2"]["close"] = {"control": [s_ctl, b_ctl], "treatment": [s_trt, b_trt]}
    check("round 2: both closes answer 200", [s_ctl, s_trt], [200, 200])

    r2_ctl, r2_trt = frozen(ctl_db), frozen(trt_db)
    check("round 2: both froze the same rows", sorted(set(r2_ctl) ^ set(r2_trt)), [])
    r2_moved = diff(r2_ctl, r2_trt)
    REPORT["round2"]["moved"] = r2_moved
    REPORT["round2"]["cells_compared"] = len(r2_ctl) * len(MONEY_COLUMNS)
    check("round 2: exactly ONE person's frozen row differs, and it is the subject",
          [m["user_id"] for m in r2_moved], [SUBJECT])
    check("round 2: and only the two computed money columns moved — the archival "
          "per-source ratings were already averages and are identical",
          sorted(r2_moved[0]["cells"]) if r2_moved else [],
          ["bonus_index", "final_rating"])

    check("round 2: the OLD close froze the last writer's index",
          round(float(r2_ctl[SUBJECT]["bonus_index"]), 4), round(HAND["round2_old_index"], 4))
    check("round 2: the NEW close froze the AVERAGED index — the hand figure",
          round(float(r2_trt[SUBJECT]["bonus_index"]), 4), round(HAND["round2_new_index"], 4))
    check("round 2: the OLD close froze the last writer's rating",
          round(float(r2_ctl[SUBJECT]["final_rating"]), 4), HAND_RATING["round2_old"])
    check("round 2: the NEW close froze the averaged rating",
          round(float(r2_trt[SUBJECT]["final_rating"]), 4), HAND_RATING["round2_new"])
    check("round 2: rating_c_level_direct — the archival per-source column — already "
          "averaged before this change and agrees on both sides",
          [r2_ctl[SUBJECT]["rating_c_level_direct"], r2_trt[SUBJECT]["rating_c_level_direct"]],
          ["7.00", "7.00"])

    everyone_else = sorted(set(r2_ctl) - {SUBJECT})
    same = all(all(r2_ctl[u][c] == r2_trt[u][c] for c in MONEY_COLUMNS) for u in everyone_else)
    REPORT["round2"]["others_identical"] = {"people": len(everyone_else), "identical": same}
    check("round 2: every other person's frozen result is byte-identical", same, True)

    # The third comparison the brief names: the same code, two databases that
    # differ only by the second C-level evaluation.
    r1_vs_r2 = diff(r1_trt, r2_trt)
    REPORT["second_evaluation_effect"] = r1_vs_r2
    check("adding a second C-level evaluation moves exactly one person under the new code",
          [m["user_id"] for m in r1_vs_r2], [SUBJECT])
    REPORT["subject_journey"] = {
        "round1_one_evaluator": {k: r1_trt[SUBJECT][k] for k in MONEY_COLUMNS},
        "round2_old_code": {k: r2_ctl[SUBJECT][k] for k in MONEY_COLUMNS},
        "round2_new_code": {k: r2_trt[SUBJECT][k] for k in MONEY_COLUMNS},
    }
    pool2_ctl = sum(float(r["bonus_index"]) for r in r2_ctl.values() if r["bonus_index"])
    pool2_trt = sum(float(r["bonus_index"]) for r in r2_trt.values() if r["bonus_index"])
    REPORT["round2"]["pool"] = {"control": pool2_ctl, "treatment": pool2_trt}
    check("round 2: the pool differs by exactly the subject's difference",
          round(pool2_trt - pool2_ctl, 4),
          round(HAND["round2_new_index"] - HAND["round2_old_index"], 4))

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

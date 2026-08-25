#!/usr/bin/env python3
"""PRELAUNCH_BATCH_NIGHT — the money claim, control against treatment.

The only change this session makes to a MONEY path is the second applicability
dimension: `managers_only` criteria are now emitted only for a person who has
direct reports, in the admin matrix AND in the close dataset, in lockstep.

That claim is proven the only way it can be: two copies of one dump, seeded
identically, each closed through its OWN real `POST /api/periods/close` — the
control stand running the workflow surface as committed at HEAD, the treatment
stand running the working tree — and the two `period_results` sets compared cell
by cell.

A row that moves is not automatically a failure; a row that moves for a person
who HAS direct reports would be. The script prints every difference and asserts
the shape of it.
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


def close_period(port: int, db: str, secret: str, actor: int, period_id: int) -> tuple[int, Any]:
    jti = str(uuid.uuid5(uuid.NAMESPACE_URL, f"epe-night-close/{port}/{actor}"))
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
    token = f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhook/api/periods/close",
        data=json.dumps({"period_id": period_id}).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
        method="POST")
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
           pr.bonus_index::text AS bonus_index,
           u.has_subordinates
    FROM performance_db.period_results pr
    JOIN performance_db.users u ON u.id = pr.user_id
    WHERE pr.period_id = 2) r"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "throwaway_env.json"))
    parser.add_argument("--out", default=str(REPO / "backups" / "2026-08-25-prelaunch-night"
                                             / "night_close_proof.json"))
    args = parser.parse_args()
    env = json.loads(Path(args.env).read_text())
    ctl_db, trt_db = env["database_control"], env["database_treatment"]
    secret = env["jwt_secret"]

    # Both stands must still be byte-identical in their evaluation data going in.
    fp = ("SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (SELECT concat_ws(':', e.id, e.subject_id,"
          " e.evaluator_id, e.period_id, e.calculated_score, e.evaluation_source,"
          " e.is_self_evaluation, s.criteria_id, s.score_value) AS t"
          " FROM performance_db.evaluations e"
          " LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) x")
    fp_ctl, fp_trt = sql(ctl_db, fp), sql(trt_db, fp)
    REPORT["fingerprint_before"] = {"control": fp_ctl, "treatment": fp_trt}
    check("the two stands are still identical going into the close", fp_ctl, fp_trt)
    if FAILURES:
        raise SystemExit("stands diverged before the close; refusing to compare")

    status_ctl, body_ctl = close_period(env["port_old"], ctl_db, secret, 1601, 2)
    status_trt, body_trt = close_period(env["port_new"], trt_db, secret, 1601, 2)
    REPORT["close_control"] = {"status": status_ctl, "body": body_ctl}
    REPORT["close_treatment"] = {"status": status_trt, "body": body_trt}
    check("both closes answer 200", [status_ctl, status_trt], [200, 200])

    rows_ctl = {int(r["user_id"]): r for r in jsql(ctl_db, RESULTS_SQL)}
    rows_trt = {int(r["user_id"]): r for r in jsql(trt_db, RESULTS_SQL)}
    REPORT["row_counts"] = {"control": len(rows_ctl), "treatment": len(rows_trt)}
    check("both closes froze the same number of rows", len(rows_ctl), len(rows_trt))
    check("neither close produced a row the other did not",
          sorted(set(rows_ctl) ^ set(rows_trt)), [])

    moved = []
    for uid in sorted(set(rows_ctl) & set(rows_trt)):
        cells = {c: [rows_ctl[uid][c], rows_trt[uid][c]]
                 for c in MONEY_COLUMNS if rows_ctl[uid][c] != rows_trt[uid][c]}
        if cells:
            moved.append({"user_id": uid,
                          "has_subordinates": rows_trt[uid]["has_subordinates"],
                          "cells": cells})
    REPORT["moved_rows"] = moved
    REPORT["cells_compared"] = len(rows_ctl) * len(MONEY_COLUMNS)

    # The change can only ever affect a person WITHOUT direct reports, and only
    # if criterion 2 had somehow been scored for them. Nobody in the fixture set
    # is in that state, so the correct answer is that nothing moved at all.
    check("not one frozen money cell moved between the two closes", moved, [])
    check("and the pool is identical to the last digit",
          sum(float(r["bonus_index"]) for r in rows_ctl.values() if r["bonus_index"]),
          sum(float(r["bonus_index"]) for r in rows_trt.values() if r["bonus_index"]))

    # The frozen numbers must also be the ones the screen showed.
    frozen = {uid: rows_trt[uid]["bonus_index"] for uid in (1602, 1603, 1604, 1605, 1612)}
    REPORT["frozen_indices"] = frozen
    check("the frozen index equals the hand figure, for every seeded person",
          {k: (None if v is None else round(float(v), 3)) for k, v in frozen.items()},
          {1602: 170.83, 1603: 108.324, 1604: 13.74, 1605: 174.708, 1612: 80.892})

    # The out-of-scope person freezes as a record with no number, by the table's
    # own CHECKs — the difference BUG-067 is about.
    for uid, label in ((1614, "excluded by admin"), (1607, "hired after the period end")):
        row = rows_trt.get(uid)
        REPORT.setdefault("out_of_scope_rows", {})[str(uid)] = row
        check(f"{label} freezes as out of scope with no data and no money",
              [row["is_in_scope"], row["has_data"], row["final_rating"], row["bonus_index"]],
              [False, False, None, None])
    check("the person who never had a participants row has no frozen row at all (BUG-067)",
          1610 in rows_trt, False)

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

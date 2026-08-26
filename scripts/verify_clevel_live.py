#!/usr/bin/env python3
"""CLEVEL_AVERAGING — verify LIVE after the deploy. Read-only.

Writes exactly one row to `performance_db.auth_sessions` (a probe session for
the owner's admin account) and deletes it in a `finally`. Nothing else on live
is written by this script: no user row, no period, no catalogue, no coefficient,
no scope change, and no route that could press the second gate is called.

The two routes are read through Caddy on the real origin, so what is checked is
what a browser would get.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

def _tls_context() -> ssl.SSLContext:
    # The delivery laptop's Python does not use the system trust store; every
    # earlier verifier hit the same wall (docs/*_live.py).
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()
HOST = "root@92.51.45.147"
ORIGIN = "https://epe.sedamedical.com"
REPO = Path(__file__).resolve().parent.parent
ADMIN = 2
FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def check(name: str, actual: Any, expected: Any) -> None:
    ok = actual == expected
    REPORT.setdefault("checks", []).append(
        {"name": name, "expected": expected, "actual": actual, "ok": ok})
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def get(path: str, token: str | None) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{ORIGIN}/webhook/{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=120, context=TLS) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPO / "backups" / "2026-08-26-clevel-averaging"
                                             / "clevel_live_verify.json"))
    args = parser.parse_args()
    secret = subprocess.run(
        ["security", "find-generic-password", "-s", "EPE JWT signing secret 92.51.45.147", "-w"],
        capture_output=True, text=True, check=True).stdout.strip()

    REPORT["read_at_utc"] = sql("epe_2026",
        "SELECT to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')")

    # ── invariants, no session needed ──────────────────────────────────────
    counts = dict(line.split("|") for line in sql("epe_2026", """
      SELECT 'users', count(*)::text FROM performance_db.users
      UNION ALL SELECT 'terminated', count(*)::text FROM performance_db.users
        WHERE terminated_at IS NOT NULL
      UNION ALL SELECT 'in_scope_h1', count(*)::text
        FROM performance_db.evaluation_period_participants WHERE period_id = 2 AND is_in_scope
      UNION ALL SELECT 'evaluations', count(*)::text FROM performance_db.evaluations
      UNION ALL SELECT 'evaluation_scores', count(*)::text FROM performance_db.evaluation_scores
      UNION ALL SELECT 'score_corrections', count(*)::text FROM performance_db.score_corrections
      UNION ALL SELECT 'period_results', count(*)::text FROM performance_db.period_results
      UNION ALL SELECT 'started', count(*)::text FROM performance_db.evaluation_periods
        WHERE evaluation_started_at IS NOT NULL
      UNION ALL SELECT 'h1_state', status || '/' || is_active
        FROM performance_db.evaluation_periods WHERE id = 2
      UNION ALL SELECT 'extensions', string_agg(extname, ',' ORDER BY extname) FROM pg_extension
    """).split("\n"))
    REPORT["counts"] = counts
    check("89 users", counts["users"], "89")
    check("3 terminated", counts["terminated"], "3")
    check("80 in H1 scope", counts["in_scope_h1"], "80")
    check("the four data tables are still 0/0/0/0",
          [counts["evaluations"], counts["evaluation_scores"],
           counts["score_corrections"], counts["period_results"]], ["0", "0", "0", "0"])
    check("the second gate is unpressed on all three periods", counts["started"], "0")
    check("H1 is active", counts["h1_state"], "active/true")
    check("no extension was created", counts["extensions"], "plpgsql")

    # ── the two workflow definitions, read from workflow_entity ────────────
    defs = dict(line.split("|", 1) for line in sql("postgres", """
      SELECT name, "updatedAt" || '|' || active || '|' || jsonb_array_length(nodes::jsonb)
      FROM public.workflow_entity
      WHERE id IN ('M9ljMDdO1mIl8m1h', 'yQNNr0i4UBFNVgMv', 'L0Zr7nVa8O5YWXd3')
    """).split("\n"))
    REPORT["definitions"] = defs
    check("EPE: Auth Guard still carries its frozen updatedAt and is still inactive",
          defs["EPE: Auth Guard"], "2026-08-18 16:34:30.674+00|false|4")
    check("Manage Periods is active with 70 nodes",
          defs["API: Manage Periods"].split("|")[1:], ["true", "70"])
    check("evaluations-matrix is active with 9 nodes",
          defs["API: evaluations-matrix"].split("|")[1:], ["true", "9"])

    cte = sql("postgres", """
      SELECT count(*)::text FROM public.workflow_entity
      WHERE id IN ('M9ljMDdO1mIl8m1h', 'yQNNr0i4UBFNVgMv')
        AND nodes::text LIKE '%c_level_direct_scores AS (%'""")
    check("both live definitions carry the c_level_direct_scores CTE", cte, "2")
    stale = sql("postgres", """
      SELECT count(*)::text FROM public.workflow_entity
      WHERE id IN ('M9ljMDdO1mIl8m1h', 'yQNNr0i4UBFNVgMv')
        AND nodes::text LIKE '%avg_c_level_score%'""")
    check("and both compute the average", stale, "2")

    counts2 = dict(line.split("|") for line in sql("postgres", """
      SELECT 'total', count(*)::text FROM public.workflow_entity
      UNION ALL SELECT 'active', count(*)::text FROM public.workflow_entity WHERE active
      UNION ALL SELECT 'archived', count(*)::text FROM public.workflow_entity WHERE "isArchived"
      UNION ALL SELECT 'webhooks', count(*)::text FROM public.webhook_entity
    """).split("\n"))
    REPORT["workflow_counts"] = counts2
    check("60 workflows / 35 active / 22 archived / 48 webhooks",
          [counts2["total"], counts2["active"], counts2["archived"], counts2["webhooks"]],
          ["60", "35", "22", "48"])

    # ── the money inputs did not move ──────────────────────────────────────
    fp = dict(line.split("|") for line in sql("epe_2026", """
      SELECT 'criteria', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
        SELECT concat_ws('|', id, title, target_audience, weight, c_level_only,
                         selfassesment, for_manager, is_active) AS t
        FROM performance_db.criteria WHERE is_active = true) x)
      UNION ALL SELECT 'score_coefficients', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
        SELECT concat_ws('|', criteria_id, score_level, coefficient) AS t
        FROM performance_db.score_coefficients) x)
      UNION ALL SELECT 'grades', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
        SELECT concat_ws('|', id, code, coefficient, coalesce(description,'')) AS t
        FROM performance_db.grades) x)
    """).split("\n"))
    REPORT["coefficient_fingerprints"] = fp
    check("catalogue, level coefficients and grades are md5-identical to the snapshot",
          [fp["criteria"], fp["score_coefficients"], fp["grades"]],
          ["fc618757f6aa2c27db5bce7613fc28c7",
           "317e09e8326edde500bfcde2bad81e78",
           "946b30a5ea8b8594321ebb5fc645bd32"])

    # ── the routes, through Caddy ──────────────────────────────────────────
    check("the matrix refuses an unauthenticated read", get("api/admin/evaluations-matrix", None)[0], 401)

    jti = str(uuid.uuid5(uuid.NAMESPACE_URL, "epe-clevel-live-verify"))
    version = int(sql("epe_2026", f"SELECT token_version FROM performance_db.users WHERE id = {ADMIN}"))
    try:
        sql("epe_2026", f"""
          INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
          VALUES ('{jti}', {ADMIN}, {version}, now(), now() + interval '10 minutes')
          ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '10 minutes'""")
        header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        now = int(time.time())
        payload = b64url(json.dumps({"sub": str(ADMIN), "iss": "epe", "aud": "epe-api",
                                     "iat": now, "exp": now + 600, "jti": jti}).encode())
        signing = f"{header}.{payload}".encode()
        token = (f"{header}.{payload}."
                 f"{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}")

        status, body = get("api/admin/evaluations-matrix", token)
        people = (body or {}).get("data") or []
        REPORT["matrix"] = {
            "status": status,
            "people": len(people),
            "period": (body or {}).get("period", {}).get("name"),
        }
        check("the live matrix answers 200", status, 200)
        check("for the active H1 period", REPORT["matrix"]["period"], "H1-2026")

        # Every c_level_only cell must now carry the count field, and with zero
        # evaluations on live every one of them must read null / 0.
        cells = [c for p in people for c in (p.get("criteria") or []) if c.get("c_level_only")]
        REPORT["c_level_cells"] = {
            "count": len(cells),
            "with_count_field": sum(1 for c in cells if "c_level_count" in c),
            "distinct_scores": sorted({str(c.get("c_level_score")) for c in cells}),
            "distinct_counts": sorted({str(c.get("c_level_count")) for c in cells}),
        }
        check("every c_level_only cell carries c_level_count",
              REPORT["c_level_cells"]["with_count_field"], len(cells))
        # With zero evaluations the grouped CTE has no row for any cell, so the
        # correlated sub-select yields NULL for both — the same shape
        # `subordinate_count` has always had. Never a score of zero.
        check("and with no evaluations on live every one reads null score / null count",
              [REPORT["c_level_cells"]["distinct_scores"],
               REPORT["c_level_cells"]["distinct_counts"]], [["None"], ["None"]])

        status, body = get("api/periods", token)
        REPORT["periods"] = {"status": status, "rows": [
            {k: p.get(k) for k in ("id", "name", "status", "is_active", "evaluation_started")}
            for p in ((body or {}).get("data") or [])]}
        check("GET /api/periods answers 200", status, 200)
        check("and no period is started",
              [p.get("evaluation_started") for p in REPORT["periods"]["rows"]],
              [False, False, False])
    finally:
        sql("epe_2026", f"DELETE FROM performance_db.auth_sessions WHERE jti = '{jti}'")
        REPORT["probe_session_deleted"] = sql(
            "epe_2026", f"SELECT count(*)::text FROM performance_db.auth_sessions WHERE jti = '{jti}'")

    check("the probe session was deleted", REPORT["probe_session_deleted"], "0")

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

#!/usr/bin/env python3
"""LIVE post-deploy probe for EMPLOYEES_PERIOD_META (2026-08-24).

Read-only against live data. The only write is ONE short-lived row in
performance_db.auth_sessions (the guard requires a session before any role can
be exercised); it carries a marked jti, expires in 30 minutes, and is deleted
by this script before it exits. No user's token_version is touched.

Checks, as compared values:
  - GET /api/employees as admin answers 200 and carries the three new keys —
    period_name / period_start_date / period_end_date — all null (H1 is
    draft, so there is no current period)
  - every previously-existing key is still present
  - live campaign state: H1 draft / inactive / not started; the four data
    tables are 0
  - a state fingerprint (criteria weights, coefficients, user classification,
    data-table counts) is identical before and after the probe
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
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
JTI = "0824ee7a-0000-4000-8000-000000000002"
ADMIN_ID = 2

EXPECTED_KEYS = {
    "success", "actor_user_id", "campaign_active", "period_in_preparation",
    "current_period_id", "current_period_status",
    "period_name", "period_start_date", "period_end_date",
    "actor_is_in_scope", "data",
}


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 1800, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def state_fingerprint() -> str:
    return live_sql("""
      SELECT md5(string_agg(c.id || '|' || c.weight, ',' ORDER BY c.id))
             || '/' || (SELECT md5(string_agg(sc.criteria_id || '|' || sc.score_level || '|' || sc.coefficient, ',' ORDER BY sc.criteria_id, sc.score_level)) FROM performance_db.score_coefficients sc)
             || '/' || (SELECT md5(string_agg(u.id || '|' || u.work_category || '|' || u.is_project_participant, ',' ORDER BY u.id)) FROM performance_db.users u)
             || '/' || (SELECT count(*) FROM performance_db.evaluations)
             || '/' || (SELECT count(*) FROM performance_db.evaluation_scores)
             || '/' || (SELECT count(*) FROM performance_db.score_corrections)
             || '/' || (SELECT count(*) FROM performance_db.period_results)
      FROM performance_db.criteria c""")


FAILURES: list[str] = []


def check(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    secret = args.secret_file.read_text().strip()

    fingerprint_before = state_fingerprint()
    sessions_before = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))

    live_sql(f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{JTI}'::uuid, {ADMIN_ID},
              (SELECT token_version FROM performance_db.users WHERE id = {ADMIN_ID}),
              now(), now() + interval '30 minutes')""")

    report: dict[str, Any] = {
        "base_url": args.base_url,
        "state_fingerprint_before": fingerprint_before,
        "auth_sessions_before": sessions_before,
    }
    try:
        token = mint(secret, ADMIN_ID, JTI)
        request = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/api/employees",
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=90, context=_tls_context()) as response:
                status, body = response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            status, body = exc.code, exc.read().decode("utf-8", "replace")

        report["admin_get_employees"] = {"status": status, "body": body}
        check("admin employees 200", status, 200)
        if isinstance(body, dict):
            check("payload keys", sorted(body), sorted(EXPECTED_KEYS))
            for key in ("period_name", "period_start_date", "period_end_date"):
                check(f"{key} null while H1 is draft", body.get(key), None)
            check("campaign_active", body.get("campaign_active"), False)
            check("period_in_preparation", body.get("period_in_preparation"), False)
            check("current_period_id", body.get("current_period_id"), None)
            check("actor_is_in_scope", body.get("actor_is_in_scope"), None)
        else:
            FAILURES.append(f"non-JSON body: {body!r:.200}")
    finally:
        live_sql(f"DELETE FROM performance_db.auth_sessions WHERE jti = '{JTI}'::uuid")

    remaining = int(live_sql(
        f"SELECT count(*) FROM performance_db.auth_sessions WHERE jti = '{JTI}'::uuid"))
    sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
    fingerprint_after = state_fingerprint()

    campaign = live_sql("""
      SELECT status || '|' || is_active || '|' || COALESCE(evaluation_started_at::text, 'null')
      FROM performance_db.evaluation_periods WHERE id = 2""")
    tables = live_sql("""
      SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
             (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
             (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
             (SELECT count(*) FROM performance_db.period_results)""")

    report.update({
        "probe_sessions_remaining": remaining,
        "auth_sessions_after": sessions_after,
        "state_fingerprint_after": fingerprint_after,
        "state_unchanged": fingerprint_after == fingerprint_before,
        "h1_row": campaign,
        "data_tables": tables,
    })
    check("probe session removed", remaining, 0)
    check("auth_sessions back to the pre-probe count", sessions_after, sessions_before)
    check("live state fingerprint unchanged", fingerprint_after, fingerprint_before)
    check("H1 still draft/inactive/not-started", campaign, "draft|false|null")
    check("four data tables still 0", tables, "0/0/0/0")

    report["failures"] = FAILURES
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"report: {args.output}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for failure in FAILURES:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("ALL LIVE CHECKS PASSED")


if __name__ == "__main__":
    main()

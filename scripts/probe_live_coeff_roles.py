#!/usr/bin/env python3
"""LIVE role x route probe for the coefficient-privacy change (2026-08-22).

Read-only against live data. The only writes are six short-lived rows in
performance_db.auth_sessions (a session is required by the guard before any
role can be exercised); they carry a marked jti prefix, expire in 30 minutes,
and are deleted by this script before it exits. No user's token_version is
touched, so nobody is logged out, and no real session row is read or removed.

Every POST in the matrix is deliberately non-mutating:
  - POST /api/score-coefficients with an empty criteria list -> 422 before SQL
  - POST /update-admin-data with empty grades/settings       -> 422 before SQL
  - POST /manage-criteria action=get                         -> read branch
so an admin row proves "reaches the handler", never "wrote to live".
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

# The python.org interpreter ships no system CA bundle; live is HTTPS-only.
def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()
JTI_PREFIX = "0822c0ef"

PROBE_USERS = {
    "admin":            (2,  f"{JTI_PREFIX}-0000-4000-8000-000000000002"),
    "c_level":          (18, f"{JTI_PREFIX}-0000-4000-8000-000000000018"),
    "c_level_readonly": (21, f"{JTI_PREFIX}-0000-4000-8000-000000000021"),
    "hr":               (52, f"{JTI_PREFIX}-0000-4000-8000-000000000052"),
    "manager":          (1,  f"{JTI_PREFIX}-0000-4000-8000-000000000001"),
    "employee":         (3,  f"{JTI_PREFIX}-0000-4000-8000-000000000003"),
}


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


def call(base: str, method: str, path: str, token: str,
         body: dict[str, Any] | None = None) -> tuple[int, Any]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90, context=TLS) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    secret = args.secret_file.read_text().strip()
    base = args.base_url

    fingerprint_before = live_sql("""
      SELECT md5(string_agg(c.id || '|' || c.weight, ',' ORDER BY c.id))
             || '/' || md5(string_agg(sc.criteria_id || '|' || sc.score_level || '|' || sc.coefficient, ',' ORDER BY sc.criteria_id, sc.score_level))
             || '/' || md5(string_agg(g.id || '|' || g.coefficient, ',' ORDER BY g.id))
      FROM performance_db.criteria c,
           performance_db.score_coefficients sc,
           performance_db.grades g""")
    sessions_before = live_sql("SELECT count(*) FROM performance_db.auth_sessions")

    values = ", ".join(
        f"('{jti}'::uuid, {uid}, (SELECT token_version FROM performance_db.users WHERE id = {uid}),"
        f" now(), now() + interval '30 minutes')"
        for uid, jti in PROBE_USERS.values())
    live_sql(f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES {values}""")

    report: dict[str, Any] = {
        "base_url": base,
        "probe_users": {k: v[0] for k, v in PROBE_USERS.items()},
        "coefficient_fingerprint_before": fingerprint_before,
        "auth_sessions_before": int(sessions_before),
    }
    try:
        matrix: dict[str, dict[str, Any]] = {}
        for role, (uid, jti) in PROBE_USERS.items():
            token = mint(secret, uid, jti)
            row: dict[str, Any] = {}

            s, b = call(base, "GET", "api/score-coefficients", token)
            row["GET /api/score-coefficients"] = {
                "status": s, "error": (b or {}).get("error") if isinstance(b, dict) else None,
                "criteria_returned": len((b or {}).get("data") or []) if isinstance(b, dict) else 0}

            s, b = call(base, "POST", "api/score-coefficients", token, {"criteria": []})
            row["POST /api/score-coefficients (empty body)"] = {
                "status": s, "error": (b or {}).get("error") if isinstance(b, dict) else None}

            s, b = call(base, "GET", "api/criteria", token)
            rows = (b or {}).get("data") or [] if isinstance(b, dict) else []
            row["GET /api/criteria"] = {
                "status": s,
                "criteria_returned": len(rows),
                "weight_present_on_any": any("weight" in c for c in rows),
                "level_texts_on_c_level_only": any(
                    "level_1_desc" in c for c in rows
                    if c.get("c_level_only") in (True, "t")),
            }

            s, b = call(base, "POST", "update-admin-data", token, {"grades": [], "settings": []})
            row["POST /update-admin-data (empty body)"] = {
                "status": s, "error": (b or {}).get("error") if isinstance(b, dict) else None}

            s, b = call(base, "POST", "manage-criteria", token, {"action": "get"})
            row["POST /manage-criteria (get)"] = {
                "status": s, "error": (b or {}).get("error") if isinstance(b, dict) else None,
                "campaign_active": (b or {}).get("campaign_active") if isinstance(b, dict) else None,
                "evaluation_started": (b or {}).get("evaluation_started") if isinstance(b, dict) else None}

            s, b = call(base, "GET", "api/employees", token)
            row["GET /api/employees"] = {
                "status": s,
                "campaign_active": (b or {}).get("campaign_active") if isinstance(b, dict) else None,
                "period_in_preparation": (b or {}).get("period_in_preparation") if isinstance(b, dict) else None,
                "current_period_id": (b or {}).get("current_period_id") if isinstance(b, dict) else None,
                "actor_is_in_scope": (b or {}).get("actor_is_in_scope") if isinstance(b, dict) else None}

            s, b = call(base, "POST", "api/periods/start-evaluation", token, {"period_id": 2})
            row["POST /api/periods/start-evaluation (H1, draft)"] = {
                "status": s, "error": (b or {}).get("error") if isinstance(b, dict) else None}

            matrix[role] = row
        report["matrix"] = matrix
    finally:
        deleted = live_sql(f"""
          WITH gone AS (
            DELETE FROM performance_db.auth_sessions
            WHERE jti::text LIKE '{JTI_PREFIX}-%' RETURNING 1
          ) SELECT count(*) FROM gone""")
        report["probe_sessions_deleted"] = int(deleted)
        report["auth_sessions_after"] = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
        report["probe_sessions_remaining"] = int(live_sql(
            f"SELECT count(*) FROM performance_db.auth_sessions WHERE jti::text LIKE '{JTI_PREFIX}-%'"))

    fingerprint_after = live_sql("""
      SELECT md5(string_agg(c.id || '|' || c.weight, ',' ORDER BY c.id))
             || '/' || md5(string_agg(sc.criteria_id || '|' || sc.score_level || '|' || sc.coefficient, ',' ORDER BY sc.criteria_id, sc.score_level))
             || '/' || md5(string_agg(g.id || '|' || g.coefficient, ',' ORDER BY g.id))
      FROM performance_db.criteria c,
           performance_db.score_coefficients sc,
           performance_db.grades g""")
    report["coefficient_fingerprint_after"] = fingerprint_after
    report["coefficients_unchanged"] = fingerprint_after == fingerprint_before
    report["periods_after"] = live_sql("""
      SELECT string_agg(id || '|' || status || '|' || is_active || '|'
             || COALESCE(evaluation_started_at::text, 'not-started'), ' ; ' ORDER BY id)
      FROM performance_db.evaluation_periods""")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

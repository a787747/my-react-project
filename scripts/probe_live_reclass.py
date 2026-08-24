#!/usr/bin/env python3
"""LIVE role x route probe for the reclassification change (2026-08-24).

Read-only against live data. The only writes are six short-lived rows in
performance_db.auth_sessions (a session is required by the guard before any
role can be exercised); they carry a marked jti prefix, expire in 30 minutes,
and are deleted by this script before it exits. No user's token_version is
touched, so nobody is logged out, and no real session row is read or removed.

Every POST is deliberately non-mutating:
  - POST /api/score-coefficients with weight 0 / 0.09  -> 422 before any SQL
    (the acceptance's live weight-floor rejections; fingerprint re-checked)
  - POST submit/update/self-review/save-user/score-correction with an empty
    body -> 422/403 before any SQL
so an admin row proves "reaches the handler", never "wrote to live".

The BUG-043 acceptance rides on GET /api/employees: with no active leaf
period, current_period_id is null for every role — container id 5 nowhere.
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


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()
JTI_PREFIX = "0824ec1a"

PROBE_USERS = {
    "admin":            (2,  f"{JTI_PREFIX}-0000-4000-8000-000000000002"),
    "c_level":          (18, f"{JTI_PREFIX}-0000-4000-8000-000000000018"),
    "c_level_readonly": (21, f"{JTI_PREFIX}-0000-4000-8000-000000000021"),
    "hr":               (52, f"{JTI_PREFIX}-0000-4000-8000-000000000052"),
    "manager":          (1,  f"{JTI_PREFIX}-0000-4000-8000-000000000001"),
    "employee":         (3,  f"{JTI_PREFIX}-0000-4000-8000-000000000003"),
}

ANNUAL_CONTAINER = 5


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


FAILURES: list[str] = []


def check(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    secret = args.secret_file.read_text().strip()
    base = args.base_url

    fingerprint_before = state_fingerprint()
    sessions_before = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))

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
        "state_fingerprint_before": fingerprint_before,
        "auth_sessions_before": sessions_before,
    }
    try:
        matrix: dict[str, dict[str, Any]] = {}
        for role, (uid, jti) in PROBE_USERS.items():
            token = mint(secret, uid, jti)
            row: dict[str, Any] = {}

            # BUG-043: with no active leaf period the answer is "none"
            s, b = call(base, "GET", "api/employees", token)
            row["GET /api/employees"] = {
                "status": s,
                "current_period_id": (b or {}).get("current_period_id") if isinstance(b, dict) else "?",
                "current_period_status": (b or {}).get("current_period_status") if isinstance(b, dict) else "?",
                "campaign_active": (b or {}).get("campaign_active") if isinstance(b, dict) else "?",
                "period_in_preparation": (b or {}).get("period_in_preparation") if isinstance(b, dict) else "?",
                "actor_is_in_scope": (b or {}).get("actor_is_in_scope") if isinstance(b, dict) else "?",
            }
            check(f"{role}: employees 200", s, 200)
            check(f"{role}: BUG-043 current period is none",
                  row["GET /api/employees"]["current_period_id"], None)
            check(f"{role}: container id {ANNUAL_CONTAINER} never current",
                  row["GET /api/employees"]["current_period_id"] == ANNUAL_CONTAINER, False)
            check(f"{role}: scope null with no period",
                  row["GET /api/employees"]["actor_is_in_scope"], None)

            for label, method, path, body_probe in [
                ("GET /api/check-evaluated", "GET", "api/check-evaluated", None),
                ("GET /api/check-self-review", "GET", "api/check-self-review", None),
                ("GET /api/get-my-manager", "GET", "api/get-my-manager", None),
                ("GET /api/admin/evaluations-matrix", "GET", "api/admin/evaluations-matrix", None),
                ("POST /api/submit-evaluation {}", "POST", "api/submit-evaluation", {}),
                ("POST /api/update-evaluation {}", "POST", "api/update-evaluation", {}),
                ("POST /api/self-review-submit {}", "POST", "api/self-review-submit", {}),
                ("POST /admin/save-user {}", "POST", "admin/save-user", {}),
                ("POST /api/admin/score-correction {}", "POST", "api/admin/score-correction", {}),
            ]:
                s, b = call(base, method, path, token, body_probe)
                row[label] = {"status": s,
                              "error": (b or {}).get("error") if isinstance(b, dict) else None}
            matrix[role] = row

        report["role_route_matrix"] = matrix

        expectations = [
            ("admin",            "GET /api/admin/evaluations-matrix", 200, None),
            ("c_level",          "GET /api/admin/evaluations-matrix", 200, None),
            ("c_level_readonly", "GET /api/admin/evaluations-matrix", 200, None),
            ("hr",               "GET /api/admin/evaluations-matrix", 403, "ROLE_FORBIDDEN"),
            ("manager",          "GET /api/admin/evaluations-matrix", 403, "ROLE_FORBIDDEN"),
            ("employee",         "GET /api/admin/evaluations-matrix", 403, "ROLE_FORBIDDEN"),
            ("admin",            "POST /api/submit-evaluation {}", 422, "INVALID_SUBJECT"),
            ("manager",          "POST /api/submit-evaluation {}", 422, "INVALID_SUBJECT"),
            ("c_level_readonly", "POST /api/submit-evaluation {}", 403, "CAPABILITY_FORBIDDEN"),
            # live hr (id 52) carries can_evaluate=true (measured 2026-08-24),
            # so the guard passes and the empty body 422s before any SQL —
            # unlike the stand fixture hr, which has can_evaluate=false.
            ("hr",               "POST /api/submit-evaluation {}", 422, "INVALID_SUBJECT"),
            ("manager",          "POST /api/update-evaluation {}", 422, "INVALID_EVALUATION_ID"),
            ("c_level_readonly", "POST /api/update-evaluation {}", 403, "CAPABILITY_FORBIDDEN"),
            ("employee",         "POST /api/self-review-submit {}", 422, "INVALID_SCORE"),
            ("admin",            "POST /api/self-review-submit {}", 403, "ROLE_FORBIDDEN"),
            ("c_level",          "POST /api/self-review-submit {}", 403, "ROLE_FORBIDDEN"),
            ("admin",            "POST /admin/save-user {}", 422, "INVALID_NAME"),
            ("c_level",          "POST /admin/save-user {}", 403, "ROLE_FORBIDDEN"),
            ("hr",               "POST /admin/save-user {}", 403, "ROLE_FORBIDDEN"),
            ("manager",          "POST /admin/save-user {}", 403, "ROLE_FORBIDDEN"),
            ("employee",         "POST /admin/save-user {}", 403, "ROLE_FORBIDDEN"),
            ("admin",            "POST /api/admin/score-correction {}", 422, "INVALID_BODY"),
            ("c_level_readonly", "POST /api/admin/score-correction {}", 403, "CAPABILITY_FORBIDDEN"),
            ("hr",               "POST /api/admin/score-correction {}", 403, "ROLE_FORBIDDEN"),
            ("employee",         "POST /api/admin/score-correction {}", 403, "ROLE_FORBIDDEN"),
        ]
        for role, label, want_status, want_error in expectations:
            got = matrix[role][label]
            check(f"live role matrix {role} / {label}",
                  (got["status"], got["error"]), (want_status, want_error))

        # ── the weight floor on the LIVE path: 0 and 0.09 are 422 before SQL ──
        admin_token = mint(secret, *PROBE_USERS["admin"])
        crit12 = json.loads(live_sql("""
          SELECT json_build_object('weight', c.weight, 'levels',
            (SELECT json_object_agg(sc.score_level::text, sc.coefficient)
             FROM performance_db.score_coefficients sc WHERE sc.criteria_id = 12))
          FROM performance_db.criteria c WHERE c.id = 12"""))
        levels12 = {str(i): float(crit12["levels"][str(i)]) for i in range(1, 11)}
        floor: dict[str, Any] = {"stored_weight_before": float(crit12["weight"])}
        for value in (0, 0.09):
            s, b = call(base, "POST", "api/score-coefficients", admin_token,
                        {"criteria": [{"id": 12, "weight": value,
                                       "score_coefficients": levels12}]})
            stored = float(live_sql("SELECT weight FROM performance_db.criteria WHERE id = 12"))
            floor[f"weight_{value}"] = {"status": s,
                                        "error": (b or {}).get("error") if isinstance(b, dict) else None,
                                        "stored_after": stored}
            check(f"live weight floor: {value} rejected",
                  (s, (b or {}).get("error")), (422, "INVALID_WEIGHT"))
            check(f"live weight floor: {value} did not change the stored weight",
                  stored, float(crit12["weight"]))
        report["weight_floor_live"] = floor

    finally:
        live_sql(f"DELETE FROM performance_db.auth_sessions WHERE jti::text LIKE '{JTI_PREFIX}-%'")

    remaining = int(live_sql(
        f"SELECT count(*) FROM performance_db.auth_sessions WHERE jti::text LIKE '{JTI_PREFIX}-%'"))
    sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
    fingerprint_after = state_fingerprint()
    report.update({
        "probe_sessions_remaining": remaining,
        "auth_sessions_after": sessions_after,
        "state_fingerprint_after": fingerprint_after,
        "state_unchanged": fingerprint_after == fingerprint_before,
    })
    check("probe sessions removed", remaining, 0)
    check("auth_sessions back to the pre-probe count", sessions_after, sessions_before)
    check("live state fingerprint unchanged", fingerprint_after, fingerprint_before)

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

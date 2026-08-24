#!/usr/bin/env python3
"""Post-deploy live probe for the finalization batch (2026-08-24).

Launch is PAUSED (no active period), so every probe is a refusal and nothing
needs cleanup beyond the probe session itself:
  - POST score-correction, project criterion (8) for a currently-general live
    subject  -> 422 CRITERIA_NOT_APPLICABLE (the deployed applicability rule,
    checked before the period gate)
  - POST score-correction, 'all' criterion (3) for the same subject
    -> 409 NO_ACTIVE_PERIOD (applicable, falls through to the period gate)
  - GET manager-subordinates-matrix -> 200 empty no-period state
  - score_corrections row count unchanged (0 -> 0)
  - money-inputs fingerprint (weights + level coefficients + grades)
    byte-identical before and after the probes

The probe session is a marked jti INSERTed for the live admin (id 2) and
deleted in finally. The JWT secret is read at probe time from the live n8n
container and never stored.
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

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent
ADMIN_ID = 2
PROBE_JTI = "fa9ade00-2026-4824-8000-000000000001"  # marked probe jti


def ssh(command: str) -> str:
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command],
                            capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 3600, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def call(base: str, method: str, path: str, token: str, body=None):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


FINGERPRINT_SQL = """
  SELECT md5(
    (SELECT COALESCE(string_agg(c.id || ':' || c.weight || ':' || c.is_active, ',' ORDER BY c.id), '')
       FROM performance_db.criteria c)
    || '|' ||
    (SELECT COALESCE(string_agg(sc.criteria_id || ':' || sc.score_level || ':' || sc.coefficient, ',' ORDER BY sc.criteria_id, sc.score_level), '')
       FROM performance_db.score_coefficients sc)
    || '|' ||
    (SELECT COALESCE(string_agg(g.id || ':' || g.code || ':' || g.coefficient, ',' ORDER BY g.id), '')
       FROM performance_db.grades g)
  )
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--output", type=Path,
                        default=REPO / "backups/2026-08-24-finalize/live_finalize_probe.json")
    args = parser.parse_args()

    report: dict = {"base_url": args.base_url}
    failures: list[str] = []

    def check(name: str, actual, expected) -> None:
        if actual != expected:
            failures.append(f"{name}: expected {expected!r}, got {actual!r}")

    # a live general subject for the probe pair (never written to)
    subject = json.loads(live_sql("""
      SELECT row_to_json(u) FROM (
        SELECT id, work_category, is_project_participant
        FROM performance_db.users
        WHERE role = 'employee' AND work_category = 'general'
          AND is_project_participant = false
        ORDER BY id LIMIT 1) u"""))
    report["probe_subject"] = subject
    check("probe subject is general", subject["is_project_participant"], False)

    fingerprint_before = live_sql(FINGERPRINT_SQL)
    corrections_before = int(live_sql("SELECT count(*) FROM performance_db.score_corrections"))
    report["money_fingerprint_before"] = fingerprint_before
    report["corrections_before"] = corrections_before

    secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
    if not secret:
        raise SystemExit("could not read JWT_SIGNING_SECRET from the live container")
    token_version = int(live_sql(f"SELECT token_version FROM performance_db.users WHERE id = {ADMIN_ID}"))

    live_sql(f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{PROBE_JTI}', {ADMIN_ID}, {token_version}, now(), now() + interval '1 hour')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
    token = mint(secret, ADMIN_ID, PROBE_JTI)

    try:
        status, body = call(args.base_url, "POST", "api/admin/score-correction", token,
                            {"subject_id": subject["id"], "criteria_id": 8, "correction_score": 5})
        report["probe_inapplicable"] = {"status": status,
                                        "error": (body or {}).get("error"),
                                        "message": (body or {}).get("message")}
        check("inapplicable criterion refused by the applicability rule",
              (status, (body or {}).get("error")), (422, "CRITERIA_NOT_APPLICABLE"))

        status, body = call(args.base_url, "POST", "api/admin/score-correction", token,
                            {"subject_id": subject["id"], "criteria_id": 3, "correction_score": 5})
        report["probe_applicable"] = {"status": status, "error": (body or {}).get("error")}
        check("applicable criterion falls through to the period gate (paused launch)",
              (status, (body or {}).get("error")), (409, "NO_ACTIVE_PERIOD"))

        status, body = call(args.base_url, "GET", "api/manager-subordinates-matrix", token)
        report["probe_mm_matrix"] = {"status": status,
                                     "rows": len((body or {}).get("data") or []),
                                     "period": (body or {}).get("period"),
                                     "campaign_active": (body or {}).get("campaign_active")}
        check("manager matrix answers the empty no-period state",
              (status, (body or {}).get("data"), (body or {}).get("period")), (200, [], None))
    finally:
        deleted = live_sql(
            f"DELETE FROM performance_db.auth_sessions WHERE jti = '{PROBE_JTI}' RETURNING jti")
        report["probe_session_deleted"] = bool(deleted)

    corrections_after = int(live_sql("SELECT count(*) FROM performance_db.score_corrections"))
    fingerprint_after = live_sql(FINGERPRINT_SQL)
    report["corrections_after"] = corrections_after
    report["money_fingerprint_after"] = fingerprint_after
    check("no correction row was written", corrections_after, corrections_before)
    check("money-inputs fingerprint unchanged", fingerprint_after, fingerprint_before)
    check("probe session removed", report["probe_session_deleted"], True)

    report["failures"] = failures
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(1)
    print("LIVE PROBES PASSED")


if __name__ == "__main__":
    main()

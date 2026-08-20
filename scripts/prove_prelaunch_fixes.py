#!/usr/bin/env python3
"""API acceptance proof against the isolated pre-launch n8n and throwaway DB."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def call(
    base: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    request_headers = {"Accept": "application/json", **(headers or {})}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
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


def has_russian_message(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    message = str(payload.get("message") or payload.get("body", {}).get("message") or "")
    return bool(re.search(r"[А-Яа-яЁё]", message)) and "/api/" not in message


def seed_pre_auth_rows(database: str) -> None:
    if not database.startswith("epe_prelaunch_"):
        raise SystemExit(f"Refusing non-throwaway database: {database}")
    sql = """
DELETE FROM performance_db.auth_login_attempts
WHERE email LIKE 'epe-throttle:verify-invite:203.0.113.%';
INSERT INTO performance_db.auth_login_attempts
  (email, window_started_at, failed_count, last_failed_at, updated_at)
VALUES
  ('epe-throttle:verify-invite:203.0.113.55', now(), 600, now(), now());
DELETE FROM performance_db.email_verification_codes
WHERE email = 'code.proof@example.invalid';
INSERT INTO performance_db.email_verification_codes
  (email, code, created_at, expires_at, is_verified, attempts)
VALUES
  ('code.proof@example.invalid', '123456', now(), now() + interval '10 minutes', false, 0);
"""
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            str(Path.home() / ".ssh/id_ed25519"),
            "root@92.51.45.147",
            f"docker exec -i postgres_n8n psql -U admin -d {database} -v ON_ERROR_STOP=1",
        ],
        input=sql.encode(),
        capture_output=True,
    )
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:25679/webhook",
    )
    parser.add_argument(
        "--database",
        default="epe_prelaunch_20260820_1328",
    )
    parser.add_argument(
        "--tokens",
        type=Path,
        default=Path("backups/2026-08-20-prelaunch-fixes/proof_tokens.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backups/2026-08-20-prelaunch-fixes/api_proof.json"),
    )
    args = parser.parse_args()
    parsed_base = urllib.parse.urlparse(args.base_url)
    if parsed_base.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Proof base URL must be loopback")
    if not args.database.startswith("epe_prelaunch_"):
        raise SystemExit("Proof database must use the epe_prelaunch_ prefix")

    tokens = json.loads(args.tokens.read_text())
    seed_pre_auth_rows(args.database)
    evidence: dict[str, Any] = {}

    def record(
        name: str,
        method: str,
        path: str,
        *,
        actor: str | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        status, payload = call(
            args.base_url,
            method,
            path,
            token=tokens.get(actor) if actor else None,
            body=body,
            headers=headers,
        )
        evidence[name] = {"status": status, "body": payload}
        return status, payload

    status, manager_subject = record(
        "manager_subject_self_review",
        "GET",
        "api/check-self-review?user_id=1002",
        actor="manager",
    )
    require(status == 200 and manager_subject.get("score") == "8.00", "manager must get report self-review")
    require(
        manager_subject.get("comments", {}).get("3", "").startswith("САМООЦЕНКА ПОДЧИНЁННОГО"),
        "manager must get report comments",
    )

    status, manager_fallback = record(
        "unauthorized_selector_falls_back",
        "GET",
        "api/check-self-review?user_id=1006",
        actor="manager",
    )
    require(status == 200 and manager_fallback.get("score") == "3.00", "foreign selector must fall back to actor")
    require(
        manager_fallback.get("comments", {}).get("3", "").startswith("МОЯ САМООЦЕНКА"),
        "fallback comments must belong to actor",
    )

    status, pending = record(
        "not_submitted_self_review",
        "GET",
        "api/check-self-review?user_id=1003",
        actor="manager",
    )
    require(status == 200 and pending.get("has_self_review") is False, "pending self-review must be graceful")

    status, employee_rows = record("manager_completion_flags", "GET", "api/employees", actor="manager")
    require(status == 200, "manager employees request failed")
    rows = {row["id"]: row for row in employee_rows.get("data", [])}
    require(set(rows) == {1002, 1003, 1004}, "manager scope must be direct in-scope reports only")
    require(
        rows[1002]["has_self_review"] and rows[1002]["has_evaluated_manager"] and rows[1002]["evaluated_by_actor"],
        "complete report flags mismatch",
    )
    require(
        not rows[1003]["has_self_review"] and not rows[1003]["has_evaluated_manager"] and rows[1003]["evaluated_by_actor"],
        "pending-self report flags mismatch",
    )
    require(
        rows[1004]["has_self_review"] and rows[1004]["has_evaluated_manager"] and not rows[1004]["evaluated_by_actor"],
        "pending-manager report flags mismatch",
    )
    require(
        all("grade_coefficient" not in row for row in rows.values()),
        "manager employees payload leaked grade coefficient",
    )
    require(
        all(
            forbidden not in row
            for row in rows.values()
            for forbidden in ("score", "calculated_score", "weighted_score", "comments")
        ),
        "manager status payload leaked score content",
    )

    status, privileged_rows = record("clevel_preserved_direct_scope", "GET", "api/employees", actor="c_level_writer")
    privileged_ids = {row["id"] for row in privileged_rows.get("data", [])}
    require(status == 200 and privileged_ids == {1006, 1007}, "c_level direct scope changed")
    require(
        all("grade_coefficient" in row for row in privileged_rows["data"]),
        "c_level must retain grade coefficient",
    )

    status, excluded = record("out_of_scope_status", "GET", "api/employees", actor="out_of_scope")
    require(
        status == 200 and excluded.get("actor_is_in_scope") is False and excluded.get("data") == [],
        "out-of-scope actor must receive no tasks",
    )

    status, manager_info = record("plain_get_manager", "GET", "api/get-my-manager", actor="subject_complete")
    require(status == 200 and "grade_coefficient" not in manager_info["manager"], "plain get-manager leaked coefficient")
    status, admin_manager_info = record("privileged_get_manager", "GET", "api/get-my-manager", actor="admin")
    require(status == 200 and "grade_coefficient" in admin_manager_info["manager"], "admin lost coefficient")

    status, profile = record("subject_profile_sealed", "GET", "api/my-profile", actor="subject_complete")
    require(status == 200, "subject profile failed")
    non_self = [row for row in profile.get("evaluations", []) if not row.get("is_self_evaluation")]
    require(non_self, "seeded non-self rows missing")
    for row in non_self:
        for field in ("score", "calculated_score", "weighted_score", "comments"):
            require(field not in row, f"subject profile leaked {field}")
    require(profile.get("stats", {}).get("average_score") == 8, "profile stats must use self-review only")

    status, _ = record(
        "subject_received_details_rejected",
        "GET",
        "api/evaluation-details?evaluation_id=2004",
        actor="subject_complete",
    )
    require(status in {403, 404}, "subject received details must be rejected")
    status, evaluator_details = record(
        "evaluator_details_unchanged",
        "GET",
        "api/evaluation-details?evaluation_id=2004",
        actor="manager",
    )
    require(status == 200 and evaluator_details.get("scores"), "evaluator must retain authored details")
    require(
        evaluator_details["scores"][0].get("comment", "").startswith("СКРЫТЫЙ КОММЕНТАРИЙ"),
        "evaluator comment access changed",
    )
    status, own_self_details = record(
        "subject_own_self_details",
        "GET",
        "api/evaluation-details?evaluation_id=2002",
        actor="subject_complete",
    )
    require(status == 200 and own_self_details.get("scores"), "subject must retain own self-review details")
    status, _ = record(
        "foreign_evaluation_id_rejected",
        "GET",
        "api/evaluation-details?evaluation_id=2009",
        actor="subject_complete",
    )
    require(status in {403, 404}, "foreign evaluation id must be rejected")

    status, plain_criteria = record("plain_criteria", "GET", "api/criteria", actor="subject_complete")
    require(status == 200, "plain criteria failed")
    plain_clevel = [row for row in plain_criteria.get("data", []) if row.get("c_level_only")]
    require(plain_clevel, "c_level_only titles must remain")
    require(
        all(
            f"level_{level}_desc" not in row
            for row in plain_clevel
            for level in range(1, 11)
        ),
        "plain criteria leaked C-level level texts",
    )
    status, admin_criteria = record("admin_criteria", "GET", "api/criteria", actor="admin")
    require(
        status == 200
        and any(row.get("c_level_only") and "level_1_desc" in row for row in admin_criteria.get("data", [])),
        "admin must retain C-level level texts",
    )

    status, correction = record(
        "readonly_clevel_correction_rejected",
        "POST",
        "api/admin/score-correction",
        actor="c_level_readonly",
        body={"subject_id": 1002, "criteria_id": 3, "correction_score": 8},
    )
    require(status == 403 and correction.get("error") == "CAPABILITY_FORBIDDEN", "read-only c_level correction must fail")

    status, duplicate_self = record(
        "duplicate_self_review_russian",
        "POST",
        "api/self-review-submit",
        actor="subject_complete",
        body={"final_score": 8, "weighted_score": 8, "grades": {"3": 8}, "comments": {}},
    )
    require(status == 409 and has_russian_message(duplicate_self), "duplicate self-review message must be Russian")
    status, duplicate_eval = record(
        "duplicate_evaluation_russian",
        "POST",
        "api/submit-evaluation",
        actor="manager",
        body={"subject_id": 1002, "evaluation_source": "manager", "grades": {"3": 8}, "comments": {}},
    )
    require(status == 409 and has_russian_message(duplicate_eval), "duplicate evaluation message must be Russian")

    status, invalid_invite = record(
        "invalid_invite_russian",
        "GET",
        "api/verify-invite?token=invalid-prelaunch-token",
        headers={"X-Forwarded-For": "203.0.113.56"},
    )
    require(status == 200 and has_russian_message(invalid_invite), "invalid invite message must be Russian")
    status, throttled_invite = record(
        "invite_throttle_russian",
        "GET",
        "api/verify-invite?token=invalid-prelaunch-token",
        headers={"X-Forwarded-For": "203.0.113.55"},
    )
    require(
        status == 200
        and throttled_invite.get("error_code") == "RATE_LIMITED"
        and has_russian_message(throttled_invite),
        "invite throttle message must be Russian",
    )
    status, invalid_code = record(
        "invalid_code_russian",
        "POST",
        "api/verify-code",
        body={"email": "code.proof@example.invalid", "code": "000000"},
    )
    require(
        status == 200
        and invalid_code.get("data", {}).get("attempts_remaining") == 4
        and has_russian_message(invalid_code),
        "invalid code message must be Russian and include attempts",
    )
    status, invalid_register = record(
        "invalid_registration_russian",
        "POST",
        "api/register",
        body={"email": "missing@example.invalid", "password": "Password123", "token": "invalid-token"},
    )
    require(status == 400 and has_russian_message(invalid_register), "invalid register message must be Russian")
    status, invalid_reset = record(
        "invalid_reset_russian",
        "POST",
        "api/reset-password",
        body={"token": "invalid-token", "password": "Password123"},
    )
    require(status == 400 and has_russian_message(invalid_reset), "invalid reset message must be Russian")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": len(evidence),
                "output": str(args.output),
                "base_url": args.base_url,
                "database": args.database,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

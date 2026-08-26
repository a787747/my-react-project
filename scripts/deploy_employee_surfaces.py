#!/usr/bin/env python3
"""Deploy the employee-profile read extension and no other workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO / "n8n_workflows"
AUTH_GUARD_ID = "L0Zr7nVa8O5YWXd3"
AUTH_GUARD_UPDATED_AT = "2026-08-18T16:34:30.674Z"
POSTGRES_CREDENTIAL_ID = "VNbfkY8IKbEzn88B"
PROFILE_ID = "jCKNLytVw0qEF17W"
PROFILE_NAME = "API: My Profile V5 (Fixed Empty)"
SSH_HOST = "root@92.51.45.147"


def request(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {"X-N8N-API-KEY": api_key, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {url} failed: {exc.code} {body[:800]}") from exc


def comparable(workflow: dict[str, Any]) -> dict[str, Any]:
    settings = workflow.get("settings") or {}
    return {
        "name": workflow.get("name"),
        "nodes": workflow.get("nodes") or [],
        "connections": workflow.get("connections") or {},
        "settings": {
            key: settings.get(key)
            for key in (
                "executionOrder",
                "saveDataErrorExecution",
                "saveDataSuccessExecution",
                "saveManualExecutions",
            )
        },
    }


def generate() -> dict[str, Any]:
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-profile-"))
    subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "build_route_guard_workflows.py"),
            "--postgres-credential-id",
            POSTGRES_CREDENTIAL_ID,
            "--guard-workflow-id",
            AUTH_GUARD_ID,
            "--output-directory",
            str(directory),
        ],
        check=True,
        capture_output=True,
        cwd=REPO,
    )
    return json.loads((directory / "my-profile.json").read_text())


def live_sql(statement: str) -> str:
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=20",
            SSH_HOST,
            "docker exec -i postgres_n8n psql -U admin -d epe_2026 "
            "-v ON_ERROR_STOP=1 -tA",
        ],
        input=statement.encode(),
        capture_output=True,
    )
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def webhook_paths(workflow: dict[str, Any]) -> list[str]:
    return sorted(
        f"{node['parameters'].get('httpMethod', 'GET')} "
        f"{node['parameters'].get('path')}"
        for node in (workflow.get("nodes") or [])
        if node.get("type") == "n8n-nodes-base.webhook"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n8n-url",
        default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"),
    )
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="PUT the profile workflow. Without this flag the command is read-only.",
    )
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")

    live_state = live_sql(
        "SELECT "
        "(SELECT count(*) FROM performance_db.users) || '/' || "
        "(SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_period_participants "
        " WHERE period_id=2 AND is_in_scope) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results) || '/' || "
        "(SELECT status || ':' || is_active::text || ':' || "
        "        (evaluation_started_at IS NOT NULL)::text "
        " FROM performance_db.evaluation_periods WHERE id=2)"
    )
    period_state = live_state.rsplit("/", 1)[-1]
    if period_state != "active:true:true":
        raise SystemExit(f"Refusing deployment: unexpected H1 state {period_state}")

    base = args.n8n_url.rstrip("/")
    guard_before = request(
        "GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key
    )
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: Auth Guard is not the frozen graph")

    source = generate()
    live = request("GET", f"{base}/api/v1/workflows/{PROFILE_ID}", args.api_key)
    if live.get("name") != PROFILE_NAME or source.get("name") != PROFILE_NAME:
        raise SystemExit("Refusing deployment: profile workflow identity mismatch")

    before_paths = webhook_paths(live)
    changed = comparable(live) != comparable(source)
    report: dict[str, Any] = {
        "applied": args.apply,
        "live_state_before": live_state,
        "id": PROFILE_ID,
        "name": PROFILE_NAME,
        "changed": changed,
        "active_before": bool(live.get("active")),
        "updatedAt_before": live.get("updatedAt"),
        "webhook_paths_before": before_paths,
    }

    if args.apply and changed:
        payload = {
            "name": source.get("name"),
            "nodes": source.get("nodes") or [],
            "connections": source.get("connections") or {},
            "settings": {
                **(live.get("settings") or {}),
                **(source.get("settings") or {}),
            },
            "staticData": live.get("staticData"),
        }
        request("PUT", f"{base}/api/v1/workflows/{PROFILE_ID}", args.api_key, payload)
        updated = request(
            "GET", f"{base}/api/v1/workflows/{PROFILE_ID}", args.api_key
        )
        if comparable(updated) != comparable(source):
            raise SystemExit("Live profile graph differs from the generated graph after PUT")
        if bool(updated.get("active")) != report["active_before"]:
            raise SystemExit("Profile workflow activation state changed during PUT")
        if webhook_paths(updated) != before_paths:
            raise SystemExit("Profile workflow webhook path changed during PUT")
        guard_after = request(
            "GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key
        )
        if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
            raise SystemExit("Auth Guard changed during profile deployment")
        (WORKFLOW_DIR / "API_ My Profile V5 (Fixed Empty).json").write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
        )
        report.update(
            {
                "active_after": bool(updated.get("active")),
                "updatedAt_after": updated.get("updatedAt"),
                "webhook_paths_after": webhook_paths(updated),
                "auth_guard_updatedAt": guard_after.get("updatedAt"),
                "export_refreshed": "API_ My Profile V5 (Fixed Empty).json",
            }
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

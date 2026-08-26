#!/usr/bin/env python3
"""Deploy HIRE_DATE_AND_SCOPE_TOGGLE workflow changes to live.

Migration 017 must already be present. This script never starts a period and
refuses unless live is still 89 users / 3 terminated / 80 in H1 / 0-0-0-0 with
evaluation_started_at NULL on every period.
"""

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
SSH_HOST = "root@92.51.45.147"

# generated file, live id, builder, tracked export
UPDATES = [
    ("save-user.json", "JCjzhRJtIDW0z8mI",
     "build_route_guard_workflows.py", "API_ Admin Save User (GUI Mode).json"),
    ("manage-periods.json", "M9ljMDdO1mIl8m1h",
     "build_route_guard_workflows.py", "API_ Manage Periods.json"),
    ("admin-users-data.json", "AwID96McjHKyk8WI",
     "build_route_guard_workflows.py", "API_ Admin Get Users Data.json"),
    ("manage-period-scope.json", "8xK4EnDJrH1b1OJ7",
     "build_route_guard_workflows.py", "API_ Manage Period Scope.json"),
    ("protected-employees.json", "bKB4Sb46yWoq1tSV",
     "build_auth_workflows.py", "API_ Get Employees (Smart Role Based).json"),
]


def request(method: str, url: str, api_key: str,
            payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"X-N8N-API-KEY": api_key, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(
            f"{method} {url} failed: {exc.code} {body[:1200]}") from exc


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", SSH_HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 "
         "-v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def generate(builder: str) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="epe-hire-scope-deploy-"))
    subprocess.run(
        [sys.executable, str(REPO / "scripts" / builder),
         "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
         "--guard-workflow-id", AUTH_GUARD_ID,
         "--output-directory", str(directory)],
        check=True, capture_output=True, cwd=REPO)
    return directory


def comparable(workflow: dict[str, Any]) -> dict[str, Any]:
    settings = workflow.get("settings") or {}
    return {
        "name": workflow.get("name"),
        "nodes": workflow.get("nodes") or [],
        "connections": workflow.get("connections") or {},
        "settings": {
            key: settings.get(key)
            for key in ("executionOrder", "saveDataErrorExecution",
                        "saveDataSuccessExecution", "saveManualExecutions")
        },
    }


def webhook_paths(workflow: dict[str, Any]) -> list[str]:
    return sorted(
        f"{node['parameters'].get('httpMethod', 'GET')} "
        f"{node['parameters'].get('path')}"
        for node in (workflow.get("nodes") or [])
        if node.get("type") == "n8n-nodes-base.webhook")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")
    base = args.n8n_url.rstrip("/")

    state = json.loads(live_sql("""
      SELECT json_build_object(
        'users', (SELECT count(*) FROM performance_db.users),
        'terminated', (SELECT count(*) FROM performance_db.users
                       WHERE terminated_at IS NOT NULL),
        'h1_in_scope', (SELECT count(*) FROM
                       performance_db.evaluation_period_participants
                       WHERE period_id=2 AND is_in_scope),
        'started', (SELECT count(*) FROM performance_db.evaluation_periods
                    WHERE evaluation_started_at IS NOT NULL),
        'evaluations', (SELECT count(*) FROM performance_db.evaluations),
        'scores', (SELECT count(*) FROM performance_db.evaluation_scores),
        'corrections', (SELECT count(*) FROM performance_db.score_corrections),
        'results', (SELECT count(*) FROM performance_db.period_results),
        'card_events_table', (SELECT count(*) FROM information_schema.tables
          WHERE table_schema='performance_db'
            AND table_name='employee_card_events'),
        'scope_override_column', (SELECT count(*) FROM information_schema.columns
          WHERE table_schema='performance_db'
            AND table_name='evaluation_period_participants'
            AND column_name='scope_override'),
        'h1_rule_disagreements', (
          SELECT count(*)
          FROM performance_db.evaluation_period_participants epp
          JOIN performance_db.users u ON u.id=epp.user_id
          JOIN performance_db.evaluation_periods p ON p.id=epp.period_id
          WHERE epp.period_id=2
            AND u.terminated_at IS NULL
            AND u.join_date IS NOT NULL
            AND u.join_date > (
              date_trunc('month', p.end_date)::date
              - interval '2 months' - interval '1 day'
            )::date
            AND epp.is_in_scope
        )
      )
    """))
    expected = {
        "users": 89, "terminated": 3, "h1_in_scope": 80, "started": 0,
        "evaluations": 0, "scores": 0, "corrections": 0, "results": 0,
        "card_events_table": 1, "scope_override_column": 1,
        "h1_rule_disagreements": 0,
    }
    if state != expected:
        raise SystemExit(
            f"Refusing deploy: live preconditions differ\n"
            f"actual={state}\nexpected={expected}")

    guard_before = request(
        "GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deploy: Auth Guard updatedAt moved")

    generated = {
        builder: generate(builder)
        for builder in {item[2] for item in UPDATES}
    }
    report: list[dict[str, Any]] = []
    for filename, workflow_id, builder, export_name in UPDATES:
        source = json.loads((generated[builder] / filename).read_text())
        live = request(
            "GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if live.get("name") != source.get("name"):
            raise SystemExit(
                f"{workflow_id}: live name {live.get('name')!r} "
                f"!= generated {source.get('name')!r}")
        changed = comparable(live) != comparable(source)
        entry = {
            "id": workflow_id,
            "name": live.get("name"),
            "changed": changed,
            "active_before": bool(live.get("active")),
            "updatedAt_before": live.get("updatedAt"),
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
            request(
                "PUT", f"{base}/api/v1/workflows/{workflow_id}",
                args.api_key, payload)
            updated = request(
                "GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
            if comparable(updated) != comparable(source):
                raise SystemExit(f"{workflow_id}: graph differs after PUT")
            if bool(updated.get("active")) != entry["active_before"]:
                raise SystemExit(f"{workflow_id}: active state changed")
            entry.update({
                "active_after": bool(updated.get("active")),
                "updatedAt_after": updated.get("updatedAt"),
                "webhook_paths": webhook_paths(updated),
            })
            (WORKFLOW_DIR / export_name).write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            entry["export_refreshed"] = export_name
            guard = request(
                "GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
            if guard.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
                raise SystemExit("Auth Guard changed during deployment")
        report.append(entry)

    print(json.dumps({
        "applied": args.apply,
        "preconditions": state,
        "updates": report,
    }, ensure_ascii=False, indent=2))
    if not args.apply:
        print("read-only; re-run with --apply", file=sys.stderr)


if __name__ == "__main__":
    main()

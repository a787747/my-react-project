#!/usr/bin/env python3
"""Deploy ADMIN_USERS_SUMMARY read-payload to LIVE — RUN FROM THE MAC.

One workflow: API: Admin Get Users Data (AwID96McjHKyk8WI). Read-payload
only: named campaign-progress flags. No epe_2026 row is written.

THE CAMPAIGN IS OPEN. evaluation_started_at, users/terminated/in-scope and
the coefficient fingerprints must not move. Table counts are read before
and after; a move is owner activity, not this PUT.
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

UPDATES: list[tuple[str, str, str, str]] = [
    ("admin-users-data.json", "AwID96McjHKyk8WI",
     "build_route_guard_workflows.py", "API_ Admin Get Users Data.json"),
]


def request(method: str, url: str, api_key: str,
            payload: dict[str, Any] | None = None) -> dict[str, Any]:
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
            for key in ("executionOrder", "saveDataErrorExecution",
                        "saveDataSuccessExecution", "saveManualExecutions")
        },
    }


def generate(builder: str) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-adminusers-"))
    subprocess.run(
        [sys.executable, str(REPO / "scripts" / builder),
         "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
         "--guard-workflow-id", AUTH_GUARD_ID,
         "--output-directory", str(directory)],
        check=True, capture_output=True, cwd=REPO)
    return directory


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", SSH_HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def campaign_snapshot() -> dict[str, str]:
    return {
        "started": live_sql(
            "SELECT id || '=' || COALESCE(evaluation_started_at::text, 'NULL') "
            "FROM performance_db.evaluation_periods ORDER BY id"),
        "tables": live_sql(
            "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
            "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
            "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
            "(SELECT count(*) FROM performance_db.period_results)"),
        "population": live_sql(
            "SELECT (SELECT count(*) FROM performance_db.users) || '/' || "
            "(SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL) || '/' || "
            "(SELECT count(*) FROM performance_db.evaluation_period_participants "
            " WHERE period_id = 2 AND is_in_scope)"),
        "coeff_criteria": live_sql(
            "SELECT md5(string_agg(id || ':' || weight, ',' ORDER BY id)) "
            "FROM performance_db.criteria WHERE is_active = true"),
        "coeff_levels": live_sql(
            "SELECT md5(string_agg(criteria_id || ':' || score_level || ':' || coefficient, "
            "',' ORDER BY criteria_id, score_level)) FROM performance_db.score_coefficients"),
        "coeff_grades": live_sql(
            "SELECT md5(string_agg(id || ':' || code || ':' || coefficient, ',' ORDER BY id)) "
            "FROM performance_db.grades"),
    }


def webhook_paths(workflow: dict[str, Any]) -> list[str]:
    return sorted(
        f"{n['parameters'].get('httpMethod', 'GET')} {n['parameters'].get('path')}"
        for n in (workflow.get("nodes") or [])
        if n.get("type") == "n8n-nodes-base.webhook")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument("--apply", action="store_true",
                        help="Write to live. Without this flag the command is read-only.")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")
    base = args.n8n_url.rstrip("/")

    before = campaign_snapshot()
    if "2=NULL" in before["started"]:
        raise SystemExit(
            "H1 (id 2) reads evaluation_started_at NULL — the campaign this deploy was "
            "written for is open. Re-establish the live state before deploying.")

    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    generated: dict[str, Path] = {}
    for builder in {b for _, _, b, _ in UPDATES}:
        generated[builder] = generate(builder)

    report: list[dict[str, Any]] = []
    for filename, workflow_id, builder, export_name in UPDATES:
        source = json.loads((generated[builder] / filename).read_text())
        live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if live.get("name") != source.get("name"):
            raise SystemExit(f"live name {live.get('name')!r} != {source.get('name')!r}")
        if not live.get("active"):
            raise SystemExit(f"{live.get('name')!r} is not active on live — wrong target?")
        changed = comparable(live) != comparable(source)
        entry: dict[str, Any] = {
            "action": "update", "file": filename, "id": workflow_id,
            "name": live.get("name"), "changed": changed,
            "active_before": bool(live.get("active")),
            "updatedAt_before": live.get("updatedAt"),
            "webhook_paths_before": webhook_paths(live),
        }
        if args.apply and changed:
            payload = {
                "name": source.get("name"),
                "nodes": source.get("nodes") or [],
                "connections": source.get("connections") or {},
                "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
                "staticData": live.get("staticData"),
            }
            request("PUT", f"{base}/api/v1/workflows/{workflow_id}", args.api_key, payload)
            updated = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
            if bool(updated.get("active")) != entry["active_before"]:
                raise SystemExit(f"activation state changed during PUT of {workflow_id}")
            if comparable(updated) != comparable(source):
                raise SystemExit(f"live graph differs after PUT of {workflow_id}")
            if webhook_paths(updated) != entry["webhook_paths_before"]:
                raise SystemExit(f"webhook paths changed during PUT of {workflow_id}")
            entry.update({
                "active_after": bool(updated.get("active")),
                "updatedAt_after": updated.get("updatedAt"),
                "webhook_paths": webhook_paths(updated),
            })
            (WORKFLOW_DIR / export_name).write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            entry["export_refreshed"] = export_name
        elif args.apply and not changed:
            entry["note"] = "generated graph already matches live — no PUT"
        report.append(entry)

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    after = campaign_snapshot()
    hard = ["started", "coeff_criteria", "coeff_levels", "coeff_grades", "population"]
    for key in hard:
        if before[key] != after[key]:
            raise SystemExit(
                f"CAMPAIGN INVARIANT MOVED during deploy: {key!r}\n"
                f"  before: {before[key]}\n  after:  {after[key]}\n"
                f"The PUT cannot cause this — investigate before anything else.")

    print(json.dumps({
        "applied": args.apply,
        "updates": report,
        "campaign_before": before,
        "campaign_after": after,
        "table_counts_moved": before["tables"] != after["tables"],
    }, ensure_ascii=False, indent=2))
    if before["tables"] != after["tables"]:
        print(
            "\nNOTE: evaluation table counts moved during the deploy window. The PUT "
            "writes a workflow definition only, so this is employee activity in the open "
            "campaign — record both figures in the report.", file=sys.stderr)
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

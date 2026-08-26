#!/usr/bin/env python3
"""Deploy the BUG-073 refusal to LIVE (PRELAUNCH_GATE, 2026-08-26).

One workflow changes: `API: Score Correction` (`rSZcm0HDMUHLYk8W`). Its
`Validate Input` lookup now also fetches the `c_level_only` criteria ids, and
`Decide Level` refuses a correction on any of them with 422
`CRITERIA_NOT_APPLICABLE` — before the period gate, exactly like the
project-criterion refusal, so the rule is provable on live while no campaign
runs. Owner's decision (2026-08-26): corrections calibrate the manager channel;
the C-level channel is calibrated by being averaged across C-level evaluators
(D-0826-1), so a correction there is refused rather than interpreted.

Proven before this runs, on two throwaway stands restored from one dump of live
(control = HEAD, treatment = this change), both closed through the real
`POST /api/periods/close`: the two frozen `period_results` sets are identical
on all 100 rows — the refusal moves no money — and on the treatment stand
criteria 1 and 10 answer 422 while criterion 3 corrections still answer 200 and
the project-dimension 422, ownership 403 and BUG-068 behaviour are unchanged.

Refusals, before anything is written: the Auth Guard must carry its frozen
updatedAt; the second gate must be unpressed; the four data tables must be
empty; the target must exist on live under exactly the expected name. This
build creates nothing and touches no other workflow.
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
    ("score-correction.json", "rSZcm0HDMUHLYk8W",
     "build_route_guard_deferred.py", "API_ Score Correction.json"),
]
CREATE = None


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
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-gatefix-"))
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

    if CREATE is not None:
        raise SystemExit("Refusing to deploy: this build creates no workflow, but CREATE is set.")

    rows = live_sql(
        "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results)")
    if rows != "0/0/0/0":
        raise SystemExit(
            f"Refusing to deploy: data tables = {rows}, expected 0/0/0/0. The refusal was "
            f"proven money-neutral on an empty database; against existing rows it must be "
            f"re-proven first.")
    started = live_sql(
        "SELECT count(*) FROM performance_db.evaluation_periods "
        "WHERE evaluation_started_at IS NOT NULL")
    if started != "0":
        raise SystemExit(
            f"Refusing to deploy: {started} period(s) already started. This brief runs "
            f"before the second gate.")

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
            guard = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
            if guard.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
                raise SystemExit("EPE Auth Guard changed during deployment")
        report.append(entry)

    print(json.dumps({"applied": args.apply, "updates": report}, ensure_ascii=False, indent=2))
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

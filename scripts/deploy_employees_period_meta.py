#!/usr/bin/env python3
"""Validate or PUT the single workflow changed by the EMPLOYEES_PERIOD_META
brief (2026-08-24): API: Get Employees (Smart Role Based).

Same contract as deploy_reclass.py:
  - refuses to run if EPE: Auth Guard moved from its frozen updatedAt, and
    re-checks it after the PUT (the guard itself is never written)
  - PUT preserves activation state
  - the live graph is re-read and compared node-for-node after the PUT
  - with --apply the tracked top-level export is rewritten from live so
    n8n_workflows/API_ Get Employees (Smart Role Based).json stays fresh
    (BUG-028 hygiene), refusing any export a generator reads as input

Source of truth is the generator, never a tracked top-level export.
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

TARGET_FILE = "protected-employees.json"
TARGET_ID = "bKB4Sb46yWoq1tSV"
TARGET_EXPORT = "API_ Get Employees (Smart Role Based).json"
BUILDER = "build_auth_workflows.py"


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


def assert_not_a_generator_input(export_name: str) -> None:
    """Refuse to refresh an export that a generator reads at build time."""
    sources = [
        REPO / "scripts" / "build_route_guard_deferred.py",
        REPO / "scripts" / "build_route_guard_workflows.py",
        REPO / "scripts" / "build_auth_workflows.py",
    ]
    for source in sources:
        text = source.read_text()
        for marker in ("legacy_node(", "legacy_query("):
            index = 0
            while True:
                index = text.find(marker, index)
                if index == -1:
                    break
                if text[index:index + 400].find(export_name) != -1:
                    raise SystemExit(
                        f"Refusing to refresh {export_name}: {source.name} reads it as a "
                        f"generator input. Inline the node into the builder first.")
                index += len(marker)


def generate(guard_id: str) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-empmeta-"))
    subprocess.run(
        [sys.executable, str(REPO / "scripts" / BUILDER),
         "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
         "--guard-workflow-id", guard_id,
         "--output-directory", str(directory)],
        check=True, capture_output=True, cwd=REPO)
    return directory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument("--apply", action="store_true",
                        help="PUT the workflow. Without this flag the command is read-only.")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")

    base = args.n8n_url.rstrip("/")
    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    source = json.loads((generate(AUTH_GUARD_ID) / TARGET_FILE).read_text())
    live = request("GET", f"{base}/api/v1/workflows/{TARGET_ID}", args.api_key)
    if live.get("name") != source.get("name"):
        raise SystemExit(f"live name {live.get('name')!r} != {source.get('name')!r}")

    changed = comparable(live) != comparable(source)
    entry: dict[str, Any] = {
        "file": TARGET_FILE,
        "id": TARGET_ID,
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
            "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
            "staticData": live.get("staticData"),
        }
        request("PUT", f"{base}/api/v1/workflows/{TARGET_ID}", args.api_key, payload)
        updated = request("GET", f"{base}/api/v1/workflows/{TARGET_ID}", args.api_key)
        if bool(updated.get("active")) != entry["active_before"]:
            raise SystemExit("activation state changed during PUT")
        if comparable(updated) != comparable(source):
            raise SystemExit("live graph differs after PUT")
        entry.update({
            "active_after": bool(updated.get("active")),
            "updatedAt_after": updated.get("updatedAt"),
            "webhook_paths": sorted(
                f"{n['parameters'].get('httpMethod', 'GET')} {n['parameters'].get('path')}"
                for n in (updated.get("nodes") or [])
                if n.get("type") == "n8n-nodes-base.webhook"),
        })
        assert_not_a_generator_input(TARGET_EXPORT)
        (WORKFLOW_DIR / TARGET_EXPORT).write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        entry["export_refreshed"] = TARGET_EXPORT

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "auth_guard_active": guard_after.get("active"),
        "workflow": entry,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

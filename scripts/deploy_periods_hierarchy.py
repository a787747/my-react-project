#!/usr/bin/env python3
"""Validate or PUT the extended API: Manage Periods workflow (brief 2026-08-21).

Same contract as deploy_prelaunch_fixes.py: refuses to run if EPE: Auth Guard
moved from its frozen updatedAt; PUT preserves activation state; live graph is
re-read and compared node-for-node after the PUT. With --apply it also rewrites
the top-level export `n8n_workflows/API_ Manage Periods.json` from live so the
tracked export stays fresh.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO / "n8n_workflows"
AUTH_GUARD_ID = "L0Zr7nVa8O5YWXd3"
AUTH_GUARD_UPDATED_AT = "2026-08-18T16:34:30.674Z"
SOURCE = "route_guard_h1/manage-periods.json"
METADATA = "API_ Manage Periods.json"


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

    source = json.loads((WORKFLOW_DIR / SOURCE).read_text())
    metadata = json.loads((WORKFLOW_DIR / METADATA).read_text())
    workflow_id = metadata.get("id")
    if not workflow_id:
        raise SystemExit(f"{METADATA}: workflow id is missing")

    live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
    if live.get("name") != source.get("name"):
        raise SystemExit(f"live name {live.get('name')!r} != source name {source.get('name')!r}")

    changed = comparable(live) != comparable(source)
    result: dict[str, Any] = {
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
            "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
            "staticData": live.get("staticData"),
        }
        request("PUT", f"{base}/api/v1/workflows/{workflow_id}", args.api_key, payload)
        updated = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if bool(updated.get("active")) != result["active_before"]:
            raise SystemExit("activation state changed during PUT")
        if comparable(updated) != comparable(source):
            raise SystemExit("live graph differs after PUT")
        result.update({
            "active_after": bool(updated.get("active")),
            "updatedAt_after": updated.get("updatedAt"),
        })
        # refresh the tracked top-level export from live
        (WORKFLOW_DIR / METADATA).write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        result["export_refreshed"] = METADATA

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "workflow": result,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

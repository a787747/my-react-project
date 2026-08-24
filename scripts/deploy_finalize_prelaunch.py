#!/usr/bin/env python3
"""Validate or PUT the two workflows changed by the 2026-08-24 finalization
batch: API: Score Correction (corrections applicability, D-0822-3 extension)
and API: Manager Subordinates Matrix (BUG-046 emission filter).

Same contract as deploy_reclass.py:
  - refuses to run if EPE: Auth Guard moved from its frozen updatedAt, and
    re-checks it after every PUT (the guard itself is never written)
  - PUT preserves activation state
  - the live graph is re-read and compared node-for-node after each PUT
  - with --apply the tracked top-level exports are rewritten from live so
    n8n_workflows/API_*.json stays fresh (BUG-028 hygiene), refusing any
    export a generator reads as input

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

# generated file  ->  (builder key, live workflow id, tracked top-level export)
TARGETS: dict[str, tuple[str, str, str]] = {
    "score-correction.json":            ("def", "rSZcm0HDMUHLYk8W", "API_ Score Correction.json"),
    "manager-subordinates-matrix.json": ("def", "EyvFZJGDxQNL20tC", "API_ Manager Subordinates Matrix.json"),
}

BUILDERS = {
    "def": "build_route_guard_deferred.py",
}


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


def generate(guard_id: str) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for key, script in BUILDERS.items():
        directory = Path(tempfile.mkdtemp(prefix=f"epe-deploy-{key}-"))
        subprocess.run(
            [sys.executable, str(REPO / "scripts" / script),
             "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
             "--guard-workflow-id", guard_id,
             "--output-directory", str(directory)],
            check=True, capture_output=True, cwd=REPO)
        out[key] = directory
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument("--apply", action="store_true",
                        help="PUT the workflows. Without this flag the command is read-only.")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")

    base = args.n8n_url.rstrip("/")
    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    generated = generate(AUTH_GUARD_ID)
    results: list[dict[str, Any]] = []

    for filename, (builder, workflow_id, export_name) in TARGETS.items():
        source = json.loads((generated[builder] / filename).read_text())
        live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if live.get("name") != source.get("name"):
            raise SystemExit(f"{filename}: live name {live.get('name')!r} != {source.get('name')!r}")

        changed = comparable(live) != comparable(source)
        entry: dict[str, Any] = {
            "file": filename,
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
            if bool(updated.get("active")) != entry["active_before"]:
                raise SystemExit(f"{filename}: activation state changed during PUT")
            if comparable(updated) != comparable(source):
                raise SystemExit(f"{filename}: live graph differs after PUT")
            entry.update({
                "active_after": bool(updated.get("active")),
                "updatedAt_after": updated.get("updatedAt"),
                "webhook_paths": sorted(
                    f"{n['parameters'].get('httpMethod', 'GET')} {n['parameters'].get('path')}"
                    for n in (updated.get("nodes") or [])
                    if n.get("type") == "n8n-nodes-base.webhook"),
            })
            assert_not_a_generator_input(export_name)
            (WORKFLOW_DIR / export_name).write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            entry["export_refreshed"] = export_name

            guard_now = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
            if guard_now.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
                raise SystemExit(f"EPE Auth Guard changed during deployment (after {filename})")

        results.append(entry)

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "auth_guard_active": guard_after.get("active"),
        "changed_count": sum(1 for r in results if r["changed"]),
        "workflows": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

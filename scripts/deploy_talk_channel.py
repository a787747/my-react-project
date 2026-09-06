#!/usr/bin/env python3
"""Create/update only `API: Management Talk`; never edits Auth Guard or campaign workflows."""
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
AUTH_GUARD_ID = "L0Zr7nVa8O5YWXd3"
AUTH_GUARD_UPDATED_AT = "2026-08-18T16:34:30.674Z"
CREDENTIAL_ID = "VNbfkY8IKbEzn88B"
SSH_HOST = "root@92.51.45.147"
SOURCE = "talk-channel.json"
EXPORT = REPO / "n8n_workflows" / "API_ Management Talk.json"


def request(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"X-N8N-API-KEY": key, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=headers, method=method), timeout=60
        ) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {url}: {exc.code} {exc.read().decode()[:800]}") from exc


def comparable(workflow: dict[str, Any]) -> dict[str, Any]:
    settings = workflow.get("settings") or {}
    return {
        "name": workflow.get("name"),
        "nodes": workflow.get("nodes") or [],
        "connections": workflow.get("connections") or {},
        "settings": {key: settings.get(key) for key in (
            "executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution",
            "saveManualExecutions",
        )},
    }


def generate(builder: Path, output: Path) -> None:
    subprocess.run([
        sys.executable, str(builder), "--postgres-credential-id", CREDENTIAL_ID,
        "--guard-workflow-id", AUTH_GUARD_ID, "--output-directory", str(output),
    ], cwd=REPO, check=True, capture_output=True)


def assert_additive() -> int:
    root = Path(tempfile.mkdtemp(prefix="epe-talk-drift-"))
    old_builder = root / "build_route_guard_workflows.py"
    addition_commit = subprocess.run(
        ["git", "log", "--diff-filter=A", "-1", "--format=%H", "--", "scripts/talk_workflow.py"],
        cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout.strip()
    base_ref = f"{addition_commit}^" if addition_commit else "HEAD"
    old_builder.write_bytes(subprocess.run(
        ["git", "show", f"{base_ref}:scripts/build_route_guard_workflows.py"],
        cwd=REPO, check=True, capture_output=True,
    ).stdout)
    old, new = root / "old", root / "new"
    old.mkdir()
    new.mkdir()
    generate(old_builder, old)
    generate(REPO / "scripts" / "build_route_guard_workflows.py", new)
    old_files = {path.name for path in old.iterdir()}
    new_files = {path.name for path in new.iterdir()}
    changed = sorted(name for name in old_files & new_files
                     if (old / name).read_bytes() != (new / name).read_bytes())
    added = new_files - old_files
    if added != {SOURCE} or old_files - new_files or changed:
        raise SystemExit(
            f"Refusing non-additive workflow deploy: added={sorted(added)} "
            f"removed={sorted(old_files-new_files)} changed={changed}"
        )
    return len(old_files)


def live_sql(statement: str) -> str:
    done = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", SSH_HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 -tA -v ON_ERROR_STOP=1"],
        input=statement, text=True, capture_output=True,
    )
    if done.returncode:
        raise SystemExit(done.stderr or done.stdout)
    return done.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")
    base = args.n8n_url.rstrip("/")

    tables = live_sql("""
SELECT count(*) FROM information_schema.tables
WHERE table_schema='performance_db'
  AND table_name IN ('management_talk_waves','management_talk_topics',
                     'management_talk_responses','management_talk_counterparts');
""")
    if tables != "4":
        raise SystemExit(f"Migration 019 is not present on live: tables={tables}/4")
    unchanged = assert_additive()
    guard = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Frozen Auth Guard updatedAt mismatch")

    output = Path(tempfile.mkdtemp(prefix="epe-talk-deploy-"))
    generate(REPO / "scripts" / "build_route_guard_workflows.py", output)
    source = json.loads((output / SOURCE).read_text())
    catalog = request("GET", f"{base}/api/v1/workflows?limit=250", args.api_key)
    matches = [item for item in catalog.get("data", []) if item.get("name") == source["name"]]
    result: dict[str, Any] = {"name": source["name"], "mode": "dry-run"}

    if args.apply and matches:
        workflow_id = matches[0]["id"]
        live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        request("PUT", f"{base}/api/v1/workflows/{workflow_id}", args.api_key, {
            "name": source["name"], "nodes": source["nodes"], "connections": source["connections"],
            "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
            "staticData": live.get("staticData"),
        })
        final = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if comparable(final) != comparable(source) or not final.get("active"):
            raise SystemExit("Updated TALK workflow differs or became inactive")
        result = {"mode": "updated", "id": workflow_id, "updatedAt": final.get("updatedAt")}
        EXPORT.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")
    elif args.apply:
        created = request("POST", f"{base}/api/v1/workflows", args.api_key, {
            "name": source["name"], "nodes": source["nodes"],
            "connections": source["connections"], "settings": source["settings"],
        })
        workflow_id = created["id"]
        inactive = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if inactive.get("active") or comparable(inactive) != comparable(source):
            raise SystemExit("Created TALK graph failed inactive verification")
        request("POST", f"{base}/api/v1/workflows/{workflow_id}/activate", args.api_key)
        final = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if not final.get("active") or comparable(final) != comparable(source):
            raise SystemExit("Activated TALK graph differs")
        result = {"mode": "created", "id": workflow_id, "updatedAt": final.get("updatedAt")}
        EXPORT.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Auth Guard changed during deployment")
    print(json.dumps({
        "workflow": result, "unchanged_existing_generated_workflows": unchanged,
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deploy the PEER_RECOGNITION workflow to LIVE (2026-08-27).

Same contract as deploy_termination.py, minus everything it does not need:
this brief UPDATES NO EXISTING WORKFLOW. It creates exactly one new one —
`API: Peer Recognition` — and touches nothing else, which is why the script
carries no UPDATES list at all. A brief that must not change the behaviour of
any existing route should not be able to.

  - refuses to run if EPE: Auth Guard moved from its frozen updatedAt, and
    re-checks it after the write (the guard itself is never written)
  - refuses to run unless migration 018 is already on live: the routes read
    performance_db.peer_recognitions, and deploying them first would 500 every
    call
  - refuses to run if the generated surface would change ANY existing workflow:
    the 19 pre-existing generated files are compared byte for byte against what
    the same builder produced at HEAD, and a single difference stops the deploy
  - the new workflow is created INACTIVE, its graph verified node-for-node, and
    only then activated — so a half-imported route can never answer a request
  - a re-run updates in place rather than growing a duplicate

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
SSH_HOST = "root@92.51.45.147"

BUILDER = "build_route_guard_workflows.py"
CREATE = ("peer-recognition.json", "API_ Peer Recognition.json")


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


def generate(builder_path: Path, directory: Path) -> None:
    subprocess.run(
        [sys.executable, str(builder_path),
         "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
         "--guard-workflow-id", AUTH_GUARD_ID,
         "--output-directory", str(directory)],
        check=True, capture_output=True, cwd=REPO)


def assert_only_the_new_file_changed() -> list[str]:
    """The builder is shared. Prove this brief added a file and edited none."""
    staging = Path(tempfile.mkdtemp(prefix="epe-recognition-drift-"))
    head_builder = staging / "head_builder.py"
    head_builder.write_bytes(subprocess.run(
        ["git", "show", f"HEAD:scripts/{BUILDER}"], check=True,
        capture_output=True, cwd=REPO).stdout)
    old_dir, new_dir = staging / "old", staging / "new"
    old_dir.mkdir()
    new_dir.mkdir()
    generate(head_builder, old_dir)
    generate(REPO / "scripts" / BUILDER, new_dir)

    old_files = {p.name for p in old_dir.iterdir()}
    new_files = {p.name for p in new_dir.iterdir()}
    added = sorted(new_files - old_files)
    removed = sorted(old_files - new_files)
    changed = sorted(name for name in old_files & new_files
                     if (old_dir / name).read_bytes() != (new_dir / name).read_bytes())
    if removed or changed or added != [CREATE[0]]:
        raise SystemExit(
            "Refusing to deploy: the generated surface is not purely additive. "
            f"added={added} removed={removed} changed={changed}")
    return sorted(old_files & new_files)


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

    # The routes read the table migration 018 adds.
    table = live_sql(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='performance_db' AND table_name='peer_recognitions'")
    constraints = live_sql(
        "SELECT count(*) FROM pg_constraint WHERE conname IN "
        "('uq_peer_recognitions_period_author','chk_peer_recognitions_not_self',"
        "'chk_peer_recognitions_texts_present')")
    if table != "1" or constraints != "3":
        raise SystemExit(
            f"Refusing to deploy: migration 018 is not on live "
            f"(peer_recognitions table={table}/1, constraints={constraints}/3)")

    unchanged = assert_only_the_new_file_changed()

    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    generated = Path(tempfile.mkdtemp(prefix="epe-deploy-recognition-"))
    generate(REPO / "scripts" / BUILDER, generated)

    filename, export_name = CREATE
    source = json.loads((generated / filename).read_text())

    existing = request("GET", f"{base}/api/v1/workflows?limit=250", args.api_key)
    before_total = len(existing.get("data", []))
    matches = [w for w in existing.get("data", []) if w.get("name") == source["name"]]
    entry: dict[str, Any] = {
        "action": "create", "file": filename, "name": source["name"],
        "already_present": [w["id"] for w in matches],
        "webhook_paths_planned": webhook_paths(source),
    }

    if matches:
        # Idempotent re-run: update in place rather than growing a duplicate.
        workflow_id = matches[0]["id"]
        live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        entry["action"] = "update-existing"
        entry["id"] = workflow_id
        entry["changed"] = comparable(live) != comparable(source)
        entry["active_before"] = bool(live.get("active"))
        if args.apply and entry["changed"]:
            request("PUT", f"{base}/api/v1/workflows/{workflow_id}", args.api_key, {
                "name": source["name"], "nodes": source["nodes"],
                "connections": source["connections"],
                "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
                "staticData": live.get("staticData")})
            updated = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
            if bool(updated.get("active")) != entry["active_before"]:
                raise SystemExit("activation state changed during PUT")
            if comparable(updated) != comparable(source):
                raise SystemExit("live graph differs after PUT")
            entry["updatedAt_after"] = updated.get("updatedAt")
            entry["webhook_paths"] = webhook_paths(updated)
            (WORKFLOW_DIR / export_name).write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            entry["export_refreshed"] = export_name
    elif args.apply:
        # Created inactive first: a half-imported route must never answer.
        created = request("POST", f"{base}/api/v1/workflows", args.api_key, {
            "name": source["name"], "nodes": source["nodes"],
            "connections": source["connections"], "settings": source["settings"]})
        workflow_id = created["id"]
        fetched = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if comparable(fetched) != comparable(source):
            raise SystemExit("created graph differs from the generated source; left INACTIVE")
        if bool(fetched.get("active")):
            raise SystemExit("new workflow was created active; expected inactive")
        request("POST", f"{base}/api/v1/workflows/{workflow_id}/activate", args.api_key)
        activated = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        if not bool(activated.get("active")):
            raise SystemExit("new workflow did not activate")
        if comparable(activated) != comparable(source):
            raise SystemExit("live graph differs after activation")
        entry.update({"id": workflow_id, "created": True, "active_after": True,
                      "updatedAt_after": activated.get("updatedAt"),
                      "webhook_paths": webhook_paths(activated)})
        (WORKFLOW_DIR / export_name).write_text(
            json.dumps(activated, ensure_ascii=False, indent=2) + "\n")
        entry["export_refreshed"] = export_name

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    total = request("GET", f"{base}/api/v1/workflows?limit=250", args.api_key)
    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "migration_018_present": True,
        "generated_files_unchanged": len(unchanged),
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "auth_guard_active": guard_after.get("active"),
        "workflow_total_before": before_total,
        "workflow_total_after": len(total.get("data", [])),
        "active_total_after": sum(1 for w in total.get("data", []) if w.get("active")),
        "workflow": entry,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

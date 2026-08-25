#!/usr/bin/env python3
"""Deploy the TERMINATED_EMPLOYEES workflow changes to LIVE (D-0825-7).

Same contract as deploy_employees_period_meta.py, extended with one thing that
script never had to do: CREATE a workflow that does not exist yet.

  - refuses to run if EPE: Auth Guard moved from its frozen updatedAt, and
    re-checks it after every write (the guard itself is never written)
  - every PUT preserves the activation state
  - the live graph is re-read and compared node-for-node after each write
  - the new workflow is created inactive, its graph verified, and only then
    activated — so a half-imported route can never answer a request
  - refuses to run at all unless migration 015 is already on live: the routes
    read users.terminated_at, and deploying them first would 500 every call

Source of truth is the generator, never a tracked top-level export.

Five workflows change:
  API: Auth Login (No Params)    a terminated employee cannot mint a session
  API: Register                  the shared invite cannot let them back in
  API: Request Password Reset    no reset link for a terminated employee
  API: Admin Get Users Data      the two new columns + no terminated manager
  API: Manage Periods            a new period never re-scopes them in

One is new:
  API: Manage Employment Status  terminate / reinstate / read the event log
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

# generated file -> (live workflow id, builder, tracked export name)
UPDATES: list[tuple[str, str, str, str]] = [
    ("login.json", "A4Ah3w21JEqHvQFR", "build_auth_workflows.py",
     "API_ Auth Login (No Params).json"),
    ("register.json", "wkDxU72Kg8fOiZCB", "build_auth_workflows.py",
     "API_ Register.json"),
    ("request-password-reset.json", "iEwAjOozioSOXC4T", "build_auth_workflows.py",
     "API_ Request Password Reset.json"),
    ("admin-users-data.json", "AwID96McjHKyk8WI", "build_route_guard_workflows.py",
     "API_ Admin Get Users Data.json"),
    ("manage-periods.json", "M9ljMDdO1mIl8m1h", "build_route_guard_workflows.py",
     "API_ Manage Periods.json"),
]
CREATE = ("manage-employment.json", "build_route_guard_workflows.py",
          "API_ Manage Employment Status.json")


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
    sources = [REPO / "scripts" / name for name in
               ("build_route_guard_deferred.py", "build_route_guard_workflows.py",
                "build_auth_workflows.py")]
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


def generate(builder: str) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-termination-"))
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

    # The routes read columns migration 015 adds. Deploying them against a
    # database without those columns would make every call 500.
    columns = live_sql(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema='performance_db' AND table_name='users' "
        "AND column_name IN ('terminated_at','termination_date')")
    events = live_sql(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='performance_db' AND table_name='employment_events'")
    if columns != "2" or events != "1":
        raise SystemExit(
            f"Refusing to deploy: migration 015 is not on live "
            f"(users termination columns={columns}/2, employment_events={events}/1)")

    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    generated: dict[str, Path] = {}
    for builder in {b for _, _, b, _ in UPDATES} | {CREATE[1]}:
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
            entry.update({
                "active_after": bool(updated.get("active")),
                "updatedAt_after": updated.get("updatedAt"),
                "webhook_paths": webhook_paths(updated),
            })
            assert_not_a_generator_input(export_name)
            (WORKFLOW_DIR / export_name).write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            entry["export_refreshed"] = export_name
            guard = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
            if guard.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
                raise SystemExit("EPE Auth Guard changed during deployment")
        report.append(entry)

    # ── the new workflow ────────────────────────────────────────────────────
    filename, builder, export_name = CREATE
    source = json.loads((generated[builder] / filename).read_text())
    existing = request("GET", f"{base}/api/v1/workflows?limit=250", args.api_key)
    matches = [w for w in existing.get("data", []) if w.get("name") == source["name"]]
    entry = {"action": "create", "file": filename, "name": source["name"],
             "already_present": [w["id"] for w in matches]}
    if matches:
        # Idempotent re-run: update in place rather than growing a duplicate.
        workflow_id = matches[0]["id"]
        live = request("GET", f"{base}/api/v1/workflows/{workflow_id}", args.api_key)
        entry["action"] = "update-existing"
        entry["id"] = workflow_id
        entry["changed"] = comparable(live) != comparable(source)
        if args.apply and entry["changed"]:
            request("PUT", f"{base}/api/v1/workflows/{workflow_id}", args.api_key, {
                "name": source["name"], "nodes": source["nodes"],
                "connections": source["connections"],
                "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
                "staticData": live.get("staticData")})
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
        entry.update({"id": workflow_id, "created": True,
                      "active_after": True,
                      "updatedAt_after": activated.get("updatedAt"),
                      "webhook_paths": webhook_paths(activated)})
        assert_not_a_generator_input(export_name)
        (WORKFLOW_DIR / export_name).write_text(
            json.dumps(activated, ensure_ascii=False, indent=2) + "\n")
        entry["export_refreshed"] = export_name
    report.append(entry)

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    total = request("GET", f"{base}/api/v1/workflows?limit=250", args.api_key)
    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "migration_015_present": True,
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "auth_guard_active": guard_after.get("active"),
        "workflow_total": len(total.get("data", [])),
        "active_total": sum(1 for w in total.get("data", []) if w.get("active")),
        "workflows": report,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

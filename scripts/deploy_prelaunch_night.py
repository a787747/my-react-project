#!/usr/bin/env python3
"""Deploy the PRELAUNCH_BATCH_NIGHT workflow changes to LIVE (2026-08-25/26).

Five existing routes change. Unlike the previous brief, this one is NOT
additive, so every safety rail matters:

  * `API: Manage Periods` — a NULL hire date now sends a person OUT of scope at
    period creation, with reason `join_date_missing` (D-0825-12), and the close
    dataset gains the `managers_only` applicability dimension.
  * `API: evaluations-matrix` — the same `managers_only` dimension, in lockstep
    with the close. Proven money-neutral on two stands closed side by side:
    824 frozen money cells, zero moved.
  * `API: Get Employees (Smart Role Based)` — carries the actor's exclusion
    reason and a SEPARATE array of employed-but-out-of-scope direct reports.
    The task list (`data`) is untouched by construction.
  * `API: Admin Get Users Data` — LEFT JOINs the active period's participants
    row so /admin/users can show the person's state in the period.
  * `API: Manage Period Scope` — `include-participant` also reverses
    `join_date_missing`, so the new reason is not a state with no exit.

Refusals, before anything is written:
  * `EPE: Auth Guard` must still carry its frozen updatedAt (and is re-checked
    after every PUT; it is never written);
  * the second gate must still be unpressed on every period;
  * every target must already exist on live under exactly the expected name —
    this build creates nothing.

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

# generated file -> (live workflow id, builder, tracked export name)
UPDATES: list[tuple[str, str, str, str]] = [
    ("manage-periods.json", "M9ljMDdO1mIl8m1h",
     "build_route_guard_workflows.py", "API_ Manage Periods.json"),
    ("admin-users-data.json", "AwID96McjHKyk8WI",
     "build_route_guard_workflows.py", "API_ Admin Get Users Data.json"),
    ("manage-period-scope.json", "8xK4EnDJrH1b1OJ7",
     "build_route_guard_workflows.py", "API_ Manage Period Scope.json"),
    ("evaluations-matrix.json", "yQNNr0i4UBFNVgMv",
     "build_route_guard_deferred.py", "API_ evaluations-matrix.json"),
    ("protected-employees.json", "bKB4Sb46yWoq1tSV",
     "build_auth_workflows.py", "API_ Get Employees (Smart Role Based).json"),
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
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-prelaunch-night-"))
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

    # This build CREATES nothing: every target must already be on live. The
    # assertion is what makes a future addition say so in the diff.
    if CREATE is not None:
        raise SystemExit(
            "Refusing to deploy: PRELAUNCH_BATCH_NIGHT creates no workflow, "
            "but CREATE is set.")

    # `include-participant` now also reverses `join_date_missing`, and the
    # period-scope routes write the table migration 016 adds.
    events = live_sql(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='performance_db' AND table_name='period_scope_events'")
    if events != "1":
        raise SystemExit(
            f"Refusing to deploy: migration 016 is not on live "
            f"(period_scope_events={events}/1)")
    # The second gate must still be unpressed: this session may not press it and
    # must not run against a database where somebody else did.
    started = live_sql(
        "SELECT count(*) FROM performance_db.evaluation_periods "
        "WHERE evaluation_started_at IS NOT NULL")
    if started != "0":
        raise SystemExit(
            f"Refusing to deploy: {started} period(s) already started. This brief "
            f"runs before the second gate.")

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

    print(json.dumps({"applied": args.apply, "updates": report}, ensure_ascii=False, indent=2))
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

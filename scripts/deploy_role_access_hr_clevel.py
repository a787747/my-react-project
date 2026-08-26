#!/usr/bin/env python3
"""Deploy ROLE_ACCESS_HR_CLEVEL to LIVE (2026-08-26) — RUN FROM THE MAC.

Four workflows change, all in who-may-read / who-is-refused only:

  API: Admin Get Users Data   — guard admin → admin+hr+c_level; the merge
                                strips options.grades[].coefficient for hr.
  API: Get Score Coefficients — GET guard admin → admin+c_level (the POST
                                save route is a different workflow, untouched).
  API: Manage Criteria Admin V7 — guard admin → admin+c_level; save/delete
                                refuse every non-admin 403 ROLE_FORBIDDEN
                                before the freeze check and before any SQL.
  API: Score Correction       — guard drops c_level (admin+manager with
                                can_evaluate); Decide Level's c_level branch
                                removed. Owner's brief: C-level is a reader.

THE CAMPAIGN IS OPEN. Unlike the pre-launch deploy scripts this one does NOT
require empty data tables or an unpressed gate — it requires instead that the
campaign is UNTOUCHED by the deploy: evaluation_started_at, the four table
counts, users/terminated/in-scope and the coefficient fingerprints are read
before and re-read after, and any difference the PUTs cannot legitimately
cause is a hard failure. The PUTs write workflow definitions only; no epe_2026
row is written by this script.

Before running with --apply, per the brief:
  1. fresh pg_dump pair copied to the Mac OUTSIDE the repo, md5 both sides;
  2. the change proven on a throwaway stand restored from that dump
     (scripts/prove_role_access.py against the stand, gate pressed there);
  3. python3 scripts/check_live_drift.py --expect-changed \
       "API: Admin Get Users Data,API: Get Score Coefficients,API: Manage Criteria Admin V7,API: Score Correction"
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

# The before/after coefficient fingerprints below prove only that THIS deploy
# moved nothing; the comparison against the versioned snapshot
# (docs/coefficients/H1-2026_coefficients_20260826T044844Z.md) is a separate
# read with the snapshot's own SQL, per its header.

UPDATES: list[tuple[str, str, str, str]] = [
    ("admin-users-data.json", "AwID96McjHKyk8WI",
     "build_route_guard_workflows.py", "API_ Admin Get Users Data.json"),
    ("score-coefficients.json", "zq3dufVhcnjkS7RV",
     "build_route_guard_workflows.py", "API_ Get Score Coefficients.json"),
    ("manage-criteria.json", "55BHbXWIS6igHHBT",
     "build_route_guard_deferred.py", "API_ Manage Criteria Admin V7.json"),
    ("score-correction.json", "rSZcm0HDMUHLYk8W",
     "build_route_guard_deferred.py", "API_ Score Correction.json"),
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
    directory = Path(tempfile.mkdtemp(prefix="epe-deploy-roleaccess-"))
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
    """Everything the deploy must not move, in one read."""
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
                f"The PUTs cannot cause this — investigate before anything else.")
    counts_moved = before["tables"] != after["tables"]

    print(json.dumps({
        "applied": args.apply,
        "updates": report,
        "campaign_before": before,
        "campaign_after": after,
        "table_counts_moved": counts_moved,
    }, ensure_ascii=False, indent=2))
    if counts_moved:
        print(
            "\nNOTE: evaluation table counts moved during the deploy window. The PUTs "
            "write workflow definitions only, so this is employee activity in the open "
            "campaign — record both figures in the report and re-run the read-only "
            "verification.", file=sys.stderr)
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

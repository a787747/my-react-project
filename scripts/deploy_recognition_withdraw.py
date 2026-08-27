#!/usr/bin/env python3
"""Deploy the recognition withdraw route to LIVE — RUN FROM THE MAC.

Updates exactly one workflow: API: Peer Recognition (KLDk6WmWZKsZ8GVX).
Adds POST api/recognition/withdraw. The other 19 generated files must be
byte-identical to what HEAD's builder produced; a single difference
refuses the deploy.

THE CAMPAIGN IS OPEN. No epe_2026 row is written. evaluation_started_at,
users/terminated/in-scope and the coefficient fingerprints must not move.
Table counts are read before and after; a move is employee activity.

  python3 scripts/deploy_recognition_withdraw.py           # dry-run
  python3 scripts/deploy_recognition_withdraw.py --apply   # write
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
WORKFLOW_ID = "KLDk6WmWZKsZ8GVX"
SOURCE_FILE = "peer-recognition.json"
EXPORT_NAME = "API_ Peer Recognition.json"
EXPECTED_PATHS = [
    "GET api/recognition/form",
    "GET api/recognition/list",
    "POST api/recognition/save",
    "POST api/recognition/withdraw",
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


def generate(builder_path: Path, directory: Path) -> None:
    subprocess.run(
        [sys.executable, str(builder_path),
         "--postgres-credential-id", POSTGRES_CREDENTIAL_ID,
         "--guard-workflow-id", AUTH_GUARD_ID,
         "--output-directory", str(directory)],
        check=True, capture_output=True, cwd=REPO)


def assert_only_recognition_changed() -> None:
    staging = Path(tempfile.mkdtemp(prefix="epe-withdraw-drift-"))
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
    if added or removed or changed != [SOURCE_FILE]:
        raise SystemExit(
            "Refusing to deploy: the generated surface moved more than "
            f"{SOURCE_FILE}. added={added} removed={removed} changed={changed}")


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
            "SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM ("
            " SELECT concat_ws('|', id, title, target_audience, weight, c_level_only,"
            " selfassesment, for_manager, is_active) AS t"
            " FROM performance_db.criteria WHERE is_active = true) x"),
        "coeff_levels": live_sql(
            "SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM ("
            " SELECT concat_ws('|', criteria_id, score_level, coefficient) AS t"
            " FROM performance_db.score_coefficients) x"),
        "coeff_grades": live_sql(
            "SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM ("
            " SELECT concat_ws('|', id, code, coefficient, coalesce(description,'')) AS t"
            " FROM performance_db.grades) x"),
        "peer_recognitions": live_sql(
            "SELECT count(*) FROM performance_db.peer_recognitions"),
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
        raise SystemExit("H1 evaluation_started_at is NULL — refusing")

    assert_only_recognition_changed()

    guard_before = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_before.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("Refusing deployment: EPE Auth Guard updatedAt does not match the frozen value")

    generated = Path(tempfile.mkdtemp(prefix="epe-deploy-withdraw-"))
    generate(REPO / "scripts" / BUILDER, generated)
    source = json.loads((generated / SOURCE_FILE).read_text())
    if webhook_paths(source) != EXPECTED_PATHS:
        raise SystemExit(f"generated webhook paths {webhook_paths(source)} != {EXPECTED_PATHS}")

    live = request("GET", f"{base}/api/v1/workflows/{WORKFLOW_ID}", args.api_key)
    if live.get("name") != source.get("name"):
        raise SystemExit(f"live name {live.get('name')!r} != {source.get('name')!r}")
    if not live.get("active"):
        raise SystemExit("API: Peer Recognition is not active on live — wrong target?")

    entry: dict[str, Any] = {
        "action": "update", "file": SOURCE_FILE, "id": WORKFLOW_ID,
        "name": live.get("name"),
        "changed": comparable(live) != comparable(source),
        "active_before": bool(live.get("active")),
        "updatedAt_before": live.get("updatedAt"),
        "webhook_paths_before": webhook_paths(live),
        "webhook_paths_planned": webhook_paths(source),
    }

    if args.apply and entry["changed"]:
        request("PUT", f"{base}/api/v1/workflows/{WORKFLOW_ID}", args.api_key, {
            "name": source["name"],
            "nodes": source["nodes"],
            "connections": source["connections"],
            "settings": {**(live.get("settings") or {}), **(source.get("settings") or {})},
            "staticData": live.get("staticData"),
        })
        updated = request("GET", f"{base}/api/v1/workflows/{WORKFLOW_ID}", args.api_key)
        if bool(updated.get("active")) != entry["active_before"]:
            raise SystemExit("activation state changed during PUT")
        if comparable(updated) != comparable(source):
            raise SystemExit("live graph differs after PUT")
        if webhook_paths(updated) != EXPECTED_PATHS:
            raise SystemExit(f"live webhook paths {webhook_paths(updated)} != {EXPECTED_PATHS}")
        entry.update({
            "active_after": bool(updated.get("active")),
            "updatedAt_after": updated.get("updatedAt"),
            "webhook_paths": webhook_paths(updated),
        })
        (WORKFLOW_DIR / EXPORT_NAME).write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        entry["export_refreshed"] = EXPORT_NAME
    elif args.apply and not entry["changed"]:
        entry["note"] = "generated graph already matches live — no PUT"

    guard_after = request("GET", f"{base}/api/v1/workflows/{AUTH_GUARD_ID}", args.api_key)
    if guard_after.get("updatedAt") != AUTH_GUARD_UPDATED_AT:
        raise SystemExit("EPE Auth Guard changed during deployment")

    after = campaign_snapshot()
    hard = ["started", "coeff_criteria", "coeff_levels", "coeff_grades", "population"]
    for key in hard:
        if before[key] != after[key]:
            raise SystemExit(
                f"CAMPAIGN INVARIANT MOVED during deploy: {key!r}\n"
                f"  before: {before[key]}\n  after:  {after[key]}")

    print(json.dumps({
        "applied": args.apply,
        "workflow": entry,
        "auth_guard_updatedAt": guard_after.get("updatedAt"),
        "campaign_before": before,
        "campaign_after": after,
        "table_counts_moved": before["tables"] != after["tables"],
        "peer_recognitions_moved": before["peer_recognitions"] != after["peer_recognitions"],
    }, ensure_ascii=False, indent=2))
    if not args.apply:
        print("\nread-only: re-run with --apply to write", file=sys.stderr)


if __name__ == "__main__":
    main()

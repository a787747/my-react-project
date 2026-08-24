#!/usr/bin/env python3
"""Zero-drift check: compare EVERY generator output against the live
workflow_entity definitions (read by SQL through the SSH tunnel host — no n8n
API key needed). Prints per-workflow identical/different so a deploy carries
only the intended delta.

Usage: python3 scripts/check_live_drift.py [--expect-changed name1,name2]
Exit 1 if the changed set differs from --expect-changed (default: empty).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOST = "root@92.51.45.147"
REPO = Path(__file__).resolve().parent.parent
CRED = "VNbfkY8IKbEzn88B"
GUARD = "L0Zr7nVa8O5YWXd3"

BUILDERS = {
    "h1": "build_route_guard_workflows.py",
    "def": "build_route_guard_deferred.py",
    "auth": "build_auth_workflows.py",
}


def generate() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, script in BUILDERS.items():
        directory = Path(tempfile.mkdtemp(prefix=f"epe-drift-{key}-"))
        subprocess.run(
            [sys.executable, str(REPO / "scripts" / script),
             "--postgres-credential-id", CRED,
             "--guard-workflow-id", GUARD,
             "--output-directory", str(directory)],
            check=True, capture_output=True, cwd=REPO)
        for f in sorted(directory.glob("*.json")):
            wf = json.loads(f.read_text())
            out[wf["name"]] = wf
    return out


def live_definitions() -> dict[str, dict]:
    statement = """
      SELECT COALESCE(json_agg(json_build_object(
        'name', w.name, 'id', w.id, 'active', w.active,
        'updatedAt', to_char(w."updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
        'nodes', w.nodes, 'connections', w.connections)), '[]'::json)
      FROM public.workflow_entity w
      WHERE w."isArchived" = false
    """
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
         "docker exec -i postgres_n8n psql -U admin -d postgres -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    rows = json.loads(result.stdout.decode())
    return {r["name"]: r for r in rows}


def canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-changed", default="",
                        help="comma-separated live workflow names allowed to differ")
    args = parser.parse_args()
    expected_changed = {n.strip() for n in args.expect_changed.split(",") if n.strip()}

    generated = generate()
    live = live_definitions()

    changed: list[str] = []
    identical: list[str] = []
    absent: list[str] = []
    for name, wf in sorted(generated.items()):
        if name == "EPE: Auth Guard":
            continue  # frozen; checked by updatedAt in every deploy script
        row = live.get(name)
        if row is None:
            absent.append(name)
            continue
        same = (canon(wf.get("nodes")) == canon(row.get("nodes"))
                and canon(wf.get("connections")) == canon(row.get("connections")))
        (identical if same else changed).append(name)

    print(json.dumps({
        "identical_count": len(identical),
        "changed": changed,
        "absent_from_live": absent,
        "expected_changed": sorted(expected_changed),
    }, indent=2, ensure_ascii=False))

    # A generator output with no live counterpart is not drift (nothing to
    # diff) but it is not silently OK either: either the workflow should be
    # imported, or the builder should stop producing it. Warn by name so the
    # gap is visible in every deploy log; whether the two long-standing absentees
    # should exist on live is an open decision (BROWSER_WALKTHROUGH §9.4).
    for name in absent:
        print(f"WARNING: generator output absent from live: {name}", file=sys.stderr)

    if set(changed) != expected_changed:
        print("DRIFT MISMATCH", file=sys.stderr)
        raise SystemExit(1)
    if absent:
        print(f"drift check OK ({len(absent)} generator output(s) absent from live — see warnings)")
    else:
        print("drift check OK")


if __name__ == "__main__":
    main()

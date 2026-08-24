#!/usr/bin/env python3
"""Stand proof for EMPLOYEES_PERIOD_META (2026-08-24): GET /api/employees
carries period_name / period_start_date / period_end_date for the current
period, and NOTHING else in the payload changes.

Runs entirely against the throwaway stand (epe-empmeta-n8n on VPS loopback
:25679, DB epe_empmeta_*). Live is never touched.

Method — compared values, not slogans:
  * Phase OLD: the pre-brief workflow definition (generated from the builder
    at HEAD, passed via --old-workflow) is imported and made the active
    api/employees handler. The three fixture actors (employee 1303, manager
    1302, out-of-scope 1311) GET the payload in three period states:
    draft -> activated-not-started (real POST api/periods/activate) ->
    started (real POST api/periods/start-evaluation). Full JSON recorded.
  * Phase NEW: H1 is rewound to draft by SQL (the documented emergency-stop
    technique, stand-only), the new definition is re-activated, and the same
    3 states x 3 actors are captured.
  * Diff: for every (state, actor) cell the NEW body minus exactly
    {period_name, period_start_date, period_end_date} must deep-equal the
    OLD body; the three values are asserted per state (null / H1-2026 +
    2026-01-01 + 2026-06-30).

The active definition is verified node-for-node (n8n export) before each
phase — `n8n import:workflow` assigns new ids and a stand accumulates
duplicates, so trusting the name would prove nothing.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
EMPLOYEES_WF_NAME = "API: Get Employees (Smart Role Based)"

ACTORS = {
    "employee": (1303, "55555555-5555-4555-8555-555555555503"),
    "manager": (1302, "55555555-5555-4555-8555-555555555502"),
    "out_of_scope": (1311, "55555555-5555-4555-8555-555555555511"),
}
ADMIN = (1301, "55555555-5555-4555-8555-555555555501")

META_KEYS = {"period_name", "period_start_date", "period_end_date"}

FAILURES: list[str] = []


def check(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


def ssh(command: str, stdin: bytes | None = None) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST, command],
        input=stdin, capture_output=True)
    if result.returncode:
        raise SystemExit(
            f"ssh failed: {command}\n"
            + (result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode()


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 7200, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


class Stand:
    def __init__(self, container: str, db: str, base_url: str):
        self.container = container
        self.db = db
        self.base_url = base_url.rstrip("/")

    def sql(self, statement: str) -> str:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", HOST,
             f"docker exec -i postgres_n8n psql -U admin -d {self.db} -v ON_ERROR_STOP=1 -tA"],
            input=statement.encode(), capture_output=True)
        if result.returncode:
            raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
        return result.stdout.decode().strip()

    def cli(self, args: str) -> str:
        return ssh(f"docker exec -u node {self.container} n8n {args}")

    def restart_and_wait(self) -> None:
        ssh(f"docker restart {self.container}")
        for _ in range(45):
            time.sleep(2)
            code = ssh("curl -s -o /dev/null -w '%{http_code}' "
                       "http://127.0.0.1:25679/healthz").strip()
            if code == "200":
                return
        raise SystemExit("stand did not become healthy after restart")

    def list_workflow_ids(self, name: str) -> list[str]:
        rows = self.cli("list:workflow")
        return [line.split("|", 1)[0] for line in rows.splitlines()
                if line.split("|", 1)[-1] == name]

    def export_workflow(self, wf_id: str) -> dict[str, Any]:
        self.cli(f"export:workflow --id={wf_id} --output=/tmp/wf_export_{wf_id}.json")
        raw = ssh(f"docker exec {self.container} cat /tmp/wf_export_{wf_id}.json")
        data = json.loads(raw)
        return data[0] if isinstance(data, list) else data

    def set_active(self, wf_id: str, active: bool) -> None:
        self.cli(f"update:workflow --id={wf_id} --active={'true' if active else 'false'}")

    def call(self, method: str, path: str, token: str,
             body: dict[str, Any] | None = None) -> tuple[int, Any]:
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, raw.decode("utf-8", "replace")


def code_of(wf: dict[str, Any], node_name: str) -> str:
    for node in wf.get("nodes") or []:
        if node.get("name") == node_name:
            return node.get("parameters", {}).get("jsCode", "")
    raise SystemExit(f"node {node_name!r} not found in workflow {wf.get('name')!r}")


def assert_definition(stand: Stand, wf_id: str, expected_file: Path, label: str) -> None:
    exported = stand.export_workflow(wf_id)
    expected = json.loads(expected_file.read_text())
    check(f"{label}: node count",
          len(exported.get("nodes") or []), len(expected.get("nodes") or []))
    for node_name in ("Build Identity-Bound Query", "Format Response", "Prepare Guard Input"):
        check(f"{label}: jsCode of {node_name!r} matches the generated file",
              code_of(exported, node_name) == code_of(expected, node_name), True)


def rewind_to_draft(stand: Stand) -> None:
    stand.sql("""
      UPDATE performance_db.evaluation_periods
      SET status = 'draft', is_active = false,
          evaluation_started_at = NULL, evaluation_started_by = NULL
      WHERE id = 2""")


def h1_state(stand: Stand) -> str:
    return stand.sql("""
      SELECT status || '|' || is_active || '|' || COALESCE(evaluation_started_at::text, 'null')
      FROM performance_db.evaluation_periods WHERE id = 2""")


def capture_state(stand: Stand, secret: str, phase: str, state: str,
                  results: dict[str, Any]) -> None:
    cell: dict[str, Any] = {"h1_row": h1_state(stand)}
    for actor, (uid, jti) in ACTORS.items():
        status, body = stand.call("GET", "api/employees", mint(secret, uid, jti))
        check(f"{phase}/{state}/{actor}: HTTP 200", status, 200)
        cell[actor] = {"status": status, "body": body}
    results.setdefault(phase, {})[state] = cell


def run_phase(stand: Stand, secret: str, phase: str, results: dict[str, Any]) -> None:
    admin_token = mint(secret, *ADMIN)

    rewind_to_draft(stand)
    capture_state(stand, secret, phase, "draft", results)

    status, body = stand.call("POST", "api/periods/activate", admin_token, {"period_id": 2})
    check(f"{phase}: activate 200", status, 200)
    capture_state(stand, secret, phase, "preparation", results)

    status, body = stand.call("POST", "api/periods/start-evaluation", admin_token,
                              {"period_id": 2})
    check(f"{phase}: start-evaluation 200", status, 200)
    capture_state(stand, secret, phase, "started", results)

    rewind_to_draft(stand)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True,
                        help="throwaway_env.json written by setup_empmeta_throwaway.sh")
    parser.add_argument("--old-workflow", type=Path, required=True,
                        help="pre-brief protected-employees.json (real ids)")
    parser.add_argument("--new-workflow", type=Path, required=True,
                        help="post-brief protected-employees.json (real ids)")
    parser.add_argument("--base-url", default="http://127.0.0.1:25679/webhook",
                        help="stand webhook base through the local SSH tunnel")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    env = json.loads(args.env_file.read_text())
    stand = Stand(env["container"], env["database"], args.base_url)
    secret = env["jwt_secret"]

    old_js = args.old_workflow.read_text()
    new_js = args.new_workflow.read_text()
    if "period_name" in old_js:
        raise SystemExit("--old-workflow already carries period_name — wrong file")
    if "period_start_date" not in new_js:
        raise SystemExit("--new-workflow lacks period_start_date — wrong file")

    report: dict[str, Any] = {
        "database": env["database"],
        "container": env["container"],
        "h1_fixture": stand.sql("""
          SELECT name || '|' || to_char(start_date, 'YYYY-MM-DD') || '|' ||
                 to_char(end_date, 'YYYY-MM-DD')
          FROM performance_db.evaluation_periods WHERE id = 2"""),
    }
    check("stand H1 row is H1-2026 / 2026-01-01 / 2026-06-30",
          report["h1_fixture"], "H1-2026|2026-01-01|2026-06-30")

    # Identify versions by DEFINITION, not by name or import order — a stand
    # accumulates same-named duplicates on re-runs (`n8n import:workflow`
    # always assigns a new id).
    new_id: str | None = None
    old_id: str | None = None
    for wf_id in stand.list_workflow_ids(EMPLOYEES_WF_NAME):
        js = code_of(stand.export_workflow(wf_id), "Build Identity-Bound Query")
        if "period_name" in js:
            if new_id is not None:
                raise SystemExit(f"two NEW-shaped employees workflows on the stand: {new_id}, {wf_id}")
            new_id = wf_id
        else:
            if old_id is not None:
                raise SystemExit(f"two OLD-shaped employees workflows on the stand: {old_id}, {wf_id}")
            old_id = wf_id
    if new_id is None:
        raise SystemExit("no NEW-shaped employees workflow on the stand")
    assert_definition(stand, new_id, args.new_workflow, "NEW definition (as imported by setup)")

    if old_id is None:
        # Import the OLD definition; the CLI assigns it a fresh id.
        prep = json.loads(old_js)
        prep["active"] = False
        prep["versionId"] = "00000000-0000-4000-8000-00000000e01d"
        ssh(f"docker exec {stand.container} rm -f /tmp/old_employees.json")
        ssh(f"docker exec -i -u node {stand.container} sh -c 'cat > /tmp/old_employees.json'",
            stdin=json.dumps([prep], ensure_ascii=False).encode())
        stand.cli("import:workflow --input=/tmp/old_employees.json")
        old_ids = [i for i in stand.list_workflow_ids(EMPLOYEES_WF_NAME) if i != new_id]
        if len(old_ids) != 1:
            raise SystemExit(f"expected exactly one imported OLD workflow, got {old_ids}")
        old_id = old_ids[0]
    assert_definition(stand, old_id, args.old_workflow, "OLD definition (imported)")
    report["workflow_ids"] = {"new": new_id, "old": old_id}

    results: dict[str, Any] = {}

    # Phase OLD: old definition answers api/employees.
    stand.set_active(new_id, False)
    stand.set_active(old_id, True)
    stand.restart_and_wait()
    assert_definition(stand, old_id, args.old_workflow, "OLD active before phase OLD")
    run_phase(stand, secret, "old", results)

    # Phase NEW: swap back.
    stand.set_active(old_id, False)
    stand.set_active(new_id, True)
    stand.restart_and_wait()
    assert_definition(stand, new_id, args.new_workflow, "NEW active before phase NEW")
    run_phase(stand, secret, "new", results)

    report["payloads"] = results

    # ── the diff: exactly the three keys, nothing else ──
    diffs: dict[str, Any] = {}
    for state in ("draft", "preparation", "started"):
        for actor in ACTORS:
            old_body = results["old"][state][actor]["body"]
            new_body = results["new"][state][actor]["body"]
            added = sorted(set(new_body) - set(old_body))
            removed = sorted(set(old_body) - set(new_body))
            stripped = {k: v for k, v in new_body.items() if k not in META_KEYS}
            diffs[f"{state}/{actor}"] = {
                "added_keys": added,
                "removed_keys": removed,
                "rest_identical": stripped == old_body,
                "meta": {k: new_body.get(k) for k in sorted(META_KEYS)},
            }
            check(f"{state}/{actor}: added keys are exactly the three meta keys",
                  added, sorted(META_KEYS))
            check(f"{state}/{actor}: no keys removed", removed, [])
            check(f"{state}/{actor}: payload minus the three keys is identical",
                  stripped == old_body, True)
    report["diffs"] = diffs

    # ── per-state values (compared, not asserted-by-slogan) ──
    for actor in ACTORS:
        d = results["new"]["draft"][actor]["body"]
        for key in sorted(META_KEYS):
            check(f"draft/{actor}: {key} is null", d.get(key), None)
        check(f"draft/{actor}: campaign_active", d.get("campaign_active"), False)
        check(f"draft/{actor}: period_in_preparation", d.get("period_in_preparation"), False)
        check(f"draft/{actor}: current_period_id", d.get("current_period_id"), None)

        p = results["new"]["preparation"][actor]["body"]
        check(f"preparation/{actor}: period_name", p.get("period_name"), "H1-2026")
        check(f"preparation/{actor}: period_start_date", p.get("period_start_date"), "2026-01-01")
        check(f"preparation/{actor}: period_end_date", p.get("period_end_date"), "2026-06-30")
        check(f"preparation/{actor}: campaign_active", p.get("campaign_active"), False)
        check(f"preparation/{actor}: period_in_preparation", p.get("period_in_preparation"), True)

        s = results["new"]["started"][actor]["body"]
        check(f"started/{actor}: period_name", s.get("period_name"), "H1-2026")
        check(f"started/{actor}: period_start_date", s.get("period_start_date"), "2026-01-01")
        check(f"started/{actor}: period_end_date", s.get("period_end_date"), "2026-06-30")
        check(f"started/{actor}: campaign_active", s.get("campaign_active"), True)
        check(f"started/{actor}: period_in_preparation", s.get("period_in_preparation"), False)

    check("preparation/out_of_scope: actor_is_in_scope false",
          results["new"]["preparation"]["out_of_scope"]["body"].get("actor_is_in_scope"), False)
    check("preparation/employee: actor_is_in_scope true",
          results["new"]["preparation"]["employee"]["body"].get("actor_is_in_scope"), True)
    started_manager_rows = sorted(
        row["id"] for row in results["new"]["started"]["manager"]["body"].get("data") or [])
    check("started/manager: data rows are the four in-scope directs (no 1311)",
          started_manager_rows, [1303, 1304, 1308, 1309])
    check("started/employee: data empty",
          results["new"]["started"]["employee"]["body"].get("data"), [])

    check("final H1 state back to draft", h1_state(stand), "draft|false|null")

    report["failures"] = FAILURES
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"report: {args.output}")
    if FAILURES:
        print(f"\nFAILURES ({len(FAILURES)}):")
        for failure in FAILURES:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("ALL STAND CHECKS PASSED")


if __name__ == "__main__":
    main()

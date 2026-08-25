#!/usr/bin/env python3
"""Logistics reports to Jafarova; Egamberdyev returns to project — on LIVE.

Brief ORG_FIX_LOGISTICS (2026-08-25), decisions D-0825-5 / D-0825-6.

Owner's instruction, applied and nothing else:
  * Jafarova (the sole «Jafarova» on live, id read at run time, not hard-coded
    by name) — job_title becomes exactly "Logistics Team Lead (Acting Head of
    Department)", role manager, manager Alexander Petrosov (id 2).
  * every other person in the Logistics department reports to her.
  * Kurbangeldyev (33) is a deliberate exception: he keeps the manager the
    owner set by hand today, even if he sits in that department.
  * Egamberdyev (74) returns to work_category='project'.

Writes only through POST /webhook/admin/save-user (API: Admin Save User (GUI
Mode)) — never raw SQL on `users`. That route is a FULL-ROW UPDATE with
dangerous defaults (`body.role || 'employee'`, `body.work_category ||
'general'`) and it lowercases/trims email and NULLs an empty job_title, so each
payload is the live row read fresh immediately before its own write with only
the intended field replaced, and every stored field is compared to what was
sent before the next call is made.

`has_subordinates` is deliberately NOT written: trg_update_has_subordinates
(AFTER INSERT OR DELETE OR UPDATE OF manager_id) owns it and recomputes it on
both the old and the new manager. The run asserts the trigger did its job.

The second gate («Запустить оценку») is never touched.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")


TLS = _tls_context()
HOST = "root@92.51.45.147"
SSH_ID = str(Path.home() / ".ssh/id_ed25519")
REPO = Path(__file__).resolve().parent.parent
PROOF_DIR = REPO / "backups/2026-08-25-logistics"
# The rollback anchor is pulled OUTSIDE the repository, per the brief.
ANCHOR_DIR = Path.home() / "EPE_ROLLBACK/2026-08-25-logistics"
VPS_TMP = "/root/epe_stand_tmp"
# The superseded PRELAUNCH_LIVE_CHECK anchor lives there and is left alone:
# it is history, not the restore point this brief hands to the smoke test.
ALLOWED_TMP = {"epe_2026_pregate_20260825T121617Z.dump"}

ADMIN_ID = 2
ADMIN_JTI = "caf10000-2026-0825-8000-000000000005"

LOGISTICS_DEPT = 4
PETROSOV = 2
KURBANGELDYEV = 33          # deliberate exception, never written
EGAMBERDYEV = 74
NEW_TITLE = "Logistics Team Lead (Acting Head of Department)"

# Columns the route's UPDATE actually SETs. Every one is resent on every call.
PAYLOAD_KEYS = ["id", "full_name", "email", "role", "job_title",
                "work_category", "department_id", "grade_id", "manager_id"]
# Columns the route must leave alone. Checked for all 89 users, before vs after.
FROZEN_COLUMNS = ["employment_type", "join_date", "salary_current",
                  "salary_proposed", "created_at", "password_hash",
                  "can_evaluate", "can_be_evaluated", "token_version"]

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
         "-i", SSH_ID, HOST, command], capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", SSH_ID, HOST,
         "docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint(secret: str, user_id: int, jti: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 3600, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())}"


def call(base: str, method: str, path: str, token: str, body=None):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120, context=TLS) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def check(name: str, actual: Any, expected: Any) -> bool:
    ok = actual == expected
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def all_users() -> dict[int, dict[str, Any]]:
    raw = live_sql("""
      SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM (
        SELECT id, full_name, email, role::text AS role, job_title, work_category,
               is_project_participant, department_id, grade_id, manager_id,
               has_subordinates, can_evaluate, can_be_evaluated, token_version,
               employment_type, join_date::text AS join_date,
               salary_current::text AS salary_current,
               salary_proposed::text AS salary_proposed,
               created_at::text AS created_at,
               (password_hash IS NOT NULL) AS password_hash
        FROM performance_db.users) u""")
    return {int(r["id"]): r for r in json.loads(raw)}


def scope() -> dict[int, bool]:
    raw = live_sql("""
      SELECT COALESCE(json_agg(json_build_object('u', user_id, 's', is_in_scope)), '[]')
      FROM performance_db.evaluation_period_participants WHERE period_id = 2""")
    return {int(r["u"]): bool(r["s"]) for r in json.loads(raw)}


def criteria_catalogue() -> list[dict[str, Any]]:
    raw = live_sql("""
      SELECT COALESCE(json_agg(row_to_json(c) ORDER BY c.id), '[]') FROM (
        SELECT id, title, target_audience, c_level_only, is_active,
               weight::float8 AS weight
        FROM performance_db.criteria) c""")
    return json.loads(raw)


def level_coefficients() -> dict[str, float]:
    raw = live_sql("""
      SELECT COALESCE(json_object_agg(criteria_id || ':' || score_level, coefficient::float8), '{}')
      FROM performance_db.score_coefficients""")
    return json.loads(raw)


def reports_of(users: dict[int, dict[str, Any]], uid: int) -> list[int]:
    return sorted(i for i, r in users.items() if r["manager_id"] == uid)


def payload_from_fresh(row: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    item = {key: row[key] for key in PAYLOAD_KEYS}
    item["id"] = int(item["id"])
    item.update(patch)
    return item


# ── derived facts, all computed from the live rules ─────────────────────────

def applicable_criteria(row: dict[str, Any], catalogue: list[dict[str, Any]]) -> list[int]:
    """The manager-path set, verbatim from live `API: Get Employees` SQL:
    is_active AND NOT c_level_only
    AND (target_audience <> 'project_participants' OR is_project_participant)
    AND (target_audience <> 'managers_only'       OR has_subordinates)."""
    out = []
    for c in catalogue:
        if not c["is_active"] or c["c_level_only"]:
            continue
        if c["target_audience"] == "project_participants" and not row["is_project_participant"]:
            continue
        if c["target_audience"] == "managers_only" and not row["has_subordinates"]:
            continue
        out.append(int(c["id"]))
    return out


def buckets(users: dict[int, dict[str, Any]], catalogue) -> dict[str, int]:
    out: dict[int, int] = {}
    for row in users.values():
        n = len(applicable_criteria(row, catalogue))
        out[n] = out.get(n, 0) + 1
    return {str(k): v for k, v in sorted(out.items())}


def category_split(users: dict[int, dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in users.values():
        out[row["work_category"]] = out.get(row["work_category"], 0) + 1
    return dict(sorted(out.items()))


def bonus_index(row, catalogue, coefficients, grade_coefficient, raw_score: float) -> float:
    """Formula #3 (HANDOVER §4): sum(score x level-coef x weight), NOT divided
    by the weight sum, times the grade coefficient."""
    total = 0.0
    level = max(0, min(10, round(raw_score)))
    for cid in applicable_criteria(row, catalogue):
        crit = next(c for c in catalogue if int(c["id"]) == cid)
        weight = float(crit["weight"]) or 1.0
        coef = coefficients.get(f"{cid}:{level}", 1.0)
        total += raw_score * coef * weight
    return total * grade_coefficient


def channels(users, in_scope, subject: int) -> dict[str, Any]:
    """Who evaluates `subject` and whom `subject` evaluates, per channel —
    from the live filters in API: Submit Evaluation / Submit Self Review."""
    row = users[subject]
    ok = lambda uid: in_scope.get(uid, False)
    manager_id = row["manager_id"]
    receives_manager = (manager_id if manager_id and row["can_be_evaluated"]
                        and ok(subject) and ok(manager_id) else None)
    upward_from = ([i for i in reports_of(users, subject)
                    if ok(i) and row["can_be_evaluated"]
                    and row["role"] not in ("c_level", "admin")]
                   if ok(subject) else [])
    # the live c_level_direct filter also excludes three subjects by email
    read_only_trio = ("cem@sedamedical.com", "hemra@sedamedical.com", "mekan@sedamedical.com")
    c_level_writers = ([i for i, r in users.items()
                        if r["role"] in ("c_level", "admin") and r["can_evaluate"]]
                       if row["can_be_evaluated"] and ok(subject)
                       and row["email"].lower() not in read_only_trio else [])
    gives_manager = [i for i in reports_of(users, subject)
                     if users[i]["can_be_evaluated"] and ok(i) and ok(subject)]
    gives_upward = (manager_id if manager_id and ok(subject) and ok(manager_id)
                    and users[manager_id]["can_be_evaluated"]
                    and users[manager_id]["role"] not in ("c_level", "admin") else None)
    return {
        "self_review": ok(subject) and row["role"] in ("employee", "manager", "hr"),
        "receives_from_manager": receives_manager,
        "receives_upward_from": sorted(upward_from),
        "receives_c_level_direct_from": sorted(c_level_writers),
        "gives_manager_evaluations_to": sorted(gives_manager),
        "gives_upward_evaluation_to": gives_upward,
        "mid_level_corrector": (users[manager_id]["manager_id"]
                                if manager_id and users.get(manager_id) else None),
    }


def org_invariants(users, in_scope) -> dict[str, Any]:
    manager_mismatch = [i for i, r in users.items()
                        if r["role"] not in ("admin", "c_level")
                        and (r["role"] == "manager") != bool(reports_of(users, i))]
    graph_drift = [i for i, r in users.items()
                   if bool(r["has_subordinates"]) != bool(reports_of(users, i))]
    no_evaluator = sorted(i for i, r in users.items()
                          if r["manager_id"] is None and r["role"] not in ("c_level", "admin"))
    cycles = []
    depth_max = 0
    for start in users:
        seen, node, depth = set(), start, 0
        while node is not None and node in users:
            if node in seen:
                cycles.append(start)
                break
            seen.add(node)
            node = users[node]["manager_id"]
            depth += 1
        depth_max = max(depth_max, depth)
    nobody_evaluates = sorted(
        i for i, r in users.items()
        if in_scope.get(i, False) and not r["can_be_evaluated"])
    no_upward = sorted(
        i for i, r in users.items()
        if in_scope.get(i, False) and r["can_be_evaluated"]
        and (r["manager_id"] is None
             or users[r["manager_id"]]["role"] in ("c_level", "admin")))
    return {
        "role_manager_iff_reports_exceptions": sorted(manager_mismatch),
        "has_subordinates_disagreements": sorted(graph_drift),
        "people_without_evaluator": no_evaluator,
        "cycles": sorted(set(cycles)),
        "max_chain_depth": depth_max,
        "managers": sorted(i for i, r in users.items() if r["role"] == "manager"),
        "in_scope_but_nobody_evaluates": nobody_evaluates,
        "evaluated_population": sum(1 for i, r in users.items()
                                    if in_scope.get(i, False) and r["can_be_evaluated"]),
        "in_scope_without_upward_channel": len(no_upward),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--output", type=Path, default=PROOF_DIR / "logistics_proof.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="run every gate and print the payloads, write nothing")
    args = parser.parse_args()
    REPORT["base_url"] = args.base_url
    REPORT["dry_run"] = bool(args.dry_run)

    # ── 0. gates ────────────────────────────────────────────────────────────
    period = json.loads(live_sql("""
      SELECT row_to_json(p) FROM (
        SELECT id, name, status, is_active, evaluation_started_at, evaluation_started_by
        FROM performance_db.evaluation_periods WHERE id = 2) p"""))
    REPORT["h1_before"] = period
    if not (period["status"] == "active" and period["is_active"] is True
            and period["evaluation_started_at"] is None):
        raise SystemExit(f"REFUSING: H1 is not active-and-not-started: {period}")

    counts = {t: int(live_sql(f"SELECT count(*) FROM performance_db.{t}"))
              for t in ("evaluations", "evaluation_scores", "score_corrections", "period_results")}
    REPORT["data_tables_before"] = counts
    if any(counts.values()):
        raise SystemExit(f"REFUSING: a data table is not empty: {counts}")

    leftover = [f for f in ssh(f"ls -1 {VPS_TMP} 2>/dev/null || true").splitlines()
                if f and f not in ALLOWED_TMP]
    REPORT["vps_tmp_unexpected"] = leftover
    if leftover:
        raise SystemExit(f"REFUSING: unexpected files in {VPS_TMP}: {leftover}")

    before = all_users()
    in_scope = scope()
    catalogue = criteria_catalogue()
    coefficients = level_coefficients()
    grades = json.loads(live_sql(
        "SELECT COALESCE(json_object_agg(id, coefficient::float8), '{}') FROM performance_db.grades"))
    check("89 users before", len(before), 89)

    # Identify Jafarova from live rather than trusting an id from the brief.
    candidates = sorted(i for i, r in before.items()
                        if "afarov" in r["full_name"].lower()
                        and r["department_id"] == LOGISTICS_DEPT)
    REPORT["jafarova_candidates"] = [
        {"id": i, "full_name": before[i]["full_name"], "job_title": before[i]["job_title"],
         "role": before[i]["role"], "manager_id": before[i]["manager_id"]} for i in candidates]
    if len(candidates) != 1:
        raise SystemExit(f"REFUSING: Jafarova is not uniquely identifiable on live: {candidates}")
    jafarova = candidates[0]

    dept_members = sorted(i for i, r in before.items() if r["department_id"] == LOGISTICS_DEPT)
    REPORT["logistics_department_before"] = [
        {"id": i, "full_name": before[i]["full_name"], "job_title": before[i]["job_title"],
         "role": before[i]["role"], "manager_id": before[i]["manager_id"],
         "in_scope": in_scope.get(i, False)} for i in dept_members]

    # The deliberate exception — recorded either way, never written.
    REPORT["kurbangeldyev_33"] = {
        "department_id": before[KURBANGELDYEV]["department_id"],
        "in_logistics_department": before[KURBANGELDYEV]["department_id"] == LOGISTICS_DEPT,
        "manager_id": before[KURBANGELDYEV]["manager_id"],
        "note": "owner's manual edit of 2026-08-25 is preserved; never written by this run",
    }
    if before[EGAMBERDYEV]["work_category"] != "general":
        raise SystemExit("REFUSING: premise broken — Egamberdyev (74) is not currently 'general': "
                         f"{before[EGAMBERDYEV]['work_category']!r}")

    # A resent payload must be a no-op for the fields we do not intend to move:
    # the route lowercases/trims email and NULLs an empty job_title.
    dirty = [i for i, r in before.items()
             if r["email"] != r["email"].strip().lower()
             or r["full_name"] != r["full_name"].strip()
             or not (r["job_title"] or "").strip()]
    REPORT["rows_a_resend_would_rewrite"] = sorted(dirty)

    drifted = [i for i, r in before.items() if bool(r["has_subordinates"]) != bool(reports_of(before, i))]
    if drifted:
        raise SystemExit(f"REFUSING: has_subordinates already disagrees with manager_id for {drifted}")

    # ── the change set, derived from live, not typed by hand ────────────────
    movers = [i for i in dept_members
              if i != jafarova and i != KURBANGELDYEV and before[i]["manager_id"] != jafarova]
    already = [i for i in dept_members
               if i not in (jafarova, KURBANGELDYEV) and before[i]["manager_id"] == jafarova]
    REPORT["logistics_moved"] = movers
    REPORT["logistics_already_reporting_to_jafarova"] = already

    changes: list[tuple[int, dict[str, Any]]] = [
        (jafarova, {"job_title": NEW_TITLE, "role": "manager", "manager_id": PETROSOV}),
    ]
    changes += [(uid, {"manager_id": jafarova}) for uid in movers]
    changes.append((EGAMBERDYEV, {"work_category": "project"}))
    REPORT["intended_changes"] = [
        {"user_id": uid, "full_name": before[uid]["full_name"], "patch": patch,
         "current": {k: before[uid][k] for k in patch}} for uid, patch in changes]

    if FAILURES:
        raise SystemExit("gate failures: " + "; ".join(FAILURES))

    # ── 1. dump first (AGENTS.md hard constraint 1) ─────────────────────────
    # A dry run takes no dump: it writes nothing, and a second file named like
    # an anchor is worse than no file at all.
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    dump_name = f"epe_2026_pregate_{stamp}.dump"
    vps_dump = f"{VPS_TMP}/{dump_name}"
    ANCHOR_DIR.mkdir(parents=True, exist_ok=True)
    local_dump = ANCHOR_DIR / dump_name
    ssh(f"install -d -m 700 {VPS_TMP}")
    if args.dry_run:
        for uid, patch in changes:
            print(f"WOULD POST admin/save-user "
                  f"{json.dumps(payload_from_fresh(before[uid], patch), ensure_ascii=False)}")
        REPORT["before"] = {
            "criteria_buckets": buckets(before, catalogue),
            "category_split": category_split(before),
            "invariants": org_invariants(before, in_scope),
            "jafarova_channels": channels(before, in_scope, jafarova),
            "jafarova_criteria": applicable_criteria(before[jafarova], catalogue),
            "egamberdyev_criteria": applicable_criteria(before[EGAMBERDYEV], catalogue),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY RUN — no dump, nothing written. Proof: {args.output}")
        return
    ssh(f"docker exec postgres_n8n pg_dump -U admin --no-owner --no-acl -Fc epe_2026 "
        f"> {vps_dump} && chmod 600 {vps_dump}")
    if ssh("ls -1 /tmp/epe_2026*.dump 2>/dev/null || true"):
        raise SystemExit("REFUSING: a dump landed in /tmp")
    vps_bytes = int(ssh(f"stat -c %s {vps_dump}"))
    if vps_bytes < 50_000:
        raise SystemExit(f"dump implausibly small on VPS: {vps_bytes} bytes")
    scp = subprocess.run(
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", SSH_ID,
         f"{HOST}:{vps_dump}", str(local_dump)], capture_output=True)
    if scp.returncode or not local_dump.is_file() or local_dump.stat().st_size != vps_bytes:
        raise SystemExit(f"scp of dump failed: rc={scp.returncode}")
    local_dump.chmod(0o600)
    vps_md5 = ssh(f"md5sum {vps_dump}").split()[0]
    local_md5 = hashlib.md5(local_dump.read_bytes()).hexdigest()
    if vps_md5 != local_md5:
        raise SystemExit(f"dump md5 mismatch: vps {vps_md5} local {local_md5}")
    REPORT["rollback_anchor"] = {
        "vps": vps_dump, "local": str(local_dump), "bytes": vps_bytes,
        "md5": local_md5, "stamp": stamp,
        "superseded": f"{VPS_TMP}/epe_2026_pregate_20260825T121617Z.dump",
    }
    print(f"anchor: {local_dump} ({vps_bytes} bytes, md5 {local_md5})")

    REPORT["before"] = {
        "criteria_buckets": buckets(before, catalogue),
        "category_split": category_split(before),
        "invariants": org_invariants(before, in_scope),
        "jafarova": {k: before[jafarova][k] for k in
                     ("full_name", "job_title", "role", "manager_id", "work_category",
                      "is_project_participant", "department_id", "grade_id", "has_subordinates")},
        "jafarova_reports": reports_of(before, jafarova),
        "jafarova_channels": channels(before, in_scope, jafarova),
        "jafarova_criteria": applicable_criteria(before[jafarova], catalogue),
        "petrosov_reports": reports_of(before, PETROSOV),
        "egamberdyev": {k: before[EGAMBERDYEV][k] for k in
                        ("full_name", "work_category", "is_project_participant",
                         "manager_id", "grade_id")},
        "egamberdyev_criteria": applicable_criteria(before[EGAMBERDYEV], catalogue),
    }

    # ── 2. probe session ────────────────────────────────────────────────────
    secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
    if not secret:
        raise SystemExit("could not read JWT_SIGNING_SECRET from the live container")
    sessions_before = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
    REPORT["auth_sessions_before"] = sessions_before
    version = int(live_sql(f"SELECT token_version FROM performance_db.users WHERE id = {ADMIN_ID}"))
    live_sql(f"""
      INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
      VALUES ('{ADMIN_JTI}', {ADMIN_ID}, {version}, now(), now() + interval '1 hour')
      ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
    token = mint(secret, ADMIN_ID, ADMIN_JTI)
    REPORT["probe_jti"] = ADMIN_JTI

    writes: list[dict[str, Any]] = []
    try:
        # ── 3. one save per user, row read fresh immediately before its write ─
        for uid, patch in changes:
            fresh = all_users()[uid]
            item = payload_from_fresh(fresh, patch)
            status, body = call(args.base_url, "POST", "admin/save-user", token, body=item)
            written_at = live_sql("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC',"
                                  "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
            rec = {"user_id": uid, "name": fresh["full_name"], "patch": patch,
                   "sent": item, "status": status, "body": body, "written_at_utc": written_at}
            writes.append(rec)
            if status != 200:
                REPORT["writes"] = writes
                raise SystemExit(f"ROUTE STOP: user {uid} returned {status} {body!r}. "
                                 f"No raw-SQL fallback. Anchor: {local_dump} / {vps_dump}")
            stored = all_users()[uid]
            for key in PAYLOAD_KEYS:
                if key == "id":
                    continue
                if stored[key] != item[key]:
                    REPORT["writes"] = writes
                    raise SystemExit(f"ROUTE REWROTE A FIELD: user {uid}.{key} "
                                     f"sent={item[key]!r} stored={stored[key]!r}. Stopping.")
            print(f"  {uid} {fresh['full_name']}: {patch} -> 200")
        REPORT["writes"] = writes

        # ── 4. after: intent, trigger, invariants, zero drift ───────────────
        after = all_users()
        scope_after = scope()
        check("89 users after", len(after), 89)

        check("Jafarova job_title", after[jafarova]["job_title"], NEW_TITLE)
        check("Jafarova role", after[jafarova]["role"], "manager")
        check("Jafarova manager", after[jafarova]["manager_id"], PETROSOV)
        expected_reports = sorted(i for i in dept_members
                                  if i != jafarova and i != KURBANGELDYEV)
        check("Jafarova reports = the logistics department minus herself and 33",
              reports_of(after, jafarova), expected_reports)
        check("Kurbangeldyev 33 untouched",
              {k: after[KURBANGELDYEV][k] for k in PAYLOAD_KEYS if k != "id"},
              {k: before[KURBANGELDYEV][k] for k in PAYLOAD_KEYS if k != "id"})
        check("Egamberdyev work_category", after[EGAMBERDYEV]["work_category"], "project")
        check("Egamberdyev is_project_participant (derived by the route)",
              after[EGAMBERDYEV]["is_project_participant"], True)

        graph_drift = [i for i, r in after.items()
                       if bool(r["has_subordinates"]) != bool(reports_of(after, i))]
        check("has_subordinates agrees with the graph everywhere (trigger)", graph_drift, [])
        check("Jafarova has_subordinates", bool(after[jafarova]["has_subordinates"]), True)

        inv_after = org_invariants(after, scope_after)
        check("role=manager <=> has direct reports",
              inv_after["role_manager_iff_reports_exceptions"], [])
        check("zero cycles", inv_after["cycles"], [])
        check("zero people without an evaluator", inv_after["people_without_evaluator"], [])
        check("the six the owner declared intentional",
              inv_after["in_scope_but_nobody_evaluates"], [2, 18, 21, 40, 47, 61])

        intended = {(uid, k) for uid, patch in changes for k in patch}
        # is_project_participant is not sent; the route derives it from work_category.
        intended.add((EGAMBERDYEV, "is_project_participant"))
        drift: list[str] = []
        for uid, row in after.items():
            for key in row:
                if (uid, key) in intended or key == "has_subordinates":
                    continue
                if before[uid][key] != row[key]:
                    drift.append(f"{uid}.{key}: {before[uid][key]!r} -> {row[key]!r}")
        check("zero drift outside the intended fields", drift, [])
        for col in FROZEN_COLUMNS:
            changed = [i for i in after if before[i][col] != after[i][col]]
            check(f"frozen column {col} untouched", changed, [])

        # money: Egamberdyev's index at equal scores, live weights and coefficients
        grade74 = float(grades[str(after[EGAMBERDYEV]["grade_id"])])
        money = []
        for raw in range(1, 11):
            b = bonus_index(before[EGAMBERDYEV], catalogue, coefficients, grade74, float(raw))
            a = bonus_index(after[EGAMBERDYEV], catalogue, coefficients, grade74, float(raw))
            money.append({"score": raw, "before": round(b, 4), "after": round(a, 4),
                          "delta": round(a - b, 4),
                          "pct": round((a / b - 1) * 100, 2) if b else None})
        REPORT["egamberdyev_bonus_index"] = {"grade_coefficient": grade74, "by_score": money}

        REPORT["after"] = {
            "criteria_buckets": buckets(after, catalogue),
            "category_split": category_split(after),
            "invariants": inv_after,
            "jafarova": {k: after[jafarova][k] for k in
                         ("full_name", "job_title", "role", "manager_id", "work_category",
                          "is_project_participant", "department_id", "grade_id", "has_subordinates")},
            "jafarova_reports": reports_of(after, jafarova),
            "jafarova_channels": channels(after, scope_after, jafarova),
            "jafarova_criteria": applicable_criteria(after[jafarova], catalogue),
            "petrosov_reports": reports_of(after, PETROSOV),
            "egamberdyev": {k: after[EGAMBERDYEV][k] for k in
                            ("full_name", "work_category", "is_project_participant",
                             "manager_id", "grade_id")},
            "egamberdyev_criteria": applicable_criteria(after[EGAMBERDYEV], catalogue),
        }
        # mid_level corrector change for the moved people
        REPORT["mid_level_corrector_change"] = [
            {"user_id": uid,
             "before": before[before[uid]["manager_id"]]["manager_id"],
             "after": after[after[uid]["manager_id"]]["manager_id"]} for uid in movers]

        period_after = json.loads(live_sql("""
          SELECT row_to_json(p) FROM (
            SELECT id, status, is_active, evaluation_started_at
            FROM performance_db.evaluation_periods WHERE id = 2) p"""))
        REPORT["h1_after"] = period_after
        check("H1 untouched", period_after,
              {"id": 2, "status": "active", "is_active": True, "evaluation_started_at": None})
        check("data tables still empty",
              {t: int(live_sql(f"SELECT count(*) FROM performance_db.{t}"))
               for t in ("evaluations", "evaluation_scores", "score_corrections", "period_results")},
              {"evaluations": 0, "evaluation_scores": 0, "score_corrections": 0, "period_results": 0})
        check("participants/in-scope counters unchanged",
              json.loads(live_sql("""
                SELECT row_to_json(x) FROM (
                  SELECT count(*)::int AS participants,
                         count(*) FILTER (WHERE is_in_scope)::int AS in_scope
                  FROM performance_db.evaluation_period_participants WHERE period_id = 2) x""")),
              {"participants": 89, "in_scope": 87})
        check("catalogue untouched: 9 criteria / 90 level coefficients",
              [int(live_sql("SELECT count(*) FROM performance_db.criteria")),
               int(live_sql("SELECT count(*) FROM performance_db.score_coefficients"))],
              [9, 90])
    finally:
        # ── 5. remove the probe session, keep the anchor ────────────────────
        live_sql(f"DELETE FROM performance_db.auth_sessions WHERE jti = '{ADMIN_JTI}'")
        sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
        REPORT["auth_sessions_after"] = sessions_after
        check("auth_sessions back to the pre-run count", sessions_after, REPORT.get("auth_sessions_before"))
        REPORT["vps_tmp_after"] = sorted(
            f for f in ssh(f"ls -1 {VPS_TMP} 2>/dev/null || true").splitlines() if f)
        REPORT["failures"] = FAILURES
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"proof: {args.output}")

    if FAILURES:
        raise SystemExit("FAILURES:\n  " + "\n  ".join(FAILURES))
    print("OK — logistics attached to Jafarova, Egamberdyev back on project, zero drift elsewhere.")


if __name__ == "__main__":
    main()

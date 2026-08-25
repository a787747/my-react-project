#!/usr/bin/env python3
"""Attach the Lab Solutions Division branch to its actual head on LIVE.

Brief LAB_DIVISION_HIERARCHY_2026-08-25. Owner statement (2026-08-25): Jahan
Hojayeva heads the Lab Solutions Division, which structurally contains Special
Lab Solutions (no leader) and two Clinical Lab Solutions sub-departments, led by
Nurmammet Hekimov and Akmyrat Jumahanov. Live had the whole branch flat under
Bayram Urayev (COO) and Hojayeva as role=employee with zero reports.

Writes only through POST /webhook/admin/save-user (API: Admin Save User (GUI
Mode)) — never raw SQL on users. That route is a FULL-ROW UPDATE with dangerous
defaults (`body.role || 'employee'`, `body.work_category || 'general'`), so each
payload is the live row read fresh immediately before its own write, with only
the one intended field replaced. Any non-200, or any field that lands different
from what was sent, stops the run with the dump path printed.

`has_subordinates` is deliberately NOT written: performance_db has an AFTER
UPDATE OF manager_id trigger (trg_update_has_subordinates) that recomputes it on
both the old and the new manager. The run asserts the trigger did its job.
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
BACKUP_DIR = REPO / "backups/2026-08-25-lab-division"
VPS_TMP = "/root/epe_stand_tmp"
# The pre-gate rollback anchor of PRELAUNCH_LIVE_CHECK lives in VPS_TMP on
# purpose and must survive; it is the only file allowed to be there already.
ALLOWED_TMP = {"epe_2026_pregate_20260825T121617Z.dump"}

ADMIN_ID = 2
ADMIN_JTI = "caf10000-2026-0825-8000-000000000003"

HOJAYEVA, HEKIMOV, JUMAHANOV, KOSTINA, MUHAMMEDOV, GARAYEV, URAYEV = 45, 68, 1, 6, 55, 53, 18

# (user_id, {field: new value}) — applied in this order, one route call each.
CHANGES: list[tuple[int, dict[str, Any]]] = [
    (HOJAYEVA,   {"role": "manager"}),
    (HEKIMOV,    {"manager_id": HOJAYEVA}),
    (JUMAHANOV,  {"manager_id": HOJAYEVA}),
    (KOSTINA,    {"manager_id": HOJAYEVA}),
    (MUHAMMEDOV, {"manager_id": HOJAYEVA}),
    (GARAYEV,    {"manager_id": HEKIMOV}),
]

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


def reports_of(users: dict[int, dict[str, Any]], uid: int) -> list[int]:
    return sorted(i for i, r in users.items() if r["manager_id"] == uid)


def payload_from_fresh(row: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    item = {key: row[key] for key in PAYLOAD_KEYS}
    item["id"] = int(item["id"])
    item.update(patch)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--output", type=Path, default=BACKUP_DIR / "lab_division_proof.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="run every gate and print the payloads, write nothing")
    args = parser.parse_args()
    REPORT["base_url"] = args.base_url
    REPORT["dry_run"] = bool(args.dry_run)

    # ── 0. gates ────────────────────────────────────────────────────────────
    period = json.loads(live_sql("""
      SELECT row_to_json(p) FROM (
        SELECT id, name, status, is_active, evaluation_started_at
        FROM performance_db.evaluation_periods WHERE id = 2) p"""))
    REPORT["h1_before"] = period
    if not (period["status"] == "active" and period["is_active"] is True
            and period["evaluation_started_at"] is None):
        raise SystemExit(f"REFUSING: H1 is not active-and-not-started: {period}")

    counts = {t: int(live_sql(f"SELECT count(*) FROM performance_db.{t}"))
              for t in ("evaluations", "evaluation_scores", "score_corrections", "period_results")}
    REPORT["data_tables_before"] = counts
    if any(counts.values()):
        raise SystemExit(f"REFUSING: a data table is not empty, this is no longer a pre-campaign edit: {counts}")

    leftover = [f for f in ssh(f"ls -1 {VPS_TMP} 2>/dev/null || true").splitlines()
                if f and f not in ALLOWED_TMP]
    REPORT["vps_tmp_unexpected"] = leftover
    if leftover:
        raise SystemExit(f"REFUSING: unexpected files in {VPS_TMP}: {leftover}")

    before = all_users()
    check("89 users before", len(before), 89)
    for uid in (HOJAYEVA, HEKIMOV, JUMAHANOV, KOSTINA, MUHAMMEDOV, GARAYEV, URAYEV):
        if uid not in before:
            raise SystemExit(f"REFUSING: user id {uid} not on live")
    # The premise this whole run rests on: the branch is currently flat under Urayev.
    for uid in (HOJAYEVA, HEKIMOV, JUMAHANOV, KOSTINA, MUHAMMEDOV, GARAYEV):
        if before[uid]["manager_id"] != URAYEV:
            raise SystemExit(
                f"REFUSING: premise broken — user {uid} already reports to "
                f"{before[uid]['manager_id']}, not {URAYEV}. Re-read before writing.")
    if before[HOJAYEVA]["role"] != "employee":
        raise SystemExit(f"REFUSING: Hojayeva's role is {before[HOJAYEVA]['role']!r}, expected 'employee'")
    # has_subordinates must agree with the graph everywhere before we start.
    drifted = [i for i, r in before.items() if bool(r["has_subordinates"]) != bool(reports_of(before, i))]
    if drifted:
        raise SystemExit(f"REFUSING: has_subordinates already disagrees with manager_id for {drifted}")
    if FAILURES:
        raise SystemExit("gate failures: " + "; ".join(FAILURES))

    # ── 1. dump first (AGENTS.md hard constraint 1) ─────────────────────────
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    dump_name = f"epe_2026_{stamp}.dump"
    vps_dump = f"{VPS_TMP}/{dump_name}"
    local_dump = BACKUP_DIR / dump_name
    ssh(f"install -d -m 700 {VPS_TMP}")
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
    REPORT["dump"] = {
        "vps": vps_dump, "local": str(local_dump), "bytes": vps_bytes,
        "md5": hashlib.md5(local_dump.read_bytes()).hexdigest(), "stamp": stamp,
    }
    print(f"dump: {local_dump} ({vps_bytes} bytes, md5 {REPORT['dump']['md5']})")

    REPORT["before"] = {
        "hierarchy": {str(u): {"role": before[u]["role"], "manager_id": before[u]["manager_id"],
                               "has_subordinates": before[u]["has_subordinates"],
                               "reports": reports_of(before, u)}
                      for u in (URAYEV, HOJAYEVA, HEKIMOV, JUMAHANOV, KOSTINA, MUHAMMEDOV, GARAYEV)},
    }

    if args.dry_run:
        for uid, patch in CHANGES:
            print(f"WOULD POST admin/save-user {json.dumps(payload_from_fresh(before[uid], patch), ensure_ascii=False)}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY RUN — nothing written. Proof: {args.output}")
        return

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
        for uid, patch in CHANGES:
            fresh = all_users()[uid]
            item = payload_from_fresh(fresh, patch)
            status, body = call(args.base_url, "POST", "admin/save-user", token, body=item)
            written_at = live_sql("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
            rec = {"user_id": uid, "name": fresh["full_name"], "patch": patch,
                   "sent": item, "status": status, "body": body, "written_at_utc": written_at}
            writes.append(rec)
            if status != 200:
                REPORT["writes"] = writes
                raise SystemExit(f"ROUTE STOP: user {uid} returned {status} {body!r}. "
                                 f"No raw-SQL fallback. Dump: {local_dump} / {vps_dump}")
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

        # ── 4. after: intent, trigger, and zero drift on everyone else ──────
        after = all_users()
        check("89 users after", len(after), 89)

        check("Hojayeva role", after[HOJAYEVA]["role"], "manager")
        check("Hojayeva still reports to Urayev", after[HOJAYEVA]["manager_id"], URAYEV)
        check("Hojayeva reports", reports_of(after, HOJAYEVA), sorted([JUMAHANOV, KOSTINA, MUHAMMEDOV, HEKIMOV]))
        check("Hekimov reports", reports_of(after, HEKIMOV), sorted([20, GARAYEV, 56, 85]))
        check("Jumahanov reports", reports_of(after, JUMAHANOV), sorted([3, 10, 31, 39, 54, 79]))
        check("Urayev reports", reports_of(after, URAYEV), sorted([17, 42, HOJAYEVA, 72]))

        # the trigger, not us, owns has_subordinates
        for uid in (HOJAYEVA, HEKIMOV, JUMAHANOV, URAYEV):
            check(f"has_subordinates {uid}", bool(after[uid]["has_subordinates"]), True)
        for uid in (KOSTINA, MUHAMMEDOV, GARAYEV):
            check(f"has_subordinates {uid}", bool(after[uid]["has_subordinates"]), False)
        graph_drift = [i for i, r in after.items() if bool(r["has_subordinates"]) != bool(reports_of(after, i))]
        check("has_subordinates agrees with the graph everywhere", graph_drift, [])

        # role=manager <=> has reports, the org-wide invariant this change had to preserve
        invariant = [i for i, r in after.items()
                     if r["role"] not in ("admin", "c_level")
                     and (r["role"] == "manager") != bool(reports_of(after, i))]
        check("role=manager <=> has direct reports", invariant, [])

        # nothing else moved, anywhere
        intended = {(uid, k) for uid, patch in CHANGES for k in patch}
        drift: list[str] = []
        for uid, row in after.items():
            for key in row:
                if (uid, key) in intended:
                    continue
                if key == "has_subordinates":
                    continue  # owned by the trigger, asserted above
                if before[uid][key] != row[key]:
                    drift.append(f"{uid}.{key}: {before[uid][key]!r} -> {row[key]!r}")
        check("zero drift outside the six intended fields", drift, [])
        for col in FROZEN_COLUMNS:
            changed = [i for i in after if before[i][col] != after[i][col]]
            check(f"frozen column {col} untouched", changed, [])

        # criteria-count distribution, recomputed from the live rule
        def buckets(users: dict[int, dict[str, Any]]) -> dict[int, int]:
            out: dict[int, int] = {}
            for r in users.values():
                n = 4 + (1 if r["has_subordinates"] else 0) + (2 if r["is_project_participant"] else 0)
                out[n] = out.get(n, 0) + 1
            return dict(sorted(out.items()))
        REPORT["criteria_buckets_before"] = buckets(before)
        REPORT["criteria_buckets_after"] = buckets(after)

        REPORT["after"] = {
            "hierarchy": {str(u): {"role": after[u]["role"], "manager_id": after[u]["manager_id"],
                                   "has_subordinates": after[u]["has_subordinates"],
                                   "reports": reports_of(after, u)}
                          for u in (URAYEV, HOJAYEVA, HEKIMOV, JUMAHANOV, KOSTINA, MUHAMMEDOV, GARAYEV)},
        }

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
    finally:
        # ── 5. remove the probe session ─────────────────────────────────────
        live_sql(f"DELETE FROM performance_db.auth_sessions WHERE jti = '{ADMIN_JTI}'")
        sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
        REPORT["auth_sessions_after"] = sessions_after
        check("auth_sessions back to the pre-run count", sessions_after, REPORT.get("auth_sessions_before"))
        ssh(f"rm -f {vps_dump}")
        REPORT["vps_dump_removed"] = ssh(f"test -e {vps_dump} && echo present || echo removed")
        REPORT["failures"] = FAILURES
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"proof: {args.output}")

    if FAILURES:
        raise SystemExit("FAILURES:\n  " + "\n  ".join(FAILURES))
    print("OK — hierarchy applied and verified, zero drift outside the six intended fields.")


if __name__ == "__main__":
    main()

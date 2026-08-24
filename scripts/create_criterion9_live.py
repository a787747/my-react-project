#!/usr/bin/env python3
"""Create the ninth criterion «Ответственность сверх роли» on LIVE epe_2026.

Executes, on live, exactly the path proven end-to-end on the finalize stand
(docs/FINALIZE_PRELAUNCH_2026-08-2x.md §3): the same POST manage-criteria
{action:'save'} the admin UI sends (draft catalogue, launch paused), then the
explicit weight + level coefficients through POST api/score-coefficients —
the mandatory second step, because until it happens every money surface
silently values the criterion at weight 1.0 x coefficient 1.0.

HARD GATE — the approved texts. The brief requires the title, description and
ten level texts VERBATIM from Alexander's document. This script refuses to run
without --texts pointing at a JSON file shaped:

    {"title": "...", "description": "...",
     "level_1_desc": "...", ..., "level_10_desc": "..."}

It never invents, trims or reformats a single character: the file's strings go
into the API body as-is, and after creation every stored field is re-read and
compared char-for-char against the file.

Approved values (brief 2026-08-24): audience all, self-assessment OFF,
manager ON, c_level OFF; weight 1.50; level coefficients
0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00 for levels 1..10.

Sequence (each step records the compared values):
  0. Refuse if a criterion with the file's title already exists
     (rerun guard — proofs are not idempotent). --resume continues from the
     coefficients step iff the criterion exists unseeded at default weight.
  1. Dump epe_2026 (pg_dump -Fc) to backups/2026-08-24-criterion9/ locally.
  2. BEFORE snapshot: raw criteria/coefficients/grades aggregates (the money
     fingerprint, kept raw for byte comparison, plus its md5) and counts.
  3. Marked admin probe session (jti below), secret read from the live n8n
     container at run time; deleted in finally.
  4. POST manage-criteria save -> id; verify: weight 1.00 default, ZERO
     coefficient rows seeded, flags as approved, texts byte-equal to the file.
  5. GET api/score-coefficients renders the unseeded criterion (all-1.0 fill).
  6. POST api/score-coefficients: weight 1.50 + the ten approved values;
     verify in SQL: exactly 10 rows, stored weight 1.50, every level to the
     digit; GET returns the same.
  7. GET api/criteria as admin (weight present) and as a live manager via a
     second marked read-only session (weight stripped, flags intact).
  8. Front-editability round-trip on the same save route: level 5
     0.50 -> 0.55 -> re-read 0.55 -> restore 0.50 -> re-read 0.50
     (all four values recorded).
  9. AFTER snapshot EXCLUDING the new id: byte-identical to BEFORE (the other
     8 criteria's weights, their 80 coefficient rows, all grades untouched);
     totals now 9 active criteria / 90 coefficient rows; periods state
     unchanged (launch stays paused; no activation, no start, no mail).

No workflow PUT, no direct SQL write to any performance_db table — the only
live writes are the two API routes Alexander's own UI calls, plus the marked
auth_sessions probe rows (deleted in finally).
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
REPO = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO / "backups/2026-08-24-criterion9"

ADMIN_ID = 2
ADMIN_JTI = "c9a90000-2026-4824-8000-000000000001"   # marked probe jti (admin)
READER_JTI = "c9a90000-2026-4824-8000-000000000002"  # marked probe jti (manager read)

APPROVED_WEIGHT = 1.50
APPROVED_LEVELS = {1: 0.20, 2: 0.25, 3: 0.30, 4: 0.35, 5: 0.50,
                   6: 0.70, 7: 1.00, 8: 2.00, 9: 3.60, 10: 6.00}
ROUNDTRIP_LEVEL = 5          # the level changed and restored in step 8
ROUNDTRIP_VALUE = 0.55
APPROVED_FLAGS = {"target_audience": "all", "is_active": True,
                  "selfassesment": False, "for_manager": True, "c_level_only": False}
TEXT_KEYS = ["title", "description"] + [f"level_{i}_desc" for i in range(1, 11)]

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def ssh(command: str) -> str:
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, command],
                            capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST,
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


def load_texts(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SystemExit(
            f"REFUSING TO RUN: texts file not found: {path}\n"
            "The approved title, description and ten level texts must come VERBATIM from\n"
            "Alexander's document. Save them as JSON with keys: " + ", ".join(TEXT_KEYS))
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in TEXT_KEYS if not isinstance(data.get(k), str) or not data[k].strip()]
    extra = [k for k in data if k not in TEXT_KEYS]
    if missing or extra:
        raise SystemExit(f"REFUSING TO RUN: texts file malformed — missing/empty {missing}, unexpected {extra}")
    return {k: data[k] for k in TEXT_KEYS}


def criteria_rows() -> list[dict[str, Any]]:
    raw = live_sql("""
      SELECT COALESCE(json_agg(row_to_json(c) ORDER BY c.id), '[]') FROM (
        SELECT id, title, description, weight, target_audience, is_active,
               selfassesment, for_manager, c_level_only,
               level_1_desc, level_2_desc, level_3_desc, level_4_desc, level_5_desc,
               level_6_desc, level_7_desc, level_8_desc, level_9_desc, level_10_desc
        FROM performance_db.criteria) c""")
    return json.loads(raw)


def snapshot(exclude_id: int | None = None) -> dict[str, str]:
    crit_filter = f"WHERE c.id <> {exclude_id}" if exclude_id else ""
    coef_filter = f"WHERE sc.criteria_id <> {exclude_id}" if exclude_id else ""
    parts = {
        "criteria": live_sql(
            "SELECT COALESCE(string_agg(c.id || ':' || c.weight || ':' || c.is_active, ',' ORDER BY c.id), '') "
            f"FROM performance_db.criteria c {crit_filter}"),
        "coefficients": live_sql(
            "SELECT COALESCE(string_agg(sc.criteria_id || ':' || sc.score_level || ':' || sc.coefficient, ',' ORDER BY sc.criteria_id, sc.score_level), '') "
            f"FROM performance_db.score_coefficients sc {coef_filter}"),
        "grades": live_sql(
            "SELECT COALESCE(string_agg(g.id || ':' || g.code || ':' || g.coefficient, ',' ORDER BY g.id), '') "
            "FROM performance_db.grades g"),
    }
    parts["md5"] = hashlib.md5("|".join(parts[k] for k in ("criteria", "coefficients", "grades")).encode()).hexdigest()
    return parts


def scoring_row(base: str, token: str, criterion_id: int) -> dict[str, Any] | None:
    status, body = call(base, "GET", "api/score-coefficients", token)
    check("scoring GET: 200 for admin", status, 200)
    return next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == criterion_id), None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--texts", type=Path, required=True,
                        help="JSON file with the VERBATIM approved texts (see module docstring)")
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--resume", action="store_true",
                        help="continue from the coefficients step if the criterion already "
                             "exists UNSEEDED at the default weight (partial earlier run)")
    parser.add_argument("--output", type=Path, default=BACKUP_DIR / "criterion9_live_proof.json")
    args = parser.parse_args()

    texts = load_texts(args.texts)
    REPORT["texts_file"] = str(args.texts)
    REPORT["base_url"] = args.base_url

    # ── 0. rerun guard ──────────────────────────────────────────────────────
    existing = [c for c in criteria_rows() if c["title"] == texts["title"]]
    resume_id: int | None = None
    if existing:
        row = existing[0]
        seeded = int(live_sql(
            f"SELECT count(*) FROM performance_db.score_coefficients WHERE criteria_id = {row['id']}"))
        if args.resume and seeded == 0 and float(row["weight"]) == 1.0:
            resume_id = int(row["id"])
            REPORT["resumed_from_existing_id"] = resume_id
        else:
            raise SystemExit(
                f"REFUSING TO RUN: a criterion titled {texts['title']!r} already exists "
                f"(id {row['id']}, weight {row['weight']}, {seeded} coefficient rows). "
                "Inspect live before rerunning; --resume only continues an unseeded default-weight leftover.")

    periods_before = live_sql(
        "SELECT COALESCE(string_agg(id || ':' || status || ':' || COALESCE(evaluation_started_at::text,'-'), ',' ORDER BY id), '') "
        "FROM performance_db.evaluation_periods")
    REPORT["periods_before"] = periods_before

    # ── 1. dump first ───────────────────────────────────────────────────────
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dump_path = BACKUP_DIR / f"epe_2026_{stamp}.dump"
    with dump_path.open("wb") as fh:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", HOST,
             "docker exec postgres_n8n pg_dump -U admin --no-owner --no-acl -Fc epe_2026"],
            stdout=fh, stderr=subprocess.PIPE)
    # known-good dumps of this DB (0 evaluations) are ~79 KB in -Fc
    if result.returncode or dump_path.stat().st_size < 50_000:
        raise SystemExit(f"dump failed or implausibly small: {dump_path} "
                         f"({dump_path.stat().st_size} bytes) {result.stderr.decode('utf-8', 'replace')}")
    REPORT["dump"] = {"path": str(dump_path), "bytes": dump_path.stat().st_size}

    # ── 2. BEFORE snapshot ──────────────────────────────────────────────────
    before = snapshot()
    counts_before = {
        "criteria_active": int(live_sql("SELECT count(*) FROM performance_db.criteria WHERE is_active")),
        "coefficient_rows": int(live_sql("SELECT count(*) FROM performance_db.score_coefficients")),
    }
    REPORT["before"] = {"snapshot_md5": before["md5"], "counts": counts_before}
    check("before: 8 active criteria", counts_before["criteria_active"], 8)
    check("before: 80 coefficient rows", counts_before["coefficient_rows"], 80)

    # ── 3. marked probe sessions ────────────────────────────────────────────
    secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
    if not secret:
        raise SystemExit("could not read JWT_SIGNING_SECRET from the live container")
    sessions_before = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))

    manager_id = int(live_sql(
        "SELECT id FROM performance_db.users WHERE role = 'manager' ORDER BY id LIMIT 1"))
    REPORT["reader_manager_id"] = manager_id

    def open_session(jti: str, user_id: int) -> str:
        version = int(live_sql(
            f"SELECT token_version FROM performance_db.users WHERE id = {user_id}"))
        live_sql(f"""
          INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
          VALUES ('{jti}', {user_id}, {version}, now(), now() + interval '1 hour')
          ON CONFLICT (jti) DO UPDATE SET expires_at = now() + interval '1 hour'""")
        return mint(secret, user_id, jti)

    admin_token = open_session(ADMIN_JTI, ADMIN_ID)
    base = args.base_url

    try:
        # ── 4. create through the UI's own route ────────────────────────────
        if resume_id is None:
            status, body = call(base, "POST", "manage-criteria", admin_token, body={
                "action": "save",
                "criteria": {**{k: texts[k] for k in TEXT_KEYS}, **APPROVED_FLAGS},
            })
            check("create: manage-criteria save accepted", status, 200)
            created = [c for c in criteria_rows() if c["title"] == texts["title"]]
            check("create: exactly one row with the approved title", len(created), 1)
            if len(created) != 1:
                raise SystemExit("creation did not land as exactly one row — stopping before any further write")
            new_id = int(created[0]["id"])
        else:
            new_id = resume_id
            created = [c for c in criteria_rows() if int(c["id"]) == new_id]
        REPORT["new_id"] = new_id
        row = created[0]

        for key in TEXT_KEYS:
            check(f"verbatim: stored {key} char-for-char equals the document", row[key], texts[key])
        check("create: flags as approved (all / self off / manager on / c_level off / active)",
              {k: row[k] for k in APPROVED_FLAGS}, APPROVED_FLAGS)
        check("create: weight is the DB default 1.00 (editor cannot set one)", float(row["weight"]), 1.0)
        check("create: NO coefficient rows seeded", int(live_sql(
            f"SELECT count(*) FROM performance_db.score_coefficients WHERE criteria_id = {new_id}")), 0)

        # ── 5. /admin/scoring renders the unseeded criterion ────────────────
        unseeded = scoring_row(base, admin_token, new_id)
        check("scoring GET: unseeded criterion rendered", unseeded is not None, True)
        if unseeded:
            check("scoring GET: unseeded server-side fill is weight 1.0, all levels 1.0",
                  (float(unseeded["weight"]),
                   sorted(set(float(v) for v in unseeded["score_coefficients"].values()))),
                  (1.0, [1.0]))

        # ── 6. the mandatory coefficients save ──────────────────────────────
        status, body = call(base, "POST", "api/score-coefficients", admin_token, body={
            "criteria": [{"id": new_id, "weight": APPROVED_WEIGHT,
                          "score_coefficients": {str(k): v for k, v in APPROVED_LEVELS.items()}}],
        })
        check("save: weight 1.50 + ten approved coefficients accepted", status, 200)
        check("save: exactly 10 coefficient rows for the new id", int(live_sql(
            f"SELECT count(*) FROM performance_db.score_coefficients WHERE criteria_id = {new_id}")), 10)
        check("save: stored weight is 1.50, not the 1.0 default", float(live_sql(
            f"SELECT weight FROM performance_db.criteria WHERE id = {new_id}")), APPROVED_WEIGHT)
        stored_levels = {int(k): float(v) for k, v in json.loads(live_sql(
            f"""SELECT COALESCE(json_object_agg(score_level, coefficient), '{{}}')
                FROM performance_db.score_coefficients WHERE criteria_id = {new_id}""")).items()}
        check("save: every level coefficient to the digit", stored_levels, APPROVED_LEVELS)
        REPORT["stored"] = {"weight": APPROVED_WEIGHT, "levels": stored_levels}

        seeded = scoring_row(base, admin_token, new_id)
        check("scoring GET after save: approved values come back",
              (float(seeded["weight"]),
               {int(k): float(v) for k, v in seeded["score_coefficients"].items()}) if seeded else None,
              (APPROVED_WEIGHT, APPROVED_LEVELS))

        # ── 7. catalogue read: flags for everyone, weight admin-only ────────
        status, body = call(base, "GET", "api/criteria", admin_token)
        check("criteria GET (admin): 200", status, 200)
        arow = next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == new_id), None)
        check("criteria GET (admin): criterion present with weight",
              (arow is not None) and float(arow.get("weight") or 0) == APPROVED_WEIGHT, True)
        reader_token = open_session(READER_JTI, manager_id)
        status, body = call(base, "GET", "api/criteria", reader_token)
        check("criteria GET (manager): 200", status, 200)
        mrow = next((r for r in ((body or {}).get("data") or []) if int(r["id"]) == new_id), None)
        check("criteria GET (manager): criterion visible with flags, weight stripped",
              (mrow is not None,
               mrow.get("weight") if mrow else "absent-row",
               (mrow.get("target_audience"), mrow.get("selfassesment"),
                mrow.get("for_manager"), mrow.get("c_level_only")) if mrow else None),
              (True, None, ("all", False, True, False)))
        REPORT["criteria_get_manager"] = mrow

        # ── 8. front-editability round-trip ─────────────────────────────────
        def save_level(value: float) -> None:
            levels = dict(APPROVED_LEVELS)
            levels[ROUNDTRIP_LEVEL] = value
            status, _ = call(base, "POST", "api/score-coefficients", admin_token, body={
                "criteria": [{"id": new_id, "weight": APPROVED_WEIGHT,
                              "score_coefficients": {str(k): v for k, v in levels.items()}}],
            })
            check(f"round-trip: save level {ROUNDTRIP_LEVEL} = {value} accepted", status, 200)

        def read_level() -> float:
            return float(live_sql(
                f"SELECT coefficient FROM performance_db.score_coefficients "
                f"WHERE criteria_id = {new_id} AND score_level = {ROUNDTRIP_LEVEL}"))

        approved_value = APPROVED_LEVELS[ROUNDTRIP_LEVEL]
        save_level(ROUNDTRIP_VALUE)
        changed = read_level()
        check("round-trip: re-read shows the changed value", changed, ROUNDTRIP_VALUE)
        save_level(approved_value)
        restored = read_level()
        check("round-trip: re-read shows the approved value restored", restored, approved_value)
        REPORT["roundtrip"] = {"level": ROUNDTRIP_LEVEL, "approved": approved_value,
                              "changed_to": ROUNDTRIP_VALUE, "read_changed": changed,
                              "read_restored": restored}
    finally:
        deleted = live_sql(
            f"DELETE FROM performance_db.auth_sessions WHERE jti IN ('{ADMIN_JTI}', '{READER_JTI}') RETURNING jti")
        REPORT["probe_sessions_deleted"] = deleted.split("\n") if deleted else []

    # ── 9. everything else byte-identical; totals; paused state ─────────────
    after = snapshot(exclude_id=REPORT.get("new_id"))
    for key in ("criteria", "coefficients", "grades"):
        check(f"fingerprint: {key} byte-identical excluding the new id", after[key], before[key])
    check("fingerprint: md5 unchanged", after["md5"], before["md5"])
    REPORT["after"] = {"snapshot_md5": after["md5"]}

    counts_after = {
        "criteria_active": int(live_sql("SELECT count(*) FROM performance_db.criteria WHERE is_active")),
        "coefficient_rows": int(live_sql("SELECT count(*) FROM performance_db.score_coefficients")),
    }
    REPORT["after"]["counts"] = counts_after
    check("after: 9 active criteria", counts_after["criteria_active"], 9)
    check("after: 90 coefficient rows", counts_after["coefficient_rows"], 90)

    periods_after = live_sql(
        "SELECT COALESCE(string_agg(id || ':' || status || ':' || COALESCE(evaluation_started_at::text,'-'), ',' ORDER BY id), '') "
        "FROM performance_db.evaluation_periods")
    check("launch stays paused: periods byte-identical", periods_after, periods_before)
    sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
    check("probe sessions cleaned", sessions_after, sessions_before)

    REPORT["failures"] = FAILURES
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} CHECK(S) FAILED — see report")
    print("CRITERION 9 CREATED AND PROVEN ON LIVE")


if __name__ == "__main__":
    main()

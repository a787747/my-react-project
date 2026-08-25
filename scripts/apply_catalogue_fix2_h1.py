#!/usr/bin/env python3
"""Remove five H1 level-6 norm labels on LIVE via manage-criteria.

Brief CATALOGUE_FIX2_H1_2026-08-25. Same mechanism as
scripts/apply_catalogue_fix_h1.py: writes only through
POST /manage-criteria {action:'save'} (API: Manage Criteria Admin V7),
never raw SQL on criteria. Reads each row fresh immediately before its
write. Stops on 409/422 or any field outside the five changing.

The route's UPDATE always SETs title, description, audience, flags and
level_0..10. Weight, category and score_definitions are not in the SET
list. The payload is the live row with only the brief's fields replaced,
so unchanged columns keep their live values.
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
BACKUP_DIR = REPO / "backups/2026-08-25-catalogue-fix2"
CATALOGUE_DIR = REPO / "docs/catalogue"
PREVIOUS_AFTER = CATALOGUE_DIR / "H1-2026_catalogue_after_20260825T062601Z.md"
VPS_TMP = "/root/epe_stand_tmp"

ADMIN_ID = 2
ADMIN_JTI = "caf10000-2026-0825-8000-000000000002"

WRITE_ORDER = (3, 4, 8, 10, 12)
EXPECTED_FIELD_COUNT = 5
EXPECTED_OTHER_TEXT = 103
WRITABLE = [
    "id", "title", "description", "target_audience",
    "is_active", "selfassesment", "for_manager", "c_level_only",
] + [f"level_{i}_desc" for i in range(0, 11)]
TEXT_KEYS = ["title", "description"] + [f"level_{i}_desc" for i in range(1, 11)]
ALL_COLUMNS = [
    "id", "title", "category", "description", "score_definitions", "weight",
    "is_active", "target_audience", "level_0_desc",
    "level_1_desc", "level_2_desc", "level_3_desc", "level_4_desc",
    "level_5_desc", "level_6_desc", "level_7_desc", "level_8_desc",
    "level_9_desc", "level_10_desc", "selfassesment", "c_level_only",
    "for_manager",
]
BOOL_KEYS = ("is_active", "selfassesment", "for_manager", "c_level_only")

FAILURES: list[str] = []
REPORT: dict[str, Any] = {}


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
         "-i", SSH_ID, HOST, command],
        capture_output=True)
    if result.returncode:
        raise SystemExit((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def live_sql(statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
         "-i", SSH_ID, HOST,
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


def criteria_rows() -> list[dict[str, Any]]:
    raw = live_sql("""
      SELECT COALESCE(json_agg(row_to_json(c) ORDER BY c.id), '[]') FROM (
        SELECT id, title, category, description, score_definitions, weight,
               is_active, target_audience,
               level_0_desc, level_1_desc, level_2_desc, level_3_desc, level_4_desc,
               level_5_desc, level_6_desc, level_7_desc, level_8_desc, level_9_desc,
               level_10_desc, selfassesment, c_level_only, for_manager
        FROM performance_db.criteria) c""")
    return json.loads(raw)


def row_by_id(rows: list[dict[str, Any]], cid: int) -> dict[str, Any]:
    found = [r for r in rows if int(r["id"]) == cid]
    if len(found) != 1:
        raise SystemExit(f"expected exactly one criterion id={cid}, got {len(found)}")
    return found[0]


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if out.get("weight") is not None:
        out["weight"] = f"{float(out['weight']):.2f}"
    for key in BOOL_KEYS:
        if key in out and out[key] is not None:
            out[key] = bool(out[key])
    return out


def load_patches(path: Path) -> dict[int, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    patches: dict[int, dict[str, str]] = {}
    total = 0
    for key, fields in data.items():
        cid = int(key)
        patches[cid] = {}
        for field, value in fields.items():
            if not isinstance(value, str):
                raise SystemExit(f"texts file: {cid}.{field} is not a string")
            patches[cid][field] = value
            total += 1
    if total != EXPECTED_FIELD_COUNT:
        raise SystemExit(
            f"texts file must contain exactly {EXPECTED_FIELD_COUNT} fields, got {total}")
    if set(patches) != set(WRITE_ORDER):
        raise SystemExit(f"texts file criteria {sorted(patches)} != {list(WRITE_ORDER)}")
    return patches


def flatten_patches(patches: dict[int, dict[str, str]]) -> list[tuple[int, str, str]]:
    flat: list[tuple[int, str, str]] = []
    for cid in WRITE_ORDER:
        for field, value in patches[cid].items():
            flat.append((cid, field, value))
    return flat


def snapshot_markdown(rows: list[dict[str, Any]], when: str, label: str) -> str:
    titles = {int(r["id"]): r["title"] for r in rows}
    lines = [
        f"# H1-2026 catalogue {label}",
        "",
        f"Live `epe_2026.performance_db.criteria`, all 9 rows, all columns, "
        f"SELECT `{when}` UTC (server clock). JSON escaping removed; "
        f"no line breaks in stored texts.",
        "",
    ]
    for row in rows:
        cid = int(row["id"])
        weight = f"{float(row['weight']):.2f}"
        sd = "NULL" if row["score_definitions"] is None else json.dumps(row["score_definitions"], ensure_ascii=False)
        l0 = "NULL" if row["level_0_desc"] is None else row["level_0_desc"]
        lines.append(f"### Criterion {cid} «{titles[cid]}»")
        lines.append("")
        lines.append(
            f"`id: {cid} · category: {row['category']} · target_audience: {row['target_audience']} · "
            f"weight: {weight} · selfassesment: {str(bool(row['selfassesment'])).lower()} · "
            f"c_level_only: {str(bool(row['c_level_only'])).lower()} · "
            f"for_manager: {str(bool(row['for_manager'])).lower()} · "
            f"is_active: {str(bool(row['is_active'])).lower()} · "
            f"score_definitions: {sd} · level_0_desc: {l0}`"
        )
        lines.append("")
        for key in TEXT_KEYS:
            lines.append(f"- **{key}:** {row[key]}")
        lines.append("")
    return "\n".join(lines)


def catalogue_body(markdown: str) -> str:
    idx = markdown.find("### Criterion")
    return markdown[idx:] if idx >= 0 else markdown


def parse_snapshot_fields(markdown: str) -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {}
    current: int | None = None
    for line in markdown.splitlines():
        if line.startswith("### Criterion "):
            current = int(line.split()[2])
            rows[current] = {}
        elif current is not None and line.startswith("`id:"):
            rows[current]["_meta"] = line
        elif current is not None and line.startswith("- **"):
            key, _, value = line[4:].partition(":** ")
            rows[current][key] = value
    return rows


def diff_snapshots(before_md: str, previous_md: str) -> list[str]:
    diffs: list[str] = []
    before = parse_snapshot_fields(before_md)
    previous = parse_snapshot_fields(previous_md)
    if set(before) != set(previous):
        diffs.append(f"criterion ids {sorted(before)} != {sorted(previous)}")
        return diffs
    for cid in sorted(before):
        if set(before[cid]) != set(previous[cid]):
            diffs.append(f"id {cid}: key set changed")
            continue
        for key in before[cid]:
            if before[cid][key] != previous[cid][key]:
                diffs.append(f"id {cid}.{key}")
    return diffs


def payload_from_fresh(row: dict[str, Any], patch: dict[str, str]) -> dict[str, Any]:
    item: dict[str, Any] = {}
    for key in WRITABLE:
        item[key] = row[key]
    for key in BOOL_KEYS:
        item[key] = bool(item[key])
    item["id"] = int(item["id"])
    item.update(patch)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--texts", type=Path,
                        default=REPO / "docs/briefs/catalogue_fix2_h1_texts.json")
    parser.add_argument("--base-url", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--output", type=Path,
                        default=BACKUP_DIR / "catalogue_fix2_h1_proof.json")
    args = parser.parse_args()

    patches = load_patches(args.texts)
    flat = flatten_patches(patches)
    REPORT["texts_file"] = str(args.texts)
    REPORT["base_url"] = args.base_url
    REPORT["field_count"] = len(flat)

    # ── 0. gates ────────────────────────────────────────────────────────────
    period = json.loads(live_sql("""
      SELECT row_to_json(p) FROM (
        SELECT id, name, status, is_active, evaluation_started_at
        FROM performance_db.evaluation_periods WHERE id = 2) p"""))
    REPORT["h1_before"] = period
    if not (period["status"] == "active" and period["is_active"] is True
            and period["evaluation_started_at"] is None):
        raise SystemExit(f"REFUSING: H1 is not active-and-not-started: {period}")

    counts = {
        "evaluations": int(live_sql("SELECT count(*) FROM performance_db.evaluations")),
        "evaluation_scores": int(live_sql("SELECT count(*) FROM performance_db.evaluation_scores")),
        "score_corrections": int(live_sql("SELECT count(*) FROM performance_db.score_corrections")),
        "period_results": int(live_sql("SELECT count(*) FROM performance_db.period_results")),
    }
    REPORT["data_tables_before"] = counts
    if any(counts.values()):
        raise SystemExit(f"REFUSING: a data table is not empty: {counts}")

    cols = live_sql("""
      SELECT string_agg(column_name, ',' ORDER BY ordinal_position)
      FROM information_schema.columns
      WHERE table_schema='performance_db' AND table_name='criteria'""")
    REPORT["criteria_columns"] = cols.split(",")
    REPORT["updated_at_column_exists"] = "updated_at" in REPORT["criteria_columns"]
    if REPORT["updated_at_column_exists"]:
        raise SystemExit("unexpected: criteria.updated_at exists — re-check the write plan")

    leftover_tmp = ssh(f"ls -1 {VPS_TMP} 2>/dev/null || true")
    REPORT["vps_tmp_before"] = leftover_tmp
    if leftover_tmp:
        raise SystemExit(f"REFUSING: {VPS_TMP} is not empty: {leftover_tmp}")

    # ── 1. dump first (VPS /root/epe_stand_tmp, then local copy) ────────────
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    dump_name = f"epe_2026_{stamp}.dump"
    vps_dump = f"{VPS_TMP}/{dump_name}"
    local_dump = BACKUP_DIR / dump_name
    ssh(f"install -d -m 700 {VPS_TMP}")
    ssh(
        f"docker exec postgres_n8n pg_dump -U admin --no-owner --no-acl -Fc epe_2026 "
        f"> {vps_dump} && chmod 600 {vps_dump}"
    )
    tmp_hits = ssh("ls -1 /tmp/epe_2026*.dump /tmp/*catalogue* 2>/dev/null || true")
    if tmp_hits:
        raise SystemExit(f"REFUSING: dump landed in /tmp: {tmp_hits}")
    vps_bytes = int(ssh(f"stat -c %s {vps_dump}"))
    if vps_bytes < 50_000:
        raise SystemExit(f"dump implausibly small on VPS: {vps_bytes} bytes")
    scp = subprocess.run(
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
         "-i", SSH_ID, f"{HOST}:{vps_dump}", str(local_dump)],
        capture_output=True)
    if scp.returncode or not local_dump.is_file() or local_dump.stat().st_size != vps_bytes:
        raise SystemExit(
            f"scp of dump failed: rc={scp.returncode} "
            f"local={local_dump.stat().st_size if local_dump.is_file() else 'missing'} "
            f"vps={vps_bytes} {(scp.stderr or b'').decode('utf-8', 'replace')}")
    REPORT["dump"] = {
        "vps": vps_dump, "local": str(local_dump), "bytes": vps_bytes, "stamp": stamp,
    }

    # ── 2. BEFORE snapshot ──────────────────────────────────────────────────
    before_ts = live_sql("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
    before_rows = criteria_rows()
    check("before: 9 rows", len(before_rows), 9)
    CATALOGUE_DIR.mkdir(parents=True, exist_ok=True)
    before_slug = before_ts.replace("-", "").replace(":", "")[:15]
    before_name = f"H1-2026_catalogue_before_{before_slug}Z.md"
    before_path = CATALOGUE_DIR / before_name
    before_md = snapshot_markdown(before_rows, before_ts, "before")
    before_path.write_text(before_md, encoding="utf-8")
    previous_md = PREVIOUS_AFTER.read_text(encoding="utf-8")
    body_equal = catalogue_body(before_md) == catalogue_body(previous_md)
    snapshot_diffs = diff_snapshots(before_md, previous_md)
    REPORT["before"] = {
        "timestamp_utc": before_ts,
        "path": str(before_path),
        "equals_previous_after": body_equal,
        "previous_after": str(PREVIOUS_AFTER),
        "diffs_vs_previous_after": snapshot_diffs,
        "rows": before_rows,
    }
    if not body_equal:
        print("SURFACED: before snapshot body differs from last after "
              f"{PREVIOUS_AFTER.name}: {snapshot_diffs or ['body mismatch']}")

    # ── 3. probe session ────────────────────────────────────────────────────
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
        # ── 4. one save per affected criterion, row read immediately before ─
        for cid in WRITE_ORDER:
            fresh = row_by_id(criteria_rows(), cid)
            item = payload_from_fresh(fresh, patches[cid])
            status, body = call(args.base_url, "POST", "manage-criteria", token, body={
                "action": "save",
                "criteria": item,
            })
            written_at = live_sql(
                "SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
            rec = {
                "criterion": cid,
                "fields": list(patches[cid].keys()),
                "status": status,
                "body": body,
                "written_at_utc": written_at,
                "updated_at": None,
                "updated_at_note": "performance_db.criteria has no updated_at column (live information_schema)",
            }
            writes.append(rec)
            if status in (409, 422) or status != 200:
                REPORT["writes"] = writes
                raise SystemExit(
                    f"ROUTE STOP: criterion {cid} returned {status} {body!r}. "
                    "No raw-SQL fallback. Dump is at "
                    f"{local_dump} / {vps_dump}.")
            stored = row_by_id(criteria_rows(), cid)
            for field, expected in patches[cid].items():
                if stored[field] != expected:
                    REPORT["writes"] = writes
                    raise SystemExit(
                        f"ROUTE REWROTE OR DROPPED TEXT: criterion {cid}.{field} "
                        f"status={status} stored≠brief. Stopping.")
        REPORT["writes"] = writes

        # ── 5. AFTER snapshot ───────────────────────────────────────────────
        after_ts = live_sql("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
        after_rows = criteria_rows()
        after_slug = after_ts.replace("-", "").replace(":", "")[:15]
        after_path = CATALOGUE_DIR / f"H1-2026_catalogue_after_{after_slug}Z.md"
        after_path.write_text(snapshot_markdown(after_rows, after_ts, "after"), encoding="utf-8")
        REPORT["after"] = {"timestamp_utc": after_ts, "path": str(after_path), "rows": after_rows}

        before_by_id = {int(r["id"]): normalize_row(r) for r in before_rows}
        after_by_id = {int(r["id"]): normalize_row(r) for r in after_rows}
        patched = {(cid, field) for cid, field, _ in flat}

        field_table = []
        for cid, field, expected in flat:
            stored = after_by_id[cid][field]
            write = next(w for w in writes if w["criterion"] == cid)
            field_table.append({
                "criterion": cid,
                "column": field,
                "equals_brief_text": stored == expected,
                "updated_at": write["updated_at"],
                "written_at_utc": write["written_at_utc"],
                "route_status": write["status"],
            })
            check(f"verbatim {cid}.{field}", stored, expected)
        REPORT["field_table"] = field_table

        other_text_ok = 0
        other_nontext_ok = 0
        unexpected: list[str] = []
        for cid, brow in before_by_id.items():
            arow = after_by_id[cid]
            if set(brow) != set(arow):
                unexpected.append(f"id {cid}: column set changed")
                continue
            for col in ALL_COLUMNS:
                if col not in brow:
                    unexpected.append(f"id {cid}: missing column {col}")
                    continue
                if (cid, col) in patched:
                    continue
                if brow[col] != arow[col]:
                    unexpected.append(f"id {cid}.{col} changed: {brow[col]!r} → {arow[col]!r}")
                elif col in TEXT_KEYS:
                    other_text_ok += 1
                else:
                    other_nontext_ok += 1
        REPORT["identity"] = {
            "other_text_fields_identical": other_text_ok,
            "other_nontext_fields_identical": other_nontext_ok,
            "unexpected_changes": unexpected,
        }
        check(f"other {EXPECTED_OTHER_TEXT} text fields identical",
              other_text_ok, EXPECTED_OTHER_TEXT)
        check("no unexpected field changes", unexpected, [])

        # ── 6. GET /api/criteria (the forms' read route) ────────────────────
        status, body = call(args.base_url, "GET", "api/criteria", token)
        check("GET /api/criteria: 200", status, 200)
        data = (body or {}).get("data") or []
        got = {int(r["id"]): r for r in data}
        read_check = {}
        for cid in WRITE_ORDER:
            row = got.get(cid)
            ok_fields = {}
            for field, expected in patches[cid].items():
                actual = None if row is None else row.get(field)
                ok_fields[field] = actual == expected
                check(f"GET /api/criteria id {cid}.{field}", actual, expected)
            read_check[cid] = ok_fields
        REPORT["forms_read"] = {"status": status, "criteria_3_4_8_10_12": read_check}

        # ── 7. live state after writes ──────────────────────────────────────
        h1_after = json.loads(live_sql("""
          SELECT row_to_json(p) FROM (
            SELECT id, name, status, is_active, evaluation_started_at
            FROM performance_db.evaluation_periods WHERE id = 2) p"""))
        counts_after = {
            "evaluations": int(live_sql("SELECT count(*) FROM performance_db.evaluations")),
            "evaluation_scores": int(live_sql("SELECT count(*) FROM performance_db.evaluation_scores")),
            "score_corrections": int(live_sql("SELECT count(*) FROM performance_db.score_corrections")),
            "period_results": int(live_sql("SELECT count(*) FROM performance_db.period_results")),
        }
        REPORT["h1_after"] = h1_after
        REPORT["data_tables_after"] = counts_after
        check("H1 still active", (h1_after["status"], h1_after["is_active"]), ("active", True))
        check("H1 still not started", h1_after["evaluation_started_at"], None)
        check("data tables still empty", counts_after, counts)

    finally:
        deleted = live_sql(
            f"DELETE FROM performance_db.auth_sessions WHERE jti = '{ADMIN_JTI}' RETURNING jti")
        REPORT["probe_session_deleted"] = bool(deleted)
        sessions_after = int(live_sql("SELECT count(*) FROM performance_db.auth_sessions"))
        remaining = int(live_sql(
            f"SELECT count(*) FROM performance_db.auth_sessions WHERE jti = '{ADMIN_JTI}'"))
        REPORT["auth_sessions_after"] = sessions_after
        REPORT["probe_sessions_remaining"] = remaining
        check("probe session removed", remaining, 0)
        check("auth_sessions count restored", sessions_after, sessions_before)
        if local_dump.is_file() and local_dump.stat().st_size == vps_bytes:
            ssh(f"rm -f {vps_dump}")
            leftover = ssh(f"ls -1 {VPS_TMP} 2>/dev/null || true")
            REPORT["vps_tmp_after"] = leftover
            REPORT["vps_dump_removed"] = dump_name not in leftover

    REPORT["failures"] = FAILURES
    args.output.parent.mkdir(parents=True, exist_ok=True)
    slim = dict(REPORT)
    slim["before"] = {k: v for k, v in REPORT["before"].items() if k != "rows"}
    slim["after"] = {k: v for k, v in REPORT["after"].items() if k != "rows"}
    args.output.write_text(json.dumps(slim, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(slim, indent=2, ensure_ascii=False))
    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} CHECK(S) FAILED — see {args.output}")
    print("CATALOGUE FIX2 APPLIED AND PROVEN ON LIVE")


if __name__ == "__main__":
    main()

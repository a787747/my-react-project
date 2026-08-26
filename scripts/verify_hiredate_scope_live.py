#!/usr/bin/env python3
"""Read-only live verification for HIRE_DATE_AND_SCOPE_TOGGLE.

The only temporary live-DB write is one auth_sessions probe row, deleted in a
finally block. The pre-deploy dump is restored into a prefixed throwaway DB for
cell-by-cell comparison; no extension is created on live.
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
import uuid
from pathlib import Path
from typing import Any

HOST = "root@92.51.45.147"
BASE = "https://epe.sedamedical.com/webhook"
REPO = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []
REPORT: dict[str, Any] = {"checks": []}
SSL_CONTEXT = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST, command],
        capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", HOST,
         f"docker exec -i postgres_n8n psql -U admin -d {database} "
         "-v ON_ERROR_STOP=1 -tA"],
        input=statement.encode(), capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).decode("utf-8", "replace"))
    return result.stdout.decode().strip()


def jsql(database: str, statement: str) -> Any:
    return json.loads(sql(database, statement) or "null")


def check(name: str, actual: Any, expected: Any) -> None:
    ok = actual == expected
    REPORT["checks"].append(
        {"name": name, "actual": actual, "expected": expected, "ok": ok})
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def token(secret: str, jti: str, user_id: int, version: int) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "sub": str(user_id), "iss": "epe", "aud": "epe-api",
        "iat": now, "exp": now + 1800, "jti": jti,
    }).encode())
    signing = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(secret.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def call(method: str, path: str, bearer: str | None = None,
         body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{BASE}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(
            request, timeout=90, context=SSL_CONTEXT
        ) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--anchor",
        default="/root/epe_stand_tmp/"
                "epe_2026_prehiredatescope_20260826T085029Z.dump")
    parser.add_argument(
        "--out",
        default=str(REPO / "backups/2026-08-26-hiredate-scope/live_verify.json"))
    args = parser.parse_args()
    verify_db = f"epe_hireverify_{int(time.time())}"
    if not verify_db.startswith("epe_hireverify_"):
        raise SystemExit("unsafe verification database name")

    jti = str(uuid.uuid4())
    session_created = False
    try:
        ssh(
            f"docker exec postgres_n8n createdb -U admin {verify_db} && "
            f"docker exec -i postgres_n8n pg_restore -U admin -d {verify_db} "
            f"--no-owner < {args.anchor} || true")
        check("anchor restore has 89 users",
              int(sql(verify_db, "SELECT count(*) FROM performance_db.users")), 89)

        users_sql = """
          SELECT COALESCE(json_agg(row_to_json(u) ORDER BY u.id), '[]') FROM
            performance_db.users u
        """
        users_anchor = jsql(verify_db, users_sql)
        users_live = jsql("epe_2026", users_sql)
        user_columns = list(users_live[0].keys()) if users_live else []
        check("all user columns are the same before and after",
              user_columns, list(users_anchor[0].keys()) if users_anchor else [])
        changed_user_cells = []
        anchor_by_id = {row["id"]: row for row in users_anchor}
        for row in users_live:
            for column in user_columns:
                if row[column] != anchor_by_id[row["id"]][column]:
                    changed_user_cells.append(
                        f"{row['id']}.{column}: "
                        f"{anchor_by_id[row['id']][column]!r}->{row[column]!r}")
        REPORT["user_cells_compared"] = len(users_live) * len(user_columns)
        check("cell-by-cell user drift is empty", changed_user_cells, [])

        participants_sql = """
          SELECT COALESCE(json_agg(row_to_json(x) ORDER BY period_id, user_id), '[]')
          FROM (
            SELECT period_id, user_id, is_in_scope, exclusion_reason,
                   created_at, updated_at
            FROM performance_db.evaluation_period_participants
          ) x
        """
        check("every pre-existing participant cell is unchanged",
              jsql("epe_2026", participants_sql),
              jsql(verify_db, participants_sql))
        check("new scope_override starts empty on all live rows",
              int(sql("epe_2026", """
                SELECT count(*) FROM performance_db.evaluation_period_participants
                WHERE scope_override IS NOT NULL
              """)), 0)

        state = jsql("epe_2026", """
          SELECT json_build_object(
            'users', (SELECT count(*) FROM performance_db.users),
            'terminated', (SELECT count(*) FROM performance_db.users
                           WHERE terminated_at IS NOT NULL),
            'h1_in_scope', (SELECT count(*) FROM
              performance_db.evaluation_period_participants
              WHERE period_id=2 AND is_in_scope),
            'started', (SELECT count(*) FROM performance_db.evaluation_periods
                        WHERE evaluation_started_at IS NOT NULL),
            'evaluations', (SELECT count(*) FROM performance_db.evaluations),
            'scores', (SELECT count(*) FROM performance_db.evaluation_scores),
            'corrections', (SELECT count(*) FROM performance_db.score_corrections),
            'results', (SELECT count(*) FROM performance_db.period_results),
            'card_events', (SELECT count(*) FROM performance_db.employee_card_events),
            'scope_events', (SELECT count(*) FROM performance_db.period_scope_events),
            'extensions', (SELECT json_agg(extname ORDER BY extname) FROM pg_extension)
          )
        """)
        check("live state after deploy", state, {
            "users": 89, "terminated": 3, "h1_in_scope": 80, "started": 0,
            "evaluations": 0, "scores": 0, "corrections": 0, "results": 0,
            "card_events": 0, "scope_events": 4, "extensions": ["plpgsql"],
        })

        hashes = {
            "criteria": sql("epe_2026", """
              SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
                SELECT concat_ws('|', id, title, target_audience, weight,
                  c_level_only, selfassesment, for_manager, is_active) AS t
                FROM performance_db.criteria WHERE is_active=true
              ) x
            """),
            "score_coefficients": sql("epe_2026", """
              SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
                SELECT concat_ws('|', criteria_id, score_level, coefficient) AS t
                FROM performance_db.score_coefficients
              ) x
            """),
            "grades": sql("epe_2026", """
              SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
                SELECT concat_ws('|', id, code, coefficient,
                  coalesce(description, '')) AS t
                FROM performance_db.grades
              ) x
            """),
        }
        check("money inputs equal the dated snapshot", hashes, {
            "criteria": "fc618757f6aa2c27db5bce7613fc28c7",
            "score_coefficients": "317e09e8326edde500bfcde2bad81e78",
            "grades": "946b30a5ea8b8594321ebb5fc645bd32",
        })

        release = ssh("readlink /var/www/epe/current")
        check("frontend release", release, "releases/20260826T085259Z")

        secret = ssh("docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET")
        if not secret:
            raise RuntimeError("could not read JWT_SIGNING_SECRET")
        version = int(sql(
            "epe_2026",
            "SELECT token_version FROM performance_db.users WHERE id=2"))
        sql("epe_2026", f"""
          INSERT INTO performance_db.auth_sessions
            (jti, user_id, token_version, issued_at, expires_at)
          VALUES ('{jti}', 2, {version}, now(), now() + interval '30 minutes')
        """)
        session_created = True
        bearer = token(secret, jti, 2, version)

        status, periods = call("GET", "api/periods", bearer)
        h1 = next(row for row in periods["data"] if row["id"] == 2)
        check("period route confirms active pre-gate H1",
              [status, h1["status"], h1["is_active"],
               h1["evaluation_started"], h1["in_scope_count"],
               h1["participant_count"]],
              [200, "active", True, False, 80, 89])

        status, users = call("GET", "api/admin-users-data", bearer)
        check("admin roster returns all users and named period scopes",
              [status, len(users["users"]),
               all(isinstance(row.get("period_scopes"), list)
                   and len(row["period_scopes"]) == 3
                   for row in users["users"])],
              [200, 89, True])

        status, events = call(
            "GET", "api/admin/employee-events?user_id=2", bearer)
        check("unified employee event reader is live", [status, events["success"]],
              [200, True])
        status, required = call("GET", "api/admin/employee-events", bearer)
        check("unbounded event read is refused",
              [status, required.get("error")], [422, "USER_ID_REQUIRED"])

        before_user_2 = next(row for row in users["users"] if row["id"] == 2)
        status, partial = call("POST", "admin/save-user", bearer, {
            "id": 2, "full_name": before_user_2["full_name"],
            "email": before_user_2["email"],
        })
        check("partial whole-row write refuses without changing anything",
              [status, partial.get("error")], [422, "INCOMPLETE_USER_ROW"])
        check("partial refusal writes no card event",
              int(sql("epe_2026", "SELECT count(*) FROM "
                                   "performance_db.employee_card_events")), 0)

        status, unauth = call("GET", "api/admin/employee-events?user_id=2")
        check("new event reader is admin-authenticated",
              [status, unauth.get("error")], [401, "TOKEN_MISSING"])

        workflow_state = jsql("postgres", """
          SELECT json_build_object(
            'total', (SELECT count(*) FROM public.workflow_entity),
            'active', (SELECT count(*) FROM public.workflow_entity WHERE active),
            'archived', (SELECT count(*) FROM public.workflow_entity
                         WHERE "isArchived"),
            'webhooks', (SELECT count(*) FROM public.webhook_entity),
            'guard_updated', (SELECT to_char("updatedAt",
              'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') FROM public.workflow_entity
              WHERE id='L0Zr7nVa8O5YWXd3'),
            'guard_active', (SELECT active FROM public.workflow_entity
              WHERE id='L0Zr7nVa8O5YWXd3')
          )
        """)
        check("workflow inventory and frozen guard", workflow_state, {
            "total": 60, "active": 35, "archived": 22, "webhooks": 49,
            "guard_updated": "2026-08-18T16:34:30.674Z",
            "guard_active": False,
        })

    finally:
        if session_created:
            try:
                sql("epe_2026", f"DELETE FROM performance_db.auth_sessions "
                                f"WHERE jti='{jti}'")
            except Exception as exc:  # noqa: BLE001
                FAILURES.append(f"probe session cleanup failed: {exc}")
        try:
            if verify_db.startswith("epe_hireverify_"):
                sql(
                    "postgres",
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname='{verify_db}'")
                ssh(
                    f"docker exec postgres_n8n dropdb -U admin "
                    f"--if-exists {verify_db}")
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(f"verification database cleanup failed: {exc}")

    check("probe session was removed",
          int(sql("epe_2026", f"SELECT count(*) FROM performance_db.auth_sessions "
                              f"WHERE jti='{jti}'")), 0)
    check("throwaway verification database was dropped",
          int(sql("postgres", f"SELECT count(*) FROM pg_database "
                              f"WHERE datname='{verify_db}'")), 0)
    check("only live project databases remain",
          sql("postgres", """
            SELECT string_agg(datname, ',' ORDER BY datname)
            FROM pg_database WHERE NOT datistemplate
          """), "epe_2026,postgres")

    REPORT["failures"] = FAILURES
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
    passed = len(REPORT["checks"]) - len(FAILURES)
    print(f"{passed}/{len(REPORT['checks'])} checks passed -> {output}")
    for failure in FAILURES:
        print("  x", failure)
    raise SystemExit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()

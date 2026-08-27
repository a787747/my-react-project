#!/usr/bin/env python3
"""Verify PEER_RECOGNITION on LIVE, read-only (2026-08-27).

Live is a running campaign with real evaluations in it. This script therefore
stores NO nomination: every call it makes either reads, or is a save the route
must refuse — and a refused save writes zero rows, which is re-proved by
counting performance_db.peer_recognitions before and after.

The one live write it does make is the same one every previous live proof made:
short-lived `auth_sessions` rows for the actors it borrows, deleted in a
`finally` block. Session rows are explicitly not an invariant (HANDOVER §3).

    python3 scripts/verify_recognition_live.py --base https://epe.sedamedical.com/webhook
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid

import requests

SSH_HOST = "root@92.51.45.147"
PG = "postgres_n8n"
DB = "epe_2026"
N8N = "n8n-n8n-1"

COUNT_KEY = re.compile(
    r"count|total|tally|rank|rating|score|weight|coefficient|index|top|leader|badge",
    re.IGNORECASE)


def ssh(script: str) -> str:
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", SSH_HOST, "bash", "-s"],
                          input=script, text=True, capture_output=True)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout)[-4000:])
    return done.stdout


def sql(statement: str) -> str:
    quoted = statement.replace('"', '\\"')
    return ssh(f'docker exec {PG} psql -U admin -d {DB} -v ON_ERROR_STOP=1 -tA '
               f'-c "{quoted}"').strip()


def mint(actors: dict[str, int]) -> dict:
    jtis = {name: str(uuid.uuid4()) for name in actors}
    specs = json.dumps({name: {"sub": str(uid), "jti": jtis[name]}
                        for name, uid in actors.items()}, separators=(",", ":"))
    values = ",\n  ".join(f"('{jtis[name]}', {uid})" for name, uid in actors.items())
    script = f"""
set -euo pipefail
SECRET=$(docker exec {N8N} printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec {N8N} sh -c \
  "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
SPECS={json.dumps(specs)}
docker exec -e SECRET="$SECRET" -e SPECS="$SPECS" -e NODE_PATH="$JWTDIR" \
  {N8N} node -e '
const jwt = require("jsonwebtoken");
const now = Math.floor(Date.now()/1000);
const specs = JSON.parse(process.env.SPECS);
const out = {{}};
for (const [name, spec] of Object.entries(specs)) {{
  out[name] = jwt.sign(
    {{ sub: spec.sub, iss: "epe", aud: "epe-api", iat: now, exp: now + 900, jti: spec.jti }},
    process.env.SECRET, {{ algorithm: "HS256" }});
}}
process.stdout.write(JSON.stringify(out) + "\\n");
'
docker exec {PG} psql -U admin -d {DB} -v ON_ERROR_STOP=1 -c "
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
SELECT v.jti::uuid, v.user_id, u.token_version, now(), now() + interval '15 minutes'
FROM (VALUES
  {values}
) AS v(jti, user_id)
JOIN performance_db.users u ON u.id = v.user_id;"
"""
    tokens = json.loads(ssh(script).strip().splitlines()[0])
    tokens["_jtis"] = list(jtis.values())
    return tokens


def call(base, method, path, token=None, body=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.request(method, f"{base}{path}", headers=headers, json=body,
                            params=params, timeout=90)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text[:300]


def keys_of(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            keys_of(item, found)
    elif isinstance(value, list):
        for item in value:
            keys_of(item, found)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="https://epe.sedamedical.com/webhook")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    base = args.base.rstrip("/")

    report: dict = {}
    failures: list[str] = []

    def check(name, ok, **evidence):
        report.setdefault("checks", []).append({"check": name, "pass": bool(ok), **evidence})
        print(("ok    " if ok else "FAIL  ") + name
              + ("" if ok else ": " + json.dumps(evidence, ensure_ascii=False)[:400]))
        if not ok:
            failures.append(name)

    campaign_before = sql(
        "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results)")
    rows_before = sql("SELECT count(*) FROM performance_db.peer_recognitions")
    report["campaign_before"] = campaign_before
    report["peer_recognitions_before"] = rows_before

    # Unauthenticated first — no session needed, no write possible.
    for path in ("/api/recognition/form", "/api/recognition/list"):
        status, body = call(base, "GET", path)
        check(f"unauthenticated GET {path} → 401 TOKEN_MISSING",
              status == 401 and isinstance(body, dict) and body.get("error") == "TOKEN_MISSING",
              status=status, body=body)
    status, body = call(base, "POST", "/api/recognition/save", None,
                        {"nominee_id": 1, "situation": "x", "action": "x", "outcome": "x"})
    check("unauthenticated POST save → 401 TOKEN_MISSING",
          status == 401 and isinstance(body, dict) and body.get("error") == "TOKEN_MISSING",
          status=status, body=body)

    # Actors: the admin, one c_level, the HR specialist and one ordinary
    # employee who is already registered. Read-only for all four.
    actors = {"admin": 2, "c_level": 47, "hr": 52, "employee": 70}
    report["actors"] = actors
    tokens = mint(actors)
    jtis = tokens.pop("_jtis")
    try:
        status, form = call(base, "GET", "/api/recognition/form", tokens["employee"])
        colleagues = {int(c["id"]) for c in form.get("colleagues", [])} if status == 200 else set()
        blocked = {int(b["id"]): b for b in form.get("blocked", [])} if status == 200 else {}
        report["form_employee"] = {
            "status": status,
            "period": form.get("period") if status == 200 else None,
            "colleagues": len(colleagues),
            "blocked": sorted((k, v["blocked_reason"]) for k, v in blocked.items()),
        }
        check("form 200 for an ordinary employee, bound to the open period",
              status == 200 and (form.get("period") or {}).get("id") == 2,
              status=status, period=form.get("period"))
        actor_manager = int(sql("SELECT manager_id FROM performance_db.users WHERE id = 70"))
        check("the actor, their manager and their reports are blocked, not offered",
              70 in blocked and blocked[70]["blocked_reason"] == "self"
              and actor_manager in blocked
              and blocked[actor_manager]["blocked_reason"] == "own_manager"
              and 70 not in colleagues and actor_manager not in colleagues,
              blocked=report["form_employee"]["blocked"], manager=actor_manager)
        terminated = [int(x) for x in sql(
            "SELECT string_agg(id::text, ' ') FROM performance_db.users "
            "WHERE terminated_at IS NOT NULL").split()]
        report["terminated_ids"] = terminated
        check("no terminated person is offered or blocked — they are simply absent",
              all(t not in colleagues and t not in blocked for t in terminated),
              terminated=terminated)

        # Refusals. Each of these writes zero rows; the count is re-checked below.
        cases = [
            ("self", "employee", 70, 422, "RECOGNITION_SELF"),
            ("own manager", "employee", actor_manager, 422, "RECOGNITION_OWN_MANAGER"),
            ("terminated", "employee", terminated[0], 422, "NOMINEE_TERMINATED"),
            ("unknown user", "employee", 999999, 404, "NOMINEE_NOT_FOUND"),
        ]
        report["refusals"] = []
        for label, actor, nominee, want, code in cases:
            status, body = call(base, "POST", "/api/recognition/save", tokens[actor],
                                {"nominee_id": nominee,
                                 "situation": "LIVE VERIFY — must be refused",
                                 "action": "LIVE VERIFY — must be refused",
                                 "outcome": "LIVE VERIFY — must be refused"})
            report["refusals"].append({"case": label, "nominee_id": nominee,
                                       "status": status,
                                       "error": body.get("error") if isinstance(body, dict) else body,
                                       "message": body.get("message") if isinstance(body, dict) else None})
            check(f"live save refused — {label}",
                  status == want and isinstance(body, dict) and body.get("error") == code,
                  status=status, want=want, body=body)

        # Readers.
        report["reader_matrix"] = {}
        for role, want in (("admin", 200), ("c_level", 200), ("hr", 403), ("employee", 403)):
            status, body = call(base, "GET", "/api/recognition/list", tokens[role])
            code = body.get("error") if isinstance(body, dict) else None
            report["reader_matrix"][role] = {"user_id": actors[role], "status": status,
                                             "error": code,
                                             "rows": len(body.get("recognitions", []))
                                             if status == 200 else None}
            check(f"live list as {role} → {want}",
                  status == want and (want == 200 or code == "ROLE_FORBIDDEN"),
                  status=status, error=code)

        # No count-shaped key in any live recognition payload.
        _, listing = call(base, "GET", "/api/recognition/list", tokens["admin"])
        offenders = {}
        for label, payload in (("form", form), ("list", listing)):
            found: set[str] = set()
            keys_of(payload, found)
            hits = sorted(k for k in found if COUNT_KEY.search(k))
            if hits:
                offenders[label] = hits
        report["count_like_keys"] = offenders
        check("no count / rank / total key in any live recognition payload",
              not offenders, offenders=offenders)
    finally:
        listed = ",".join(f"'{j}'::uuid" for j in jtis)
        ssh(f'docker exec {PG} psql -U admin -d {DB} -v ON_ERROR_STOP=1 '
            f'-c "DELETE FROM performance_db.auth_sessions WHERE jti IN ({listed});"')

    rows_after = sql("SELECT count(*) FROM performance_db.peer_recognitions")
    campaign_after = sql(
        "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results)")
    started = sql("SELECT COALESCE(to_char(evaluation_started_at AT TIME ZONE 'UTC',"
                  "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'),'null') "
                  "FROM performance_db.evaluation_periods WHERE id = 2")
    report.update({"peer_recognitions_after": rows_after,
                   "campaign_after": campaign_after,
                   "evaluation_started_at": started})
    check("this verification stored ZERO nominations on live",
          rows_after == rows_before == "0", before=rows_before, after=rows_after)
    check("evaluation_started_at unchanged",
          started == "2026-08-26T10:08:54.340312Z", value=started)
    report["campaign_moved"] = campaign_before != campaign_after
    print(f"\ncampaign tables: {campaign_before} → {campaign_after} "
          f"({'MOVED — real employees are working' if report['campaign_moved'] else 'unchanged'})")

    report["verdict"] = "PASS" if not failures else "FAIL"
    report["failed"] = failures
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"{report['verdict']}  ({len(report.get('checks', []))} checks, {len(failures)} failed)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

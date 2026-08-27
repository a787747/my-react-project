#!/usr/bin/env python3
"""Verify the withdraw route on LIVE, without storing or deleting a nomination.

THE CAMPAIGN IS OPEN. Real employees may have nominated by the time this
runs. This script therefore never calls withdraw without a recognition_id
that cannot be the caller's own live row: unauthenticated, a missing id,
a fabricated id, and — if any live row exists that is not the actor's —
that foreign id. Each of those must refuse. The table count before and
after is the proof that nothing was removed.

    python3 scripts/verify_recognition_withdraw_live.py \
        --base https://epe.sedamedical.com/webhook
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid

import requests

SSH_HOST = "root@92.51.45.147"
PG = "postgres_n8n"
DB = "epe_2026"
N8N = "n8n-n8n-1"


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


def call(base, method, path, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.request(method, f"{base}{path}", headers=headers, json=body,
                            timeout=90)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text[:300]


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

    rows_before = sql(
        "SELECT count(*) || '|' || COALESCE(string_agg(id::text, ',' ORDER BY id), '') "
        "FROM performance_db.peer_recognitions")
    campaign_before = sql(
        "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results)")
    started_before = sql(
        "SELECT evaluation_started_at::text FROM performance_db.evaluation_periods WHERE id = 2")
    report.update({
        "peer_recognitions_before": rows_before,
        "campaign_before": campaign_before,
        "started_before": started_before,
    })

    status, body = call(base, "POST", "/api/recognition/withdraw",
                        None, {"recognition_id": 1})
    check("unauthenticated withdraw → 401 TOKEN_MISSING",
          status == 401 and isinstance(body, dict) and body.get("error") == "TOKEN_MISSING",
          status=status, body=body)

    actors = {"employee": 70, "other": 31, "c_level": 47, "admin": 2}
    tokens = mint(actors)
    jtis = tokens.pop("_jtis")
    try:
        status, form = call(base, "GET", "/api/recognition/form", tokens["employee"])
        check("form still 200 for an ordinary employee",
              status == 200 and (form.get("period") or {}).get("id") == 2,
              status=status, period=form.get("period"))

        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["employee"], {})
        check("missing recognition_id → 422 INVALID_RECOGNITION_ID",
              status == 422 and isinstance(body, dict)
              and body.get("error") == "INVALID_RECOGNITION_ID",
              status=status, body=body)

        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["employee"], {"recognition_id": 999_999})
        check("fabricated id → 404 RECOGNITION_NOT_FOUND",
              status == 404 and isinstance(body, dict)
              and body.get("error") == "RECOGNITION_NOT_FOUND",
              status=status, body=body)

        # If a live nomination exists that is NOT author 70, 70 withdrawing
        # that id must be 403 and must not delete it. If the only live row
        # is 70's own, we do not call withdraw on it.
        foreign = sql(
            "SELECT COALESCE(min(id)::text, '') FROM performance_db.peer_recognitions "
            "WHERE author_id <> 70")
        report["foreign_live_id"] = foreign
        if foreign:
            status, body = call(base, "POST", "/api/recognition/withdraw",
                                tokens["employee"], {"recognition_id": int(foreign)})
            check("live foreign id → 403 RECOGNITION_NOT_OWN",
                  status == 403 and isinstance(body, dict)
                  and body.get("error") == "RECOGNITION_NOT_OWN",
                  status=status, body=body)
        else:
            check("no foreign live nomination to probe — skipped 403 case", True,
                  note="peer_recognitions has no row with author_id <> 70")

        status, listing = call(base, "GET", "/api/recognition/list", tokens["c_level"])
        check("c_level list still 200", status == 200, status=status)
        report["live_list_rows"] = len(listing.get("recognitions", [])) if status == 200 else None
    finally:
        listed = ",".join(f"'{j}'::uuid" for j in jtis)
        ssh(f'docker exec {PG} psql -U admin -d {DB} -v ON_ERROR_STOP=1 '
            f'-c "DELETE FROM performance_db.auth_sessions WHERE jti IN ({listed});"')

    rows_after = sql(
        "SELECT count(*) || '|' || COALESCE(string_agg(id::text, ',' ORDER BY id), '') "
        "FROM performance_db.peer_recognitions")
    campaign_after = sql(
        "SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' || "
        "(SELECT count(*) FROM performance_db.evaluation_scores) || '/' || "
        "(SELECT count(*) FROM performance_db.score_corrections) || '/' || "
        "(SELECT count(*) FROM performance_db.period_results)")
    started_after = sql(
        "SELECT evaluation_started_at::text FROM performance_db.evaluation_periods WHERE id = 2")
    report.update({
        "peer_recognitions_after": rows_after,
        "campaign_after": campaign_after,
        "started_after": started_after,
    })
    check("this verification deleted ZERO nominations on live",
          rows_after == rows_before, before=rows_before, after=rows_after)
    check("evaluation_started_at unchanged",
          started_after == started_before == "2026-08-26 10:08:54.340312+00",
          before=started_before, after=started_after)
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

#!/usr/bin/env python3
"""Live TALK acceptance: role matrix plus authorised admin 0→1→read→0 smoke."""
from __future__ import annotations

import argparse
import json
import subprocess
import uuid

import requests

ACTORS = {"admin": 2, "c_level": 47, "hr": 52, "manager": 15, "employee": 70}


def ssh(script):
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", "root@92.51.45.147", "bash", "-s"],
                          input=script, text=True, capture_output=True)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout)[-5000:])
    return done.stdout.strip()


def sql(statement):
    return ssh(f"""docker exec -i postgres_n8n psql -U admin -d epe_2026 -tA -v ON_ERROR_STOP=1 <<'SQL'
{statement}
SQL""")


def call(base, method, path, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.request(method, f"{base.rstrip('/')}{path}", headers=headers,
                                json=body, timeout=90)
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, response.text[:500]


def mint():
    jtis = {name: str(uuid.uuid4()) for name in ACTORS}
    specs = json.dumps({name: {"sub": str(uid), "jti": jtis[name]}
                        for name, uid in ACTORS.items()}, separators=(",", ":"))
    values = ",\n".join(f"('{jtis[name]}', {uid})" for name, uid in ACTORS.items())
    output = ssh(f"""
set -euo pipefail
SECRET=$(docker exec n8n-n8n-1 printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec n8n-n8n-1 sh -c "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
docker exec -i -e SECRET="$SECRET" -e SPECS='{specs}' -e NODE_PATH="$JWTDIR" n8n-n8n-1 node - <<'JS'
const jwt = require('jsonwebtoken');
const specs = JSON.parse(process.env.SPECS);
const now = Math.floor(Date.now()/1000), out = {{}};
for (const [name, spec] of Object.entries(specs)) out[name] = jwt.sign(
  {{sub:spec.sub,iss:'epe',aud:'epe-api',iat:now,exp:now+1800,jti:spec.jti}},
  process.env.SECRET, {{algorithm:'HS256'}});
console.log(JSON.stringify(out));
JS
docker exec -i postgres_n8n psql -U admin -d epe_2026 -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO performance_db.auth_sessions (jti,user_id,token_version,issued_at,expires_at)
SELECT v.jti::uuid,v.user_id,u.token_version,now(),now()+interval '30 minutes'
FROM (VALUES {values}) v(jti,user_id) JOIN performance_db.users u ON u.id=v.user_id;
SQL
""")
    return json.loads(output.splitlines()[0]), list(jtis.values())


def campaign():
    return sql("""
SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
       (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
       (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
       (SELECT count(*) FROM performance_db.period_results) || '|' ||
       (SELECT evaluation_started_at::text FROM performance_db.evaluation_periods WHERE id=2);
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://epe.sedamedical.com/webhook")
    parser.add_argument("--out")
    args = parser.parse_args()
    checks, failed = [], 0

    def check(name, ok, **evidence):
        nonlocal failed
        checks.append({"check": name, "pass": bool(ok), **evidence})
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            failed += 1

    campaign_before = campaign()
    initial = sql("""
SELECT count(*) FROM performance_db.management_talk_responses r
JOIN performance_db.management_talk_waves w ON w.id=r.wave_id
WHERE w.wave_key='talk-2026-wave-1' AND r.responder_id=2;
""")
    if initial != "0":
        raise SystemExit("Refusing live smoke: admin already has a real TALK response")
    tokens, jtis = mint()
    wrote = False
    try:
        matrix = {}
        for role, wanted in {"admin": 200, "c_level": 403, "hr": 403,
                             "manager": 403, "employee": 403}.items():
            status, body = call(args.base, "GET", "/api/talk/list", tokens[role])
            matrix[role] = {"status": status, "error": body.get("error")}
            check(f"reader {role} {wanted}", status == wanted, found=matrix[role])
        status, body = call(args.base, "GET", "/api/talk/list")
        matrix["unauthenticated"] = {"status": status, "error": body.get("error")}
        check("reader unauthenticated 401 TOKEN_MISSING",
              status == 401 and body.get("error") == "TOKEN_MISSING",
              found=matrix["unauthenticated"])

        status, saved = call(args.base, "POST", "/api/talk/save", tokens["admin"], {
            "answer_key": "all_good", "topic_key": None, "counterpart_mode": "none",
            "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None,
        })
        wrote = status == 200
        count_saved = sql("""
SELECT count(*) FROM performance_db.management_talk_responses r
JOIN performance_db.management_talk_waves w ON w.id=r.wave_id
WHERE w.wave_key='talk-2026-wave-1' AND r.responder_id=2;
""")
        check("admin save 0 -> 1", status == 200 and count_saved == "1",
              status=status, body=saved, before=initial, after=count_saved)

        read_status, form = call(args.base, "GET", "/api/talk/form", tokens["admin"])
        read_value = form.get("my_response", {}).get("answer_key") if isinstance(form, dict) else None
        check("admin reads saved answer back", read_status == 200 and read_value == "all_good",
              status=read_status, value=read_value)

        withdraw_status, withdrawn = call(args.base, "POST", "/api/talk/withdraw", tokens["admin"])
        count_withdrawn = sql("""
SELECT count(*) FROM performance_db.management_talk_responses r
JOIN performance_db.management_talk_waves w ON w.id=r.wave_id
WHERE w.wave_key='talk-2026-wave-1' AND r.responder_id=2;
""")
        wrote = False if count_withdrawn == "0" else wrote
        check("admin withdraw 1 -> 0", withdraw_status == 200 and count_withdrawn == "0",
              status=withdraw_status, body=withdrawn, before=count_saved, after=count_withdrawn)
        smoke = {
            "before": int(initial), "after_save": int(count_saved),
            "read_back": read_value, "after_withdraw": int(count_withdrawn),
        }
    finally:
        # This can only delete the row this script created: the script refused
        # to start unless the admin had zero rows.
        if wrote:
            sql("""
DELETE FROM performance_db.management_talk_responses r USING performance_db.management_talk_waves w
WHERE r.wave_id=w.id AND w.wave_key='talk-2026-wave-1' AND r.responder_id=2;
""")
        ids = ",".join(f"'{value}'::uuid" for value in jtis)
        sql(f"DELETE FROM performance_db.auth_sessions WHERE jti IN ({ids});")

    campaign_after = campaign()
    check("campaign values untouched by smoke", campaign_before == campaign_after,
          before=campaign_before, after=campaign_after)
    report = {
        "reader_matrix": matrix, "admin_smoke": smoke,
        "campaign_before": campaign_before, "campaign_after": campaign_after,
        "checks": checks, "failed": failed,
    }
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"checks": len(checks), "failed": failed, "admin_smoke": smoke}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

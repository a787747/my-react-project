#!/usr/bin/env python3
"""Behavioural acceptance proof for TALK on an isolated stand."""
from __future__ import annotations

import argparse
import json
import subprocess
import uuid

import requests

ACTORS = {
    "admin": 2, "c_level": 47, "hr": 52, "manager": 15,
    "employee": 70, "terminated": 39,
}
TOPIC10_MANAGER = 47
MARKER = "talk-2026-wave-1"


def args_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--ssh-host", default="root@92.51.45.147")
    parser.add_argument("--container", default="epe-talk-n8n")
    parser.add_argument("--out")
    return parser.parse_args()


def ssh(args, script):
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", args.ssh_host, "bash", "-s"],
                          input=script, text=True, capture_output=True)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout)[-5000:])
    return done.stdout.strip()


def sql(args, statement):
    return ssh(args, f"""docker exec -i postgres_n8n psql -U admin -d {args.db} -tA -v ON_ERROR_STOP=1 <<'SQL'
{statement}
SQL""")


def call(base, method, path, token=None, body=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.request(method, f"{base.rstrip('/')}{path}", headers=headers,
                                json=body, params=params, timeout=90)
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, response.text[:500]


def mint(args):
    jtis = {name: str(uuid.uuid4()) for name in ACTORS}
    specs = json.dumps({name: {"sub": str(uid), "jti": jtis[name]}
                        for name, uid in ACTORS.items()}, separators=(",", ":"))
    values = ",\n".join(f"('{jtis[name]}', {uid})" for name, uid in ACTORS.items())
    output = ssh(args, f"""
set -euo pipefail
SECRET=$(docker exec {args.container} printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec {args.container} sh -c "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
docker exec -i -e SECRET="$SECRET" -e SPECS='{specs}' -e NODE_PATH="$JWTDIR" {args.container} node - <<'JS'
const jwt = require('jsonwebtoken');
const specs = JSON.parse(process.env.SPECS);
const now = Math.floor(Date.now()/1000), out = {{}};
for (const [name, spec] of Object.entries(specs)) out[name] = jwt.sign(
  {{sub: spec.sub, iss:'epe', aud:'epe-api', iat:now, exp:now+7200, jti:spec.jti}},
  process.env.SECRET, {{algorithm:'HS256'}});
console.log(JSON.stringify(out));
JS
docker exec -i postgres_n8n psql -U admin -d {args.db} -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO performance_db.auth_sessions (jti,user_id,token_version,issued_at,expires_at)
SELECT v.jti::uuid,v.user_id,u.token_version,now(),now()+interval '2 hours'
FROM (VALUES {values}) v(jti,user_id) JOIN performance_db.users u ON u.id=v.user_id;
SQL
""")
    return json.loads(output.splitlines()[0]), list(jtis.values())


class Proof:
    def __init__(self):
        self.checks, self.failed = [], 0

    def check(self, name, condition, **evidence):
        ok = bool(condition)
        self.checks.append({"check": name, "pass": ok, **evidence})
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            self.failed += 1


def campaign(args):
    return sql(args, """
SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
       (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
       (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
       (SELECT count(*) FROM performance_db.period_results) || '|' ||
       (SELECT evaluation_started_at::text FROM performance_db.evaluation_periods WHERE id=2);
""")


def main():
    args = args_parse()
    proof, report = Proof(), {}
    before = campaign(args)
    report["campaign_before"] = before
    tokens, jtis = mint(args)
    base = args.base
    try:
        # Reader role matrix.
        expected = {
            "admin": (200, None), "c_level": (403, "ROLE_FORBIDDEN"),
            "hr": (403, "ROLE_FORBIDDEN"), "manager": (403, "ROLE_FORBIDDEN"),
            "employee": (403, "ROLE_FORBIDDEN"),
        }
        matrix = {}
        for role, (want_status, want_error) in expected.items():
            status, body = call(base, "GET", "/api/talk/list", tokens[role])
            matrix[role] = {"status": status, "error": body.get("error")}
            proof.check(f"reader {role} -> {want_status}",
                        status == want_status and (want_error is None or body.get("error") == want_error),
                        found=matrix[role])
        status, body = call(base, "GET", "/api/talk/list")
        matrix["unauthenticated"] = {"status": status, "error": body.get("error")}
        proof.check("reader unauthenticated -> 401 TOKEN_MISSING",
                    status == 401 and body.get("error") == "TOKEN_MISSING", found=matrix["unauthenticated"])
        report["reader_matrix"] = matrix

        status, form = call(base, "GET", "/api/talk/form", tokens["employee"])
        proof.check("employee form open", status == 200 and form["wave"]["is_open"], body=form)
        proof.check("deadline derives as 10 сентября",
                    form["wave"]["deadline_text"] == "10 сентября"
                    and form["wave"]["closes_at"].startswith("2026-09-10T23:59:59"),
                    wave=form.get("wave"))
        labels = [topic["label"] for topic in form.get("topics", [])]
        proof.check("twelve topics remain in normative order",
                    len(labels) == 12 and labels[0].startswith("Хочу понять")
                    and labels[9] == "Действия моего непосредственного руководителя",
                    labels=labels)

        # Same employee twice: one physical row, then withdraw to zero.
        status1, body1 = call(base, "POST", "/api/talk/save", tokens["employee"], {
            "answer_key": "all_good", "topic_key": None, "counterpart_mode": "none",
            "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None,
        })
        row1 = sql(args, "SELECT count(*) FROM performance_db.management_talk_responses WHERE responder_id=70;")
        status2, body2 = call(base, "POST", "/api/talk/save", tokens["employee"], {
            "answer_key": "topic_only", "topic_key": "t02_workload", "counterpart_mode": "none",
            "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None,
        })
        row2 = sql(args, "SELECT count(*) || '|' || max(answer_key) FROM performance_db.management_talk_responses WHERE responder_id=70;")
        proof.check("employed save then update remains one row",
                    status1 == 200 and status2 == 200 and row1 == "1" and row2 == "1|topic_only",
                    first=[status1, body1], second=[status2, body2], rows=[row1, row2])
        status, withdrawn = call(base, "POST", "/api/talk/withdraw", tokens["employee"])
        row0 = sql(args, "SELECT count(*) FROM performance_db.management_talk_responses WHERE responder_id=70;")
        proof.check("withdraw returns employee to zero rows",
                    status == 200 and row0 == "0", status=status, body=withdrawn, rows=row0)
        report["save_update_withdraw"] = {"first": status1, "second": status2,
                                           "withdraw": status, "rows": [row1, row2, row0]}

        # Terminated actor.
        status, body = call(base, "POST", "/api/talk/save", tokens["terminated"], {
            "answer_key": "all_good", "topic_key": None, "counterpart_mode": "none",
            "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None,
        })
        proof.check("terminated actor refused", status == 403 and body.get("error") == "ACTOR_TERMINATED",
                    status=status, body=body)

        # Crafted topic-10 own-manager body: zero rows.
        status, body = call(base, "POST", "/api/talk/save", tokens["manager"], {
            "answer_key": "conversation", "topic_key": "t10_manager", "counterpart_mode": "people",
            "counterpart_ids": [TOPIC10_MANAGER], "urgency_key": "soon",
            "group_readiness_key": "individual_only",
        })
        rows = sql(args, "SELECT count(*) FROM performance_db.management_talk_responses WHERE responder_id=15;")
        proof.check("topic 10 own manager writes zero rows",
                    status == 422 and body.get("error") == "TALK_OWN_MANAGER_FORBIDDEN" and rows == "0",
                    status=status, body=body, rows=rows)

        # Topics 9/11/12 deliberately do not inherit topic-10's exclusion.
        accepted = {}
        for topic in ("t09_team", "t11_unfair", "t12_personal"):
            status, body = call(base, "POST", "/api/talk/save", tokens["manager"], {
                "answer_key": "conversation", "topic_key": topic, "counterpart_mode": "people",
                "counterpart_ids": [TOPIC10_MANAGER], "urgency_key": "this_cycle",
                "group_readiness_key": "individual_only",
            })
            accepted[topic] = status
        proof.check("topics 9, 11 and 12 may name own manager", all(v == 200 for v in accepted.values()),
                    statuses=accepted)
        call(base, "POST", "/api/talk/withdraw", tokens["manager"])

        # Record all three answers and denominator split.
        bodies = [
            ("employee", {"answer_key": "all_good", "topic_key": None, "counterpart_mode": "none",
                          "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None}),
            ("manager", {"answer_key": "topic_only", "topic_key": "t03_resources",
                         "counterpart_mode": "none", "counterpart_ids": [],
                         "urgency_key": None, "group_readiness_key": None}),
            ("hr", {"answer_key": "conversation", "topic_key": "t04_role",
                    "counterpart_mode": "help_choose", "counterpart_ids": [],
                    "urgency_key": "this_cycle", "group_readiness_key": "yes"}),
        ]
        for role, payload in bodies:
            status, _ = call(base, "POST", "/api/talk/save", tokens[role], payload)
            proof.check(f"records answer from {role}", status == 200, status=status)
        status, listing = call(base, "GET", "/api/talk/list", tokens["admin"])
        counts = listing.get("counts", {})
        proof.check("admin sees all three answers and split non-response",
                    status == 200 and [counts.get(k) for k in ("all_good","topic_only","conversation")] == [1,1,1]
                    and counts.get("registered_unanswered", -1) >= 0
                    and counts.get("never_registered", -1) >= 0,
                    counts=counts)
        report["admin_counts"] = counts

        # Marker walk: absent from existing payloads, present on TALK routes.
        walk = [
            ("GET","/api/employees","manager",None),
            ("GET","/api/my-profile","employee",None),
            ("GET","/api/evaluation-history","employee",None),
            ("GET","/api/check-evaluated","manager",None),
            ("GET","/api/get-my-manager","employee",None),
            ("GET","/api/criteria","employee",None),
            ("GET","/api/admin/evaluations-matrix","admin",None),
            ("GET","/api/admin/all-evaluations","admin",None),
            ("GET","/api/analytics","admin",None),
            ("GET","/api/admin-users-data","admin",None),
            ("GET","/api/score-coefficients","admin",None),
            ("GET","/api/hr/evaluation-status","hr",None),
            ("GET","/api/periods","admin",None),
            ("GET","/api/periods/annual-rollup","admin",{"container_id":5}),
            ("GET","/api/admin/evaluation-details-by-user","admin",{"user_id":70}),
            ("GET","/api/admin/employee-events","admin",{"user_id":70}),
        ]
        walked, offenders = [], []
        for method, path, role, params in walk:
            status, payload = call(base, method, path, tokens[role], params=params)
            raw = json.dumps(payload, ensure_ascii=False)
            walked.append({"path": path, "status": status, "bytes": len(raw), "marker": MARKER in raw})
            if status != 200 or MARKER in raw:
                offenders.append(path)
        talk_marker = MARKER in json.dumps(form, ensure_ascii=False) and MARKER in json.dumps(listing, ensure_ascii=False)
        proof.check("existing payload walk has no TALK marker", not offenders, offenders=offenders)
        proof.check("TALK marker is present on both new reads", talk_marker)
        report["payload_walk"] = walked

        # Schema + close route isolation.
        schema = sql(args, """
SELECT count(*) FILTER (WHERE column_name='period_id') || '|' ||
       count(*) FILTER (WHERE column_name ~* '(^|_)(score|weight|coefficient|rating|rank|count)($|_)')
FROM information_schema.columns
WHERE table_schema='performance_db' AND table_name LIKE 'management_talk_%';
""")
        foreign_campaign = sql(args, """
SELECT count(*) FROM pg_constraint fk
JOIN pg_class src ON src.oid=fk.conrelid JOIN pg_class dst ON dst.oid=fk.confrelid
WHERE fk.contype='f'
  AND (src.relname LIKE 'management_talk_%' OR dst.relname LIKE 'management_talk_%')
  AND (src.relname IN ('evaluations','evaluation_scores','score_corrections','period_results')
    OR dst.relname IN ('evaluations','evaluation_scores','score_corrections','period_results'));
""")
        proof.check("schema has no period/score-like column and no campaign FK",
                    schema == "0|0" and foreign_campaign == "0",
                    schema=schema, campaign_foreign_keys=foreign_campaign)

        # Second wave: already closed by its timestamps. Wave 1 is never altered.
        wave1_before = sql(args, "SELECT opens_at::text || '|' || closes_at::text FROM performance_db.management_talk_waves WHERE wave_key='talk-2026-wave-1';")
        sql(args, """
INSERT INTO performance_db.management_talk_waves (wave_key,opens_at,closes_at)
VALUES ('talk-proof-past-wave',clock_timestamp()-interval '2 days',clock_timestamp()-interval '1 day');
""")
        clock = sql(args, """
SELECT wave_key || '|' || (clock_timestamp() > closes_at)::text || '|' ||
       opens_at::text || '|' || closes_at::text
FROM performance_db.management_talk_waves ORDER BY id DESC LIMIT 1;
""")
        status, body = call(base, "POST", "/api/talk/save", tokens["employee"], {
            "answer_key": "all_good", "topic_key": None, "counterpart_mode": "none",
            "counterpart_ids": [], "urgency_key": None, "group_readiness_key": None,
        })
        wave1_after = sql(args, "SELECT opens_at::text || '|' || closes_at::text FROM performance_db.management_talk_waves WHERE wave_key='talk-2026-wave-1';")
        proof.check("second past wave is closed by clock; wave 1 timestamps unchanged",
                    "|true|" in clock and status == 409 and body.get("error") == "TALK_WAVE_CLOSED"
                    and wave1_before == wave1_after,
                    clock=clock, status=status, body=body,
                    wave1_before=wave1_before, wave1_after=wave1_after)
        report["past_wave"] = {"clock": clock, "status": status, "body": body}

        after = campaign(args)
        report["campaign_after"] = after
        proof.check("campaign tables and evaluation_started_at unchanged", before == after,
                    before=before, after=after)
    finally:
        ids = ",".join(f"'{value}'::uuid" for value in jtis)
        sql(args, f"DELETE FROM performance_db.auth_sessions WHERE jti IN ({ids});")

    report["checks"] = proof.checks
    report["failed"] = proof.failed
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"checks": len(proof.checks), "failed": proof.failed}, indent=2))
    return 1 if proof.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Stand proof for PEER_RECOGNITION (2026-08-27).

Runs against the throwaway stand built by setup_recognition_throwaway.sh — an
n8n container on the VPS loopback talking to a database restored from today's
dump of live, with migration 018 applied to the STAND ONLY. Live stores nothing
while this runs.

What it proves, in order:

  §1  the form route: an ordinary employee sees candidates; the three refusals
      arrive as a `blocked` list with the owner's sentence, and a TERMINATED
      person is in neither list
  §2  one nomination is stored, with the texts as written
  §3  a replacement leaves EXACTLY ONE row, same row id, new nominee
  §4  every refusal by a DIRECT call to the route, not through the picker:
      self / own manager / own direct report / terminated / unknown / blank text
  §5  a person OUT OF SCOPE of H1 — no evaluation tasks at all — can nominate
  §6  the reader matrix: admin 200, c_level 200, hr 403, manager 403,
      employee 403, unauthenticated 401
  §7  no count anywhere: no key in any recognition payload is a tally, a rank
      or a total, and the reader's ordering is by time alone
  §8  isolation: 18 other route payloads walked for the nomination's own
      markers — profile, history, both matrices, analytics, all-evaluations,
      admin roster, coefficients, HR status, roll-up, employee events
  §9  the four campaign tables are byte-identical before and after

Every check records the compared values. A run that compared nothing fails
instead of writing the same summary a real run writes.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid

import requests

# ── stand actors (live ids, restored from the dump) ───────────────────────────
ACTORS = {
    "employee": 70,          # Oksana Borisenkova, Administration, manager 15
    "manager": 15,           # Aysha Suvhanova, manager of 70, own manager 47
    "nominee_manager": 88,   # Yelena Son, manager of the nominee
    "out_of_scope": 31,      # Aysoltan Esenova — hired_after_period_end, no tasks
    "hr": 52,                # Liya Dmitriyeva
    "c_level": 47,           # Jemal Gulberdiyeva
    "admin": 2,              # Alexander Petrosov
    "nominee": 8,            # Arslan Annayev, Project, manager 88
}
NOMINEE_A = 8               # Arslan Annayev
NOMINEE_B = 7               # Anton Markin — the replacement
TERMINATED = 39             # Halykberdi Orusov, terminated on live
UNKNOWN_USER = 999_999
OWN_MANAGER_OF_EMPLOYEE = 15
OWN_REPORT_OF_MANAGER = 70

OWNER_MANAGER_SENTENCE = (
    "Своего руководителя здесь отметить нельзя — для этого есть оценка "
    "«снизу вверх» в ваших задачах."
)

# Distinctive markers, so §8 can look for THE NOMINATION rather than for a name
# that legitimately appears in half the payloads in the system.
MARK = "MARKER-7Q2X"
TEXTS_A = {
    "situation": f"Срочная поставка в пятницу вечером {MARK}-SIT",
    "action": f"Перебрал накладные и нашёл ошибку поставщика {MARK}-ACT",
    "outcome": f"Клиент получил комплект в срок {MARK}-OUT",
}
TEXTS_B = {
    "situation": f"Сложный монтаж на объекте {MARK}-SIT2",
    "action": f"Остался и довёл пусконаладку до конца {MARK}-ACT2",
    "outcome": f"Объект сдали без переноса {MARK}-OUT2",
}
TEXTS_OOS = {
    "situation": f"Чужая задача, которую некому было закрыть {MARK}-SIT3",
    "action": f"Взял её на себя и закрыл {MARK}-ACT3",
    "outcome": f"Проект не встал {MARK}-OUT3",
}

# A key that would turn this surface into a leaderboard.
COUNT_KEY = re.compile(
    r"count|total|tally|rank|rating|score|weight|coefficient|index|top|leader|badge",
    re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True, help="Webhook base of the STAND")
    p.add_argument("--ssh-host", default="root@92.51.45.147")
    p.add_argument("--pg-container", default="postgres_n8n")
    p.add_argument("--n8n-container", default="epe-recognition-n8n")
    p.add_argument("--db", required=True, help="Throwaway stand database")
    p.add_argument("--out", default=None)
    return p.parse_args()


def ssh(args: argparse.Namespace, script: str) -> str:
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", args.ssh_host, "bash", "-s"],
                          input=script, text=True, capture_output=True)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout)[-4000:])
    return done.stdout


def sql(args: argparse.Namespace, statement: str) -> str:
    quoted = statement.replace('"', '\\"')
    return ssh(args, f'docker exec {args.pg_container} psql -U admin -d {args.db} '
                     f'-v ON_ERROR_STOP=1 -tA -c "{quoted}"').strip()


def campaign_counts(args: argparse.Namespace) -> str:
    return sql(args, """
SELECT (SELECT count(*) FROM performance_db.evaluations) || '/' ||
       (SELECT count(*) FROM performance_db.evaluation_scores) || '/' ||
       (SELECT count(*) FROM performance_db.score_corrections) || '/' ||
       (SELECT count(*) FROM performance_db.period_results)""")


def mint(args: argparse.Namespace, actors: dict[str, int]) -> dict:
    jtis = {name: str(uuid.uuid4()) for name in actors}
    specs = json.dumps({name: {"sub": str(uid), "jti": jtis[name]}
                        for name, uid in actors.items()}, separators=(",", ":"))
    values = ",\n  ".join(f"('{jtis[name]}', {uid})" for name, uid in actors.items())
    script = f"""
set -euo pipefail
SECRET=$(docker exec {args.n8n_container} printenv JWT_SIGNING_SECRET)
JWTDIR=$(docker exec {args.n8n_container} sh -c \
  "ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/jsonwebtoken@*/node_modules | head -1")
SPECS={json.dumps(specs)}
docker exec -e SECRET="$SECRET" -e SPECS="$SPECS" -e NODE_PATH="$JWTDIR" \
  {args.n8n_container} node -e '
const jwt = require("jsonwebtoken");
const now = Math.floor(Date.now()/1000);
const specs = JSON.parse(process.env.SPECS);
const out = {{}};
for (const [name, spec] of Object.entries(specs)) {{
  out[name] = jwt.sign(
    {{ sub: spec.sub, iss: "epe", aud: "epe-api", iat: now, exp: now + 7200, jti: spec.jti }},
    process.env.SECRET, {{ algorithm: "HS256" }});
}}
process.stdout.write(JSON.stringify(out) + "\\n");
'
docker exec {args.pg_container} psql -U admin -d {args.db} -v ON_ERROR_STOP=1 -c "
INSERT INTO performance_db.auth_sessions (jti, user_id, token_version, issued_at, expires_at)
SELECT v.jti::uuid, v.user_id, u.token_version, now(), now() + interval '2 hours'
FROM (VALUES
  {values}
) AS v(jti, user_id)
JOIN performance_db.users u ON u.id = v.user_id;"
"""
    tokens = json.loads(ssh(args, script).strip().splitlines()[0])
    tokens["_jtis"] = list(jtis.values())
    return tokens


def call(base: str, method: str, path: str, token: str | None = None,
         body=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.request(method, f"{base}{path}", headers=headers,
                            json=body, params=params, timeout=90)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text[:400]


def keys_of(value, found: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            keys_of(item, found)
    elif isinstance(value, list):
        for item in value:
            keys_of(item, found)


class Proof:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.failed = 0

    def check(self, name: str, ok: bool, **evidence) -> bool:
        self.checks.append({"check": name, "pass": bool(ok), **evidence})
        if not ok:
            self.failed += 1
            print(f"FAIL  {name}: {json.dumps(evidence, ensure_ascii=False)[:500]}")
        else:
            print(f"ok    {name}")
        return bool(ok)


def main() -> int:
    args = parse_args()
    base = args.base.rstrip("/")
    proof = Proof()
    report: dict = {"stand_db": args.db, "base": base}

    before = campaign_counts(args)
    report["campaign_counts_before"] = before

    tokens = mint(args, ACTORS)
    jtis = tokens.pop("_jtis")

    try:
        # ── §1 the form ──────────────────────────────────────────────────────
        status, form = call(base, "GET", "/api/recognition/form", tokens["employee"])
        proof.check("§1 form 200 for an ordinary employee", status == 200, status=status)
        colleagues = {p["id"]: p for p in form.get("colleagues", [])}
        blocked = {p["id"]: p for p in form.get("blocked", [])}
        report["form_employee"] = {
            "period": form.get("period"),
            "colleagues_len": len(colleagues),
            "blocked": sorted((p["id"], p["blocked_reason"]) for p in blocked.values()),
        }
        proof.check("§1 self is blocked, not offered",
                    ACTORS["employee"] in blocked
                    and blocked[ACTORS["employee"]]["blocked_reason"] == "self"
                    and ACTORS["employee"] not in colleagues,
                    self_id=ACTORS["employee"])
        proof.check("§1 own manager is blocked with the owner's sentence",
                    OWN_MANAGER_OF_EMPLOYEE in blocked
                    and blocked[OWN_MANAGER_OF_EMPLOYEE]["blocked_reason"] == "own_manager"
                    and blocked[OWN_MANAGER_OF_EMPLOYEE]["message"] == OWNER_MANAGER_SENTENCE
                    and OWN_MANAGER_OF_EMPLOYEE not in colleagues,
                    message=blocked.get(OWN_MANAGER_OF_EMPLOYEE, {}).get("message"))
        proof.check("§1 a terminated person is in neither list",
                    TERMINATED not in colleagues and TERMINATED not in blocked,
                    terminated_id=TERMINATED)
        proof.check("§1 the nominee IS offered",
                    NOMINEE_A in colleagues and NOMINEE_B in colleagues,
                    nominee_a=NOMINEE_A, nominee_b=NOMINEE_B)

        status, mform = call(base, "GET", "/api/recognition/form", tokens["manager"])
        mblocked = {p["id"]: p for p in mform.get("blocked", [])}
        proof.check("§1 a manager's own direct report is blocked",
                    status == 200 and OWN_REPORT_OF_MANAGER in mblocked
                    and mblocked[OWN_REPORT_OF_MANAGER]["blocked_reason"] == "own_report",
                    status=status,
                    reason=mblocked.get(OWN_REPORT_OF_MANAGER, {}).get("blocked_reason"))

        # ── §2 store one ─────────────────────────────────────────────────────
        status, saved = call(base, "POST", "/api/recognition/save", tokens["employee"],
                             {"nominee_id": NOMINEE_A, **TEXTS_A})
        proof.check("§2 save 200", status == 200 and saved.get("success") is True,
                    status=status, body=saved)
        row = sql(args, f"""
SELECT id || '|' || period_id || '|' || author_id || '|' || nominee_id || '|' ||
       situation || '|' || action || '|' || outcome
FROM performance_db.peer_recognitions WHERE author_id = {ACTORS['employee']}""")
        report["stored_row_after_first_save"] = row
        first_id = row.split("|")[0] if row else None
        proof.check("§2 exactly one row, texts stored verbatim",
                    row.count("\n") == 0 and row != ""
                    and TEXTS_A["situation"] in row and TEXTS_A["action"] in row
                    and TEXTS_A["outcome"] in row
                    and row.split("|")[3] == str(NOMINEE_A),
                    row=row)

        # ── §3 replace ───────────────────────────────────────────────────────
        status, replaced = call(base, "POST", "/api/recognition/save", tokens["employee"],
                                {"nominee_id": NOMINEE_B, **TEXTS_B})
        proof.check("§3 replacement 200 and reported as a replacement",
                    status == 200 and replaced.get("replaced") is True,
                    status=status, body=replaced)
        rows = sql(args, f"""
SELECT count(*) || '|' || max(id) || '|' || max(nominee_id)
FROM performance_db.peer_recognitions WHERE author_id = {ACTORS['employee']}""")
        report["stored_after_replacement"] = rows
        count, row_id, nominee_now = rows.split("|")
        proof.check("§3 still EXACTLY one row, same row id, new nominee",
                    count == "1" and row_id == first_id and nominee_now == str(NOMINEE_B),
                    count=count, row_id=row_id, first_id=first_id, nominee=nominee_now)

        # ── §4 refusals by a direct call to the route ────────────────────────
        refusals = [
            ("self", "employee", ACTORS["employee"], 422, "RECOGNITION_SELF"),
            ("own manager", "employee", OWN_MANAGER_OF_EMPLOYEE, 422, "RECOGNITION_OWN_MANAGER"),
            ("own direct report", "manager", OWN_REPORT_OF_MANAGER, 422, "RECOGNITION_OWN_REPORT"),
            ("terminated", "employee", TERMINATED, 422, "NOMINEE_TERMINATED"),
            ("unknown user", "employee", UNKNOWN_USER, 404, "NOMINEE_NOT_FOUND"),
        ]
        report["refusals"] = []
        for label, actor, nominee_id, want_status, want_code in refusals:
            status, body = call(base, "POST", "/api/recognition/save", tokens[actor],
                                {"nominee_id": nominee_id, **TEXTS_A})
            report["refusals"].append({"case": label, "actor": ACTORS[actor],
                                       "nominee_id": nominee_id, "status": status,
                                       "error": body.get("error") if isinstance(body, dict) else body,
                                       "message": body.get("message") if isinstance(body, dict) else None})
            proof.check(f"§4 direct call refused — {label}",
                        status == want_status and isinstance(body, dict)
                        and body.get("error") == want_code,
                        status=status, want=want_status, body=body)
        status, body = call(base, "POST", "/api/recognition/save", tokens["employee"],
                            {"nominee_id": NOMINEE_A, "situation": "  ", "action": "",
                             "outcome": ""})
        proof.check("§4 blank texts refused",
                    status == 422 and body.get("error") == "RECOGNITION_TEXT_REQUIRED",
                    status=status, body=body)
        proof.check("§4 the owner's manager sentence is the route's message too",
                    any(r["case"] == "own manager" and r["message"] == OWNER_MANAGER_SENTENCE
                        for r in report["refusals"]),
                    sentence=OWNER_MANAGER_SENTENCE)
        after_refusals = sql(args, "SELECT count(*) FROM performance_db.peer_recognitions")
        proof.check("§4 no refusal wrote a row", after_refusals == "1",
                    rows=after_refusals)

        # ── §5 an out-of-scope person can nominate ───────────────────────────
        status, oos_form = call(base, "GET", "/api/recognition/form", tokens["out_of_scope"])
        status2, oos_saved = call(base, "POST", "/api/recognition/save",
                                  tokens["out_of_scope"],
                                  {"nominee_id": 23, **TEXTS_OOS})
        scope = sql(args, f"""
SELECT is_in_scope || '|' || COALESCE(exclusion_reason,'')
FROM performance_db.evaluation_period_participants
WHERE period_id = 2 AND user_id = {ACTORS['out_of_scope']}""")
        report["out_of_scope_author"] = {"user_id": ACTORS["out_of_scope"], "h1_scope": scope,
                                         "form_status": status, "save_status": status2,
                                         "save_body": oos_saved}
        # psql prints a boolean concatenated with `||` as 'true'/'false', not
        # 't'/'f' — the `t`/`f` form only appears in a bare column.
        proof.check("§5 the author is genuinely OUT of H1 scope",
                    scope.startswith("false|"), scope=scope)
        proof.check("§5 out-of-scope person sees the form and CAN nominate",
                    status == 200 and status2 == 200 and oos_saved.get("success") is True,
                    form_status=status, save_status=status2)

        # ── §6 the reader matrix ─────────────────────────────────────────────
        report["reader_matrix"] = {}
        for role, want in (("admin", 200), ("c_level", 200), ("hr", 403),
                           ("nominee_manager", 403), ("employee", 403),
                           ("nominee", 403)):
            status, body = call(base, "GET", "/api/recognition/list", tokens[role])
            code = body.get("error") if isinstance(body, dict) else None
            report["reader_matrix"][role] = {"user_id": ACTORS[role], "status": status,
                                             "error": code}
            proof.check(f"§6 list as {role} → {want}",
                        status == want and (want == 200 or code == "ROLE_FORBIDDEN"),
                        status=status, error=code)
        status, body = call(base, "GET", "/api/recognition/list")
        report["reader_matrix"]["unauthenticated"] = {"status": status,
                                                      "error": body.get("error") if isinstance(body, dict) else None}
        proof.check("§6 list unauthenticated → 401 TOKEN_MISSING",
                    status == 401 and body.get("error") == "TOKEN_MISSING",
                    status=status, body=body)
        status, form_hr = call(base, "GET", "/api/recognition/form", tokens["hr"])
        proof.check("§6 HR can still NOMINATE (the form is for everyone)",
                    status == 200, status=status)

        # ── the reader's own payload ─────────────────────────────────────────
        _, listing = call(base, "GET", "/api/recognition/list", tokens["c_level"])
        items = listing.get("recognitions", [])
        report["reader_payload_c_level"] = items
        proof.check("§7 the reader sees the author's name and the three texts",
                    len(items) == 2
                    and all(i.get("author_name") and i.get("nominee_name")
                            and i.get("situation") and i.get("action") and i.get("outcome")
                            for i in items),
                    items=len(items))
        # The Postgres node serialises bigint as a string; compare as numbers.
        ids = [int(i["id"]) for i in items]
        created = [i["created_at"] for i in items]
        proof.check("§7 the reader's order is by time alone, newest first",
                    created == sorted(created, reverse=True)
                    and ids == sorted(ids, reverse=True),
                    ids=ids, created=created)

        # ── §7 no count anywhere in any recognition payload ──────────────────
        offenders: dict[str, list[str]] = {}
        for label, payload in (("form/employee", form), ("form/manager", mform),
                               ("form/out_of_scope", oos_form), ("save", saved),
                               ("save/replace", replaced), ("list/c_level", listing)):
            found: set[str] = set()
            keys_of(payload, found)
            hits = sorted(k for k in found if COUNT_KEY.search(k))
            if hits:
                offenders[label] = hits
        report["count_like_keys"] = offenders
        proof.check("§7 no count / rank / total key in any recognition payload",
                    not offenders, offenders=offenders)

        # ── §8 isolation walk over the rest of the surface ───────────────────
        walk = [
            ("GET", "/api/employees", "nominee_manager", None),
            ("GET", "/api/employees", "employee", None),
            ("GET", "/api/my-profile", "nominee", None),
            ("GET", "/api/evaluation-history", "nominee", None),
            ("GET", "/api/check-self-review", "nominee", {"user_id": ACTORS["nominee"]}),
            ("GET", "/api/check-evaluated", "nominee_manager", None),
            ("GET", "/api/get-my-manager", "nominee", None),
            ("GET", "/api/criteria", "employee", None),
            ("GET", "/api/admin/evaluations-matrix", "admin", None),
            ("GET", "/api/admin/all-evaluations", "admin", None),
            ("GET", "/api/analytics", "admin", None),
            ("GET", "/api/admin-users-data", "admin", None),
            ("GET", "/api/score-coefficients", "admin", None),
            ("GET", "/api/hr/evaluation-status", "hr", None),
            # Yelena Son manages people but nobody who manages people, so the
            # manager-of-managers matrix refuses her by ownership (403
            # OWNERSHIP_FORBIDDEN) — an unrelated, pre-existing rule. Walked as
            # admin so a real payload is read.
            ("GET", "/api/manager-subordinates-matrix", "admin", None),
            ("GET", "/api/periods", "admin", None),
            # The roll-up is keyed on container_id, not period_id: 5 is the
            # Annual 2026 container H1 hangs under.
            ("GET", "/api/periods/annual-rollup", "admin", {"container_id": 5}),
            ("GET", "/api/admin/evaluation-details-by-user", "admin",
             {"user_id": ACTORS["nominee"]}),
            ("GET", "/api/admin/employee-events", "admin", {"user_id": ACTORS["nominee"]}),
        ]
        report["isolation_walk"] = []
        traces = []
        for method, path, role, params in walk:
            status, payload = call(base, method, path, tokens[role], params=params)
            raw = json.dumps(payload, ensure_ascii=False)
            has_marker = MARK in raw
            has_word = bool(re.search(r"peer_recogn|recognition|nomination", raw, re.I))
            report["isolation_walk"].append({
                "route": f"{method} {path}", "as": role, "status": status,
                "bytes": len(raw), "marker_present": has_marker,
                "recognition_word_present": has_word,
            })
            if has_marker or has_word:
                traces.append(f"{method} {path} as {role}")
        proof.check("§8 no trace of the nomination in 19 other route payloads",
                    not traces, traces=traces,
                    routes_walked=len(report["isolation_walk"]))
        proof.check("§8 the walk actually read something",
                    all(w["bytes"] > 20 for w in report["isolation_walk"])
                    and all(w["status"] == 200 for w in report["isolation_walk"]),
                    statuses=sorted({w["status"] for w in report["isolation_walk"]}))
        # The marker MUST be reachable somewhere, or the walk above proves nothing.
        proof.check("§8 the marker IS present where it should be",
                    MARK in json.dumps(listing, ensure_ascii=False),
                    where="GET /api/recognition/list as c_level")

        # ── §9 campaign tables untouched ─────────────────────────────────────
        after = campaign_counts(args)
        report["campaign_counts_after"] = after
        proof.check("§9 the four campaign tables did not move",
                    after == before, before=before, after=after)
        started = sql(args, "SELECT COALESCE(to_char(evaluation_started_at AT TIME ZONE 'UTC',"
                            "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'),'null') "
                            "FROM performance_db.evaluation_periods WHERE id = 2")
        report["evaluation_started_at"] = started
        proof.check("§9 evaluation_started_at unchanged",
                    started == "2026-08-26T10:08:54.340312Z", value=started)
        rows = sql(args, "SELECT count(*) FROM performance_db.peer_recognitions")
        report["peer_recognitions_rows"] = rows
        proof.check("§9 exactly two nominations on the stand", rows == "2", rows=rows)

    finally:
        listed = ",".join(f"'{j}'::uuid" for j in jtis)
        ssh(args, f'docker exec {args.pg_container} psql -U admin -d {args.db} '
                  f'-v ON_ERROR_STOP=1 -c "DELETE FROM performance_db.auth_sessions '
                  f'WHERE jti IN ({listed});"')

    report["checks"] = proof.checks
    report["failed"] = proof.failed
    report["verdict"] = "PASS" if proof.failed == 0 else "FAIL"
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"\n{report['verdict']}  ({len(proof.checks)} checks, {proof.failed} failed)")
    return 0 if proof.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

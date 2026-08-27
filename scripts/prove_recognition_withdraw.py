#!/usr/bin/env python3
"""Stand proof for PEER_RECOGNITION_DISCLOSURE_AND_WITHDRAW (2026-08-27).

Runs against the throwaway stand. Live is never written. The stand is a
restore of today's live dump — any nomination that came across in the dump
is a copy of a real person's row and is snapshotted, not edited.

What it proves, in order:

  §1  author 70 stores one nomination; author 31 stores another
  §2  70 withdraws their own row — the row is gone (not blanked), form
      returns my_nomination=null, c_level no longer sees it, 31's row
      is byte-identical
  §3  70 nominates again — exactly one row for 70, new id, 31 untouched
  §4  31 withdraws 70's id → 403 RECOGNITION_NOT_OWN; 70's row remains
      (also with a forged author_id=70 in the body — still 403)
  §5  missing id → 422; unknown id → 404; unauthenticated → 401
  §6  after the stand period is closed by the real route, 70 withdraws
      their own → 409 NO_ACTIVE_PERIOD; both rows still present
  §7  dump-originated rows (if any) are still present and unrewritten
  §8  evaluation_started_at unchanged; the four campaign tables on the
      stand are recorded before the close (close writes period_results
      on the STAND only)

    python3 scripts/prove_recognition_withdraw.py \
        --base http://127.0.0.1:25679/webhook --db <stand_db>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid

import requests

ACTORS = {
    "employee": 70,       # Oksana — withdraws her own
    "other": 31,          # Aysoltan — the other author's row
    "c_level": 47,
    "admin": 2,
}
NOMINEE_A = 8             # Arslan
NOMINEE_B = 7             # Anton
MARK = "WD-4K9M"
TEXTS_A = {
    "situation": f"Срочная поставка вечером {MARK}-SIT",
    "action": f"Нашёл ошибку в накладной {MARK}-ACT",
    "outcome": f"Клиент получил комплект {MARK}-OUT",
}
TEXTS_B = {
    "situation": f"Чужая задача без исполнителя {MARK}-SIT2",
    "action": f"Взял и закрыл {MARK}-ACT2",
    "outcome": f"Проект не встал {MARK}-OUT2",
}
TEXTS_C = {
    "situation": f"Сложный монтаж {MARK}-SIT3",
    "action": f"Довёл пусконаладку {MARK}-ACT3",
    "outcome": f"Сдали без переноса {MARK}-OUT3",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--ssh-host", default="root@92.51.45.147")
    p.add_argument("--pg-container", default="postgres_n8n")
    p.add_argument("--n8n-container", default="epe-recognition-n8n")
    p.add_argument("--db", required=True)
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


def row_fingerprint(args: argparse.Namespace, author_id: int) -> str:
    return sql(args, f"""
SELECT COALESCE(id::text || '|' || period_id || '|' || author_id || '|' ||
                nominee_id || '|' || situation || '|' || action || '|' || outcome, '')
FROM performance_db.peer_recognitions WHERE author_id = {author_id}
ORDER BY id""")


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
                            json=body, params=params, timeout=180)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text[:400]


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
    started_before = sql(args, "SELECT evaluation_started_at::text "
                               "FROM performance_db.evaluation_periods WHERE id = 2")
    dump_rows = sql(args, """
SELECT COALESCE(string_agg(id::text || ':' || author_id::text || ':' ||
                           md5(situation || action || outcome), ';' ORDER BY id), '')
FROM performance_db.peer_recognitions""")
    report.update({
        "campaign_counts_before": before,
        "evaluation_started_at_before": started_before,
        "dump_originated_rows": dump_rows,
    })

    tokens = mint(args, ACTORS)
    jtis = tokens.pop("_jtis")

    try:
        # ── §1 two authors store one each ──────────────────────────────────
        status, saved_a = call(base, "POST", "/api/recognition/save",
                               tokens["employee"], {"nominee_id": NOMINEE_A, **TEXTS_A})
        proof.check("§1 employee 70 save 200",
                    status == 200 and saved_a.get("success") is True,
                    status=status, body=saved_a)
        fp_a = row_fingerprint(args, ACTORS["employee"])
        first_id = fp_a.split("|")[0] if fp_a else ""
        proof.check("§1 70 has exactly one row, texts verbatim",
                    fp_a.count("\n") == 0 and fp_a != ""
                    and TEXTS_A["situation"] in fp_a
                    and fp_a.split("|")[2] == str(ACTORS["employee"])
                    and fp_a.split("|")[3] == str(NOMINEE_A),
                    row=fp_a)

        status, saved_b = call(base, "POST", "/api/recognition/save",
                               tokens["other"], {"nominee_id": NOMINEE_B, **TEXTS_B})
        proof.check("§1 employee 31 save 200",
                    status == 200 and saved_b.get("success") is True,
                    status=status)
        fp_b = row_fingerprint(args, ACTORS["other"])
        other_id = fp_b.split("|")[0] if fp_b else ""
        proof.check("§1 31 has exactly one row, different from 70",
                    fp_b.count("\n") == 0 and fp_b != ""
                    and TEXTS_B["situation"] in fp_b
                    and other_id != first_id,
                    row=fp_b, other_id=other_id, first_id=first_id)
        report["first_ids"] = {"employee": first_id, "other": other_id}

        _, listing = call(base, "GET", "/api/recognition/list", tokens["c_level"])
        list_ids = {int(i["id"]) for i in listing.get("recognitions", [])}
        proof.check("§1 c_level sees both nominations",
                    int(first_id) in list_ids and int(other_id) in list_ids,
                    list_ids=sorted(list_ids))

        # ── §2 withdraw own — removed, not blanked ─────────────────────────
        status, withdrawn = call(base, "POST", "/api/recognition/withdraw",
                                 tokens["employee"], {"recognition_id": int(first_id)})
        proof.check("§2 withdraw own → 200, message «Отметка снята»",
                    status == 200 and withdrawn.get("success") is True
                    and withdrawn.get("withdrawn") is True
                    and withdrawn.get("message") == "Отметка снята",
                    status=status, body=withdrawn)
        gone = sql(args, f"SELECT count(*) FROM performance_db.peer_recognitions "
                         f"WHERE id = {first_id}")
        blanked = sql(args, f"SELECT count(*) FROM performance_db.peer_recognitions "
                            f"WHERE author_id = {ACTORS['employee']} "
                            f"AND (btrim(situation) = '' OR btrim(action) = '' "
                            f"OR btrim(outcome) = '')")
        mine = sql(args, f"SELECT count(*) FROM performance_db.peer_recognitions "
                         f"WHERE author_id = {ACTORS['employee']}")
        proof.check("§2 the row is gone, not blanked, author has none",
                    gone == "0" and blanked == "0" and mine == "0",
                    gone=gone, blanked=blanked, mine=mine)

        status, form = call(base, "GET", "/api/recognition/form", tokens["employee"])
        proof.check("§2 form after withdraw: my_nomination is null",
                    status == 200 and form.get("my_nomination") is None,
                    status=status, mine=form.get("my_nomination"))

        _, listing2 = call(base, "GET", "/api/recognition/list", tokens["c_level"])
        list_ids2 = {int(i["id"]) for i in listing2.get("recognitions", [])}
        texts2 = json.dumps(listing2, ensure_ascii=False)
        proof.check("§2 c_level no longer sees the withdrawn nomination",
                    int(first_id) not in list_ids2
                    and TEXTS_A["situation"] not in texts2,
                    list_ids=sorted(list_ids2), first_id=first_id)

        fp_b_after = row_fingerprint(args, ACTORS["other"])
        proof.check("§2 the other author's row is byte-identical",
                    fp_b_after == fp_b, before=fp_b, after=fp_b_after)

        # ── §3 nominate again — exactly one, new id ────────────────────────
        status, saved_c = call(base, "POST", "/api/recognition/save",
                               tokens["employee"], {"nominee_id": NOMINEE_B, **TEXTS_C})
        proof.check("§3 re-nominate 200",
                    status == 200 and saved_c.get("success") is True
                    and saved_c.get("replaced") is not True,
                    status=status, body=saved_c)
        fp_c = row_fingerprint(args, ACTORS["employee"])
        second_id = fp_c.split("|")[0] if fp_c else ""
        proof.check("§3 exactly one row for 70, new id, new texts",
                    fp_c.count("\n") == 0 and fp_c != ""
                    and second_id != first_id
                    and TEXTS_C["situation"] in fp_c
                    and TEXTS_A["situation"] not in fp_c,
                    row=fp_c, first_id=first_id, second_id=second_id)
        fp_b_again = row_fingerprint(args, ACTORS["other"])
        proof.check("§3 the other author's row still byte-identical",
                    fp_b_again == fp_b, before=fp_b, after=fp_b_again)
        report["second_id"] = second_id

        # ── §4 cross-author refused ────────────────────────────────────────
        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["other"], {"recognition_id": int(second_id)})
        proof.check("§4 other employee against 70's row → 403 RECOGNITION_NOT_OWN",
                    status == 403 and isinstance(body, dict)
                    and body.get("error") == "RECOGNITION_NOT_OWN",
                    status=status, body=body)
        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["other"],
                            {"recognition_id": int(second_id),
                             "author_id": ACTORS["employee"]})
        proof.check("§4 forged author_id in the body is ignored — still 403",
                    status == 403 and isinstance(body, dict)
                    and body.get("error") == "RECOGNITION_NOT_OWN",
                    status=status, body=body)
        fp_c_after = row_fingerprint(args, ACTORS["employee"])
        fp_b_after2 = row_fingerprint(args, ACTORS["other"])
        proof.check("§4 both rows untouched by the cross-author calls",
                    fp_c_after == fp_c and fp_b_after2 == fp_b,
                    employee=fp_c_after, other=fp_b_after2)

        # ── §5 shape refusals ──────────────────────────────────────────────
        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["employee"], {})
        proof.check("§5 missing recognition_id → 422 INVALID_RECOGNITION_ID",
                    status == 422 and isinstance(body, dict)
                    and body.get("error") == "INVALID_RECOGNITION_ID",
                    status=status, body=body)
        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["employee"], {"recognition_id": 999_999})
        proof.check("§5 unknown id → 404 RECOGNITION_NOT_FOUND",
                    status == 404 and isinstance(body, dict)
                    and body.get("error") == "RECOGNITION_NOT_FOUND",
                    status=status, body=body)
        status, body = call(base, "POST", "/api/recognition/withdraw",
                            None, {"recognition_id": int(second_id)})
        proof.check("§5 unauthenticated → 401 TOKEN_MISSING",
                    status == 401 and isinstance(body, dict)
                    and body.get("error") == "TOKEN_MISSING",
                    status=status, body=body)
        proof.check("§5 shape refusals wrote zero rows",
                    row_fingerprint(args, ACTORS["employee"]) == fp_c
                    and row_fingerprint(args, ACTORS["other"]) == fp_b)

        # ── §6 close the STAND period, then withdraw is refused ────────────
        status, closed = call(base, "POST", "/api/periods/close",
                              tokens["admin"], {"period_id": 2})
        report["close"] = {"status": status, "body": closed}
        proof.check("§6 stand period closed by the real route",
                    status == 200 and isinstance(closed, dict)
                    and closed.get("success") is True,
                    status=status, body=closed)

        status, body = call(base, "POST", "/api/recognition/withdraw",
                            tokens["employee"], {"recognition_id": int(second_id)})
        proof.check("§6 withdraw after close → 409 NO_ACTIVE_PERIOD",
                    status == 409 and isinstance(body, dict)
                    and body.get("error") == "NO_ACTIVE_PERIOD",
                    status=status, body=body)
        proof.check("§6 both nominations survived the close and the refused withdraw",
                    row_fingerprint(args, ACTORS["employee"]) == fp_c
                    and row_fingerprint(args, ACTORS["other"]) == fp_b,
                    employee=row_fingerprint(args, ACTORS["employee"]),
                    other=row_fingerprint(args, ACTORS["other"]))

        # ── §7 dump-originated rows ────────────────────────────────────────
        dump_after = sql(args, """
SELECT COALESCE(string_agg(id::text || ':' || author_id::text || ':' ||
                           md5(situation || action || outcome), ';' ORDER BY id), '')
FROM performance_db.peer_recognitions
WHERE id NOT IN ({ids})
""".format(ids=",".join(x for x in (other_id, second_id) if x)))
        # The first_id was deleted by us; dump rows are those whose id is
        # neither of the two we still hold.
        proof.check("§7 dump-originated rows still present and unrewritten",
                    dump_after == dump_rows,
                    before=dump_rows, after=dump_after)

        # ── §8 campaign mark ───────────────────────────────────────────────
        started_after = sql(args, "SELECT evaluation_started_at::text "
                                 "FROM performance_db.evaluation_periods WHERE id = 2")
        after = campaign_counts(args)
        report["campaign_counts_after_close"] = after
        report["evaluation_started_at_after"] = started_after
        proof.check("§8 evaluation_started_at unchanged on the stand",
                    started_after == started_before, before=started_before,
                    after=started_after)
        # Close writes period_results on the STAND. The other three campaign
        # tables must not have been written by this proof.
        ev, sc, corr, pr = after.split("/")
        ev_b, sc_b, corr_b, _pr_b = before.split("/")
        proof.check("§8 evaluations / scores / corrections unchanged on the stand",
                    (ev, sc, corr) == (ev_b, sc_b, corr_b),
                    before=before, after=after)
        report["period_results_written_by_stand_close"] = pr

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

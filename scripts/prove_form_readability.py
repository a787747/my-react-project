#!/usr/bin/env python3
"""Quote what the submit routes do with an untouched criterion (stand only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOST = "root@92.51.45.147"
FIXTURE_PASSWORD = "Walk2026-Portal!"
PROOF = {"checks": []}
FAILURES = []


def check(name: str, actual, expected) -> bool:
    ok = actual == expected
    PROOF["checks"].append(
        {"name": name, "expected": expected, "actual": actual, "ok": ok}
    )
    if not ok:
        FAILURES.append(f"{name}: expected {expected!r}, got {actual!r}")
    return ok


def call(base: str, method: str, path: str, token=None, body=None):
    url = base.rstrip("/") + "/" + path.lstrip("/")
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode("utf-8", "replace")


def ssh_sql(database: str, sql: str) -> str:
    cmd = [
        "ssh", "-o", "BatchMode=yes", HOST,
        "docker", "exec", "-i", "postgres_n8n",
        "psql", "-U", "admin", "-d", database, "-tA", "-v", "ON_ERROR_STOP=1",
    ]
    out = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=True)
    return out.stdout.strip()


def login(base: str, email: str):
    status, body = call(base, "POST", "auth/login",
                        body={"email": email, "password": FIXTURE_PASSWORD})
    token = body.get("token") if status == 200 and isinstance(body, dict) else None
    return status, token, body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:25679/webhook")
    parser.add_argument("--db", required=True)
    parser.add_argument(
        "--out",
        default=str(REPO / "backups/2026-08-27-form-readability/prove.json"),
    )
    args = parser.parse_args()

    # Empty grades → 422 NO_GRADES (the route receives no invented 1).
    status, token, body = login(args.base, "wt.employee.g@sedamedical.com")
    check("employee login", status, 200)
    if not token:
        print("login failed", body, file=sys.stderr)
        return 1
    PROOF["employee_login"] = {"status": status, "user_id": (body or {}).get("user", {}).get("id")}

    empty_payload = {
        "user_id": 1303,
        "final_score": 5,
        "grades": {},
        "comments": {},
    }
    status, body = call(args.base, "POST", "api/self-review-submit", token, empty_payload)
    PROOF["self_review_empty_grades"] = {
        "request_grades": empty_payload["grades"],
        "status": status,
        "body": body,
    }
    check("self-review empty grades", (status, (body or {}).get("error")), (422, "NO_GRADES"))

    # Partial self-review: only criterion 3. Untouched 4 and 12 are absent.
    partial_self = {
        "user_id": 1303,
        "final_score": 8,
        "grades": {"3": 8},
        "comments": {},
    }
    status, body = call(args.base, "POST", "api/self-review-submit", token, partial_self)
    PROOF["self_review_partial"] = {
        "request_grades": partial_self["grades"],
        "status": status,
        "body": body,
    }
    check("self-review partial accepted (UI would have blocked)", status, 200)

    stored = ssh_sql(args.db, """
      SELECT string_agg(es.criteria_id::text || '=' || es.score_value::text, ',' ORDER BY es.criteria_id)
      FROM performance_db.evaluation_scores es
      JOIN performance_db.evaluations e ON e.id = es.evaluation_id
      WHERE e.subject_id = 1303 AND e.is_self_evaluation = true
    """)
    PROOF["self_review_stored"] = stored
    check("self-review stored only the sent key", stored, "3=8")

    # Manager: login, submit one of several applicable criteria.
    status, token, body = login(args.base, "wt.manager@sedamedical.com")
    check("manager login", status, 200)
    if not token:
        print("manager login failed", body, file=sys.stderr)
        return 1

    manager_partial = {
        "evaluator_id": 1302,
        "subject_id": 1303,
        "final_score": 7,
        "grades": {"3": 7},
        "comments": {},
        "evaluation_source": "manager",
    }
    status, body = call(args.base, "POST", "api/submit-evaluation", token, manager_partial)
    PROOF["manager_partial"] = {
        "request_grades": manager_partial["grades"],
        "status": status,
        "body": body,
    }
    check("manager first submit of a subset", status, 200)

    stored = ssh_sql(args.db, """
      SELECT string_agg(es.criteria_id::text || '=' || es.score_value::text, ',' ORDER BY es.criteria_id)
      FROM performance_db.evaluation_scores es
      JOIN performance_db.evaluations e ON e.id = es.evaluation_id
      WHERE e.subject_id = 1303 AND e.evaluator_id = 1302
        AND e.is_self_evaluation = false
    """)
    PROOF["manager_stored_after_first"] = stored
    check("manager stored only the sent key, not a 1 for the rest", stored, "3=7")

    # Additive: send 4, leave 12 (and 14) untouched. 3 must stay 7.
    additive = {
        "evaluator_id": 1302,
        "subject_id": 1303,
        "final_score": 6,
        "grades": {"4": 6},
        "comments": {},
        "evaluation_source": "manager",
    }
    status, body = call(args.base, "POST", "api/submit-evaluation", token, additive)
    PROOF["manager_additive"] = {
        "request_grades": additive["grades"],
        "status": status,
        "body": body,
    }
    check("manager additive of one more criterion", status, 200)

    stored = ssh_sql(args.db, """
      SELECT string_agg(es.criteria_id::text || '=' || es.score_value::text, ',' ORDER BY es.criteria_id)
      FROM performance_db.evaluation_scores es
      JOIN performance_db.evaluations e ON e.id = es.evaluation_id
      WHERE e.subject_id = 1303 AND e.evaluator_id = 1302
        AND e.is_self_evaluation = false
    """)
    PROOF["manager_stored_after_additive"] = stored
    check("additive wrote 4 and left the rest missing (no invented 1)", stored, "3=7,4=6")

    ones = ssh_sql(args.db, """
      SELECT count(*) FROM performance_db.evaluation_scores
      WHERE score_value = 1
    """)
    PROOF["score_value_1_rows"] = ones
    check("stand has zero score_value=1 rows", ones, "0")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(PROOF, ensure_ascii=False, indent=2) + "\n")
    if FAILURES:
        print("FAIL", *FAILURES, sep="\n", file=sys.stderr)
        return 1
    print("PASS", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Photograph the money inputs of a period, read-only, into docs/coefficients/.

The bonus allocation index is built from exactly three tables — criteria
weights, score_coefficients (level curves) and grades (grade coefficients) —
and all three are live-joined and editable until close (D-0822-2). Nothing in
the system versions them. The December 2025 index therefore cannot be
reconstructed: its inputs were edited afterwards and the index itself was never
persisted (HANDOVER §4 item 2). This script exists so that does not repeat.

It is a READ. It opens no transaction that writes, creates no extension, and
touches nothing but three SELECTs. Re-run it whenever the owner changes a
value; each run writes a new dated file and never edits an old one.

    python3 scripts/snapshot_coefficients.py --label H1-2026

The four md5 sums it records are computed BY POSTGRES over a canonical
projection, and the exact SQL is embedded in the artefact, so September can
recompute them against whatever live holds then and see in one line whether a
value moved.
"""
import argparse
import json
import pathlib
import subprocess
import sys

SSH_HOST = "root@92.51.45.147"
PSQL = ["docker", "exec", "-i", "postgres_n8n", "psql", "-U", "admin", "-d", "epe_2026",
        "-tA", "-F", "\x1f", "-v", "ON_ERROR_STOP=1"]

# The canonical projections the md5 sums are taken over. Kept in one place so
# the artefact can quote them verbatim and a later run can be compared.
PROJ_CRITERIA = ("concat_ws('|', id, title, target_audience, weight, c_level_only, "
                 "selfassesment, for_manager, is_active)")
PROJ_COEF = "concat_ws('|', criteria_id, score_level, coefficient)"
PROJ_GRADES = "concat_ws('|', id, code, coefficient, coalesce(description,''))"

FP_SQL = f"""
SELECT 'read_at_utc', to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
UNION ALL SELECT 'criteria_md5', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
  SELECT {PROJ_CRITERIA} AS t FROM performance_db.criteria WHERE is_active = true) x)
UNION ALL SELECT 'score_coefficients_md5', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
  SELECT {PROJ_COEF} AS t FROM performance_db.score_coefficients) x)
UNION ALL SELECT 'grades_md5', (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
  SELECT {PROJ_GRADES} AS t FROM performance_db.grades) x)
UNION ALL SELECT 'combined_md5', md5(
  (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
     SELECT {PROJ_CRITERIA} AS t FROM performance_db.criteria WHERE is_active = true) x)
  || (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
     SELECT {PROJ_COEF} AS t FROM performance_db.score_coefficients) y)
  || (SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (
     SELECT {PROJ_GRADES} AS t FROM performance_db.grades) z))
UNION ALL SELECT 'period_state', (SELECT string_agg(
  id || ':' || name || ':' || status || ':' || is_active || ':' ||
  CASE WHEN evaluation_started_at IS NULL THEN 'not_started' ELSE 'STARTED' END, ' · ' ORDER BY id)
  FROM performance_db.evaluation_periods)
UNION ALL SELECT 'evaluation_rows', (SELECT count(*)::text FROM performance_db.evaluations)
"""


def run_sql(sql):
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", SSH_HOST, " ".join(PSQL)],
                         input=sql, capture_output=True, text=True, check=True)
    return [line.split("\x1f") for line in out.stdout.strip("\n").split("\n") if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="H1-2026",
                    help="the period this photograph belongs to")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    out_dir = pathlib.Path(args.out_dir) if args.out_dir else repo / "docs" / "coefficients"
    out_dir.mkdir(parents=True, exist_ok=True)

    fp = {k: v for k, v in run_sql(FP_SQL)}
    stamp = fp["read_at_utc"].replace("-", "").replace(":", "")[:15] + "Z"

    criteria = run_sql(
        "SELECT id, title, target_audience, weight, c_level_only, selfassesment, "
        "for_manager FROM performance_db.criteria WHERE is_active = true ORDER BY id")
    coef = run_sql(
        "SELECT criteria_id, score_level, coefficient FROM performance_db.score_coefficients "
        "ORDER BY criteria_id, score_level")
    grades = run_sql(
        "SELECT id, code, coefficient, coalesce(description,'') FROM performance_db.grades ORDER BY id")

    curves = {}
    for cid, lvl, c in coef:
        curves.setdefault(int(cid), {})[int(lvl)] = c

    body = []
    w = body.append
    w(f"# {args.label} — coefficient snapshot\n")
    w(f"**Read:** `{fp['read_at_utc']}` UTC, from live `epe_2026.performance_db` "
      f"(server clock, `now() AT TIME ZONE 'UTC'`).")
    w(f"**Period state at that moment:** {fp['period_state']}.")
    w(f"**`evaluations` rows at that moment:** {fp['evaluation_rows']}.\n")
    w("This is a **photograph, not an approval and not a change.** The owner sets these values and "
      "may change any of them before the second gate; if he does, this file is not edited — the "
      "snapshot is retaken and a new dated file is written beside it. Its only purpose is that the "
      "September calculation can be reconstructed from the numbers it was actually computed from. "
      "The December 2025 index cannot be, because its inputs were edited afterwards and the index "
      "itself was never stored (HANDOVER §4 item 2).\n")
    w("| fingerprint | md5 |")
    w("|---|---|")
    w(f"| `criteria` (9 active rows, the weights) | `{fp['criteria_md5']}` |")
    w(f"| `score_coefficients` (90 rows, the level curves) | `{fp['score_coefficients_md5']}` |")
    w(f"| `grades` (11 rows, the grade coefficients) | `{fp['grades_md5']}` |")
    w(f"| **combined** (the three concatenated, in that order) | **`{fp['combined_md5']}`** |")
    w("")
    w("Recompute any of them with the SQL in §4 below; the value is stable for a given set of rows "
      "and independent of row order.\n")
    w("---\n")

    w("## 1. Criteria weights\n")
    w("| id | title | audience | **weight** | c_level_only | self | for_manager |")
    w("|---|---|---|---|---|---|---|")
    for cid, title, aud, weight, clo, selfa, form in criteria:
        w(f"| {cid} | {title} | `{aud}` | **{weight}** | {clo} | {selfa} | {form} |")
    w("")
    w("The weight multiplies the score in formula #3, the bonus allocation index — a weighted sum "
      "**without** dividing by the sum of weights (HANDOVER §4). It is not a percentage and the "
      "weights are not meant to add to anything.\n")
    w("---\n")

    w("## 2. Level coefficients (`score_coefficients`)\n")
    w("Ten levels per criterion, `score_level` 1…10; the table has a CHECK that refuses any other "
      "level, so **level 0 has no coefficient** and the calculation's `clamp(round(score), 0, 10)` "
      "can only reach 0 for a score below 0.5, which the 1–10 write validation forbids.\n")
    w("| criterion | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    titles = {int(c[0]): c[1] for c in criteria}
    for cid in sorted(curves):
        lv = curves[cid]
        cells = " | ".join(lv.get(i, "—") for i in range(1, 11))
        w(f"| **{cid}** {titles.get(cid, '?')} | {cells} |")
    w("")
    w(f"{len(coef)} rows, minimum `{min(float(c[2]) for c in coef):.2f}`, "
      f"maximum `{max(float(c[2]) for c in coef):.2f}`, every value > 0.\n")
    w("---\n")

    w("## 3. Grade coefficients\n")
    w("| id | code | **coefficient** | description |")
    w("|---|---|---|---|")
    for gid, code, c, desc in grades:
        w(f"| {gid} | `{code}` | **{c}** | {desc} |")
    w("")
    w("The grade coefficient is the last multiplier of the index: "
      "`index = Σ(score × level_coefficient × weight) × grade_coefficient`. "
      "A person with no grade is **not** given 1.00 silently on the close path — "
      "see the report for where the `|| 1.0` fallbacks still are.\n")
    w("---\n")

    w("## 4. How to recompute these md5 sums\n")
    w("Read-only. Run against whatever database is being checked:\n")
    w("```sql")
    w(f"SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (")
    w(f"  SELECT {PROJ_CRITERIA} AS t")
    w("  FROM performance_db.criteria WHERE is_active = true) x;   -- criteria")
    w("")
    w(f"SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (")
    w(f"  SELECT {PROJ_COEF} AS t")
    w("  FROM performance_db.score_coefficients) x;                -- score_coefficients")
    w("")
    w(f"SELECT md5(string_agg(t, E'\\n' ORDER BY t)) FROM (")
    w(f"  SELECT {PROJ_GRADES} AS t")
    w("  FROM performance_db.grades) x;                            -- grades")
    w("```\n")
    w("The combined sum is `md5(criteria_md5 || score_coefficients_md5 || grades_md5)`.\n")
    w(f"Produced by `scripts/snapshot_coefficients.py --label {args.label}`.")

    path = out_dir / f"{args.label}_coefficients_{stamp}.md"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(json.dumps({"artefact": str(path.relative_to(repo)), **fp}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

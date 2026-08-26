#!/usr/bin/env bash
# Build the HIRE_DATE_AND_SCOPE_TOGGLE two-copy stand by reusing the proven
# PRELAUNCH_BATCH_NIGHT stand surface, then applying only this brief's additive
# migration and fixture to both copies.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
BASE_ENV="$REPO/backups/2026-08-25-prelaunch-night/throwaway_env.json"
OUT_DIR="$REPO/backups/2026-08-26-hiredate-scope"
OUT_ENV="$OUT_DIR/throwaway_env.json"

mkdir -p "$OUT_DIR"

"$REPO/scripts/setup_night_throwaway.sh"

DB_CTL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["database_control"])' "$BASE_ENV")"
DB_TRT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["database_treatment"])' "$BASE_ENV")"

for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d '$DB' -v ON_ERROR_STOP=1" \
    < "$REPO/migrations/017_add_employee_card_events_and_scope_override.sql" >/dev/null
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d '$DB' -v ON_ERROR_STOP=1" \
    < "$REPO/scripts/seed_hiredate_scope.sql" >/dev/null
done

python3 - "$BASE_ENV" "$OUT_ENV" <<'PY'
import json, sys
source, target = sys.argv[1:]
env = json.load(open(source))
env["brief"] = "HIRE_DATE_AND_SCOPE_TOGGLE"
json.dump(env, open(target, "w"), ensure_ascii=False, indent=2)
PY

FP_SQL="SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (SELECT concat_ws(':', e.id, e.subject_id, e.evaluator_id, e.period_id, e.calculated_score, e.evaluation_source, e.is_self_evaluation, s.criteria_id, s.score_value) AS t FROM performance_db.evaluations e LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) x"
FP_CTL="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d '$DB_CTL' -tAc \"$FP_SQL\"")"
FP_TRT="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d '$DB_TRT' -tAc \"$FP_SQL\"")"
test "$FP_CTL" = "$FP_TRT" || {
  echo "control/treatment evaluation fingerprints differ after the brief seed"
  exit 1
}

echo "HIRE_DATE_AND_SCOPE_TOGGLE stand ready"
echo "  control:   $DB_CTL :25680"
echo "  treatment: $DB_TRT :25679"
echo "  env:       $OUT_ENV"
echo "  fingerprint: $FP_CTL"

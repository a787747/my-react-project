#!/usr/bin/env bash
# Build the isolated TERMINATED_EMPLOYEES stand on the VPS (brief 2026-08-25,
# D-0825-7). Live epe_2026 and the live n8n are never written by this script.
#
#   - one dated dump of live epe_2026
#   - TWO throwaway databases restored from that same dump:
#       epe_term_<stamp>_ctl   control   — nobody is terminated, then closed
#       epe_term_<stamp>_trt   treatment — 1503 terminated, then closed
#     Two copies of one dump is what makes the money claim provable: the two
#     period_results sets differ only by the termination, because they started
#     byte-identical.
#   - migration 015 applied to both (additive; the only schema change)
#   - scripts/seed_termination_throwaway.sql applied to both (synthetic
#     ids 1501-1507 with REAL scrypt logins: the browser drives the real form)
#   - isolated n8n `epe-term-n8n` on VPS loopback :25679, same pinned image
#     digest as live, pointed at the TREATMENT database, carrying the FULL
#     generated workflow surface including the new API: Manage Employment Status
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
STAND_TMP="/root/epe_stand_tmp"   # never /tmp: PROJECT_RULES 2026-08-24 (BUG-053)
DB_CTL="epe_term_${STAMP}_ctl"
DB_TRT="epe_term_${STAMP}_trt"
BACKUP_DIR="$REPO/backups/2026-08-25-termination"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER="epe-term-n8n"
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"

mkdir -p "$BACKUP_DIR"

echo "== 0. Refuse to run unless live is in the expected state =="
LIVE_STATE="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d epe_2026 -tAc \"SELECT (SELECT count(*) FROM performance_db.users) || '/' || (SELECT count(*) FROM performance_db.evaluations) || '/' || (SELECT coalesce((SELECT 'started' FROM performance_db.evaluation_periods WHERE id=2 AND evaluation_started_at IS NOT NULL), 'notstarted'))\"")"
echo "live users/evaluations/gate = $LIVE_STATE"
test "$LIVE_STATE" = "89/0/notstarted" || { echo "live is not in the expected pre-gate state; refusing"; exit 1; }

echo "== 1. Dated dump of live epe_2026 =="
"${SSH[@]}" "mkdir -p $STAND_TMP && chmod 700 $STAND_TMP && docker exec postgres_n8n pg_dump -U admin -Fc --no-owner --no-acl epe_2026 > $STAND_TMP/epe_2026_term_${STAMP}.dump && chmod 600 $STAND_TMP/epe_2026_term_${STAMP}.dump && ls -la $STAND_TMP/epe_2026_term_${STAMP}.dump"
"${SSH[@]}" "cat $STAND_TMP/epe_2026_term_${STAMP}.dump" > "$BACKUP_DIR/epe_2026_term_${STAMP}.dump"
echo "local copy: $BACKUP_DIR/epe_2026_term_${STAMP}.dump ($(wc -c < "$BACKUP_DIR/epe_2026_term_${STAMP}.dump") bytes)"

echo "== 2. Two throwaway DBs restored from the SAME dump =="
for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
  "${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner < $STAND_TMP/epe_2026_term_${STAMP}.dump" || true
  N="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
  C="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.criteria WHERE is_active = true'")"
  test "$N" = "89" || { echo "restore verification failed on $DB: users=$N"; exit 1; }
  test "$C" = "9"  || { echo "restore verification failed on $DB: active criteria=$C"; exit 1; }
  echo "  $DB restored: users=$N active_criteria=$C"
done

echo "== 3. Migration 015 on both (additive only) =="
for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/migrations/015_add_employment_termination.sql" >/dev/null
  # Second application must be a no-op: the migration claims idempotence.
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/migrations/015_add_employment_termination.sql" >/dev/null
  echo "  $DB: migration 015 applied twice, no error"
done

echo "== 4. Fixture seed on both =="
for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/scripts/seed_termination_throwaway.sql" >/dev/null
  echo "  $DB seeded"
done

echo "== 4b. The two copies start identical =="
FP_SQL="SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (SELECT concat_ws(':', e.id, e.subject_id, e.evaluator_id, e.period_id, e.calculated_score, e.evaluation_source, e.is_self_evaluation, s.criteria_id, s.score_value) AS t FROM performance_db.evaluations e LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) x"
FP_CTL="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB_CTL -tAc \"$FP_SQL\"")"
FP_TRT="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB_TRT -tAc \"$FP_SQL\"")"
echo "  evaluations fingerprint control=$FP_CTL treatment=$FP_TRT"
test "$FP_CTL" = "$FP_TRT" || { echo "the two stands did not start identical; refusing"; exit 1; }

echo "== 5. Generate the workflow surface from the builders =="
GEN_H1="$(mktemp -d)"; GEN_DEF="$(mktemp -d)"; GEN_AUTH="$(mktemp -d)"
# Top-level n8n_workflows/ exports are untrusted (BUG-028/045). Everything is
# generated here, from the same builders that will deploy to live.
python3 "$REPO/scripts/build_route_guard_workflows.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_H1" >/dev/null
python3 "$REPO/scripts/build_route_guard_deferred.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_DEF" >/dev/null
python3 "$REPO/scripts/build_auth_workflows.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_AUTH" >/dev/null
test -f "$GEN_H1/manage-employment.json" || { echo "manage-employment.json was not generated"; exit 1; }

echo "== 6. Isolated n8n on VPS loopback :25679, pointed at the TREATMENT db =="
JWT_SECRET="$(openssl rand -hex 32)"
ENC_KEY="$(openssl rand -hex 24)"
PGPASS="$("${SSH[@]}" "docker exec postgres_n8n env | grep '^POSTGRES_PASSWORD=' | cut -d= -f2-")"
test -n "$PGPASS"
"${SSH[@]}" "docker rm -f $CONTAINER 2>/dev/null || true"
"${SSH[@]}" "docker run -d --name $CONTAINER --network n8n_default \
  -p 127.0.0.1:25679:5678 \
  -e N8N_ENCRYPTION_KEY=$ENC_KEY \
  -e JWT_SIGNING_SECRET=$JWT_SECRET \
  -e NODE_FUNCTION_ALLOW_BUILTIN=crypto \
  -e NODE_FUNCTION_ALLOW_EXTERNAL=jsonwebtoken \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e N8N_SECURE_COOKIE=false \
  -e EPE_FRONTEND_URL=https://epe.sedamedical.com \
  -e WEBHOOK_URL=http://127.0.0.1:25679/ \
  -e GENERIC_TIMEZONE=Europe/Moscow -e TZ=Europe/Moscow \
  $IMAGE"

cat > "$BACKUP_DIR/throwaway_env.json" <<EOF
{"database_control": "$DB_CTL", "database_treatment": "$DB_TRT", "jwt_secret": "$JWT_SECRET", "container": "$CONTAINER", "stamp": "$STAMP", "fixture_password": "Term2026-Portal!"}
EOF
echo "stand facts written to $BACKUP_DIR/throwaway_env.json (backups/ is gitignored)"

echo "== 7. Import credential + workflows via the n8n CLI =="
CRED_FILE="$(mktemp)"
python3 - "$DB_TRT" "$PGPASS" > "$CRED_FILE" <<'PYEOF'
import json, sys
db, password = sys.argv[1], sys.argv[2]
print(json.dumps([{
    "id": "VNbfkY8IKbEzn88B",
    "name": "EPE 2026 Postgres",
    "type": "postgres",
    "data": {
        "host": "postgres_n8n", "port": 5432, "database": db,
        "user": "admin", "password": password, "ssl": "disable",
        "allowUnauthorizedCerts": False, "sshTunnel": False,
    },
}]))
PYEOF

IMPORT_DIR="$(mktemp -d)"
prep () {  # <src> <dest-name> [id] — the CLI import needs explicit active + versionId
  python3 - "$1" "$IMPORT_DIR/$2" "${3:-}" <<'PYEOF'
import json, sys, uuid
wf = json.load(open(sys.argv[1]))
wf["active"] = False
wf["versionId"] = str(uuid.uuid4())
# n8n import assigns a NEW id unless the file carries one. The guard MUST keep
# the live id: every Run Auth Guard node references it by literal id, and a
# regenerated guard id makes every protected route answer an empty 200.
if len(sys.argv) > 3 and sys.argv[3]:
    wf["id"] = sys.argv[3]
json.dump(wf, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PYEOF
}
prep "$GEN_AUTH/auth-guard.json" auth-guard.json "$GUARD_ID"
for SRC in "$GEN_AUTH" "$GEN_H1" "$GEN_DEF"; do
  for F in "$SRC"/*.json; do
    BASE="$(basename "$F")"
    [ "$BASE" = "auth-guard.json" ] && continue
    prep "$F" "$BASE"
  done
done

# docker cp <dir> container:/path NESTS when the target exists, and the CLI then
# re-imports the previous file. Clear the container-side directory first.
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf && docker exec $CONTAINER mkdir -p /tmp/wf"
tar -C "$IMPORT_DIR" -cf - . | "${SSH[@]}" "docker exec -i $CONTAINER tar -C /tmp/wf -xf -"
cat "$CRED_FILE" | "${SSH[@]}" "docker exec -i $CONTAINER sh -c 'cat > /tmp/cred.json'"

echo "   waiting for n8n to come up"
for _ in $(seq 1 60); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then
    break
  fi
  sleep 2
done

"${SSH[@]}" "docker exec $CONTAINER n8n import:credentials --input=/tmp/cred.json"
"${SSH[@]}" "docker exec $CONTAINER n8n import:workflow --separate --input=/tmp/wf"
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf /tmp/cred.json"

echo "== 8. Activate every imported workflow that has a webhook trigger =="
"${SSH[@]}" "docker exec $CONTAINER n8n update:workflow --all --active=true" >/dev/null
"${SSH[@]}" "docker restart $CONTAINER" >/dev/null
for _ in $(seq 1 60); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then
    break
  fi
  sleep 2
done

echo
echo "Stand up."
echo "  control DB   : $DB_CTL"
echo "  treatment DB : $DB_TRT   (the n8n stand talks to this one)"
echo "  n8n          : VPS 127.0.0.1:25679"
echo "  tunnel       : ssh -N -L 25679:127.0.0.1:25679 $HOST"
echo "  frontend     : VITE_DEV_API_PROXY=http://127.0.0.1:25679 npm run dev -- --port 5299 --strictPort"
echo "  teardown     : scripts/teardown_termination_throwaway.sh"

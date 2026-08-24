#!/usr/bin/env bash
# Build the isolated reclassification proof stand on the VPS (brief 2026-08-24,
# D-0822-3 + BUG-041 + BUG-043 + weight floor):
#   - dated dump of live epe_2026
#   - throwaway DB epe_reclass_<stamp> restored from it (no migration needed:
#     this brief changes no schema)
#   - fixture seed applied to the throwaway ONLY
#   - isolated n8n `epe-reclass-n8n` on VPS loopback :25679 (same pinned image),
#     with the guard + every workflow this brief touches imported
# Live epe_2026 and the live n8n are never written by this script.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
DB="epe_reclass_${STAMP}"
BACKUP_DIR="$REPO/backups/2026-08-24-reclass"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER="epe-reclass-n8n"
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"

mkdir -p "$BACKUP_DIR"

echo "== 1. Dated dump of live epe_2026 =="
"${SSH[@]}" "docker exec postgres_n8n pg_dump -U admin -Fc epe_2026 > /tmp/epe_2026_reclass_${STAMP}.dump && ls -la /tmp/epe_2026_reclass_${STAMP}.dump"
"${SSH[@]}" "cat /tmp/epe_2026_reclass_${STAMP}.dump" > "$BACKUP_DIR/epe_2026_reclass_${STAMP}.dump"
echo "local copy: $BACKUP_DIR/epe_2026_reclass_${STAMP}.dump ($(wc -c < "$BACKUP_DIR/epe_2026_reclass_${STAMP}.dump") bytes)"

echo "== 2. Throwaway DB $DB restored from the dump =="
"${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
"${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner < /tmp/epe_2026_reclass_${STAMP}.dump" || true
USER_COUNT="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
test "$USER_COUNT" = "89" || { echo "restore verification failed: users=$USER_COUNT"; exit 1; }
STARTED_COL="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc \"SELECT count(*) FROM information_schema.columns WHERE table_schema='performance_db' AND table_name='evaluation_periods' AND column_name='evaluation_started_at'\"")"
test "$STARTED_COL" = "1" || { echo "restore verification failed: migration 014 column missing"; exit 1; }
echo "restore verified: users=$USER_COUNT, evaluation_started_at present"

echo "== 3. Fixture seed on the throwaway =="
"${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" < "$REPO/scripts/seed_reclass_throwaway.sql"

echo "== 4. Generate workflows with real credential/guard ids =="
GEN_H1="$(mktemp -d)"; GEN_DEF="$(mktemp -d)"; GEN_AUTH="$(mktemp -d)"
# NOTE: top-level exports are untrusted (BUG-028). Everything is generated here.
python3 "$REPO/scripts/build_route_guard_workflows.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_H1" >/dev/null
python3 "$REPO/scripts/build_route_guard_deferred.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_DEF" >/dev/null
python3 "$REPO/scripts/build_auth_workflows.py" \
  --postgres-credential-id "$CRED_ID" --guard-workflow-id "$GUARD_ID" \
  --output-directory "$GEN_AUTH" >/dev/null

echo "== 5. Isolated n8n on VPS loopback :25679 =="
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
  -e WEBHOOK_URL=http://127.0.0.1:25679/ \
  -e GENERIC_TIMEZONE=Europe/Moscow -e TZ=Europe/Moscow \
  $IMAGE"

cat > "$BACKUP_DIR/throwaway_env.json" <<EOF
{"database": "$DB", "jwt_secret": "$JWT_SECRET", "container": "$CONTAINER", "stamp": "$STAMP"}
EOF
echo "stand facts written to $BACKUP_DIR/throwaway_env.json (backups/ is gitignored)"

echo "== 6. Import credential + workflows via n8n CLI =="
CRED_FILE="$(mktemp)"
python3 - "$DB" "$PGPASS" > "$CRED_FILE" <<'PYEOF'
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
prep () {  # <src> <dest-name> [id]  — n8n CLI import needs explicit active + versionId
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
prep "$GEN_AUTH/auth-guard.json"            auth-guard.json "$GUARD_ID"
prep "$GEN_AUTH/protected-employees.json"   protected-employees.json
prep "$GEN_H1/manage-periods.json"          manage-periods.json
prep "$GEN_H1/save-score-coefficients.json" save-score-coefficients.json
prep "$GEN_H1/submit-evaluation.json"       submit-evaluation.json
prep "$GEN_H1/self-review-submit.json"      self-review-submit.json
prep "$GEN_H1/update-evaluation.json"       update-evaluation.json
prep "$GEN_H1/check-self-review.json"       check-self-review.json
prep "$GEN_H1/check-evaluated.json"         check-evaluated.json
prep "$GEN_H1/get-my-manager.json"          get-my-manager.json
prep "$GEN_H1/save-user.json"               save-user.json
prep "$GEN_DEF/score-correction.json"       score-correction.json
prep "$GEN_DEF/evaluations-matrix.json"     evaluations-matrix.json

for i in $(seq 1 30); do
  if "${SSH[@]}" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:25679/healthz" | grep -q 200; then
    break
  fi
  sleep 2
done
scp -q "$CRED_FILE" "$HOST:/tmp/epe_reclass_cred.json"
# docker cp NESTS a directory when the target exists — clear the container path first.
tar -C "$IMPORT_DIR" -cf - . | "${SSH[@]}" "rm -rf /tmp/epe_rc_wf && mkdir -p /tmp/epe_rc_wf && tar -C /tmp/epe_rc_wf -xf -"
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf 2>/dev/null || true"
"${SSH[@]}" "docker cp /tmp/epe_reclass_cred.json $CONTAINER:/tmp/cred.json && docker cp /tmp/epe_rc_wf $CONTAINER:/tmp/wf && docker exec -u root $CONTAINER chown -R node:node /tmp/cred.json /tmp/wf"
"${SSH[@]}" "docker exec -u node $CONTAINER n8n import:credentials --input=/tmp/cred.json"
"${SSH[@]}" "docker exec -u node $CONTAINER n8n import:workflow --separate --input=/tmp/wf/"
"${SSH[@]}" "rm -f /tmp/epe_reclass_cred.json && rm -rf /tmp/epe_rc_wf"

echo "== 7. Activate webhook workflows (guard stays inactive, live parity) =="
LIST="$("${SSH[@]}" "docker exec -u node $CONTAINER n8n list:workflow")"
echo "$LIST"
for NAME in \
  "API: Manage Periods" \
  "API: Get Employees (Smart Role Based)" \
  "API: Save Score Coefficients" \
  "API: Submit Evaluation" \
  "API: Submit Self Review" \
  "API: Update Evaluation WITH PERIOD" \
  "API: Check Self Review" \
  "API: Check Evaluated V2" \
  "API: Get My Manager" \
  "API: Admin Save User (GUI Mode)" \
  "API: Score Correction" \
  "API: evaluations-matrix"; do
  WF_ID="$(echo "$LIST" | grep -F "|$NAME" | cut -d'|' -f1 | head -1)"
  test -n "$WF_ID" || { echo "workflow not found: $NAME"; exit 1; }
  "${SSH[@]}" "docker exec -u node $CONTAINER n8n update:workflow --id=$WF_ID --active=true" >/dev/null
  echo "activated $WF_ID $NAME"
done
"${SSH[@]}" "docker restart $CONTAINER" >/dev/null
sleep 12
"${SSH[@]}" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:25679/healthz" | grep -q 200 && echo "stand healthy"

echo "== DONE. Stand: $CONTAINER, DB: $DB, VPS loopback :25679 =="
echo "Local access: ssh -N -L 25679:127.0.0.1:25679 $HOST  (then http://127.0.0.1:25679/webhook)"

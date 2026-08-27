#!/usr/bin/env bash
# Build the PEER_RECOGNITION stand on the VPS (2026-08-27).
# Live epe_2026 and the live n8n are never written by this script.
#
# ONE database restored from TODAY's dump of live — the campaign is OPEN, so the
# restored period 2 already carries evaluation_started_at — plus migration 018
# applied to the STAND ONLY, and ONE isolated n8n container carrying the
# working-tree workflow surface, i.e. exactly what the deploy will PUT/POST.
#
#   epe_recognition_<stamp>  ← container epe-recognition-n8n (:25679, VPS loopback)
#
# The stand is where every nomination in the proof is stored. Live must store
# none until the proof has passed.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
STAND_TMP="/root/epe_stand_tmp"   # never /tmp: PROJECT_RULES 2026-08-24 (BUG-053)
# The close proof runs this script twice — once for the treatment database and
# once for the control — so the database name, container and port are
# overridable. The prefix `epe_recognition_` is load-bearing either way: the
# teardown loop refuses to drop anything that does not carry it.
DB="epe_recognition_${EPE_RECOGNITION_TAG:-}${STAMP}"
DUMP="${EPE_RECOGNITION_DUMP:?set EPE_RECOGNITION_DUMP to the VPS-side dump path}"
BACKUP_DIR="$REPO/backups/2026-08-27-peer-recognition"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER="${EPE_RECOGNITION_CONTAINER:-epe-recognition-n8n}"
PORT="${EPE_RECOGNITION_PORT:-25679}"
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"

mkdir -p "$BACKUP_DIR"

echo "== 1. Throwaway DB restored from today's dump =="
"${SSH[@]}" "test -f $DUMP" || { echo "dump $DUMP not found on VPS"; exit 1; }
"${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
"${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner --no-acl < $DUMP" || true
N="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
S="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc \"SELECT count(*) FROM performance_db.evaluation_periods WHERE id=2 AND evaluation_started_at IS NOT NULL\"")"
test "$N" = "89" || { echo "restore verification failed: users=$N"; exit 1; }
test "$S" = "1"  || { echo "restore verification failed: stand period 2 not started"; exit 1; }
echo "  $DB restored: users=$N, period 2 started (inherited from live)"

echo "== 2. Migration 018 on the STAND ONLY =="
"${SSH[@]}" "cat > $STAND_TMP/018_peer_recognitions.sql && chmod 600 $STAND_TMP/018_peer_recognitions.sql" \
  < "$REPO/migrations/018_add_peer_recognitions.sql"
"${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1 -f -" \
  < "$REPO/migrations/018_add_peer_recognitions.sql" >/dev/null
T="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc \"SELECT count(*) FROM information_schema.tables WHERE table_schema='performance_db' AND table_name='peer_recognitions'\"")"
test "$T" = "1" || { echo "migration 018 did not create the table on the stand"; exit 1; }
echo "  performance_db.peer_recognitions present on the stand, live untouched"

echo "== 3. Generate the working-tree workflow surface =="
GEN="$(mktemp -d)"
for SCRIPT in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  python3 "$REPO/scripts/$SCRIPT.py" --postgres-credential-id "$CRED_ID" \
    --guard-workflow-id "$GUARD_ID" --output-directory "$GEN" >/dev/null
done
test -f "$GEN/peer-recognition.json" || { echo "surface incomplete: peer-recognition.json missing"; exit 1; }

echo "== 4. Isolated n8n container on VPS loopback :$PORT =="
JWT_SECRET="$(openssl rand -hex 32)"
PGPASS="$("${SSH[@]}" "docker exec postgres_n8n env | grep '^POSTGRES_PASSWORD=' | cut -d= -f2-")"
test -n "$PGPASS"
"${SSH[@]}" "docker rm -f $CONTAINER 2>/dev/null || true"
"${SSH[@]}" "docker run -d --name $CONTAINER --network n8n_default \
  -p 127.0.0.1:$PORT:5678 \
  -e N8N_ENCRYPTION_KEY=$(openssl rand -hex 24) \
  -e JWT_SIGNING_SECRET=$JWT_SECRET \
  -e NODE_FUNCTION_ALLOW_BUILTIN=crypto \
  -e NODE_FUNCTION_ALLOW_EXTERNAL=jsonwebtoken \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e N8N_SECURE_COOKIE=false \
  -e EPE_FRONTEND_URL=https://epe.sedamedical.com \
  -e WEBHOOK_URL=http://127.0.0.1:$PORT/ \
  -e GENERIC_TIMEZONE=Europe/Moscow -e TZ=Europe/Moscow \
  $IMAGE" >/dev/null

echo "== 5. Import credential + workflows =="
IMPORT_DIR="$(mktemp -d)"
prep () {  # <src> <dest> [id]
  python3 - "$1" "$2" "${3:-}" <<'PYEOF'
import json, sys, uuid
wf = json.load(open(sys.argv[1]))
wf["active"] = False
wf["versionId"] = str(uuid.uuid4())
# n8n import assigns a NEW id unless the file carries one. The guard MUST keep
# the live id: every Run Auth Guard node references it by literal id.
if len(sys.argv) > 3 and sys.argv[3]:
    wf["id"] = sys.argv[3]
json.dump(wf, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
PYEOF
}
prep "$GEN/auth-guard.json" "$IMPORT_DIR/auth-guard.json" "$GUARD_ID"
for F in "$GEN"/*.json; do
  BASE="$(basename "$F")"
  [ "$BASE" = "auth-guard.json" ] && continue
  prep "$F" "$IMPORT_DIR/$BASE"
done

CRED_FILE="$(mktemp)"
python3 - "$DB" "$PGPASS" "$CRED_ID" > "$CRED_FILE" <<'PYEOF'
import json, sys
db, password, cred_id = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps([{
    "id": cred_id, "name": "EPE 2026 Postgres", "type": "postgres",
    "data": {"host": "postgres_n8n", "port": 5432, "database": db,
             "user": "admin", "password": password, "ssl": "disable",
             "allowUnauthorizedCerts": False, "sshTunnel": False},
}]))
PYEOF

echo "   waiting for $CONTAINER"
for _ in $(seq 1 90); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then break; fi
  sleep 2
done
# docker cp <dir> container:/path NESTS when the target exists; clear it first.
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf && docker exec $CONTAINER mkdir -p /tmp/wf"
tar -C "$IMPORT_DIR" -cf - . | "${SSH[@]}" "docker exec -i $CONTAINER tar -C /tmp/wf -xf -"
cat "$CRED_FILE" | "${SSH[@]}" "docker exec -i $CONTAINER sh -c 'cat > /tmp/cred.json'"
"${SSH[@]}" "docker exec $CONTAINER n8n import:credentials --input=/tmp/cred.json" >/dev/null
"${SSH[@]}" "docker exec $CONTAINER n8n import:workflow --separate --input=/tmp/wf" >/dev/null
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf /tmp/cred.json"
"${SSH[@]}" "docker exec $CONTAINER n8n update:workflow --all --active=true" >/dev/null
"${SSH[@]}" "docker restart $CONTAINER" >/dev/null
for _ in $(seq 1 90); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then break; fi
  sleep 2
done
rm -f "$CRED_FILE"

cat > "$BACKUP_DIR/throwaway_env_${CONTAINER}.json" <<EOF
{"database": "$DB", "jwt_secret": "$JWT_SECRET",
 "container": "$CONTAINER", "port": $PORT,
 "stamp": "$STAMP", "dump": "$DUMP", "brief": "PEER_RECOGNITION"}
EOF
echo "stand facts written to $BACKUP_DIR/throwaway_env_${CONTAINER}.json (backups/ is gitignored)"

echo
echo "Stand up."
echo "  DB        : $DB ← $CONTAINER (:$PORT, working-tree surface)"
echo "  tunnel    : ssh -N -L $PORT:127.0.0.1:$PORT $HOST"
echo "  prove     : python3 scripts/prove_recognition.py --base http://127.0.0.1:$PORT/webhook --db $DB"
echo "  teardown  : scripts/teardown_recognition_throwaway.sh"

#!/usr/bin/env bash
# Throwaway stand for EVALUATION_FORM_READABILITY (2026-08-27).
# Fresh dump of live → epe_readability_<stamp> → isolated n8n on :25679.
# Live epe_2026 and the live n8n are never written.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
STAND_TMP="/root/epe_stand_tmp"
DB="epe_readability_${STAMP}"
DUMP_NAME="epe_2026_readability_${STAMP}.dump"
BACKUP_DIR="$REPO/backups/2026-08-27-form-readability"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER="epe-readability-n8n"
PORT=25679
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"

mkdir -p "$BACKUP_DIR"

echo "== 1. Dated dump of live epe_2026 (stand source; no live write) =="
"${SSH[@]}" "mkdir -p $STAND_TMP && chmod 700 $STAND_TMP && docker exec postgres_n8n pg_dump -U admin -Fc epe_2026 > $STAND_TMP/$DUMP_NAME && chmod 600 $STAND_TMP/$DUMP_NAME && ls -la $STAND_TMP/$DUMP_NAME"
"${SSH[@]}" "cat $STAND_TMP/$DUMP_NAME" > "$BACKUP_DIR/$DUMP_NAME"
LOCAL_MD5="$(md5 -q "$BACKUP_DIR/$DUMP_NAME")"
REMOTE_MD5="$("${SSH[@]}" "md5sum $STAND_TMP/$DUMP_NAME | awk '{print \$1}'")"
test "$LOCAL_MD5" = "$REMOTE_MD5" || { echo "dump md5 mismatch local=$LOCAL_MD5 remote=$REMOTE_MD5"; exit 1; }
echo "  dump md5 $LOCAL_MD5 (both sides)"

echo "== 2. Throwaway DB $DB restored from that dump =="
"${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
"${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner --no-acl < $STAND_TMP/$DUMP_NAME" || true
N="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
S="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc \"SELECT count(*) FROM performance_db.evaluation_periods WHERE id=2 AND evaluation_started_at IS NOT NULL\"")"
test "$N" = "89" || { echo "restore verification failed: users=$N"; exit 1; }
test "$S" = "1"  || { echo "restore verification failed: stand period 2 not started"; exit 1; }
echo "  restored: users=$N, period 2 started (inherited from live)"

echo "== 3. Walkthrough fixture seed (guard rewritten to epe_readability_) =="
sed 's/\^epe_walk_/\^epe_readability_/' "$REPO/scripts/seed_walkthrough_throwaway.sql" \
  | "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" >/dev/null
F="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users WHERE id BETWEEN 1301 AND 1310'")"
test "$F" = "10" || { echo "fixture seed failed: $F"; exit 1; }

echo "== 4. Generate the working-tree workflow surface =="
GEN="$(mktemp -d)"
for SCRIPT in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  python3 "$REPO/scripts/$SCRIPT.py" --postgres-credential-id "$CRED_ID" \
    --guard-workflow-id "$GUARD_ID" --output-directory "$GEN" >/dev/null
done
test -f "$GEN/submit-evaluation.json" || { echo "surface incomplete"; exit 1; }

echo "== 5. Isolated n8n on VPS loopback :$PORT =="
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

echo "== 6. Import credential + workflows =="
IMPORT_DIR="$(mktemp -d)"
prep () {
  python3 - "$1" "$2" "${3:-}" <<'PYEOF'
import json, sys, uuid
wf = json.load(open(sys.argv[1]))
wf["active"] = False
wf["versionId"] = str(uuid.uuid4())
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

for _ in $(seq 1 90); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then
    break
  fi
  sleep 2
done

"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf && docker exec $CONTAINER mkdir -p /tmp/wf"
tar -C "$IMPORT_DIR" -cf - . | "${SSH[@]}" "docker exec -i $CONTAINER tar -C /tmp/wf -xf -"
cat "$CRED_FILE" | "${SSH[@]}" "docker exec -i $CONTAINER sh -c 'cat > /tmp/cred.json'"
"${SSH[@]}" "docker exec $CONTAINER n8n import:credentials --input=/tmp/cred.json" >/dev/null
"${SSH[@]}" "docker exec $CONTAINER n8n import:workflow --separate --input=/tmp/wf" >/dev/null
"${SSH[@]}" "docker exec $CONTAINER rm -rf /tmp/wf /tmp/cred.json"
"${SSH[@]}" "docker exec $CONTAINER n8n update:workflow --all --active=true" >/dev/null
# Guard is a sub-workflow on live (active=false). Keep that parity.
"${SSH[@]}" "docker exec $CONTAINER n8n update:workflow --id=$GUARD_ID --active=false" >/dev/null || true
"${SSH[@]}" "docker restart $CONTAINER" >/dev/null
for _ in $(seq 1 90); do
  if "${SSH[@]}" "docker exec $CONTAINER sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then
    break
  fi
  sleep 2
done
rm -f "$CRED_FILE"

cat > "$BACKUP_DIR/throwaway_env.json" <<EOF
{"database": "$DB", "jwt_secret": "$JWT_SECRET",
 "container": "$CONTAINER", "port": $PORT,
 "stamp": "$STAMP", "dump": "$DUMP_NAME", "dump_md5": "$LOCAL_MD5",
 "brief": "EVALUATION_FORM_READABILITY"}
EOF
echo "stand facts: $BACKUP_DIR/throwaway_env.json (gitignored)"
echo
echo "Stand up."
echo "  DB        : $DB ← $CONTAINER (:$PORT)"
echo "  tunnel    : ssh -N -L $PORT:127.0.0.1:$PORT $HOST"
echo "  frontend  : VITE_DEV_API_PROXY=http://127.0.0.1:$PORT npm run dev -- --port 5299 --strictPort"
echo "  teardown  : scripts/teardown_readability_throwaway.sh"

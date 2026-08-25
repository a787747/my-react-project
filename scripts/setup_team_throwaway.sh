#!/usr/bin/env bash
# Build the isolated TEAM_PAGE_AND_DEPLOY_LOCK stand on the VPS (brief 2026-08-25).
# Live epe_2026 and the live n8n are never written by this script.
#
#   - one fresh dated dump of live epe_2026 (also the session's rollback anchor)
#   - ONE throwaway database epe_team_<stamp> restored from it: the real org,
#     89 people, the real hierarchy, the two real terminations
#   - scripts/seed_team_throwaway.sql: password hashes for ids 2 and 88 only,
#     generated per run and passed in, never committed
#   - isolated n8n `epe-team-n8n` on VPS loopback :25679, same pinned image
#     digest as live, carrying the FULL generated workflow surface
#
# The evaluation is STARTED afterwards, on the stand, through the real
# POST /api/periods/start-evaluation route — never on live.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
STAND_TMP="/root/epe_stand_tmp"   # never /tmp: PROJECT_RULES 2026-08-24 (BUG-053)
DB="epe_team_${STAMP}"
BACKUP_DIR="$REPO/backups/2026-08-25-teampage"
ANCHOR_DIR="$HOME/EPE_ROLLBACK/2026-08-25-teampage"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER="epe-team-n8n"
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"
STAND_PASSWORD="Team2026-Portal!"

mkdir -p "$BACKUP_DIR" "$ANCHOR_DIR"
chmod 700 "$ANCHOR_DIR"

echo "== 0. Refuse to run unless live is in the expected state =="
LIVE_STATE="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d epe_2026 -tAc \"SELECT (SELECT count(*) FROM performance_db.users) || '/' || (SELECT count(*) FROM performance_db.evaluations) || '/' || (SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL) || '/' || (SELECT coalesce((SELECT 'started' FROM performance_db.evaluation_periods WHERE id=2 AND evaluation_started_at IS NOT NULL), 'notstarted'))\"")"
echo "live users/evaluations/terminated/gate = $LIVE_STATE"
test "$LIVE_STATE" = "89/0/2/notstarted" || { echo "live is not in the expected pre-gate state; refusing"; exit 1; }

echo "== 1. Fresh dated dump of live epe_2026 (rollback anchor for this session) =="
DUMP="epe_2026_teampage_${STAMP}.dump"
"${SSH[@]}" "mkdir -p $STAND_TMP && chmod 700 $STAND_TMP && docker exec postgres_n8n pg_dump -U admin -Fc --no-owner --no-acl epe_2026 > $STAND_TMP/$DUMP && chmod 600 $STAND_TMP/$DUMP && ls -la $STAND_TMP/$DUMP"
"${SSH[@]}" "cat $STAND_TMP/$DUMP" > "$ANCHOR_DIR/$DUMP"
chmod 600 "$ANCHOR_DIR/$DUMP"
MD5_REMOTE="$("${SSH[@]}" "md5sum $STAND_TMP/$DUMP | cut -d' ' -f1")"
MD5_LOCAL="$(md5 -q "$ANCHOR_DIR/$DUMP")"
echo "  anchor: $ANCHOR_DIR/$DUMP ($(wc -c < "$ANCHOR_DIR/$DUMP") bytes)"
echo "  md5 remote=$MD5_REMOTE local=$MD5_LOCAL"
test "$MD5_REMOTE" = "$MD5_LOCAL" || { echo "anchor md5 mismatch; refusing"; exit 1; }

echo "== 2. Throwaway DB restored from that dump =="
"${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
"${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner < $STAND_TMP/$DUMP" || true
N="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
T="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users WHERE terminated_at IS NOT NULL'")"
C="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.criteria WHERE is_active = true'")"
S="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.evaluation_period_participants WHERE period_id=2 AND is_in_scope=true'")"
echo "  $DB restored: users=$N terminated=$T active_criteria=$C h1_in_scope=$S"
test "$N" = "89" || { echo "restore verification failed: users=$N"; exit 1; }
test "$T" = "2"  || { echo "restore verification failed: terminated=$T"; exit 1; }
test "$C" = "9"  || { echo "restore verification failed: active criteria=$C"; exit 1; }
test "$S" = "85" || { echo "restore verification failed: h1 in scope=$S"; exit 1; }

echo "== 3. Seed: two real accounts become loggable-in, on the copy only =="
ADMIN_HASH="$(node -e "const c=require('crypto');const s=c.randomBytes(16);const d=c.scryptSync(process.argv[1],s,64,{N:16384,r:8,p:1,maxmem:67108864});console.log(['','scrypt','N=16384,r=8,p=1',s.toString('base64url'),d.toString('base64url')].join('\$'))" "$STAND_PASSWORD")"
MANAGER_HASH="$(node -e "const c=require('crypto');const s=c.randomBytes(16);const d=c.scryptSync(process.argv[1],s,64,{N:16384,r:8,p:1,maxmem:67108864});console.log(['','scrypt','N=16384,r=8,p=1',s.toString('base64url'),d.toString('base64url')].join('\$'))" "$STAND_PASSWORD")"
"${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1 -v admin_hash='$ADMIN_HASH' -v manager_hash='$MANAGER_HASH'" \
  < "$REPO/scripts/seed_team_throwaway.sql"

echo "== 4. Generate the workflow surface from the builders =="
GEN_H1="$(mktemp -d)"; GEN_DEF="$(mktemp -d)"; GEN_AUTH="$(mktemp -d)"
# Top-level n8n_workflows/ exports are untrusted (BUG-028/045). Everything is
# generated here, from the same builders that deploy to live.
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
  -e EPE_FRONTEND_URL=https://epe.sedamedical.com \
  -e WEBHOOK_URL=http://127.0.0.1:25679/ \
  -e GENERIC_TIMEZONE=Europe/Moscow -e TZ=Europe/Moscow \
  $IMAGE"

cat > "$BACKUP_DIR/throwaway_env.json" <<JSON
{"database": "$DB", "jwt_secret": "$JWT_SECRET", "container": "$CONTAINER", "stamp": "$STAMP", "stand_password": "$STAND_PASSWORD", "anchor": "$ANCHOR_DIR/$DUMP", "anchor_md5": "$MD5_LOCAL"}
JSON
echo "stand facts written to $BACKUP_DIR/throwaway_env.json (backups/ is gitignored)"

echo "== 6. Import credential + workflows via the n8n CLI =="
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

echo "== 7. Activate every imported workflow that has a webhook trigger =="
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
echo "  database : $DB"
echo "  n8n      : VPS 127.0.0.1:25679"
echo "  tunnel   : ssh -N -L 25679:127.0.0.1:25679 $HOST"
echo "  frontend : VITE_DEV_API_PROXY=http://127.0.0.1:25679 npm run dev -- --port 5399 --strictPort"
echo "  accounts : alexander@sedamedical.com (admin) / yelena@sedamedical.com (manager), password in throwaway_env.json"
echo "  next     : start the evaluation on the STAND via POST /api/periods/start-evaluation"
echo "  teardown : scripts/teardown_team_throwaway.sh"

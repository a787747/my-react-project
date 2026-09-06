#!/usr/bin/env bash
# Restore live into an isolated TALK stand; never writes live epe_2026.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
DB="epe_talk_${EPE_TALK_TAG:-}${STAMP}"
DUMP="${EPE_TALK_DUMP:?set EPE_TALK_DUMP to the VPS-side dump path}"
CONTAINER="${EPE_TALK_CONTAINER:-epe-talk-n8n}"
PORT="${EPE_TALK_PORT:-25679}"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"
OUT="$REPO/backups/2026-09-07-talk"
mkdir -p "$OUT"

"${SSH[@]}" "test -f '$DUMP' && docker exec postgres_n8n createdb -U admin '$DB'"
"${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d '$DB' --no-owner --no-acl < '$DUMP'" || true
USERS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d '$DB' -tAc 'SELECT count(*) FROM performance_db.users'")"
test "$USERS" -gt 80 || { echo "restore verification failed: users=$USERS"; exit 1; }

"${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d '$DB' -v ON_ERROR_STOP=1" \
  < "$REPO/migrations/019_add_management_talk.sql" >/dev/null
# Idempotency: second application must succeed and keep exactly one wave + 12 topics.
"${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d '$DB' -v ON_ERROR_STOP=1" \
  < "$REPO/migrations/019_add_management_talk.sql" >/dev/null
SHAPE="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d '$DB' -tAc \"
SELECT (SELECT count(*) FROM performance_db.management_talk_waves) || '/' ||
       (SELECT count(*) FROM performance_db.management_talk_topics) || '/' ||
       (SELECT count(*) FROM performance_db.management_talk_responses) || '/' ||
       (SELECT count(*) FROM performance_db.management_talk_counterparts)\"")"
test "$SHAPE" = "1/12/0/0" || { echo "bad TALK migration shape: $SHAPE"; exit 1; }

GEN="$(mktemp -d)"
for BUILDER in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  python3 "$REPO/scripts/$BUILDER.py" --postgres-credential-id "$CRED_ID" \
    --guard-workflow-id "$GUARD_ID" --output-directory "$GEN" >/dev/null
done
IMPORT="$(mktemp -d)"
python3 - "$GEN" "$IMPORT" "$GUARD_ID" <<'PY'
import json, pathlib, sys, uuid
src, dst, guard = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
for path in src.glob("*.json"):
    data = json.loads(path.read_text())
    data["active"] = False
    data["versionId"] = str(uuid.uuid4())
    if path.name == "auth-guard.json":
        data["id"] = guard
    (dst / path.name).write_text(json.dumps(data, ensure_ascii=False, indent=2))
PY

JWT_SECRET="$(openssl rand -hex 32)"
PGPASS="$("${SSH[@]}" "docker exec postgres_n8n env | awk -F= '/^POSTGRES_PASSWORD=/{sub(/^[^=]*=/,\"\"); print}'")"
"${SSH[@]}" "docker rm -f '$CONTAINER' 2>/dev/null || true" >/dev/null
"${SSH[@]}" "docker run -d --name '$CONTAINER' --network n8n_default \
  -p 127.0.0.1:$PORT:5678 \
  -e N8N_ENCRYPTION_KEY=$(openssl rand -hex 24) \
  -e JWT_SIGNING_SECRET=$JWT_SECRET \
  -e NODE_FUNCTION_ALLOW_BUILTIN=crypto \
  -e NODE_FUNCTION_ALLOW_EXTERNAL=jsonwebtoken \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e N8N_SECURE_COOKIE=false \
  -e EPE_FRONTEND_URL=https://epe.sedamedical.com \
  -e WEBHOOK_URL=http://127.0.0.1:$PORT/ \
  -e GENERIC_TIMEZONE=Europe/Moscow -e TZ=Europe/Moscow '$IMAGE'" >/dev/null

for _ in $(seq 1 90); do
  "${SSH[@]}" "docker exec '$CONTAINER' sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok && break
  sleep 2
done

CRED="$(mktemp)"
python3 - "$DB" "$PGPASS" "$CRED_ID" > "$CRED" <<'PY'
import json, sys
db, password, cid = sys.argv[1:]
print(json.dumps([{"id": cid, "name": "EPE 2026 Postgres", "type": "postgres",
  "data": {"host": "postgres_n8n", "port": 5432, "database": db, "user": "admin",
           "password": password, "ssl": "disable", "allowUnauthorizedCerts": False,
           "sshTunnel": False}}]))
PY
"${SSH[@]}" "docker exec '$CONTAINER' rm -rf /tmp/wf && docker exec '$CONTAINER' mkdir -p /tmp/wf"
tar -C "$IMPORT" -cf - . | "${SSH[@]}" "docker exec -i '$CONTAINER' tar -C /tmp/wf -xf -"
cat "$CRED" | "${SSH[@]}" "docker exec -i '$CONTAINER' sh -c 'cat > /tmp/cred.json'"
"${SSH[@]}" "docker exec '$CONTAINER' n8n import:credentials --input=/tmp/cred.json" >/dev/null
"${SSH[@]}" "docker exec '$CONTAINER' n8n import:workflow --separate --input=/tmp/wf" >/dev/null
"${SSH[@]}" "docker exec '$CONTAINER' rm -rf /tmp/wf /tmp/cred.json"
"${SSH[@]}" "docker exec '$CONTAINER' n8n update:workflow --all --active=true" >/dev/null
"${SSH[@]}" "docker restart '$CONTAINER'" >/dev/null
for _ in $(seq 1 90); do
  "${SSH[@]}" "docker exec '$CONTAINER' sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok && break
  sleep 2
done
rm -f "$CRED"

cat > "$OUT/throwaway_env.json" <<EOF
{"database":"$DB","container":"$CONTAINER","port":$PORT,"dump":"$DUMP"}
EOF
echo "TALK stand ready: db=$DB container=$CONTAINER port=$PORT"

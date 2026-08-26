#!/usr/bin/env bash
# Build the isolated CLEVEL_AVERAGING stand on the VPS (2026-08-25/26).
# Live epe_2026 and the live n8n are never written by this script.
#
# TWO databases restored from ONE dump of live, seeded identically, and TWO
# isolated n8n containers:
#
#   epe_mid_night_clv_<stamp>_ctl  ← container epe-clevel-n8n-old (:25680)
#                                the workflow surface AS COMMITTED AT HEAD
#   epe_mid_night_clv_<stamp>_trt  ← container epe-clevel-n8n-new (:25679)
#                                the workflow surface FROM THE WORKING TREE
#
# Two copies of one dump is what makes the money claim provable: after both are
# closed through their own real close route, the two period_results sets differ
# only by what this session changed, because they started byte-identical. The
# NEW stand is also the one the browser walkthrough runs against, so the screens
# and the frozen numbers come from the same database.
#
# The stand's period 2 is STARTED (the seed presses the second gate). That is a
# stand-only change; live's gate is never touched, and this script refuses to
# run at all if live has been started.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%d_%H%M)"
STAND_TMP="/root/epe_stand_tmp"   # never /tmp: PROJECT_RULES 2026-08-24 (BUG-053)
DB_CTL="epe_mid_night_clv_${STAMP}_ctl"
DB_TRT="epe_mid_night_clv_${STAMP}_trt"
BACKUP_DIR="$REPO/backups/2026-08-26-clevel-averaging"
IMAGE="n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673"
CONTAINER_NEW="epe-clevel-n8n-new"
CONTAINER_OLD="epe-clevel-n8n-old"
PORT_NEW=25679
PORT_OLD=25680
CRED_ID="VNbfkY8IKbEzn88B"
GUARD_ID="L0Zr7nVa8O5YWXd3"

mkdir -p "$BACKUP_DIR"

echo "== 0. Refuse to run unless live is in the expected state =="
LIVE_STATE="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d epe_2026 -tAc \"SELECT (SELECT count(*) FROM performance_db.users) || '/' || (SELECT count(*) FROM performance_db.evaluations) || '/' || (SELECT coalesce((SELECT 'started' FROM performance_db.evaluation_periods WHERE evaluation_started_at IS NOT NULL LIMIT 1), 'notstarted'))\"")"
echo "live users/evaluations/gate = $LIVE_STATE"
test "$LIVE_STATE" = "89/0/notstarted" || { echo "live is not in the expected pre-gate state; refusing"; exit 1; }

echo "== 1. Dated dump of live epe_2026 =="
"${SSH[@]}" "mkdir -p $STAND_TMP && chmod 700 $STAND_TMP && docker exec postgres_n8n pg_dump -U admin -Fc --no-owner --no-acl epe_2026 > $STAND_TMP/epe_2026_clevel_${STAMP}.dump && chmod 600 $STAND_TMP/epe_2026_clevel_${STAMP}.dump"
"${SSH[@]}" "cat $STAND_TMP/epe_2026_clevel_${STAMP}.dump" > "$BACKUP_DIR/epe_2026_clevel_${STAMP}.dump"
echo "local copy: $BACKUP_DIR/epe_2026_clevel_${STAMP}.dump ($(wc -c < "$BACKUP_DIR/epe_2026_clevel_${STAMP}.dump") bytes)"

echo "== 2. Two throwaway DBs restored from the SAME dump =="
for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec postgres_n8n createdb -U admin $DB"
  "${SSH[@]}" "docker exec -i postgres_n8n pg_restore -U admin -d $DB --no-owner < $STAND_TMP/epe_2026_clevel_${STAMP}.dump" || true
  N="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.users'")"
  C="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB -tAc 'SELECT count(*) FROM performance_db.criteria WHERE is_active = true'")"
  test "$N" = "89" || { echo "restore verification failed on $DB: users=$N"; exit 1; }
  test "$C" = "9"  || { echo "restore verification failed on $DB: active criteria=$C"; exit 1; }
  echo "  $DB restored: users=$N active_criteria=$C"
done

echo "== 3. Fixture seed on both (midyear 1601-1611, night 1612-1615, clevel 1616) =="
for DB in "$DB_CTL" "$DB_TRT"; do
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/scripts/seed_midyear_throwaway.sql" >/dev/null
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/scripts/seed_night_extra.sql" >/dev/null
  "${SSH[@]}" "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1" \
    < "$REPO/scripts/seed_clevel_second.sql" >/dev/null
  echo "  $DB seeded"
done

echo "== 3b. The two copies start identical =="
FP_SQL="SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (SELECT concat_ws(':', e.id, e.subject_id, e.evaluator_id, e.period_id, e.calculated_score, e.evaluation_source, e.is_self_evaluation, s.criteria_id, s.score_value) AS t FROM performance_db.evaluations e LEFT JOIN performance_db.evaluation_scores s ON s.evaluation_id = e.id) x"
FP_CTL="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB_CTL -tAc \"$FP_SQL\"")"
FP_TRT="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d $DB_TRT -tAc \"$FP_SQL\"")"
echo "  evaluations fingerprint control=$FP_CTL treatment=$FP_TRT"
test "$FP_CTL" = "$FP_TRT" || { echo "the two stands did not start identical; refusing"; exit 1; }

echo "== 4. Generate BOTH workflow surfaces =="
GEN_NEW="$(mktemp -d)"
OLD_SCRIPTS="$(mktemp -d)"
GEN_OLD="$(mktemp -d)"
# NEW — the working tree, i.e. exactly what will be deployed.
for S in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  python3 "$REPO/scripts/$S.py" --postgres-credential-id "$CRED_ID" \
    --guard-workflow-id "$GUARD_ID" --output-directory "$GEN_NEW" >/dev/null
done
# OLD — the same three builders as committed at HEAD, so the control stand is
# what live serves today and the diff is exactly this session's change. The
# builders resolve their legacy inputs as <script>/../n8n_workflows, so the
# throwaway tree has to have the same shape as the repository.
mkdir -p "$OLD_SCRIPTS/scripts"
ln -s "$REPO/n8n_workflows" "$OLD_SCRIPTS/n8n_workflows"
for S in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  git -C "$REPO" show "HEAD:scripts/$S.py" > "$OLD_SCRIPTS/scripts/$S.py"
done
for S in build_route_guard_workflows build_route_guard_deferred build_auth_workflows; do
  python3 "$OLD_SCRIPTS/scripts/$S.py" --postgres-credential-id "$CRED_ID" \
    --guard-workflow-id "$GUARD_ID" --output-directory "$GEN_OLD" >/dev/null
done
test -f "$GEN_NEW/manage-period-scope.json" || { echo "NEW surface incomplete"; exit 1; }
test -f "$GEN_OLD/manage-periods.json" || { echo "OLD surface incomplete"; exit 1; }
# The two surfaces must actually differ, or the control proves nothing.
if diff -rq "$GEN_OLD" "$GEN_NEW" >/dev/null 2>&1; then
  echo "OLD and NEW workflow surfaces are identical — the control would be vacuous; refusing"
  exit 1
fi
echo "  surfaces differ in: $(diff -rq "$GEN_OLD" "$GEN_NEW" | wc -l | tr -d ' ') files"

echo "== 5. Two isolated n8n containers on VPS loopback =="
JWT_SECRET="$(openssl rand -hex 32)"
PGPASS="$("${SSH[@]}" "docker exec postgres_n8n env | grep '^POSTGRES_PASSWORD=' | cut -d= -f2-")"
test -n "$PGPASS"

start_container () {  # <name> <port> <db>
  local NAME="$1" PORT="$2" DB="$3"
  "${SSH[@]}" "docker rm -f $NAME 2>/dev/null || true"
  "${SSH[@]}" "docker run -d --name $NAME --network n8n_default \
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
}
start_container "$CONTAINER_NEW" "$PORT_NEW" "$DB_TRT"
start_container "$CONTAINER_OLD" "$PORT_OLD" "$DB_CTL"

cat > "$BACKUP_DIR/throwaway_env.json" <<EOF
{"database_control": "$DB_CTL", "database_treatment": "$DB_TRT",
 "jwt_secret": "$JWT_SECRET",
 "container_new": "$CONTAINER_NEW", "container_old": "$CONTAINER_OLD",
 "port_new": $PORT_NEW, "port_old": $PORT_OLD,
 "stamp": "$STAMP", "fixture_password": "Mid2026-Portal!"}
EOF
echo "stand facts written to $BACKUP_DIR/throwaway_env.json (backups/ is gitignored)"

echo "== 6. Import credential + workflows into each container =="
IMPORT_ROOT="$(mktemp -d)"
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

load_container () {  # <container> <generated-dir> <db>
  local NAME="$1" GEN="$2" DB="$3"
  local DIR="$IMPORT_ROOT/$NAME"
  mkdir -p "$DIR"
  prep "$GEN/auth-guard.json" "$DIR/auth-guard.json" "$GUARD_ID"
  for F in "$GEN"/*.json; do
    local BASE; BASE="$(basename "$F")"
    [ "$BASE" = "auth-guard.json" ] && continue
    prep "$F" "$DIR/$BASE"
  done

  local CRED; CRED="$(mktemp)"
  python3 - "$DB" "$PGPASS" "$CRED_ID" > "$CRED" <<'PYEOF'
import json, sys
db, password, cred_id = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps([{
    "id": cred_id, "name": "EPE 2026 Postgres", "type": "postgres",
    "data": {"host": "postgres_n8n", "port": 5432, "database": db,
             "user": "admin", "password": password, "ssl": "disable",
             "allowUnauthorizedCerts": False, "sshTunnel": False},
}]))
PYEOF

  echo "   waiting for $NAME"
  for _ in $(seq 1 90); do
    if "${SSH[@]}" "docker exec $NAME sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then break; fi
    sleep 2
  done
  # docker cp <dir> container:/path NESTS when the target exists, and the CLI
  # then re-imports the previous file. Clear the container-side dir first.
  "${SSH[@]}" "docker exec $NAME rm -rf /tmp/wf && docker exec $NAME mkdir -p /tmp/wf"
  tar -C "$DIR" -cf - . | "${SSH[@]}" "docker exec -i $NAME tar -C /tmp/wf -xf -"
  cat "$CRED" | "${SSH[@]}" "docker exec -i $NAME sh -c 'cat > /tmp/cred.json'"
  "${SSH[@]}" "docker exec $NAME n8n import:credentials --input=/tmp/cred.json" >/dev/null
  "${SSH[@]}" "docker exec $NAME n8n import:workflow --separate --input=/tmp/wf" >/dev/null
  "${SSH[@]}" "docker exec $NAME rm -rf /tmp/wf /tmp/cred.json"
  "${SSH[@]}" "docker exec $NAME n8n update:workflow --all --active=true" >/dev/null
  "${SSH[@]}" "docker restart $NAME" >/dev/null
  for _ in $(seq 1 90); do
    if "${SSH[@]}" "docker exec $NAME sh -c 'wget -q -O- http://127.0.0.1:5678/healthz 2>/dev/null'" | grep -q ok; then break; fi
    sleep 2
  done
  rm -f "$CRED"
  echo "  $NAME loaded against $DB"
}

load_container "$CONTAINER_NEW" "$GEN_NEW" "$DB_TRT"
load_container "$CONTAINER_OLD" "$GEN_OLD" "$DB_CTL"

echo
echo "Stand up."
echo "  control DB   : $DB_CTL   ← $CONTAINER_OLD (:$PORT_OLD, workflow surface at HEAD)"
echo "  treatment DB : $DB_TRT   ← $CONTAINER_NEW (:$PORT_NEW, working-tree surface)"
echo "  tunnel       : ssh -N -L $PORT_NEW:127.0.0.1:$PORT_NEW -L $PORT_OLD:127.0.0.1:$PORT_OLD $HOST"
echo "  frontend     : VITE_DEV_API_PROXY=http://127.0.0.1:$PORT_NEW npm run dev -- --port 5299 --strictPort"
echo "  teardown     : scripts/teardown_clevel_throwaway.sh"

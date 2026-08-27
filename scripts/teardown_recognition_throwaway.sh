#!/usr/bin/env bash
# Remove the PEER_RECOGNITION stand. The drop loop refuses any database whose
# name does not carry the stand prefix, so epe_2026 can never be a candidate,
# and only this brief's own container is touched. Also empties
# /root/epe_stand_tmp (PROJECT_RULES teardown checklist) — the kept copy is the
# local dated one under ~/EPE_ROLLBACK, md5-verified at copy time.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
PREFIX="epe_recognition_"

# Both containers: the treatment stand and the control the close proof adds.
for C in epe-recognition-n8n epe-recognition-n8n-ctl epe-recognition-n8n-ui; do
  "${SSH[@]}" "docker rm -f $C 2>/dev/null || true" >/dev/null
  echo "container $C removed"
done

DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT datname FROM pg_database WHERE datname LIKE '${PREFIX}%'\"")"
for DB in $DBS; do
  case "$DB" in
    "${PREFIX}"*) ;;
    *) echo "refusing to drop '$DB': not a recognition stand"; exit 1;;
  esac
  "${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB'\"" >/dev/null
  "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --if-exists $DB"
  echo "database $DB dropped"
done

"${SSH[@]}" "rm -f /root/epe_stand_tmp/*.dump /root/epe_stand_tmp/018_peer_recognitions.sql 2>/dev/null || true; ls -la /root/epe_stand_tmp 2>/dev/null || true"
echo "remaining databases: $("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE NOT datistemplate\"")"
echo "containers now: $("${SSH[@]}" "docker ps --format '{{.Names}}' | tr '\n' ' '")"

#!/usr/bin/env bash
# Remove the PRELAUNCH_BATCH_NIGHT stand. The drop loop refuses any database
# whose name does not carry the stand prefix, so epe_2026 can never be a
# candidate, and only this session's own two containers are touched.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
PREFIX="epe_mid_night_"

for C in epe-night-n8n-new epe-night-n8n-old; do
  "${SSH[@]}" "docker rm -f $C 2>/dev/null || true" >/dev/null
  echo "container $C removed"
done

DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT datname FROM pg_database WHERE datname LIKE '${PREFIX}%'\"")"
for DB in $DBS; do
  case "$DB" in
    "${PREFIX}"*) ;;
    *) echo "refusing to drop '$DB': not a night stand"; exit 1;;
  esac
  "${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB'\"" >/dev/null
  "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --if-exists $DB"
  echo "database $DB dropped"
done

echo "remaining databases: $("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE NOT datistemplate\"")"
echo "containers now: $("${SSH[@]}" "docker ps --format '{{.Names}}' | tr '\n' ' '")"

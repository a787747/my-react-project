#!/usr/bin/env bash
set -euo pipefail
HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
PREFIX="epe_talk_"

for container in epe-talk-n8n epe-talk-n8n-closed epe-talk-n8n-ui; do
  "${SSH[@]}" "docker rm -f '$container' 2>/dev/null || true" >/dev/null
done

DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \
  \"SELECT datname FROM pg_database WHERE datname LIKE '${PREFIX}%'\"")"
for db in $DBS; do
  case "$db" in "${PREFIX}"*) ;; *) echo "refusing to drop $db"; exit 1;; esac
  "${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -c \
    \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$db'\"" >/dev/null
  "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --if-exists '$db'"
done

"${SSH[@]}" "rm -f /root/epe_stand_tmp/*talk* 2>/dev/null || true"
echo "remaining databases: $("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \
  \"SELECT string_agg(datname,',' ORDER BY datname) FROM pg_database WHERE NOT datistemplate\"")"

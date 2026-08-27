#!/usr/bin/env bash
# Remove the EVALUATION_FORM_READABILITY stand. The drop loop refuses any
# database whose name does not carry the stand prefix, so epe_2026 can never
# be a candidate. Empties this brief's files under /root/epe_stand_tmp.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
PREFIX="epe_readability_"

"${SSH[@]}" "docker rm -f epe-readability-n8n 2>/dev/null || true" >/dev/null
echo "container epe-readability-n8n removed"

DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT datname FROM pg_database WHERE datname LIKE '${PREFIX}%'\"")"
for DB in $DBS; do
  case "$DB" in
    "${PREFIX}"*) ;;
    *) echo "refusing to drop '$DB': not a readability stand"; exit 1;;
  esac
  "${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB'\"" >/dev/null
  "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --if-exists $DB"
  echo "database $DB dropped"
done

"${SSH[@]}" "rm -f /root/epe_stand_tmp/epe_2026_readability_*.dump /root/epe_stand_tmp/epe_readability_* 2>/dev/null || true"
echo "remaining databases: $("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE NOT datistemplate\"")"

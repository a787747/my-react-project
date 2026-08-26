#!/usr/bin/env bash
# Remove the ROLE_ACCESS_DEPLOY stand. The drop loop refuses any database whose
# name does not carry the stand prefix, so epe_2026 can never be a candidate,
# and only this brief's own container is touched. Also empties /root/epe_stand_tmp
# (PROJECT_RULES teardown checklist) — the kept copies are the local dated ones
# under ~/EPE_ROLLBACK, md5-verified at copy time.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
PREFIX="epe_roleaccess_"

"${SSH[@]}" "docker rm -f epe-roleaccess-n8n 2>/dev/null || true" >/dev/null
echo "container epe-roleaccess-n8n removed"

DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT datname FROM pg_database WHERE datname LIKE '${PREFIX}%'\"")"
for DB in $DBS; do
  case "$DB" in
    "${PREFIX}"*) ;;
    *) echo "refusing to drop '$DB': not a role-access stand"; exit 1;;
  esac
  "${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB'\"" >/dev/null
  "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --if-exists $DB"
  echo "database $DB dropped"
done

"${SSH[@]}" "rm -f /root/epe_stand_tmp/*.dump 2>/dev/null || true; ls -la /root/epe_stand_tmp 2>/dev/null || true"
echo "remaining databases: $("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE NOT datistemplate\"")"
echo "containers now: $("${SSH[@]}" "docker ps --format '{{.Names}}' | tr '\n' ' '")"

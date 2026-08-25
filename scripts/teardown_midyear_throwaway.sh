#!/usr/bin/env bash
# Tear the MID_YEAR_HIRES_SCOPE stand down (brief 2026-08-25).
#
# A stand database is a second copy of production personal data outside the
# backup regime — it is not a place to leave things (PROJECT_RULES). This
# removes the stand container, drops every epe_mid_* database, and empties
# /root/epe_stand_tmp of this brief's dumps.
#
# The drop loop refuses any database name that does not start with epe_mid_,
# so epe_2026 can never be a candidate.
set -euo pipefail

HOST="root@92.51.45.147"
SSH=(ssh -o BatchMode=yes "$HOST")
CONTAINER="epe-mid-n8n"

echo "== container =="
"${SSH[@]}" "docker rm -f $CONTAINER 2>/dev/null || true"

echo "== databases =="
DBS="$("${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc \"SELECT datname FROM pg_database WHERE datname LIKE 'epe\\_mid\\_%'\"")"
for DB in $DBS; do
  case "$DB" in
    epe_mid_*) "${SSH[@]}" "docker exec postgres_n8n dropdb -U admin --force $DB" && echo "  dropped $DB" ;;
    *) echo "  REFUSED: $DB does not match the stand prefix"; exit 1 ;;
  esac
done

echo "== VPS scratch =="
"${SSH[@]}" "rm -f /root/epe_stand_tmp/epe_2026_mid_*.dump; ls -la /root/epe_stand_tmp"

echo "== what remains on postgres_n8n =="
"${SSH[@]}" "docker exec postgres_n8n psql -U admin -d postgres -tAc 'SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname'"

echo "== containers (unchanged set expected) =="
"${SSH[@]}" "docker ps --format '{{.Names}}' | sort"

#!/bin/bash
# EPE live backup — the LIVE campaign database and the n8n application schema.
#
#   epe_2026            all schemas  -> daily/epe_2026_<stamp>.dump.gz
#   postgres, schema public          -> daily/n8n_app_<stamp>.dump.gz
#                                       (workflow_entity, credentials_entity, settings, ...)
#
# Companion to backup-performance-db.sh, which dumps the read-only 2025 archive
# (database postgres, schema performance_db). That script and its cron line are NOT
# touched by this one. Together the two jobs cover every schema of both databases.
#
# Pruning is stem-scoped: this script only ever deletes epe_2026_* / n8n_app_* files,
# never performance_db_* files, and the archive job never deletes these.
#
# Installed 2026-08-21 for BUG-032. Cron: 20 3 * * * (host TZ MSK) = 00:20 UTC.
#
# Failure contract: any failure exits non-zero, writes a FAIL line to backup.log,
# writes FAIL into the status file, prints to stderr, and removes the partial dump.
# There is no MTA on this host, so the status file and the log ARE the alarm:
#   cat /root/backups/epe/backup-epe-live.status
#
# PGC exists so the failure path can be exercised without touching a container
# (PGC=no_such_container /root/backups/epe/backup-epe-live.sh). Cron passes no env,
# so the scheduled run always uses postgres_n8n.

set -Eeuo pipefail

DIR=/root/backups/epe/daily
LOG=/root/backups/epe/backup.log
STATUS=/root/backups/epe/backup-epe-live.status
PGC=${PGC:-postgres_n8n}
RETAIN_DAYS=14
MIN_BYTES=1000

CURRENT_FILE=""

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

fail() {
  local msg="$1"
  [ -n "$CURRENT_FILE" ] && rm -f "$CURRENT_FILE"
  echo "[$(ts)] FAIL epe-live $msg" >>"$LOG"
  echo "FAIL $(ts) $msg" >"$STATUS"
  echo "epe-live backup FAILED: $msg" >&2
  exit 1
}
trap 'fail "unexpected error at line $LINENO"' ERR

mkdir -p "$DIR"
chmod 700 /root/backups /root/backups/epe "$DIR"
STAMP=$(date -u +%Y-%m-%dT%H%MZ)

dump_one() {
  local label="$1"; shift
  local file="$DIR/${label}_${STAMP}.dump.gz"
  local size deleted retained
  CURRENT_FILE="$file"
  echo "[$(ts)] start $file" >>"$LOG"
  if ! docker exec "$PGC" pg_dump -U admin "$@" --no-owner --no-acl -Fc 2>>"$LOG" | gzip -9 >"$file"; then
    fail "$label pg_dump failed"
  fi
  chmod 600 "$file"
  size=$(wc -c <"$file" | tr -d " ")
  if [ "$size" -lt "$MIN_BYTES" ]; then
    fail "$label dump too small: $size bytes"
  fi
  CURRENT_FILE=""
  deleted=$(find "$DIR" -type f -name "${label}_*.dump.gz" -mtime +${RETAIN_DAYS} -print -delete | wc -l | tr -d " ")
  retained=$(ls -1 "$DIR"/${label}_*.dump.gz | wc -l | tr -d " ")
  echo "[$(ts)] ok $label size=$size retained=$retained pruned=$deleted" >>"$LOG"
}

dump_one epe_2026 -d epe_2026
dump_one n8n_app  -d postgres -n public

echo "OK $(ts) stamp=$STAMP" >"$STATUS"
echo "[$(ts)] ok epe-live all targets stamp=$STAMP" >>"$LOG"

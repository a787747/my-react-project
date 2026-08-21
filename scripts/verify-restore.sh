#!/bin/bash
# Restore-proof for the epe-live backup job (BUG-032).
# Restores the newest dump of one stem into a THROWAWAY database and prints a
# row-count table for every table, throwaway vs live. Drops the throwaway.
#
#   ./verify-restore.sh epe_2026 epe_2026 ""        # whole DB
#   ./verify-restore.sh n8n_app  postgres  public   # n8n application schema
#
# The throwaway name always starts with epe_bkverify_ — the drop at the end
# refuses any name that does not.
set -Eeuo pipefail

STEM="$1"; LIVE_DB="$2"; ONLY_SCHEMA="${3:-}"
DIR=/root/backups/epe/daily
STAMP=$(date -u +%Y%m%d_%H%M%S)
TMP="epe_bkverify_${STEM}_${STAMP}"

SRC=$(ls -1t "$DIR"/${STEM}_*.dump.gz | head -1)
echo "### stem=$STEM  source dump = $SRC"
ls -la --time-style=long-iso "$SRC"
echo "### throwaway = $TMP   live = $LIVE_DB${ONLY_SCHEMA:+ (schema $ONLY_SCHEMA)}"

gunzip -c "$SRC" >/tmp/_verify.dump
docker cp /tmp/_verify.dump postgres_n8n:/tmp/_verify.dump >/dev/null
rm -f /tmp/_verify.dump

docker exec postgres_n8n createdb -U admin "$TMP"
# The dumps carry CREATE SCHEMA for their own schemas; a fresh database already has
# an empty public schema, so drop it first and let the dump recreate it. Otherwise
# pg_restore reports "schema public already exists" and exits non-zero on a restore
# that is in fact complete.
docker exec postgres_n8n psql -U admin -d "$TMP" -q -c "DROP SCHEMA IF EXISTS public CASCADE;"
echo "### pg_restore:"
set +e
docker exec postgres_n8n pg_restore -U admin -d "$TMP" --no-owner --no-acl --exit-on-error /tmp/_verify.dump 2>&1 | tail -20
RC=${PIPESTATUS[0]}
set -e
echo "### pg_restore exit=$RC (0 = no errors, --exit-on-error was set)"
if [ "$RC" -ne 0 ]; then
  docker exec postgres_n8n dropdb -U admin --if-exists "$TMP"
  echo "restore failed; throwaway dropped"
  exit 1
fi

COUNTQ="SELECT table_schema||'.'||table_name AS t,
        (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text::bigint AS n
        FROM information_schema.tables
        WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')"
if [ -n "$ONLY_SCHEMA" ]; then
  COUNTQ="$COUNTQ AND table_schema='$ONLY_SCHEMA'"
fi
COUNTQ="$COUNTQ ORDER BY 1;"

docker exec postgres_n8n psql -U admin -d "$TMP"     -Atc "$COUNTQ" | sort >/tmp/_restored.txt
docker exec postgres_n8n psql -U admin -d "$LIVE_DB" -Atc "$COUNTQ" | sort >/tmp/_live.txt

echo "### row counts — table | restored | live | verdict"
awk -F"|" '
  NR==FNR { live[$1]=$2; seen[$1]=1; next }
  { r=$2; l=($1 in live)? live[$1] : "ABSENT"; got[$1]=1;
    v = (l==r) ? "MATCH" : "DIFF"; if (v=="DIFF") bad++;
    printf "%-46s %10s %10s  %s\n", $1, r, l, v; n++ }
  END {
    for (t in live) if (!(t in got)) { printf "%-46s %10s %10s  %s\n", t, "ABSENT", live[t], "DIFF"; bad++; n++ }
    printf "\nTABLES=%d MISMATCHES=%d\n", n, bad+0
  }' /tmp/_live.txt /tmp/_restored.txt

echo "### dropping throwaway"
case "$TMP" in
  epe_bkverify_*) docker exec postgres_n8n dropdb -U admin "$TMP"; echo "dropped $TMP" ;;
  *) echo "REFUSED to drop '$TMP' — name does not start with epe_bkverify_"; exit 1 ;;
esac
docker exec postgres_n8n rm -f /tmp/_verify.dump

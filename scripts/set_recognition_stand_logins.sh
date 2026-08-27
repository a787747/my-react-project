#!/usr/bin/env bash
# Set stand-local scrypt passwords on the throwaway DB only.
# Live epe_2026 is never a candidate: the database name must carry the
# epe_recognition_ prefix.
#
# The hash is piped on stdin so remote bash cannot expand the $scrypt$…
# markers (that is what produced a 79-char truncated hash the first time).
set -euo pipefail

HOST="root@92.51.45.147"
DB="${1:?stand database name}"
PASSWORD="${2:?stand password}"
case "$DB" in
  epe_recognition_*) ;;
  *) echo "refusing: '$DB' is not a recognition stand"; exit 1 ;;
esac

# Hash inside the stand n8n container — same Node/OpenSSL as the login route.
# A hash made on the laptop can verify locally and still 401 on the stand.
CONTAINER="${3:-epe-recognition-n8n-ui}"
HASH="$(ssh -o BatchMode=yes "$HOST" "docker exec -e PW=$(printf %q "$PASSWORD") $CONTAINER node -e \"
const c=require('crypto');
const s=c.randomBytes(16);
const d=c.scryptSync(process.env.PW,s,64,{N:16384,r:8,p:1,maxmem:64*1024*1024});
process.stdout.write(['','scrypt','N=16384,r=8,p:1',s.toString('base64url'),d.toString('base64url')].join('\\\\$'));
\"")"
test "${#HASH}" -ge 120

# Dollar-quote the hash so psql never interpolates it.
SQL="UPDATE performance_db.users
SET password_hash = \$h\$${HASH}\$h\$
WHERE id IN (2, 8, 15, 31, 47, 52, 70, 88);
SELECT id || '=' || length(password_hash) || '=' || left(password_hash, 8)
FROM performance_db.users WHERE id IN (2, 8, 15, 31, 47, 52, 70, 88)
ORDER BY id;"

printf '%s\n' "$SQL" | ssh -o BatchMode=yes "$HOST" \
  "docker exec -i postgres_n8n psql -U admin -d $DB -v ON_ERROR_STOP=1"

echo "stand logins set on $DB for ids 2,8,15,31,47,52,70,88"

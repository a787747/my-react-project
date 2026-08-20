#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOST="${EPE_DEPLOY_HOST:-root@92.51.45.147}"
REMOTE_ROOT="/var/www/epe"
RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$REPO_ROOT"

npm ci
VITE_API_URL=/webhook npm run build

if rg -q 'http://92\.51\.45\.147:5678' dist; then
  echo "Refusing deploy: legacy n8n URL remains in the bundle." >&2
  exit 1
fi

if ! rg -q '/webhook' dist; then
  echo "Refusing deploy: same-origin /webhook API base is absent." >&2
  exit 1
fi

ssh "$REMOTE_HOST" \
  "install -d -m 755 '$REMOTE_ROOT/releases/$RELEASE_ID'"

COPYFILE_DISABLE=1 tar --no-xattrs -C dist -cf - . | ssh "$REMOTE_HOST" \
  "tar -xf - -C '$REMOTE_ROOT/releases/$RELEASE_ID'"

OLD_LINK="$(ssh "$REMOTE_HOST" "readlink '$REMOTE_ROOT/current' || true")"

if ! ssh "$REMOTE_HOST" \
  "test -s '$REMOTE_ROOT/releases/$RELEASE_ID/index.html' && \
   ln -sfn 'releases/$RELEASE_ID' '$REMOTE_ROOT/current'"; then
  if [[ "$OLD_LINK" == releases/* ]]; then
    ssh "$REMOTE_HOST" \
      "ln -sfn '$OLD_LINK' '$REMOTE_ROOT/current'"
  fi
  echo "Deploy failed; previous release restored." >&2
  exit 1
fi

echo "Deployed release $RELEASE_ID to $REMOTE_HOST:$REMOTE_ROOT/current"

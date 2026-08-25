#!/usr/bin/env bash
# Deploy the EPE frontend to the live host.
#
# Two things this script must never do, both learned the hard way:
#
#   1. Pass its safety gates on one laptop and fail them on another (BUG-040).
#      The gates used `rg`, which is a real binary in one terminal and a shell
#      function — invisible to this script — in another. A gate whose outcome
#      depends on which terminal launched the deploy is not a gate. They now use
#      `grep -r`, which is POSIX and present on every machine this project runs
#      on, and the script proves the tool works before trusting a negative
#      result, so a broken toolchain can never look like a clean bundle.
#
#   2. Overwrite a release somebody else put live (BUG-062). On 2026-08-25 two
#      sessions deployed eleven minutes apart from the same checkout; the second
#      only avoided reverting the first because a human re-read the symlink by
#      hand. There are now two independent protections: an exclusive lock, held
#      locally and on the host for the whole upload-and-flip, and a
#      compare-and-swap — `current` is read before the build and re-read inside
#      the same remote command that flips it, so a deploy that started from a
#      stale reading refuses instead of silently winning.
#
# Refusing is always the correct outcome when either check trips. This script
# never breaks a lock and never forces a flip; both need a human who has looked.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOST="${EPE_DEPLOY_HOST:-root@92.51.45.147}"
REMOTE_ROOT="/var/www/epe"
RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOCAL_LOCK="$REPO_ROOT/.epe-deploy.lock"
REMOTE_LOCK="$REMOTE_ROOT/.deploy.lock"
# Test hook: sleep this many seconds between the build and the flip so a
# concurrent deploy can be demonstrated. It can only ever delay the deploy — it
# bypasses no gate and skips no step.
PAUSE_BEFORE_FLIP="${EPE_DEPLOY_PAUSE_BEFORE_FLIP:-0}"

cd "$REPO_ROOT"

say () { printf '%s\n' "$*" >&2; }
die () { say "$*"; exit 1; }

# ---------------------------------------------------------------- local lock
# mkdir is atomic on every filesystem this runs on; `set -e` turns the failure
# into an exit, so the message has to come from the test itself.
LOCAL_LOCK_HELD=0
if mkdir "$LOCAL_LOCK" 2>/dev/null; then
  LOCAL_LOCK_HELD=1
  printf 'pid=%s user=%s started=%s\n' "$$" "${USER:-unknown}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$LOCAL_LOCK/holder"
else
  say "Refusing deploy: another deploy is already running in this checkout."
  say "  lock: $LOCAL_LOCK"
  [ -f "$LOCAL_LOCK/holder" ] && say "  held by: $(cat "$LOCAL_LOCK/holder")"
  say "  If that process is gone, remove the lock by hand after checking:"
  say "    rm -rf '$LOCAL_LOCK'"
  exit 1
fi

REMOTE_LOCK_HELD=0
cleanup () {
  local rc=$?
  if [ "$REMOTE_LOCK_HELD" = "1" ]; then
    ssh "$REMOTE_HOST" "rm -rf '$REMOTE_LOCK'" 2>/dev/null || true
  fi
  if [ "$LOCAL_LOCK_HELD" = "1" ]; then
    rm -rf "$LOCAL_LOCK"
  fi
  exit $rc
}
trap cleanup EXIT INT TERM

# ------------------------------------------------------- baseline: what is live
# Read BEFORE the build. Everything this deploy does is predicated on this
# value, and the flip refuses if it has moved.
BASELINE_LINK="$(ssh "$REMOTE_HOST" "readlink '$REMOTE_ROOT/current' || true")"
say "current release at start: ${BASELINE_LINK:-<none>}"

npm ci
VITE_API_URL=/webhook npm run build

# ------------------------------------------------------------- safety gates
# A gate that can pass without inspecting anything is not a gate, so the bundle
# is proved to exist and `grep -r` is proved to work on it first. Only then is a
# "no match" allowed to mean "the legacy URL is absent".
test -s dist/index.html || die "Refusing deploy: dist/index.html is missing or empty."
command -v grep >/dev/null 2>&1 || die "Refusing deploy: grep is not available; the safety gates cannot run."
grep -r -q 'assets' dist/index.html \
  || die "Refusing deploy: the gate tool found nothing in dist/index.html, so a clean result would be meaningless."

if grep -r -q 'http://92\.51\.45\.147:5678' dist; then
  die "Refusing deploy: legacy n8n URL remains in the bundle."
fi

if ! grep -r -q '/webhook' dist; then
  die "Refusing deploy: same-origin /webhook API base is absent."
fi
say "gates: legacy :5678 absent, /webhook base present"

# ------------------------------------------------------------- remote lock
if ssh "$REMOTE_HOST" "mkdir '$REMOTE_LOCK' 2>/dev/null && printf 'release=%s from=%s started=%s\n' '$RELEASE_ID' '${USER:-unknown}@$(hostname -s 2>/dev/null || echo unknown)' \"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\" > '$REMOTE_LOCK/holder'"; then
  REMOTE_LOCK_HELD=1
else
  say "Refusing deploy: another deploy holds the lock on $REMOTE_HOST."
  say "  lock: $REMOTE_LOCK"
  say "  held by: $(ssh "$REMOTE_HOST" "cat '$REMOTE_LOCK/holder' 2>/dev/null || echo unknown")"
  say "  If that deploy is gone, remove the lock by hand after checking:"
  say "    ssh $REMOTE_HOST \"rm -rf '$REMOTE_LOCK'\""
  exit 1
fi

ssh "$REMOTE_HOST" \
  "install -d -m 755 '$REMOTE_ROOT/releases/$RELEASE_ID'"

COPYFILE_DISABLE=1 tar --no-xattrs -C dist -cf - . | ssh "$REMOTE_HOST" \
  "tar -xf - -C '$REMOTE_ROOT/releases/$RELEASE_ID'"

if [ "$PAUSE_BEFORE_FLIP" -gt 0 ] 2>/dev/null; then
  say "test hook: pausing ${PAUSE_BEFORE_FLIP}s before the flip"
  sleep "$PAUSE_BEFORE_FLIP"
fi

# --------------------------------------------------------- compare-and-swap
# The re-read and the flip are one remote command, so nothing can move `current`
# between them. Exit 9 is the conflict: this deploy started from a reading that
# is no longer true, and flipping would revert whoever is live now.
set +e
FLIP_OUT="$(ssh "$REMOTE_HOST" bash -s -- "$REMOTE_ROOT" "$RELEASE_ID" "$BASELINE_LINK" <<'REMOTE'
set -eu
ROOT="$1"; RELEASE_ID="$2"; BASELINE="$3"
CURRENT="$(readlink "$ROOT/current" || true)"
if [ "$CURRENT" != "$BASELINE" ]; then
  printf 'CONFLICT expected=%s actual=%s\n' "${BASELINE:-<none>}" "${CURRENT:-<none>}"
  exit 9
fi
if [ ! -s "$ROOT/releases/$RELEASE_ID/index.html" ]; then
  printf 'BADRELEASE %s\n' "$RELEASE_ID"
  exit 8
fi
ln -sfn "releases/$RELEASE_ID" "$ROOT/current"
printf 'FLIPPED %s\n' "$(readlink "$ROOT/current")"
REMOTE
)"
FLIP_RC=$?
set -e
say "$FLIP_OUT"

if [ "$FLIP_RC" = "9" ]; then
  say ""
  say "Refusing deploy: $REMOTE_ROOT/current moved while this deploy was running."
  say "  Somebody else deployed. Flipping now would revert their release."
  say "  Nothing was changed: current still points where they left it."
  say "  Release $RELEASE_ID is uploaded and unlinked; rebuild on top of what is"
  say "  actually live, then deploy again."
  exit 1
fi
if [ "$FLIP_RC" != "0" ]; then
  # The upload itself failed verification. `current` was never touched, so
  # there is nothing to roll back.
  die "Deploy failed before the flip; $REMOTE_ROOT/current is unchanged (${BASELINE_LINK:-<none>})."
fi

say "Deployed release $RELEASE_ID to $REMOTE_HOST:$REMOTE_ROOT/current (was ${BASELINE_LINK:-<none>})"

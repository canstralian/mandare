#!/bin/sh
# Fly (and most volume mounts) replace /app/data with a root-owned filesystem.
# Image-build `chown appuser /app/data` is overwritten at mount time, so the
# non-root process cannot seed policies.json or append JSONL ledgers.
# Run as root briefly, fix ownership, then drop privileges.
set -eu
APP_UID=10001
APP_GID=10001
if [ -d /app/data ]; then
  chown -R "${APP_UID}:${APP_GID}" /app/data
fi
exec setpriv --reuid="${APP_UID}" --regid="${APP_GID}" --clear-groups -- "$@"

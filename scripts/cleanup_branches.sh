#!/usr/bin/env bash
# List (default) or delete (--delete) remote branches fully merged into main.
#
# Usage:
#   ./scripts/cleanup_branches.sh            # dry run: print deletable branches
#   ./scripts/cleanup_branches.sh --delete   # delete them on the remote
#
# Only branches whose history is entirely contained in $REMOTE/$BASE are
# considered, so branches with unmerged commits are never touched. Long-lived
# branches (main, release/*, hotfix/*) are always skipped.
#
# Override the remote or base branch via environment variables:
#   REMOTE=upstream BASE=main ./scripts/cleanup_branches.sh

set -euo pipefail

REMOTE="${REMOTE:-origin}"
BASE="${BASE:-main}"
PROTECTED='^(main|master|HEAD|release(/.*)?|hotfix(/.*)?)$'

DELETE=false
case "${1:-}" in
  --delete) DELETE=true ;;
  "") ;;
  *)
    echo "usage: $0 [--delete]" >&2
    exit 2
    ;;
esac

git fetch "$REMOTE" --prune

git rev-parse --verify --quiet "$REMOTE/$BASE" >/dev/null || {
  echo "Error: remote branch '$REMOTE/$BASE' does not exist." >&2
  exit 1
git fetch "$REMOTE" --prune

# Verify that the base branch exists on the remote
git rev-parse --verify --quiet "$REMOTE/$BASE" >/dev/null || {
  echo "Error: Remote branch '$REMOTE/$BASE' does not exist." >&2
  exit 1
}

merged=$(git branch -r --merged "$REMOTE/$BASE" --format='%(refname:short)' |
  sed -n "s|^$REMOTE/||p" |
  grep -Ev "$PROTECTED" || true)

if [ -z "$merged" ]; then
  echo "No merged branches to clean up on $REMOTE."
  exit 0
fi

count=$(printf '%s\n' "$merged" | wc -l | tr -d ' ')
if [ "$DELETE" = true ]; then
  echo "Deleting $count merged branch(es) on $REMOTE:"
  printf '%s\n' "$merged" | sed 's/^/  deleting /'
  printf '%s\n' "$merged" | xargs git push "$REMOTE" --delete
  git fetch "$REMOTE" --prune
  echo "Done."
else
  echo "Merged into $REMOTE/$BASE and safe to delete ($count):"
  printf '%s\n' "$merged" | sed 's/^/  /'
  echo
  echo "Dry run only. Re-run with --delete to remove these branches on $REMOTE."
fi

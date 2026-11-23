#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
set -a
. ./.env
set +a

WORKDIR="${WORKDIR:-./work}"

if [ -d "$WORKDIR/worktrees" ]; then
  find "$WORKDIR/worktrees" -mindepth 1 -maxdepth 1 -type d -mtime +1 -exec rm -rf -- {} +
fi

if [ -d "$WORKDIR/repos" ]; then
  for repo in "$WORKDIR"/repos/*; do
    [ -d "$repo" ] || continue
    git -C "$repo" worktree prune || true
  done
fi

echo "Old worktrees removed and git metadata pruned."

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_HOST="${SSH_HOST:-cateam}"
remote_source=/root/password-game

mkdir -p "$repo_root/build"
stage="$(mktemp -d "$repo_root/build/.password-game.XXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
revision="$(ssh "$SSH_HOST" "git -C '$remote_source' rev-parse HEAD")"
ssh "$SSH_HOST" "git -C '$remote_source' archive '$revision'" | tar -x -C "$stage"
docker build --tag cateam/password-game:local --label "org.opencontainers.image.revision=$revision" "$stage"
printf 'Built password-game image from remote commit %s.\n' "$revision"

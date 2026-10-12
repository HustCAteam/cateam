#!/usr/bin/env bash
set -euo pipefail

# Stage the committed template artifact without rewriting any remote source.
# Edit/build the homepage yourself, then commit and push public/ before staging.
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="$repo_root/build"
release_dir="$build_dir/mainpage"
ssh_host="${SSH_HOST:-cateam}"
remote_source="${MAINPAGE_REMOTE_SOURCE:-/root/mainpage/cateam}"
ssh_options=(-o BatchMode=yes)
local_stage=''

cleanup() {
  local status=$?
  trap - EXIT
  if [[ -n "$local_stage" ]]; then
    rm -rf -- "$local_stage"
  fi
  exit "$status"
}
trap cleanup EXIT

for command in ssh tar mktemp; do
  command -v "$command" >/dev/null || { printf 'Missing required command: %s\n' "$command" >&2; exit 1; }
done
mkdir -p -- "$build_dir"
# Remove only this script's previous artifact so a failure cannot look successful.
rm -rf -- "$release_dir"
local_stage="$(mktemp -d "$build_dir/.mainpage.XXXXXXXX")"
printf -v quoted_source '%q' "$remote_source"
revision="$(ssh "${ssh_options[@]}" "$ssh_host" "git -C $quoted_source rev-parse --verify HEAD")"
printf -v quoted_revision '%q' "$revision"
ssh "${ssh_options[@]}" "$ssh_host" \
  "git -C $quoted_source archive $quoted_revision public" \
  | tar --extract --directory "$local_stage"

test -s "$local_stage/public/index.html"
mv -- "$local_stage/public" "$release_dir"
rm -rf -- "$local_stage"
local_stage=''
printf 'Mainpage release from committed public/ (%s): %s\n' "$revision" "$release_dir"

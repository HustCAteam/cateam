#!/usr/bin/env bash
set -euo pipefail
umask 022

# Build committed remote sources without rewriting any source working tree.
# Commit and push each remote repository before running this script.
# Requires Node 22.12–26.x, pnpm 11, Go 1.27.1, SSH, tar, and rsync on the build host.
# Only the Vite dist and a static Linux/amd64 executable enter the release.
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
ssh_host="${SSH_HOST:-cateam}"
source_root="${TOURANKI_REMOTE_SOURCE:-/root/touranki}"
ssh_options=(-o BatchMode=yes)
build_root="$repo_root/build"
release_dir="$build_root/touranki"
stage=""

cleanup() {
    local status=$?
    trap - EXIT
    if [[ -n "$stage" ]]; then
        rm -rf -- "$stage"
    fi
    if (( status != 0 )); then
        # A failed rebuild must never expose a partial or stale release.
        rm -rf -- "$release_dir"
        printf 'Touranki build failed; no release was published.\n' >&2
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p -- "$build_root"
rm -rf -- "$release_dir"
for tool in node pnpm go ssh tar rsync; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required build tool not found: %s\n' "$tool" >&2
        exit 1
    fi
done

stage="$(mktemp -d "$build_root/.touranki.XXXXXXXX")"
workspace="$stage/source"
staged_release="$stage/release"
mkdir -p -- "$staged_release/web"

# Capture each immutable HEAD, not uncommitted edits or deployed dist files.
# The frontend archive excludes raw assets/sources and all build outputs.
for module in touranki-web touranki-server touranki-core; do
    destination="$workspace/$module"
    mkdir -p -- "$destination"
    printf -v quoted_source '%q' "$source_root/$module"
    revision="$(ssh "${ssh_options[@]}" "$ssh_host" "git -C $quoted_source rev-parse --verify HEAD")"
    printf -v quoted_revision '%q' "$revision"
    if [[ "$module" == touranki-web ]]; then
        archive_paths='package.json pnpm-lock.yaml pnpm-workspace.yaml index.html tsconfig.json vite.config.ts src public'
    else
        archive_paths=''
    fi
    ssh "${ssh_options[@]}" "$ssh_host" \
        "git -C $quoted_source archive $quoted_revision $archive_paths" \
        | tar --extract --directory "$destination"
    printf 'Touranki source: %s %s\n' "$module" "$revision"
done

(
    cd -- "$workspace/touranki-web"
    # Build tools are devDependencies and are required even with NODE_ENV=production.
    pnpm install --frozen-lockfile --prod=false
    pnpm run build
)
rsync -a -- "$workspace/touranki-web/dist/" "$staged_release/web/"

(
    cd -- "$workspace/touranki-server"
    # The sibling workspace preserves replace touranki-core => ../touranki-core.
    # Disable ambient Go workspaces and pin the compiler required by both modules.
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOTOOLCHAIN=go1.27.1 GOWORK=off \
        go build -mod=readonly -trimpath -ldflags='-s -w' \
        -o "$staged_release/touranki-server" ./cmd/touranki-server
)
chmod 0755 "$staged_release/touranki-server"

# Publish both artifacts together only after both real production builds finish.
mv -- "$staged_release" "$release_dir"
printf 'Touranki release: %s\n' "$release_dir"

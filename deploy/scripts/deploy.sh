#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export SSH_HOST="${SSH_HOST:-cateam}"
remote_root=/root/cateam
caddy_ref='caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d'

bash "$repo_root/scripts/stage-mainpage.sh"
bash "$repo_root/scripts/build-touranki.sh"

docker pull "$caddy_ref"
docker tag "$caddy_ref" caddy:2.10.2-alpine
docker build --file "$repo_root/touranki.Dockerfile" --tag cateam/touranki-server:local "$repo_root"

ssh "$SSH_HOST" "mkdir -p '$remote_root/build/touranki' '$remote_root/caddy' /root/mainpage/cateam/public /root/touranki/web"
rsync -a "$repo_root/compose.yaml" "$repo_root/touranki.Dockerfile" "$repo_root/.dockerignore" "$SSH_HOST:$remote_root/"
rsync -a "$repo_root/caddy/Caddyfile" "$SSH_HOST:$remote_root/caddy/"
rsync -a "$repo_root/build/touranki/touranki-server" "$SSH_HOST:$remote_root/build/touranki/"
rsync -a --delete "$repo_root/build/mainpage/" "$SSH_HOST:/root/mainpage/cateam/public/"
rsync -a --delete "$repo_root/build/touranki/web/" "$SSH_HOST:/root/touranki/web/"

# The ECS host cannot reach Docker Hub; transfer the real built images over SSH.
docker image save caddy:2.10.2-alpine cateam/touranki-server:local | ssh "$SSH_HOST" docker image load

ssh "$SSH_HOST" "docker compose --project-directory '$remote_root' config --quiet && docker run --rm --pull never -v '$remote_root/caddy:/etc/caddy:ro' caddy:2.10.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile"
ssh "$SSH_HOST" "systemctl disable --now nginx && docker compose --project-directory '$remote_root' up -d --no-build --pull never --wait --wait-timeout 60 && docker compose --project-directory '$remote_root' exec -T gateway caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile"

curl --noproxy '*' --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 20 https://hustca.cn/ --output /dev/null
curl --noproxy '*' --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 20 https://touranki.1037.games/api/v1/version
printf '\nDeployed hustca.cn and touranki.1037.games via %s.\n' "$SSH_HOST"
printf 'Temporary HTTPS entries: https://hustca.cn:404/ and https://touranki.1037.games:404/ (direct responses; existing 443 remains available).\n'

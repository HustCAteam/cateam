#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export SSH_HOST="${SSH_HOST:-cateam}"
remote_root=/root/cateam
caddy_image='cateam/caddy:2.11.7-go1.27.3'

bash "$repo_root/scripts/build-touranki.sh"
bash "$repo_root/scripts/build-password-game.sh"

docker build --network host --file "$repo_root/caddy.Dockerfile" --tag "$caddy_image" "$repo_root"
docker build --file "$repo_root/touranki.Dockerfile" --tag cateam/touranki-server:local "$repo_root"

ssh "$SSH_HOST" "test -s /srv/hustca/current/index.html && mkdir -p '$remote_root/build/touranki' '$remote_root/caddy' /root/touranki/web"
rsync -a "$repo_root/compose.yaml" "$repo_root/caddy.Dockerfile" "$repo_root/touranki.Dockerfile" "$repo_root/.dockerignore" "$SSH_HOST:$remote_root/"
rsync -a "$repo_root/caddy/Caddyfile" "$SSH_HOST:$remote_root/caddy/"
rsync -a "$repo_root/build/touranki/touranki-server" "$SSH_HOST:$remote_root/build/touranki/"
rsync -a --delete "$repo_root/build/touranki/web/" "$SSH_HOST:/root/touranki/web/"

# The ECS host cannot reach Docker Hub; transfer the real built images over SSH.
docker image save "$caddy_image" cateam/touranki-server:local cateam/password-game:local | ssh "$SSH_HOST" docker image load

ssh "$SSH_HOST" "docker compose --project-directory '$remote_root' config --quiet && docker run --rm --pull never -v '$remote_root/caddy:/etc/caddy:ro' '$caddy_image' caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile"
ssh "$SSH_HOST" "systemctl disable --now nginx && docker compose --project-directory '$remote_root' up -d --no-build --pull never --wait --wait-timeout 60 && docker compose --project-directory '$remote_root' exec -T gateway caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile"

curl --noproxy '*' --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 20 https://hustca.cn/ --output /dev/null
curl --noproxy '*' --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 20 https://touranki.1037.games/api/v1/version
curl --noproxy '*' --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 20 https://pg.hustca.cn:404/ --output /dev/null
curl --noproxy '*' --fail --silent --show-error --max-time 20 https://pg.hustca.cn:404/healthz --output /dev/null
printf '\nUpdated gateway and game services; homepage content is published by GitHub Actions.\n'
printf 'Temporary HTTPS entries: https://hustca.cn:404/, https://touranki.1037.games:404/ and https://pg.hustca.cn:404/ (direct responses; existing 443 remains available).\n'

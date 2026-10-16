#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export SSH_HOST="${SSH_HOST:-cateam}"
remote_root=/root/cateam

bash "$repo_root/scripts/build-password-game.sh"
ssh "$SSH_HOST" "mkdir -p '$remote_root/caddy'"
docker image save cateam/password-game:local | ssh "$SSH_HOST" docker image load
rsync -a "$repo_root/compose.yaml" "$SSH_HOST:$remote_root/"
rsync -a "$repo_root/caddy/Caddyfile" "$SSH_HOST:$remote_root/caddy/"

# Only recreate password-game; its SQLite volume survives. Never restart Touranki.
ssh "$SSH_HOST" "docker compose --project-directory '$remote_root' config --quiet && docker compose --project-directory '$remote_root' up -d --no-deps --no-build --pull never --wait --wait-timeout 60 password-game && docker compose --project-directory '$remote_root' exec -T gateway caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && docker compose --project-directory '$remote_root' exec -T gateway caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile"
curl --noproxy '*' --fail --silent --show-error --retry 5 --retry-delay 3 --retry-all-errors --max-time 20 https://pg.hustca.cn:404/ --output /dev/null
curl --noproxy '*' --fail --silent --show-error --max-time 20 https://pg.hustca.cn:404/healthz --output /dev/null
printf 'Deployed https://pg.hustca.cn:404/ via %s without restarting Touranki.\n' "$SSH_HOST"

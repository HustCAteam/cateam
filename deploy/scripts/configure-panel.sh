#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ssh_host="${SSH_HOST:-cateam}"
remote_root=/root/cateam/panel
password_file="${PORTAINER_PASSWORD_FILE:-$HOME/.ssh/cateam_portainer_password}"
image_ref='portainer/portainer-ce:2.45.2@sha256:03f94a406496dc84d37b552795fc424ccad8d0d7200353b6a82915f6e8f73ab0'

# Keep the bootstrap credential outside the repository and out of command output.
if [[ ! -s "$password_file" ]]; then
  mkdir -p -- "$(dirname -- "$password_file")"
  (umask 077; printf '%s' "$(openssl rand -hex 24)" > "$password_file")
fi
chmod 600 -- "$password_file"

if ! docker image inspect "$image_ref" >/dev/null 2>&1; then
  docker pull "$image_ref"
fi
docker tag "$image_ref" portainer/portainer-ce:2.45.2
docker image save portainer/portainer-ce:2.45.2 | ssh "$ssh_host" docker image load

ssh "$ssh_host" "install -d -m 700 '$remote_root/secrets'"
rsync -a "$repo_root/panel/compose.yaml" "$ssh_host:$remote_root/compose.yaml"
rsync -a --chmod=F600 "$password_file" "$ssh_host:$remote_root/secrets/portainer-admin-password"
ssh "$ssh_host" "docker compose --project-directory '$remote_root' config --quiet && docker compose --project-directory '$remote_root' up -d --pull never"

printf 'Panel installed as a separate Compose project; existing applications are unchanged.\n'
printf 'Initial username: admin\nInitial password file: %s\n' "$password_file"
printf 'The bootstrap file does not reset an existing administrator password.\n'
printf 'Public access: https://121.40.128.93:9443\n'
printf 'Self-signed certificate: verify the recorded SHA-256 fingerprint before logging in.\n'
printf 'The ECS security group must also allow inbound TCP 9443.\n'

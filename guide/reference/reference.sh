#!/usr/bin/env bash
# The guide's reference instance: a Docker Compose project `refiroo-guide-ref` with the engine image
# and the guide's reference set (about 3,500 records) loaded through the public API.
#
#   guide/reference/reference.sh up       build and start, create the administrator, load the set
#   guide/reference/reference.sh update   rebuild the engine and the web (frontend) image from the current
#                                          code and restart them, keeping the data and settings (no
#                                          administrator, no load)
#   guide/reference/reference.sh load     load the set again (safe to repeat)
#   guide/reference/reference.sh stop     stop, keeping the data
#   guide/reference/reference.sh start    start again
#   guide/reference/reference.sh down     remove the instance and its data (the .env stays)
#   guide/reference/reference.sh status
#
# Open http://localhost:8480 and sign in as `guide`; the password is GUIDE_ADMIN_PASSWORD in
# guide/reference/.env (generated on the first `up`, git-ignored). Ports 8480 and 8443 only.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
env_file=guide/reference/.env
compose=(docker compose -p refiroo-guide-ref -f compose.yml -f guide/reference/compose.override.yml --env-file "$env_file")

make_env() {
  [ -f "$env_file" ] && return
  echo "Making $env_file with generated secrets"
  mkdir -p guide/reference/certs
  while IFS= read -r line; do
    case "$line" in
      POSTGRES_PASSWORD=@generated) echo "POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=\n')" ;;
      SECRETS_ENCRYPTION_KEY=@generated) echo "SECRETS_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')" ;;
      RDM_CURSOR_SIGNING_KEY=@generated) echo "RDM_CURSOR_SIGNING_KEY=$(openssl rand -base64 32)" ;;
      GUIDE_ADMIN_PASSWORD=@generated) echo "GUIDE_ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=\n')" ;;
      *) echo "$line" ;;
    esac
  done <guide/reference/.env.example >"$env_file"
  chmod 600 "$env_file"
}

value() { grep "^$1=" "$env_file" | cut -d= -f2-; }

load() {
  python3 guide/samples/load.py --set reference --base "http://localhost:$(value WEB_HTTP_PORT)" \
    --env "$env_file" --client "Stops reader (guide)"
}

case "${1:-}" in
  up)
    make_env
    "${compose[@]}" up -d --build --wait
    value GUIDE_ADMIN_PASSWORD | "${compose[@]}" run --rm -T engine python -m app.cli.create_admin \
      --email "$(value GUIDE_ADMIN_EMAIL)" --name "Guide Admin" --password-stdin || true
    load
    ;;
  update) "${compose[@]}" up -d --build --wait engine web ;;
  load) load ;;
  stop) "${compose[@]}" stop ;;
  start) "${compose[@]}" up -d --wait ;;
  down) "${compose[@]}" down -v ;;
  status) "${compose[@]}" ps ;;
  *) sed -n '2,16p' "$0"; exit 2 ;;
esac

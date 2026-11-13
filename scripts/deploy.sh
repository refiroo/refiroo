#!/usr/bin/env bash
# The first deployment of refiroo with Docker Compose (0.17), on a server or on this computer: write
# the settings file with generated secrets, build, create the database, start everything, wait until
# the engine answers and create the first administrator. Run it from a checkout of the version to
# deploy (docs/OPERATIONS.md, Deploying). Later versions: scripts/upgrade.sh.
#
#   scripts/deploy.sh                  ask for what is missing, then deploy
#   scripts/deploy.sh --local          a laptop: http://localhost:8080, no certificate
#   scripts/deploy.sh --dry-run        print every command it would run, run nothing
#   scripts/deploy.sh --yes --url https://refiroo.example.org --https acme \
#       --admin-email me@example.org --admin-name "Me" --password-stdin < password-file
#
# Steps: 1 pre-flight (docker, Compose 2.24+, the ports free, disk, no installation here yet);
# 2 the env file (from .env.example, secrets generated, mode 600); 3 docker compose pull and build;
# 4 start the database and run python -m app.cli.database_upgrade; 5 docker compose up -d and wait
# for /health; 6 create the first administrator; then a summary with the next steps.
#
# Options:
#   -h, --help              this text
#   --local                 a laptop preset: --https local, address http://localhost:8080
#   --url URL               the address people open, no path, no trailing slash (asked when missing).
#                           It cannot change its host later without signing everyone out
#   --https MODE            acme   automatic certificates from a public name (compose.acme.yml, Caddy;
#                                  needs DNS pointing here and port 443 open; ports 80 and 443)
#                           files  your certificate in ./certs (fullchain.pem and privkey.pem)
#                           proxy  plain HTTP behind a load balancer that ends HTTPS
#                           local  plain HTTP on this computer (the --local preset)
#   --trusted-proxies LIST  with proxy: the balancer's addresses or ranges, comma-separated
#   --http-port N           the host port for HTTP (default 80; 8080 with local)
#   --https-port N          the host port for HTTPS (default 443; 8443 with local)
#   --admin-email ADDRESS   the first administrator's e-mail address, their sign-in name
#   --admin-name NAME       the first administrator's name (default "Installation administrator")
#   --password-stdin        read the administrator's password from the first line of standard
#                           input (implies --yes); otherwise it is asked twice, without echo
#   --env-file FILE         the env file to write (default .env, or RDM_ENV_FILE); an existing one
#                           is never overwritten without --force
#   -p, --project NAME      the Compose project name, when you override refiroo
#   --yes                   no prompts (--url, --https and --admin-email are then required)
#   --dry-run               print the commands, run nothing (the env file is not written)
#   --force                 write over an existing env file (the old one is kept beside it as
#                           <file>.old-<time>) and go on although free disk space is low
#
# Mail and a sign-in provider are not part of the first deployment: they are set in the application
# afterwards (Settings > This instance > Mail; Settings > Security > Sign-in). An installation that
# already has its database volume is refused: use scripts/upgrade.sh. Never runs `docker compose
# down -v`. Needs bash 3.2 or newer.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOCAL=0
URL=""
HTTPS_MODE=""
TRUSTED_PROXIES=""
HTTP_PORT=""
HTTPS_PORT=""
ADMIN_EMAIL=""
ADMIN_NAME=""
PASSWORD_STDIN=0
PASSWORD=""
YES=0
DRY=0
FORCE=0
FILES=()
PROJECT_OPT=""
ENV_FILE_OPT=""

usage() { sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'; }
need() { [ "$2" -ge 2 ] || { echo "$1 needs a value" >&2; exit 2; }; }

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --local) LOCAL=1 ;;
    --url) need "$1" $#; URL="$2"; shift ;;
    --https) need "$1" $#; HTTPS_MODE="$2"; shift ;;
    --trusted-proxies) need "$1" $#; TRUSTED_PROXIES="$2"; shift ;;
    --http-port) need "$1" $#; HTTP_PORT="$2"; shift ;;
    --https-port) need "$1" $#; HTTPS_PORT="$2"; shift ;;
    --admin-email) need "$1" $#; ADMIN_EMAIL="$2"; shift ;;
    --admin-name) need "$1" $#; ADMIN_NAME="$2"; shift ;;
    --password-stdin) PASSWORD_STDIN=1; YES=1 ;;
    --env-file) need "$1" $#; ENV_FILE_OPT="$2"; shift ;;
    -p|--project) need "$1" $#; PROJECT_OPT="$2"; shift ;;
    --yes|-y) YES=1 ;;
    --dry-run) DRY=1 ;;
    --force) FORCE=1 ;;
    *) echo "Unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

# shellcheck source=scripts/lib/ops.sh
. "$ROOT/scripts/lib/ops.sh"
umask 077
STAMP="$(date +%Y%m%d-%H%M%S)"
PROJECT="${PROJECT_OPT:-refiroo}"
ENV_WRITTEN=0
FINISHED=0

# --- small helpers -------------------------------------------------------------------------------
# ask_value VAR "question" [default]: asks on the terminal; the default is taken on an empty answer.
ask_value() {
  local var="$1" question="$2" default="${3:-}" reply
  if [ -n "$default" ]; then printf '  %s [%s]: ' "$question" "$default"; else printf '  %s: ' "$question"; fi
  read -r reply || reply=""
  [ -n "$reply" ] || reply="$default"
  printf -v "$var" '%s' "$reply"
}

port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1; }

# rand_b64 BYTES: random bytes in base64, one line.
rand_b64() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -base64 "$1" | tr -d '\n'
  else head -c "$1" /dev/urandom | base64 | tr -d '\n'; fi
}

# set_env FILE KEY VALUE: replace KEY= (or its commented #KEY=) line, or append it. The value never
# appears on a command line or in the output.
set_env() {
  local file="$1" tmp
  tmp="$(mktemp "$file.XXXXXX")"
  K="$2" V="$3" awk '
    BEGIN { k = ENVIRON["K"]; v = ENVIRON["V"] }
    !done && (index($0, k "=") == 1 || index($0, "#" k "=") == 1) { print k "=" v; done = 1; next }
    { print }
    END { if (!done) print k "=" v }' "$file" > "$tmp"
  mv "$tmp" "$file"
}

valid_port() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "$1" -ge 1 ] && [ "$1" -le 65535 ]; }

# --- the password up front, so nothing else reads standard input after it -----------------------------
if [ "$PASSWORD_STDIN" = 1 ]; then
  IFS= read -r PASSWORD || true
  PASSWORD="${PASSWORD%$'\r'}"
  [ -n "$PASSWORD" ] || { echo "--password-stdin: the first line of standard input is empty" >&2; exit 2; }
fi

# --- what is missing: ask, or (with --yes) refuse -----------------------------------------------------
if [ "$LOCAL" = 1 ]; then
  [ -z "$HTTPS_MODE" ] || [ "$HTTPS_MODE" = local ] || { echo "--local cannot be combined with --https $HTTPS_MODE" >&2; exit 2; }
  HTTPS_MODE=local
fi
INTERACTIVE=0
if [ "$YES" = 0 ]; then
  [ -t 0 ] || { echo "No terminal to ask on: run it from a terminal, or give every value and --yes" >&2; exit 2; }
  INTERACTIVE=1
fi
if [ "$INTERACTIVE" = 1 ]; then
  printf '%srefiroo first deployment%s: a few questions (Enter takes the value in brackets)\n\n' "$C_STEP" "$C_OFF"
  if [ -z "$HTTPS_MODE" ]; then
    echo "  How is the installation reached?"
    echo "    1  a public name, certificates that renew themselves (acme: Caddy, needs DNS and port 443)"
    echo "    2  my own certificate files in ./certs (files)"
    echo "    3  behind a load balancer that ends HTTPS (proxy)"
    echo "    4  only on this computer, plain http://localhost (local)"
    choice=""; ask_value choice "Choose 1-4" "1"
    case "$choice" in 1) HTTPS_MODE=acme ;; 2) HTTPS_MODE=files ;; 3) HTTPS_MODE=proxy ;; 4) HTTPS_MODE=local ;;
      *) echo "Choose 1, 2, 3 or 4" >&2; exit 2 ;; esac
  fi
  if [ -z "$URL" ]; then
    if [ "$HTTPS_MODE" = local ]; then URL="http://localhost:${HTTP_PORT:-8080}"
    else ask_value URL "The address people open (for example https://refiroo.example.org)"; fi
  fi
  if [ "$HTTPS_MODE" = proxy ] && [ -z "$TRUSTED_PROXIES" ]; then
    ask_value TRUSTED_PROXIES "The load balancer's addresses or ranges, comma-separated (empty: trust nobody)" ""
  fi
  [ -n "$ADMIN_EMAIL" ] || ask_value ADMIN_EMAIL "The first administrator's e-mail address"
  [ -n "$ADMIN_NAME" ] || ask_value ADMIN_NAME "Their name" "Installation administrator"
  echo
fi
[ -n "$ADMIN_NAME" ] || ADMIN_NAME="Installation administrator"
missing=""
[ -n "$URL" ] || [ "$HTTPS_MODE" = local ] || missing="$missing --url"
[ -n "$HTTPS_MODE" ] || missing="$missing --https"
[ -n "$ADMIN_EMAIL" ] || missing="$missing --admin-email"
[ -z "$missing" ] || { echo "Missing:$missing (or run without --yes to be asked)" >&2; exit 2; }

if [ -z "$URL" ] && [ "$HTTPS_MODE" = local ]; then URL="http://localhost:${HTTP_PORT:-8080}"; fi
URL="${URL%/}"
case "$HTTPS_MODE" in acme|files|proxy|local) ;; *) echo "--https is acme, files, proxy or local, not '$HTTPS_MODE'" >&2; exit 2 ;; esac
case "$URL" in
  http://*|https://*) ;;
  *) echo "The address must start with https:// (or http:// with local): $URL" >&2; exit 2 ;;
esac
case "${URL#*://}" in */*|*\ *|'') echo "The address has no path and no spaces: $URL" >&2; exit 2 ;; esac
if [ "$HTTPS_MODE" != local ]; then
  case "$URL" in https://*) ;; *) echo "With --https $HTTPS_MODE the address must be https://..., not $URL" >&2; exit 2 ;; esac
fi
case "$ADMIN_EMAIL" in ?*@?*.?*) ;; *) echo "That is not an e-mail address: $ADMIN_EMAIL" >&2; exit 2 ;; esac
case "$ADMIN_EMAIL" in *\ *) echo "That is not an e-mail address: $ADMIN_EMAIL" >&2; exit 2 ;; esac

# Ports published on the host, and the Compose files for the mode.
case "$HTTPS_MODE" in
  local) DEFAULT_HTTP=8080; DEFAULT_HTTPS=8443 ;;
  *) DEFAULT_HTTP=80; DEFAULT_HTTPS=443 ;;
esac
if [ "$HTTPS_MODE" = acme ]; then
  [ -z "$HTTP_PORT$HTTPS_PORT" ] || { echo "With --https acme, Caddy publishes ports 80 and 443; --http-port and --https-port do not apply" >&2; exit 2; }
  FILES=(compose.yml compose.acme.yml)
fi
HTTP_PORT="${HTTP_PORT:-$DEFAULT_HTTP}"; HTTPS_PORT="${HTTPS_PORT:-$DEFAULT_HTTPS}"
if ! valid_port "$HTTP_PORT" || ! valid_port "$HTTPS_PORT"; then echo "A port is a number from 1 to 65535" >&2; exit 2; fi
if [ "$HTTPS_MODE" = local ]; then
  case "$URL" in http://localhost|http://localhost:*|http://127.0.0.1*) ;; *) echo "--local serves http://localhost only; for a name use --https acme, files or proxy" >&2; exit 2 ;; esac
fi

ops_compose_init
if [ "$INTERACTIVE" = 0 ] && [ "$PASSWORD_STDIN" = 0 ] && [ ! -t 0 ] && [ "$DRY" = 0 ]; then
  echo "The administrator's password needs a terminal, or --password-stdin" >&2; exit 2
fi

case "$HTTPS_MODE" in
  acme) MODE_TEXT="automatic certificates (Caddy, compose.acme.yml)" ;;
  files) MODE_TEXT="your certificate files in ./certs" ;;
  proxy) MODE_TEXT="plain HTTP behind a load balancer (WEB_TLS=proxy)" ;;
  local) MODE_TEXT="plain HTTP on this computer" ;;
esac

on_exit() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$FINISHED" = 0 ] && [ "$DRY" = 0 ] && [ -n "${STEP_NAME:-}" ]; then
    printf '\n%sStopped at: %s.%s\n' "$C_ERR" "$STEP_NAME" "$C_OFF" >&2
    [ "$ENV_WRITTEN" = 1 ] && printf 'The env file %s was written and is kept (it holds the generated secrets).\n' "$ENV_FILE" >&2
    if [ "$ENV_WRITTEN" = 1 ]; then
      printf 'After fixing the cause, continue by hand: %s up -d --build, then the administrator:\n  %s run --rm engine python -m app.cli.create_admin --email %s --name %s\n' \
        "$COMPOSE_TEXT" "$COMPOSE_TEXT" "$(quote "$ADMIN_EMAIL")" "$(quote "$ADMIN_NAME")" >&2
    fi
  fi
  return 0
}
trap on_exit EXIT

# --- the plan and one confirmation ------------------------------------------------------------------------
printf '%srefiroo first deployment%s  (%s%s)\n' "$C_STEP" "$C_OFF" "$ROOT" "$([ "$DRY" = 1 ] && echo ', dry run')"
cat <<EOF

Address people open:   $URL
HTTPS:                 $MODE_TEXT
Ports on this host:    HTTP $HTTP_PORT, HTTPS $HTTPS_PORT$([ "$HTTPS_MODE" = acme ] && echo ' (Caddy)')
Env file to write:     $ENV_FILE (mode 600; secrets generated, never printed)
First administrator:   $ADMIN_EMAIL ($ADMIN_NAME)
Compose command:       $COMPOSE_TEXT

It will: check the host, write the env file, pull and build the images, start the database and
create its schema, start everything, wait for the engine and create the administrator.
EOF
echo
confirm "Start the deployment?" || { echo "Cancelled."; exit 1; }

# --- 1. pre-flight --------------------------------------------------------------------------------------------
step "1/6 Pre-flight"
ops_require_docker
if [ "$DRY" = 0 ]; then
  docker info >/dev/null 2>&1 || die "the Docker daemon does not answer: start it, and use an account allowed to run docker"
  ver="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
  case "$ver" in ''|*[!0-9.]*) warn "could not read the Compose version ($ver); 2.24 or newer is needed" ;; *)
    awk -v v="$ver" 'BEGIN { split(v, a, "."); exit !((a[1] + 0 > 2) || (a[1] + 0 == 2 && a[2] + 0 >= 24)) }' \
      || die "docker compose $ver is too old: 2.24 or newer is needed (compose.acme.yml uses !reset)" ;;
  esac
  info "docker and docker compose $ver"
else
  show "docker info; docker compose version --short    # Compose 2.24 or newer"
fi
[ -f .env.example ] || die ".env.example not found in $ROOT (it is the template of the env file)"
[ -f compose.acme.yml ] || [ "$HTTPS_MODE" != acme ] || die "compose.acme.yml not found in $ROOT"
if [ -e "$ENV_FILE" ] && [ "$FORCE" = 0 ]; then
  die "the env file $ENV_FILE already exists: this looks like an installation (use scripts/upgrade.sh), or name another file with --env-file, or overwrite it with --force"
fi
if [ "$DRY" = 0 ]; then
  if docker volume inspect "${PROJECT}_database" >/dev/null 2>&1; then
    die "the volume ${PROJECT}_database already exists: an installation was started here. A first deployment would give its database a new password and fail. Upgrade it with scripts/upgrade.sh; for a second installation use another folder or -p NAME"
  fi
  if [ -n "$(compose ps -q 2>/dev/null | head -n 1 || true)" ]; then
    die "containers of the Compose project $PROJECT already exist: use scripts/upgrade.sh"
  fi
else
  show "docker volume inspect ${PROJECT}_database    # none must exist: an installation here is upgraded, not deployed"
fi
if [ "$HTTPS_MODE" = files ]; then
  certs="${WEB_CERTS_DIR:-./certs}"
  if [ -f "$certs/fullchain.pem" ] && [ -f "$certs/privkey.pem" ]; then info "certificate files found in $certs"
  elif [ "$DRY" = 1 ]; then warn "$certs/fullchain.pem and privkey.pem are missing (web will refuse to start without them)"
  else die "put your certificate and key in $certs as fullchain.pem and privkey.pem first (or choose --https acme, proxy or --local)"
  fi
fi
ports="$HTTP_PORT $HTTPS_PORT"
for p in $ports; do
  if port_in_use "$p"; then die "port $p is already in use on this host: stop what uses it, or choose another with --http-port / --https-port"; fi
done
info "ports $HTTP_PORT and $HTTPS_PORT are free"
free_kb="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
free=$((free_kb * 1024))
info "free disk space here: $(human "$free")"
if [ "$free" -lt $((5 * 1024 * 1024 * 1024)) ]; then
  msg="less than 5 GB is free here; image builds and the database need room (a rough guard: the minimum is not measured)"
  if [ "$FORCE" = 1 ]; then warn "$msg"; else die "$msg (--force goes on)"; fi
fi
if [ "$HTTPS_MODE" = acme ]; then
  info "automatic certificates need ${URL#https://} to point to this host, and port 443 open from the internet"
fi
step_done

# --- 2. the env file --------------------------------------------------------------------------------------------------
step "2/6 The env file  ->  $ENV_FILE"
if [ "$DRY" = 1 ]; then
  show "cp .env.example $(quote "$ENV_FILE") && chmod 600 $(quote "$ENV_FILE")"
  show "set PUBLIC_URL=$URL, POSTGRES_PASSWORD, SECRETS_ENCRYPTION_KEY, RDM_CURSOR_SIGNING_KEY (generated; values not shown)"
  case "$HTTPS_MODE" in proxy|local) show "set WEB_TLS=proxy" ;; esac
  if [ "$HTTPS_MODE" = proxy ] && [ -n "$TRUSTED_PROXIES" ]; then show "set WEB_TRUSTED_PROXIES=$TRUSTED_PROXIES"; fi
  if [ "$HTTPS_MODE" != acme ]; then show "set WEB_HTTP_PORT=$HTTP_PORT and WEB_HTTPS_PORT=$HTTPS_PORT where they differ from 80 and 443"; fi
  info "(dry run: the file is not written)"
else
  if [ -e "$ENV_FILE" ]; then
    mv "$ENV_FILE" "$ENV_FILE.old-$STAMP"
    warn "the existing $ENV_FILE is kept as $ENV_FILE.old-$STAMP"
  fi
  cp .env.example "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  ENV_WRITTEN=1
  set_env "$ENV_FILE" PUBLIC_URL "$URL"
  set_env "$ENV_FILE" POSTGRES_PASSWORD "$(rand_b64 24 | tr -d '/+=')"
  set_env "$ENV_FILE" SECRETS_ENCRYPTION_KEY "$(rand_b64 32 | tr '+/' '-_')"
  set_env "$ENV_FILE" RDM_CURSOR_SIGNING_KEY "$(rand_b64 32)"
  case "$HTTPS_MODE" in proxy|local) set_env "$ENV_FILE" WEB_TLS proxy ;; esac
  if [ "$HTTPS_MODE" = proxy ] && [ -n "$TRUSTED_PROXIES" ]; then set_env "$ENV_FILE" WEB_TRUSTED_PROXIES "$TRUSTED_PROXIES"; fi
  if [ "$HTTPS_MODE" != acme ]; then
    [ "$HTTP_PORT" = 80 ] || set_env "$ENV_FILE" WEB_HTTP_PORT "$HTTP_PORT"
    [ "$HTTPS_PORT" = 443 ] || set_env "$ENV_FILE" WEB_HTTPS_PORT "$HTTPS_PORT"
  fi
  for key in PUBLIC_URL POSTGRES_PASSWORD SECRETS_ENCRYPTION_KEY RDM_CURSOR_SIGNING_KEY; do
    grep -q "^$key=." "$ENV_FILE" || die "$key is empty in $ENV_FILE"
  done
  info "written with a new database password, sealing key and cursor key (mode 600)"
  show "$COMPOSE_TEXT config --quiet"
  compose config --quiet || die "docker compose rejects the settings (see above)"
fi
step_done

# --- 3. pull and build -------------------------------------------------------------------------------------------------
step "3/6 Pull and build"
run "${COMPOSE[@]}" pull --ignore-buildable
run "${COMPOSE[@]}" build
step_done

# --- 4. the database ---------------------------------------------------------------------------------------------------
step "4/6 Start the database and create its schema"
run "${COMPOSE[@]}" up -d --wait database
run "${COMPOSE[@]}" run --rm engine python -m app.cli.database_upgrade
step_done

# --- 5. start and wait --------------------------------------------------------------------------------------------------------
step "5/6 Start everything and wait for the engine"
run "${COMPOSE[@]}" up -d
if [ "$DRY" = 1 ]; then
  show "wait up to ${WAIT_SECONDS} s, every ${POLL_SECONDS} s: $COMPOSE_TEXT exec -T engine python -c 'urlopen(\"http://127.0.0.1:8000/health\")'"
else
  if wait_for_engine; then info "the engine answered /health after about ${WAITED} s"
  else
    compose ps || true
    die "the engine did not answer /health within ${WAIT_SECONDS} s: look at '$COMPOSE_TEXT logs --tail=100 engine' ($ENV_FILE is kept)"
  fi
fi
run "${COMPOSE[@]}" ps
step_done

# --- 6. the first administrator ---------------------------------------------------------------------------------------------------
step "6/6 The first administrator"
if [ "$PASSWORD_STDIN" = 1 ]; then
  show "printf '<password>\\n' | $COMPOSE_TEXT run --rm -T engine python -m app.cli.create_admin --email $(quote "$ADMIN_EMAIL") --name $(quote "$ADMIN_NAME") --password-stdin"
  if [ "$DRY" = 0 ]; then
    printf '%s\n' "$PASSWORD" | compose run --rm -T engine python -m app.cli.create_admin \
      --email "$ADMIN_EMAIL" --name "$ADMIN_NAME" --password-stdin \
      || die "the administrator was not created (see above); the installation is running. Retry: printf '%s\\n' \"\$PASSWORD\" | $COMPOSE_TEXT run --rm -T engine python -m app.cli.create_admin --email $(quote "$ADMIN_EMAIL") --name $(quote "$ADMIN_NAME") --password-stdin"
  fi
else
  info "you are asked for the password twice (nothing is shown as you type; at least 15 characters)"
  attempt=1
  while :; do
    show "$COMPOSE_TEXT run --rm engine python -m app.cli.create_admin --email $(quote "$ADMIN_EMAIL") --name $(quote "$ADMIN_NAME")"
    [ "$DRY" = 1 ] && break
    if compose run --rm engine python -m app.cli.create_admin --email "$ADMIN_EMAIL" --name "$ADMIN_NAME"; then break; fi
    if [ "$attempt" -ge 3 ]; then
      die "the administrator was not created; the installation is running. Retry: $COMPOSE_TEXT run --rm engine python -m app.cli.create_admin --email $(quote "$ADMIN_EMAIL") --name $(quote "$ADMIN_NAME")"
    fi
    attempt=$((attempt + 1))
    warn "nothing was created: try again ($attempt of 3)"
  done
fi
step_done

# --- summary ------------------------------------------------------------------------------------------------------------------------
FINISHED=1
VERSION="$(engine_version)"
printf '\n%s==> Done%s\n' "$C_STEP" "$C_OFF"
info "refiroo $VERSION is running."
info "Open:            $URL"
info "Sign in as:      $ADMIN_EMAIL (the password you just set)"
case "$ENV_FILE" in /*) ENV_PATH="$ENV_FILE" ;; *) ENV_PATH="$ROOT/$ENV_FILE" ;; esac
info "Settings file:   $ENV_PATH  (mode 600; it holds the keys that open what the database stores)"
info "                 Copy it off this server into protected storage now, apart from the database backups."
if [ "$HTTPS_MODE" = acme ]; then
  info "Certificates:    wait for \"certificate obtained successfully\" in: $COMPOSE_TEXT logs -f caddy"
  info "                 Every later docker compose command needs both files: COMPOSE_FILE=compose.yml:compose.acme.yml"
fi
echo
info "Next steps:"
info "  1. Take the first backup (guide: Deploy to production with Docker, step 7; docs/OPERATIONS.md,"
info "     Backup and restore). scripts/upgrade.sh takes one before every upgrade."
info "  2. Work through the production and security checklists (guide: Production checklist,"
info "     Security checklist), then reduce the setup administrator's grants."
info "  3. Mail and a sign-in provider are set in the application: Settings > This instance > Mail and"
info "     Settings > Security > Sign-in (guide: Set up sign-in and mail)."
info "  4. Later versions: scripts/upgrade.sh$([ "$HTTPS_MODE" = acme ] && echo ' -f compose.yml -f compose.acme.yml')."
printf '\n%sDeployment finished%s%s.\n' "$C_OK" "$([ "$DRY" = 1 ] && echo ' (dry run: nothing was run)')" "$C_OFF"

#!/usr/bin/env bash
# A developer instance in two terminals (0.12 Track DP, D411): the engine and the frontend, on this
# computer or reachable from a phone or another computer on the same network over https.
#
#   scripts/dev.sh settings            write .dev/settings.env once: the database address and a new
#                                      SECRETS_ENCRYPTION_KEY (or the one already in your
#                                      environment); edit it to switch capabilities on
#   scripts/dev.sh admin <username> "<name>"
#                                      create the first administrator (asks for a password)
#   scripts/dev.sh engine              run the engine on http://localhost:8000
#   scripts/dev.sh frontend            run the frontend on http://localhost:5173
#
#   scripts/dev.sh cert                find this computer's address on the network and make a
#                                      certificate for it with mkcert (once, and again when the
#                                      address changes); says how a phone trusts it
#   scripts/dev.sh engine --network    run the engine on https://<address>:8000
#   scripts/dev.sh frontend --network  run the frontend on https://<address>:5173; open that
#                                      address on the phone, and on this computer too
#   scripts/dev.sh address             print the address the network commands use
#
# Each server runs in the foreground of its own terminal (Ctrl-C stops it); nothing starts in the
# background. A setting already in your environment wins over .dev/settings.env. The database comes
# from scripts/postgres.sh start. RDM_DEV_ADDRESS overrides the address found.
#
# Why https on the network: a browser offers the sign-in's cryptography (PKCE) and passkeys only on
# a secure page, which is https or localhost; a phone opening http://<address> gets neither.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV="$ROOT/.dev"
SETTINGS="$DEV/settings.env"
CERTS="$DEV/certs"
ENGINE_PORT=8000
FRONTEND_PORT=5173

say() { printf '%s\n' "$*"; }
fail() { printf '%s\n' "$*" >&2; exit 1; }

# This computer's address on the local network: the one its default route leaves from.
address() {
  if [[ -n "${RDM_DEV_ADDRESS:-}" ]]; then
    say "$RDM_DEV_ADDRESS"
    return
  fi
  local found=""
  if [[ "$(uname)" == "Darwin" ]]; then
    local interface
    interface="$(route -n get default 2>/dev/null | awk '/interface:/ {print $2}')"
    [[ -n "$interface" ]] && found="$(ipconfig getifaddr "$interface" 2>/dev/null || true)"
  else
    found="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
    [[ -z "$found" ]] && found="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  [[ -n "$found" ]] || fail "No network address found. Connect to a network, or set RDM_DEV_ADDRESS."
  say "$found"
}

# The settings file's values, for each one not already in the environment.
load_settings() {
  [[ -f "$SETTINGS" ]] || fail "No $SETTINGS yet: run 'scripts/dev.sh settings' first."
  local line name value
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# || "$line" != *=* ]] && continue
    name="${line%%=*}"
    value="${line#*=}"
    [[ -z "${!name:-}" ]] && export "$name=$value"
  done < "$SETTINGS"
}

settings() {
  mkdir -p "$DEV"
  if [[ -f "$SETTINGS" ]]; then
    say "$SETTINGS exists; it is left as it is."
    return
  fi
  local key="${SECRETS_ENCRYPTION_KEY:-}" source="your environment"
  if [[ -z "$key" ]]; then
    key="$("$ROOT/backend/.venv/bin/python" -m app.cli.generate_key 2>/dev/null || python3 -c \
      'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
    source="a new key"
  fi
  umask 077
  cat > "$SETTINGS" <<EOF
# The developer instance's settings, read by scripts/dev.sh (never committed: .dev/ is ignored).
# A setting in your environment wins over this file. All settings: docs/OPERATIONS.md.

# The database scripts/postgres.sh starts.
DATABASE_URL=${DATABASE_URL:-postgresql+psycopg://postgres@localhost:54320/rdm}

# Seals the signing and webhook keys stored in the database. Keep it: a database sealed with one
# key cannot be read with another.
SECRETS_ENCRYPTION_KEY=$key

# Browser origins allowed to call the engine (plain 'engine' only; --network sets its own). The
# default is the frontend and the engine's own addresses, so the API reference at /docs can call it.
#CORS_ORIGINS=http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000

# Capabilities, off by default; remove the # to switch one on.
#MODEL_ADMIN_MUTATIONS_ENABLED=true
#WORKSPACE_ADMIN_MUTATIONS_ENABLED=true
#INTEGRATION_JOBS_ENABLED=true
#CONSUMER_SUBSCRIPTIONS_ENABLED=true
EOF
  say "Wrote $SETTINGS with $source as SECRETS_ENCRYPTION_KEY."
}

# Refuse a port another server already listens on: two servers on one port (one on IPv4, one on
# IPv6) answer different addresses, and the browser meets whichever it reaches.
free() {
  command -v lsof >/dev/null || return 0
  local holders
  holders="$(lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
  [[ -z "$holders" ]] && return 0
  say "Port $1 is already in use; stop that server first (Ctrl-C in its terminal, or kill <pid>):" >&2
  local pid
  for pid in $holders; do say "  pid $pid: $(ps -o command= -p "$pid" | cut -c1-120)" >&2; done
  exit 1
}

venv() {
  [[ -x "$ROOT/backend/.venv/bin/uvicorn" ]] || fail \
    "No backend/.venv: run 'cd backend && python3.14 -m venv .venv && .venv/bin/pip install -e \".[dev]\"'."
}

cert() {
  command -v mkcert >/dev/null || fail "mkcert is needed: 'brew install mkcert' on macOS, the 'mkcert'
package on Linux, or https://github.com/FiloSottile/mkcert#installation."
  local here
  here="$(address)"
  mkdir -p "$CERTS"
  # Trust mkcert's own authority on this computer (asks for your password the first time).
  mkcert -install
  mkcert -cert-file "$CERTS/cert.pem" -key-file "$CERTS/key.pem" "$here" localhost 127.0.0.1 ::1
  say "$here" > "$CERTS/address"
  local authority
  authority="$(mkcert -CAROOT)/rootCA.pem"
  say ""
  say "Certificate for $here in $CERTS."
  say "On a phone, trust mkcert's authority once: send $authority to it (AirDrop, mail)."
  say "  iPhone: open the file, install the profile in Settings › General › VPN & Device Management,"
  say "          then switch it on in Settings › General › About › Certificate Trust Settings."
  say "  Android: Settings › Security › Encryption & credentials › Install a certificate › CA certificate."
}

# The network address and certificate for --network, checked against the address now.
network() {
  [[ -f "$CERTS/cert.pem" && -f "$CERTS/address" ]] || fail "No certificate yet: run 'scripts/dev.sh cert'."
  NETWORK_ADDRESS="$(address)"
  [[ "$(cat "$CERTS/address")" == "$NETWORK_ADDRESS" ]] || fail \
    "The certificate is for $(cat "$CERTS/address"), this computer is now at $NETWORK_ADDRESS: run 'scripts/dev.sh cert' again."
}

engine() {
  venv
  load_settings
  free "$ENGINE_PORT"
  cd "$ROOT/backend"
  if [[ "${1:-}" == "--network" ]]; then
    network
    export PUBLIC_URL="https://$NETWORK_ADDRESS:$ENGINE_PORT"
    # The frontend under every name this computer reaches it by (the network address for the phone,
    # localhost here), and the engine itself likewise: its API reference at /docs (Scalar) calls it
    # from the page's own origin, whichever name opened it.
    export CORS_ORIGINS="https://$NETWORK_ADDRESS:$FRONTEND_PORT,https://localhost:$FRONTEND_PORT,https://127.0.0.1:$FRONTEND_PORT,$PUBLIC_URL,https://localhost:$ENGINE_PORT,https://127.0.0.1:$ENGINE_PORT"
    say "Engine at $PUBLIC_URL (PUBLIC_URL), for pages at $CORS_ORIGINS (CORS_ORIGINS)."
    exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port "$ENGINE_PORT" \
      --ssl-certfile "$CERTS/cert.pem" --ssl-keyfile "$CERTS/key.pem"
  fi
  # The frontend, and the engine itself (also as 127.0.0.1): its API reference at /docs (Scalar)
  # calls it from there. A CORS_ORIGINS already in the environment is left as it is.
  export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:$FRONTEND_PORT,http://localhost:$ENGINE_PORT,http://127.0.0.1:$ENGINE_PORT}"
  say "Engine at http://localhost:$ENGINE_PORT, for pages at $CORS_ORIGINS (CORS_ORIGINS)."
  exec .venv/bin/uvicorn app.main:app --reload --port "$ENGINE_PORT"
}

frontend() {
  cd "$ROOT/frontend"
  [[ -d node_modules ]] || fail "No frontend/node_modules: run 'cd frontend && npm install'."
  free "$FRONTEND_PORT"
  if [[ "${1:-}" == "--network" ]]; then
    network
    export VITE_API_URL="https://$NETWORK_ADDRESS:$ENGINE_PORT"
    export DEV_HTTPS_CERT="$CERTS/cert.pem" DEV_HTTPS_KEY="$CERTS/key.pem"
    say "Open https://$NETWORK_ADDRESS:$FRONTEND_PORT on the phone; this computer may use it or"
    say "https://localhost:$FRONTEND_PORT. Both call $VITE_API_URL."
    exec npx vite --host --port "$FRONTEND_PORT" --strictPort
  fi
  exec npx vite --port "$FRONTEND_PORT" --strictPort
}

admin() {
  [[ $# -ge 2 ]] || fail "Usage: scripts/dev.sh admin <username> \"<name>\""
  venv
  load_settings
  cd "$ROOT/backend"
  exec .venv/bin/python -m app.cli.create_admin --username "$1" --name "$2"
}

case "${1:-}" in
  settings) settings ;;
  cert) cert ;;
  address) address ;;
  engine) shift; engine "$@" ;;
  frontend) shift; frontend "$@" ;;
  admin) shift; admin "$@" ;;
  *) sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac

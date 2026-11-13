#!/usr/bin/env bash
# Shared by scripts/upgrade.sh and scripts/deploy.sh (0.17): coloured step lines with their
# duration, the --yes / --dry-run / --force handling, the confirmation, the Compose command and what
# a running installation reports. Sourced, never run; the caller sets DRY, YES and FORCE (0 or 1),
# FILES, PROJECT_OPT and ENV_FILE_OPT, and has `set -euo pipefail` on.
# shellcheck disable=SC2034
DRY="${DRY:-0}"; YES="${YES:-0}"; FORCE="${FORCE:-0}"
PROJECT_OPT="${PROJECT_OPT:-}"; ENV_FILE_OPT="${ENV_FILE_OPT:-}"
DB_USER="${DB_USER:-rdm}"; DB_NAME="${DB_NAME:-rdm}"
WAIT_SECONDS="${WAIT_SECONDS:-120}"; POLL_SECONDS="${POLL_SECONDS:-2}"

# --- output ---------------------------------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_STEP=$'\033[1;36m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[1;31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
  C_STEP=""; C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_OFF=""
fi
STEP_START=0
STEP_NAME=""
step() { STEP_NAME="$1"; STEP_START=$SECONDS; printf '\n%s==> %s%s\n' "$C_STEP" "$1" "$C_OFF"; }
step_done() { printf '%s    done: %s (%ss)%s\n' "$C_OK" "$STEP_NAME" "$((SECONDS - STEP_START))" "$C_OFF"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '%s    warning: %s%s\n' "$C_WARN" "$*" "$C_OFF" >&2; }
die() { printf '%s    error: %s%s\n' "$C_ERR" "$*" "$C_OFF" >&2; exit 1; }
show() { printf '%s    $ %s%s\n' "$C_DIM" "$*" "$C_OFF"; }

quote() { local a out=""; for a in "$@"; do out="$out $(printf '%q' "$a")"; done; printf '%s' "${out# }"; }

# Run a command, printing it first; with --dry-run only print it.
run() { show "$(quote "$@")"; [ "$DRY" = 1 ] || "$@"; }
human() { awk -v b="$1" 'BEGIN { s="B KB MB GB TB"; split(s, u, " "); i=1; while (b >= 1024 && i < 5) { b /= 1024; i++ } printf (i == 1 ? "%d %s" : "%.1f %s"), b, u[i] }'; }
filesize() { wc -c < "$1" | tr -d ' '; }

# --- compose ----------------------------------------------------------------------------------
# Call after parsing FILES (-f), PROJECT_OPT (-p) and ENV_FILE_OPT (--env-file): sets COMPOSE,
# COMPOSE_TEXT, ENV_FILE and FILES_GIVEN.
ops_compose_init() {
  COMPOSE=(docker compose)
  local f
  for f in ${FILES[@]+"${FILES[@]}"}; do COMPOSE+=(-f "$f"); done
  if [ -n "$PROJECT_OPT" ]; then COMPOSE+=(-p "$PROJECT_OPT"); fi
  # shellcheck disable=SC2034
  ENV_FILE="${ENV_FILE_OPT:-${RDM_ENV_FILE:-.env}}"
  if [ -n "$ENV_FILE_OPT" ]; then
    # compose.yml reads RDM_ENV_FILE for the engine; --env-file serves the ${...} values in compose.
    export RDM_ENV_FILE="$ENV_FILE_OPT"
    COMPOSE+=(--env-file "$ENV_FILE_OPT")
  fi
  COMPOSE_TEXT="$(quote "${COMPOSE[@]}")"
  FILES_GIVEN=0
  if [ ${#FILES[@]} -gt 0 ] || [ -n "${COMPOSE_FILE:-}" ]; then FILES_GIVEN=1; fi
}
compose() { "${COMPOSE[@]}" "$@"; }
# What a running installation reports (read-only; "unknown" when the container is not running).
# With --dry-run they print the command and answer a stand-in.
engine_version() {
  if [ "$DRY" = 1 ]; then show "$COMPOSE_TEXT exec -T engine python -c 'from app.config import ENGINE_VERSION; print(ENGINE_VERSION)'" >&2; echo unknown; return 0; fi
  compose exec -T engine python -c 'from app.config import ENGINE_VERSION; print(ENGINE_VERSION)' 2>/dev/null || echo unknown
}
database_revision() {
  if [ "$DRY" = 1 ]; then show "$COMPOSE_TEXT exec -T database psql -U $DB_USER -d $DB_NAME -Atc 'SELECT version_num FROM alembic_version'" >&2; echo unknown; return 0; fi
  compose exec -T database psql -U "$DB_USER" -d "$DB_NAME" -Atc 'SELECT version_num FROM alembic_version' 2>/dev/null || echo unknown
}
database_credentials() {
  if [ "$DRY" = 1 ]; then show "$COMPOSE_TEXT exec -T database sh -c 'echo \"\$POSTGRES_USER \$POSTGRES_DB\"'" >&2; echo "rdm rdm"; return 0; fi
  # shellcheck disable=SC2016
  compose exec -T database sh -c 'echo "$POSTGRES_USER $POSTGRES_DB"'
}
database_size() {
  if [ "$DRY" = 1 ]; then show "$COMPOSE_TEXT exec -T database psql -U $DB_USER -d $DB_NAME -Atc 'SELECT pg_database_size(current_database())'" >&2; echo 0; return 0; fi
  compose exec -T database psql -U "$DB_USER" -d "$DB_NAME" -Atc 'SELECT pg_database_size(current_database())' | tr -d '[:space:]'
}

# docker, the Compose plugin (v2) and compose.yml. In a dry run a missing docker is a warning.
ops_require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    if [ "$DRY" = 1 ]; then warn "docker not found (a real run needs it)"; return 0; fi
    die "docker is not installed or not on PATH"
  fi
  if [ "$DRY" = 0 ] && ! docker compose version >/dev/null 2>&1; then
    die "docker compose (v2) is not available: install the Compose plugin"
  fi
  [ -f compose.yml ] || die "compose.yml not found in $PWD"
}

# Ask a yes/no question; --yes answers yes, no terminal is an error.
confirm() {
  [ "$YES" = 1 ] && return 0
  [ -t 0 ] || die "no terminal to ask on: run it from a terminal, or add --yes"
  local reply
  printf '%s [y/N] ' "$1"
  read -r reply || reply=""
  case "$reply" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

# Wait (bounded, polling) until the engine answers /health inside its container; sets WAITED.
wait_for_engine() {
  WAITED=0
  while [ "$WAITED" -lt "$WAIT_SECONDS" ]; do
    if compose exec -T engine python -c "import urllib.request as r; r.urlopen('http://127.0.0.1:8000/health', timeout=2)" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$POLL_SECONDS"; WAITED=$((WAITED + POLL_SECONDS))
  done
  return 1
}

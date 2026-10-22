#!/usr/bin/env bash
# The development PostgreSQL server (0.9.0-alpha.1, PG-D8): Homebrew's postgresql@17 binaries on
# the data directory backend/.postgres/, started and stopped by hand. Never use `brew services`.
#
#   scripts/postgres.sh start    create the server on first use (ICU root collation, PG-D11) and the
#                                database "rdm", start it, and print the DATABASE_URL to use
#   scripts/postgres.sh stop     stop it
#   scripts/postgres.sh status   say whether it runs
#   scripts/postgres.sh backup   write backend/.postgres/backups/rdm-<time>.dump (pg_dump -Fc),
#                                without the engine processes' rows (0.11 O2, D203)
#   scripts/postgres.sh rehearse [<dump>]
#                                restore the newest (or the named) dump into a scratch database,
#                                check it with app.cli.restore_check, record the result in "rdm"
#                                and drop the scratch database (0.11 O2)
#
# The server listens on localhost:${RDM_POSTGRES_PORT:-54320} and on a socket in its directory, and
# trusts local connections: it is for development only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$ROOT/backend/.postgres"
DATA="$DIR/data"
LOG="$DIR/server.log"
PORT="${RDM_POSTGRES_PORT:-54320}"
DATABASE="rdm"
BIN="${RDM_POSTGRES_BIN:-}"
if [[ -z "$BIN" ]]; then
  for candidate in /opt/homebrew/opt/postgresql@17/bin /usr/local/opt/postgresql@17/bin; do
    [[ -x "$candidate/pg_ctl" ]] && BIN="$candidate" && break
  done
fi
if [[ -z "$BIN" || ! -x "$BIN/pg_ctl" ]]; then
  echo "PostgreSQL 17 binaries not found. Install them with 'brew install postgresql@17' (do not" >&2
  echo "start them with 'brew services'), or set RDM_POSTGRES_BIN to their directory." >&2
  exit 1
fi
# macOS refuses to start a postmaster whose inherited locale is unset or invalid.
export LC_ALL=C
URL="postgresql+psycopg://postgres@localhost:$PORT/$DATABASE"

running() { [[ -d "$DATA" ]] && "$BIN/pg_ctl" status -D "$DATA" >/dev/null 2>&1; }

case "${1:-}" in
  start)
    if [[ ! -f "$DATA/PG_VERSION" ]]; then
      mkdir -p "$DIR"
      "$BIN/initdb" -D "$DATA" -U postgres --auth=trust -E UTF8 --locale=C \
        --locale-provider=icu --icu-locale=und >/dev/null
      {
        echo ""
        echo "# RDM Engine development server (scripts/postgres.sh)"
        echo "listen_addresses = 'localhost'"
        echo "port = $PORT"
        echo "unix_socket_directories = '$DIR'"
      } >>"$DATA/postgresql.conf"
      echo "Created the development server in $DATA."
    fi
    if running; then
      echo "The development server is already running."
    else
      "$BIN/pg_ctl" start -D "$DATA" -l "$LOG" -w -s || {
        echo "The development server did not start; see $LOG." >&2
        exit 1
      }
    fi
    if [[ -z "$("$BIN/psql" -h "$DIR" -p "$PORT" -U postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname = '$DATABASE'")" ]]; then
      "$BIN/createdb" -h "$DIR" -p "$PORT" -U postgres "$DATABASE"
      echo "Created the database '$DATABASE'."
    fi
    echo "DATABASE_URL=$URL"
    ;;
  stop)
    if running; then
      "$BIN/pg_ctl" stop -D "$DATA" -m fast -w -s
      echo "Stopped the development server."
    else
      echo "The development server is not running."
    fi
    ;;
  status)
    if running; then echo "running: DATABASE_URL=$URL"; else echo "stopped"; fi
    ;;
  backup)
    running || { echo "Start the development server first: scripts/postgres.sh start" >&2; exit 1; }
    mkdir -p "$DIR/backups"
    target="$DIR/backups/$DATABASE-$(date +%Y%m%d-%H%M%S).dump"
    "$BIN/pg_dump" -h "$DIR" -p "$PORT" -U postgres -Fc --exclude-table-data=engine_processes \
      -f "$target" "$DATABASE"
    echo "Wrote $target"
    ;;
  rehearse)
    running || { echo "Start the development server first: scripts/postgres.sh start" >&2; exit 1; }
    dump="${2:-$(ls -t "$DIR"/backups/*.dump 2>/dev/null | head -n 1)}"
    [[ -n "$dump" && -f "$dump" ]] || {
      echo "No dump to rehearse. Write one with 'scripts/postgres.sh backup', or name one." >&2
      exit 1
    }
    scratch="rdm_restore_check"
    "$BIN/dropdb" -h "$DIR" -p "$PORT" -U postgres --if-exists "$scratch"
    "$BIN/createdb" -h "$DIR" -p "$PORT" -U postgres -T template0 --locale-provider=icu \
      --icu-locale=und --locale=C "$scratch"
    status=0
    if "$BIN/pg_restore" -h "$DIR" -p "$PORT" -U postgres --no-owner -d "$scratch" "$dump"; then
      (cd "$ROOT/backend" && DATABASE_URL="$URL" .venv/bin/python -m app.cli.restore_check \
        --restored "postgresql+psycopg://postgres@localhost:$PORT/$scratch" \
        --backup "$(basename "$dump")") || status=$?
    else
      echo "pg_restore could not restore $dump; nothing was checked or recorded." >&2
      status=1
    fi
    "$BIN/dropdb" -h "$DIR" -p "$PORT" -U postgres --if-exists "$scratch"
    exit "$status"
    ;;
  *)
    echo "usage: scripts/postgres.sh start|stop|status|backup|rehearse [<dump>]" >&2
    exit 2
    ;;
esac

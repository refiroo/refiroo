#!/usr/bin/env bash
# Upgrade a Docker Compose installation in one command (0.17): check, back up, pull and build,
# migrate the database, start, and wait until the engine answers. Run it from a checkout of the
# version you are upgrading to, on the host that runs the installation. Put that version in the
# folder first:  git fetch --tags --force && git checkout v<version>   (git tag --list 'v*' --sort=-v:refname
# | head shows the versions). It prints the checkout's version next to the running one, asks before
# rebuilding the version that already runs, and stops on an older one. It replaces the
# copy-and-paste commands of docs/OPERATIONS.md, Upgrades.
#
#   scripts/upgrade.sh                 ask once, then upgrade the installation next to compose.yml
#   scripts/upgrade.sh --dry-run       print every command it would run, run nothing
#   scripts/upgrade.sh --yes           no questions (for a script or a terminal-less session)
#
# Steps: 1 pre-flight (docker, compose.yml, the env file, the database container running, free
# space for the backup); 2 backup (database dump checked with pg_restore --list, job-files volume,
# env file); 3 docker compose pull (images from a registry) and build; 4 stop the engine and run
# python -m app.cli.database_upgrade; 5 docker compose up -d and wait for /health; 6 summary with
# the versions before and after and the commands that restore the backup.
#
# Options:
#   -h, --help            this text
#   --backups DIR         where the backup goes (default /opt/refiroo/backups); old backups stay,
#                         nothing is pruned
#   --with-assistant      also back up the assistant volume (open assistant tasks' folders and logs)
#   --skip-backup         no backup (asks for confirmation unless --yes)
#   --yes                 no prompts
#   --dry-run             print the commands, run nothing
#   --force               go on although the backup folder has less free space than twice the
#                         database's size, or the automatic-HTTPS check fails; with --yes, also
#                         rebuild and restart the version that is already running
#   -f, --file FILE       a compose file, as docker compose -f (repeat it); COMPOSE_FILE in the
#                         environment works too. With automatic HTTPS give both files:
#                         -f compose.yml -f compose.acme.yml
#   -p, --project NAME    the Compose project name, when you override refiroo
#   --env-file FILE       the env file (default .env, or RDM_ENV_FILE); passed to docker compose
#
# Never runs `docker compose down -v`. If the database upgrade fails the database stays at its
# previous revision (one transaction); the script then stops, leaves the engine stopped, prints the
# commands that restore the backup it made, and exits 1. Needs bash 3.2 or newer and docker compose v2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKUPS="/opt/refiroo/backups"
WITH_ASSISTANT=0
SKIP_BACKUP=0
YES=0
DRY=0
FORCE=0
PROJECT_OPT=""
ENV_FILE_OPT=""
FILES=()
WAIT_SECONDS=120
POLL_SECONDS=2

usage() { sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --backups) [ $# -ge 2 ] || { echo "--backups needs a folder" >&2; exit 2; }; BACKUPS="$2"; shift ;;
    --with-assistant) WITH_ASSISTANT=1 ;;
    --skip-backup) SKIP_BACKUP=1 ;;
    --yes|-y) YES=1 ;;
    --dry-run) DRY=1 ;;
    --force) FORCE=1 ;;
    -f|--file) [ $# -ge 2 ] || { echo "$1 needs a file" >&2; exit 2; }; FILES+=("$2"); shift ;;
    -p|--project) [ $# -ge 2 ] || { echo "$1 needs a name" >&2; exit 2; }; PROJECT_OPT="$2"; shift ;;
    --env-file) [ $# -ge 2 ] || { echo "--env-file needs a file" >&2; exit 2; }; ENV_FILE_OPT="$2"; shift ;;
    *) echo "Unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

# shellcheck source=scripts/lib/ops.sh
. "$ROOT/scripts/lib/ops.sh"
ops_compose_init

STAMP="$(date +%Y%m%d-%H%M%S)"
umask 077
VERSION_BEFORE="unknown"
VERSION_AFTER="unknown"
REVISION_BEFORE="unknown"
REVISION_AFTER="unknown"
DB_USER="rdm"
DB_NAME="rdm"
PROJECT="refiroo"
DUMP_FILE="$BACKUPS/rdm-$STAMP.dump"
JOBS_FILE="$BACKUPS/job-files-$STAMP.tgz"
ASSISTANT_FILE="$BACKUPS/assistant-$STAMP.tgz"
ENV_COPY="$BACKUPS/env-$STAMP"
HELPER_IMAGE=""
ENGINE_STOPPED=0
FINISHED=0

on_exit() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$FINISHED" = 0 ] && [ "$DRY" = 0 ]; then
    printf '\n%sStopped at: %s.%s\n' "$C_ERR" "${STEP_NAME:-start}" "$C_OFF" >&2
    [ "$ENGINE_STOPPED" = 1 ] && printf 'The engine is stopped. Once the cause is fixed, run this script again (or "%s up -d").\n' "$COMPOSE_TEXT" >&2
    [ "$SKIP_BACKUP" = 0 ] && [ -f "$DUMP_FILE" ] && printf 'Backup files written so far stay in %s (stamp %s).\n' "$BACKUPS" "$STAMP" >&2
  fi
  return 0
}
trap on_exit EXIT

restore_commands() {
  cat <<EOF
  # 1. put the previous application version back in this folder (git checkout of the version
  #    ${VERSION_BEFORE}), then:
  $COMPOSE_TEXT stop web engine
  $COMPOSE_TEXT exec -T database pg_restore -U $DB_USER -d $DB_NAME --clean --if-exists --no-owner < $(quote "$DUMP_FILE")
  docker run --rm --entrypoint tar -v ${PROJECT}_job-files:/data -v $(quote "$BACKUPS"):/backup $(quote "${HELPER_IMAGE:-<database image>}") xzf /backup/$(basename "$JOBS_FILE") -C /data
  cp $(quote "$ENV_COPY") $(quote "$ENV_FILE")   # only if the env file changed
  $COMPOSE_TEXT build
  $COMPOSE_TEXT up -d
EOF
}

# --- confirmation (confirm() is in lib/ops.sh) ---------------------------------------------
printf '%srefiroo upgrade%s  (%s%s)\n' "$C_STEP" "$C_OFF" "$ROOT" "$([ "$DRY" = 1 ] && echo ', dry run')"
cat <<EOF

It will:
  1. check docker, compose.yml, the env file ($ENV_FILE), the running database and the free space
EOF
if [ "$SKIP_BACKUP" = 1 ]; then
  echo "  2. make NO backup (--skip-backup)"
else
  echo "  2. back up the database, the job-files volume$([ "$WITH_ASSISTANT" = 1 ] && echo ', the assistant volume') and the env file into $BACKUPS (stamp $STAMP)"
fi
cat <<EOF
  3. pull the registry images and build the new images
  4. stop the engine and run the database upgrade
  5. start everything and wait up to ${WAIT_SECONDS} s for the engine to answer
  6. print a summary and the commands that restore the backup
Compose command: $COMPOSE_TEXT
EOF
echo
if [ "$SKIP_BACKUP" = 1 ] && [ "$YES" = 0 ]; then
  confirm "No backup means no way back if the upgrade damages the database. Go on without one?" || { echo "Cancelled."; exit 1; }
fi
confirm "Start the upgrade?" || { echo "Cancelled."; exit 1; }

# --- 1. pre-flight --------------------------------------------------------------------------------
step "1/6 Pre-flight"
if ! command -v docker >/dev/null 2>&1; then
  if [ "$DRY" = 1 ]; then warn "docker not found (a real run needs it)"; else die "docker is not installed or not on PATH"; fi
elif [ "$DRY" = 0 ] && ! docker compose version >/dev/null 2>&1; then
  die "docker compose (v2) is not available: install the Compose plugin"
fi
[ -f compose.yml ] || die "compose.yml not found in $ROOT"
[ -f "$ENV_FILE" ] || die "the env file $ENV_FILE does not exist (fill it from .env.example, or name it with --env-file)"
info "compose.yml and $ENV_FILE present"

if [ "$DRY" = 0 ]; then
  DB_CONTAINER="$(compose ps -q database 2>/dev/null | head -n 1 || true)"
  [ -n "$DB_CONTAINER" ] || die "the database container is not running ($COMPOSE_TEXT up -d database); the backup needs it. Run from the folder and with the compose files of the installation."
  [ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || echo false)" = true ] || die "the database container exists but is not running"
  PROJECT="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$DB_CONTAINER" 2>/dev/null || true)"
  [ -n "$PROJECT" ] || PROJECT="refiroo"
  HELPER_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$DB_CONTAINER" 2>/dev/null || true)"
  info "database container running (Compose project $PROJECT)"
  if [ "$FILES_GIVEN" = 0 ] && [ -f compose.acme.yml ] \
     && docker volume inspect "${PROJECT}_caddy-data" >/dev/null 2>&1; then
    msg="the volume ${PROJECT}_caddy-data exists (automatic HTTPS), but no compose files were given: without compose.acme.yml web would be recreated without Caddy. Use -f compose.yml -f compose.acme.yml (or COMPOSE_FILE=compose.yml:compose.acme.yml)."
    if [ "$FORCE" = 1 ]; then warn "$msg"; else die "$msg (--force overrides)"; fi
  fi
else
  show "$COMPOSE_TEXT ps -q database    # the database container must be running"
  [ -n "$PROJECT_OPT" ] && PROJECT="$PROJECT_OPT"
  HELPER_IMAGE="<database image>"
fi

creds="$(database_credentials)"
DB_USER="${creds%% *}"; DB_NAME="${creds##* }"
[ -n "$DB_USER" ] && [ -n "$DB_NAME" ] || die "could not read POSTGRES_USER and POSTGRES_DB from the database container"
info "database $DB_NAME, user $DB_USER"

VERSION_BEFORE="$(engine_version)"
REVISION_BEFORE="$(database_revision)"
info "running now: engine $VERSION_BEFORE, database revision $REVISION_BEFORE"
VERSION_CHECKOUT="$(sed -n 's/^ENGINE_VERSION = "\([^"]*\)".*/\1/p' backend/app/config.py 2>/dev/null | head -n 1)"
[ -n "$VERSION_CHECKOUT" ] || die "could not read ENGINE_VERSION from backend/app/config.py (run the script from a checkout of refiroo)"
info "this checkout: engine $VERSION_CHECKOUT"
case "$VERSION_BEFORE" in
  unknown) ;;
  "$VERSION_CHECKOUT")
    warn "this checkout is the version already running ($VERSION_BEFORE); to upgrade, first put the new version in this folder: git fetch --tags --force && git checkout vNEW (git tag --list 'v*' --sort=-v:refname | head shows the versions), then run this script again."
    if [ "$YES" = 1 ]; then
      [ "$FORCE" = 1 ] || die "nothing to upgrade: the checkout is the running version (--force rebuilds and restarts it anyway)"
    elif [ "$FORCE" = 0 ]; then
      confirm "Rebuild and restart the same version?" || { echo "Cancelled: nothing changed."; exit 0; }
    fi ;;
  *)
    if [ "$(printf '%s\n%s\n' "$VERSION_CHECKOUT" "$VERSION_BEFORE" | sort -V | head -n 1)" = "$VERSION_CHECKOUT" ]; then
      die "this checkout (engine $VERSION_CHECKOUT) is older than the running engine ($VERSION_BEFORE). A downgrade is not an upgrade: restore a backup instead (docs/OPERATIONS.md, Upgrades), or check out the newer version: git fetch --tags --force && git checkout vNEW"
    fi ;;
esac

if [ "$SKIP_BACKUP" = 0 ]; then
  d="$BACKUPS"
  while [ ! -d "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do d="$(dirname "$d")"; done
  size="$(database_size)"
  case "$size" in ''|*[!0-9]*) die "could not read the database size" ;; esac
  if [ "$DRY" = 1 ]; then
    show "df -Pk $(quote "$d")    # free space must be at least twice the database size"
  else
    free_kb="$(df -Pk "$d" | awk 'NR==2 {print $4}')"
    need=$((size * 2)); free=$((free_kb * 1024))
    info "database $(human "$size"); backup folder has $(human "$free") free, needs about $(human "$need")"
    if [ "$free" -lt "$need" ]; then
      msg="less than twice the database size is free in $d (free $(human "$free"), needed $(human "$need"))"
      if [ "$FORCE" = 1 ]; then warn "$msg"; else die "$msg: free space, choose another folder with --backups, or use --force"; fi
    fi
  fi
fi
step_done

# --- 2. backup ------------------------------------------------------------------------------------
if [ "$SKIP_BACKUP" = 1 ]; then
  step "2/6 Backup"
  warn "skipped (--skip-backup)"
  step_done
else
  step "2/6 Backup  ->  $BACKUPS"
  if [ "$DRY" = 0 ]; then
    mkdir -p "$BACKUPS" 2>/dev/null || die "cannot create $BACKUPS (use --backups DIR, or run with sudo)"
    [ -w "$BACKUPS" ] || die "$BACKUPS is not writable (use --backups DIR, or run with sudo)"
  else
    show "mkdir -p $(quote "$BACKUPS")"
  fi

  show "$COMPOSE_TEXT exec -T database pg_dump -U $DB_USER -d $DB_NAME -Fc --exclude-table-data=engine_processes > $(quote "$DUMP_FILE")"
  if [ "$DRY" = 0 ]; then
    if ! compose exec -T database pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc --exclude-table-data=engine_processes > "$DUMP_FILE.partial"; then
      rm -f "$DUMP_FILE.partial"; die "pg_dump failed"
    fi
    show "$COMPOSE_TEXT exec -T database pg_restore --list < $(quote "$DUMP_FILE.partial")    # the dump must be readable"
    if ! compose exec -T database pg_restore --list < "$DUMP_FILE.partial" > /dev/null; then
      rm -f "$DUMP_FILE.partial"; die "the dump cannot be read back by pg_restore --list"
    fi
    mv "$DUMP_FILE.partial" "$DUMP_FILE"
  else
    show "$COMPOSE_TEXT exec -T database pg_restore --list < $(quote "$DUMP_FILE")    # the dump must be readable"
  fi

  tar_volume() { # volume file
    local volume="$1" file="$2"
    # The helper runs as root; hand the tarball to the invoking user before the mode is set, so the
    # operator can read, move and delete their own backup.
    local name owner
    name="$(basename "$file")"; owner="$(id -u):$(id -g)"
    run docker run --rm --entrypoint sh -v "$volume:/data:ro" -v "$BACKUPS:/backup" "$HELPER_IMAGE" \
      -c "tar czf /backup/$name -C /data . && chown $owner /backup/$name && chmod 600 /backup/$name"
    show "tar tzf $(quote "$file") > /dev/null    # the tarball must be readable"
    if [ "$DRY" = 0 ]; then
      [ -r "$file" ] || die "the backup $file was written but cannot be read by $(id -un) (check the owner of $BACKUPS)"
      tar tzf "$file" > /dev/null 2>&1 || die "the backup $file cannot be read back with tar tzf"
    fi
  }
  if [ "$DRY" = 0 ]; then
    docker volume inspect "${PROJECT}_job-files" >/dev/null 2>&1 || die "the volume ${PROJECT}_job-files does not exist (another project name? use -p NAME)"
  fi
  tar_volume "${PROJECT}_job-files" "$JOBS_FILE"
  if [ "$WITH_ASSISTANT" = 1 ]; then
    [ "$DRY" = 1 ] || docker volume inspect "${PROJECT}_assistant" >/dev/null 2>&1 || die "the volume ${PROJECT}_assistant does not exist"
    tar_volume "${PROJECT}_assistant" "$ASSISTANT_FILE"
  fi
  run cp "$ENV_FILE" "$ENV_COPY"
  [ "$DRY" = 1 ] || chmod 600 "$ENV_COPY"
  show "chmod 600 $(quote "$ENV_COPY")"

  info "written:"
  for f in "$DUMP_FILE" "$JOBS_FILE" "$ENV_COPY" $([ "$WITH_ASSISTANT" = 1 ] && echo "$ASSISTANT_FILE"); do
    if [ "$DRY" = 1 ]; then info "  $f"; else bytes="$(filesize "$f")" || exit 1; info "  $f  ($(human "$bytes"))"; fi
  done
  step_done
fi

# --- 3. pull and build ------------------------------------------------------------------------------
step "3/6 Pull and build"
run "${COMPOSE[@]}" pull --ignore-buildable
run "${COMPOSE[@]}" build
step_done

# --- 4. database upgrade ------------------------------------------------------------------------------
step "4/6 Stop the engine and upgrade the database"
run "${COMPOSE[@]}" stop engine
ENGINE_STOPPED=1
if ! run "${COMPOSE[@]}" run --rm engine python -m app.cli.database_upgrade; then
  printf '\n%sThe database upgrade failed.%s\n' "$C_ERR" "$C_OFF" >&2
  cat >&2 <<EOF
The upgrade runs in one transaction, so the database was left at its previous revision
($REVISION_BEFORE). The engine is stopped and was NOT started again: the old engine must not
run against a half-understood state, and the new one cannot start until the cause is fixed.
Read the message above (cause, current and target revision), fix it and run this script again.
EOF
  if [ "$SKIP_BACKUP" = 0 ]; then
    printf '\nThe backup just made (stamp %s) restores the whole installation:\n' "$STAMP" >&2
    restore_commands >&2
  else
    printf '\nNo backup was made in this run.\n' >&2
  fi
  FINISHED=1
  exit 1
fi
step_done

# --- 5. start and wait -------------------------------------------------------------------------------------
step "5/6 Start and wait for the engine"
run "${COMPOSE[@]}" up -d
ENGINE_STOPPED=0
if [ "$DRY" = 1 ]; then
  show "wait up to ${WAIT_SECONDS} s, every ${POLL_SECONDS} s: $COMPOSE_TEXT exec -T engine python -c 'urlopen(\"http://127.0.0.1:8000/health\")'"
else
  if wait_for_engine; then ready=1; else ready=0; fi
  waited=$WAITED
  if [ "$ready" = 1 ]; then
    info "the engine answered /health after about ${waited} s"
  else
    warn "the engine did not answer /health within ${WAIT_SECONDS} s"
    compose ps || true
    FINISHED=1
    cat >&2 <<EOF
The new images are running but not ready. Look at: $COMPOSE_TEXT logs --tail=100 engine
The database upgrade itself succeeded. If it cannot be made ready, restore the backup:
EOF
    [ "$SKIP_BACKUP" = 0 ] && restore_commands >&2
    exit 1
  fi
fi
run "${COMPOSE[@]}" ps
VERSION_AFTER="$(engine_version)"
REVISION_AFTER="$(database_revision)"
step_done

# --- 6. summary -------------------------------------------------------------------------------------------------
step "6/6 Summary"
FINISHED=1
info "engine version:     $VERSION_BEFORE -> $VERSION_AFTER"
if [ "$DRY" = 0 ] && [ "$VERSION_AFTER" != "$VERSION_CHECKOUT" ]; then
  warn "the engine now reports $VERSION_AFTER but this checkout is $VERSION_CHECKOUT"
fi
info "database revision:  $REVISION_BEFORE -> $REVISION_AFTER"
if [ "$SKIP_BACKUP" = 1 ]; then
  info "backup:             none (--skip-backup)"
else
  info "backup (kept, never pruned):"
  info "  $DUMP_FILE"
  info "  $JOBS_FILE"
  info "  $ENV_COPY"
  [ "$WITH_ASSISTANT" = 1 ] && info "  $ASSISTANT_FILE"
  info "to go back to this backup:"
  restore_commands | sed 's/^/  /'
fi
echo
info "Next: sign in, open Settings > This instance > Operations and check every workspace (see"
info "docs/OPERATIONS.md, Upgrades). Never run \`docker compose down -v\`: it deletes the volumes."
printf '\n%sUpgrade finished%s%s.\n' "$C_OK" "$([ "$DRY" = 1 ] && echo ' (dry run: nothing was run)')" "$C_OFF"

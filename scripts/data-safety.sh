#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
STATE_FILE="$PROJECT_ROOT/.teacher-assistant-installation"
COMPOSE=(docker compose -f "$PROJECT_ROOT/compose.yml" -f "$PROJECT_ROOT/compose.dev.yml")
PLACEHOLDER_ID=teacher-assistant-change-me
POSTGRES_IMAGE=postgres:16.4-alpine

fail() {
  printf 'Data safety error: %s\n' "$*" >&2
  exit 1
}

read_key() {
  local file=$1
  local key=$2
  [[ -f "$file" ]] || return 0
  awk -F= -v wanted="$key" '
    $1 == wanted {
      sub(/^[^=]*=/, "")
      sub(/\r$/, "")
      print
      exit
    }
  ' "$file"
}

validate_id() {
  local value=$1
  [[ "$value" =~ ^[a-z0-9][a-z0-9_-]{1,47}$ ]] ||
    fail "Installation IDs must be 2-48 lowercase letters, digits, hyphens, or underscores."
  [[ "$value" != "$PLACEHOLDER_ID" ]] || fail "The placeholder is not an installation ID."
}

legacy_directory_project() {
  local value
  value=$(basename "$PROJECT_ROOT" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+//g; s/^[^a-z0-9]+//')
  [[ -n "$value" ]] || value=teacher_assistant
  printf '%s\n' "$value"
}

volume_name() {
  printf '%s_%s\n' "$1" "$2"
}

volume_exists() {
  docker volume inspect "$1" >/dev/null 2>&1
}

volume_nonempty() {
  local volume=$1
  volume_exists "$volume" || return 1
  docker run --rm --read-only -v "$volume:/inspect:ro" --entrypoint sh "$POSTGRES_IMAGE" \
    -c 'test -n "$(find /inspect -mindepth 1 -print -quit)"'
}

database_volume_valid() {
  local volume=$1
  volume_exists "$volume" || return 1
  docker run --rm --read-only -v "$volume:/inspect:ro" --entrypoint sh "$POSTGRES_IMAGE" \
    -c 'test -s /inspect/PG_VERSION && test -d /inspect/base'
}

volume_digest() {
  local volume=$1
  docker run --rm --read-only -v "$volume:/inspect:ro" --entrypoint sh "$POSTGRES_IMAGE" -c '
    cd /inspect
    find . \( -type f -o -type l \) -print | LC_ALL=C sort | while IFS= read -r path; do
      if test -L "$path"; then
        printf "link %s %s\n" "$path" "$(readlink "$path")"
      else
        printf "file %s " "$path"
        sha256sum "$path" | awk "{print \$1}"
      fi
    done | sha256sum | awk "{print \$1}"
  '
}

course_directory() {
  local configured
  configured=$(read_key "$ENV_FILE" COURSE_DATA_DIR)
  configured=${configured:-./data/course_content}
  if [[ "$configured" = /* ]]; then
    realpath -m "$configured"
  else
    realpath -m "$PROJECT_ROOT/$configured"
  fi
}

mail_directory() {
  local configured
  configured=$(read_key "$ENV_FILE" MAIL_DATA_DIR)
  configured=${configured:-./data/mail_attachments}
  if [[ "$configured" = /* ]]; then
    realpath -m "$configured"
  else
    realpath -m "$PROJECT_ROOT/$configured"
  fi
}

backup_directory() {
  local configured
  configured=$(read_key "$ENV_FILE" BACKUP_ROOT)
  configured=${configured:-./backups}
  if [[ "$configured" = /* ]]; then
    realpath -m "$configured"
  else
    realpath -m "$PROJECT_ROOT/$configured"
  fi
}

write_env_key() {
  local key=$1
  local value=$2
  local temporary
  [[ -f "$ENV_FILE" ]] || cp "$ENV_EXAMPLE" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  temporary=$(mktemp "$PROJECT_ROOT/.env.write.XXXXXX")
  chmod 600 "$temporary"
  awk -F= -v wanted="$key" -v replacement="$value" '
    BEGIN { found = 0 }
    $1 == wanted {
      print wanted "=" replacement
      found = 1
      next
    }
    { print }
    END {
      if (!found) print wanted "=" replacement
    }
  ' "$ENV_FILE" > "$temporary"
  mv "$temporary" "$ENV_FILE"
}

write_state() {
  local installation_id=$1
  local initialized=$2
  local temporary
  temporary=$(mktemp "$PROJECT_ROOT/.teacher-assistant-installation.write.XXXXXX")
  chmod 600 "$temporary"
  {
    printf 'format_version=1\n'
    printf 'installation_id=%s\n' "$installation_id"
    printf 'database_volume=%s\n' "$(volume_name "$installation_id" database-data)"
    printf 'codex_auth_volume=%s\n' "$(volume_name "$installation_id" codex-auth-data)"
    printf 'integration_credential_volume=%s\n' "$(volume_name "$installation_id" integration-credential-data)"
    printf 'initialized=%s\n' "$initialized"
  } > "$temporary"
  mv "$temporary" "$STATE_FILE"
}

new_installation_id() {
  local suffix
  if [[ -r /proc/sys/kernel/random/uuid ]]; then
    suffix=$(tr -d '-' < /proc/sys/kernel/random/uuid | cut -c1-12)
  else
    suffix=$(docker run --rm --entrypoint sh "$POSTGRES_IMAGE" \
      -c 'tr -d "-" < /proc/sys/kernel/random/uuid | cut -c1-12')
  fi
  [[ -n "$suffix" ]] || fail "Cannot generate an installation ID; set INSTALLATION_ID explicitly."
  printf 'teacher-assistant-%s\n' "$suffix"
}

print_volume_status() {
  local label=$1
  local volume=$2
  local status=missing
  if volume_exists "$volume"; then
    if volume_nonempty "$volume"; then
      status='reachable (contains data)'
    else
      status='reachable (empty)'
    fi
  fi
  printf '%-20s %s [%s]\n' "$label:" "$volume" "$status"
}

list_candidates() {
  local volume project status
  printf '\nCompose database-volume candidates on this host:\n'
  while IFS= read -r volume; do
    [[ -n "$volume" ]] || continue
    project=$(docker volume inspect "$volume" --format '{{index .Labels "com.docker.compose.project"}}' 2>/dev/null || true)
    status=empty
    if database_volume_valid "$volume"; then
      status='reachable PostgreSQL data'
    elif volume_nonempty "$volume"; then
      status='nonempty but not recognized as PostgreSQL'
    fi
    printf '  - project=%s volume=%s [%s]\n' "${project:-unknown}" "$volume" "$status"
  done < <(docker volume ls -q --filter label=com.docker.compose.volume=database-data)
}

preflight() {
  local installation_id state_id initialized database_volume auth_volume integration_volume course_root mail_root identity_source
  installation_id=$(read_key "$ENV_FILE" COMPOSE_PROJECT_NAME)
  state_id=$(read_key "$STATE_FILE" installation_id)
  initialized=$(read_key "$STATE_FILE" initialized)
  identity_source=.env
  if [[ -z "$installation_id" ]]; then
    installation_id=$(legacy_directory_project)
    identity_source='directory-derived legacy identity (not relocation-safe)'
  elif [[ "$installation_id" == "$PLACEHOLDER_ID" ]]; then
    identity_source='new-install placeholder (not initialized)'
  fi
  database_volume=$(volume_name "$installation_id" database-data)
  auth_volume=$(volume_name "$installation_id" codex-auth-data)
  integration_volume=$(volume_name "$installation_id" integration-credential-data)
  course_root=$(course_directory)
  mail_root=$(mail_directory)

  printf 'Teacher Assistant data preflight (read-only)\n'
  printf '%-20s %s\n' 'Resolved identity:' "$installation_id"
  printf '%-20s %s\n' 'Identity source:' "$identity_source"
  printf '%-20s %s\n' 'State identity:' "${state_id:-not recorded}"
  printf '%-20s %s\n' 'Initialized:' "${initialized:-not recorded}"
  print_volume_status 'Database volume' "$database_volume"
  print_volume_status 'Codex-auth volume' "$auth_volume"
  print_volume_status 'Integration secrets' "$integration_volume"
  if [[ -d "$course_root" ]]; then
    printf '%-20s %s [reachable]\n' 'Course storage:' "$course_root"
  else
    printf '%-20s %s [missing]\n' 'Course storage:' "$course_root"
  fi
  if [[ -d "$mail_root" ]]; then
    printf '%-20s %s [reachable]\n' 'Mail attachments:' "$mail_root"
  else
    printf '%-20s %s [missing]\n' 'Mail attachments:' "$mail_root"
  fi
  printf '%-20s %s\n' 'Backup root:' "$(backup_directory)"
  printf '%-20s %s\n' 'Browser UI state:' 'convenience-only local browser storage (planned M19)'
  printf '%-20s %s\n' 'Disposable data:' 'runtime workspaces, caches, build output, node_modules, test/E2E volumes'
  list_candidates

  if [[ "$identity_source" != '.env' || -z "$state_id" ]]; then
    printf '\nAction required: initialize a new installation or explicitly adopt an existing namespace.\n'
    return 2
  fi
  if [[ "$state_id" != "$installation_id" ]]; then
    printf '\nUnsafe state: .env and the installation marker disagree. No data-changing command will run.\n'
    return 3
  fi
  if [[ "$initialized" == 1 ]] && ! database_volume_valid "$database_volume"; then
    printf '\nUnsafe state: the recorded installation database is missing or invalid. No fresh database will be created.\n'
    return 4
  fi
}

init_installation() {
  local requested=${INSTALLATION_ID:-}
  local current legacy database_volume course_root
  current=$(read_key "$ENV_FILE" COMPOSE_PROJECT_NAME)
  legacy=$(legacy_directory_project)
  course_root=$(course_directory)

  if [[ -f "$STATE_FILE" ]]; then
    fail "This repository already has an installation marker. Run make data-preflight."
  fi
  if [[ -z "$requested" ]]; then
    requested=$(new_installation_id)
  fi
  validate_id "$requested"
  database_volume=$(volume_name "$requested" database-data)
  if volume_nonempty "$database_volume"; then
    fail "Target database volume $database_volume already contains data; use data-adopt with an explicit source."
  fi
  if database_volume_valid "$(volume_name "$legacy" database-data)"; then
    fail "Legacy data exists under $legacy. Use: make data-adopt LEGACY_PROJECT=$legacy INSTALLATION_ID=$legacy"
  fi
  if [[ -d "$course_root" ]] && find "$course_root" -mindepth 1 -print -quit | grep -q .; then
    fail "Course storage already contains files; use data-adopt instead of initializing."
  fi
  if [[ -n "$current" && "$current" != "$PLACEHOLDER_ID" ]]; then
    fail ".env already has an explicit identity. Use data-preflight or data-adopt."
  fi
  write_env_key COMPOSE_PROJECT_NAME "$requested"
  write_state "$requested" 0
  printf 'Initialized stable data identity %s. No Docker volume was created yet.\n' "$requested"
}

prepare() {
  local installation_id state_id initialized database_volume legacy course_root
  [[ -f "$ENV_FILE" ]] || fail ".env is missing. For a new installation, run: cp .env.example .env && make dev. For existing data, run make data-preflight."
  installation_id=$(read_key "$ENV_FILE" COMPOSE_PROJECT_NAME)
  if [[ -z "$installation_id" ]]; then
    legacy=$(legacy_directory_project)
    fail "This is a legacy installation without a stable identity. Run: make data-adopt LEGACY_PROJECT=$legacy INSTALLATION_ID=$legacy"
  fi
  if [[ "$installation_id" == "$PLACEHOLDER_ID" ]]; then
    init_installation
    installation_id=$(read_key "$ENV_FILE" COMPOSE_PROJECT_NAME)
  fi
  validate_id "$installation_id"
  state_id=$(read_key "$STATE_FILE" installation_id)
  initialized=$(read_key "$STATE_FILE" initialized)
  database_volume=$(volume_name "$installation_id" database-data)
  if [[ -z "$state_id" ]]; then
    if volume_nonempty "$database_volume"; then
      fail "Volume $database_volume contains unadopted data. Run data-adopt explicitly."
    fi
    course_root=$(course_directory)
    if [[ -d "$course_root" ]] && find "$course_root" -mindepth 1 -print -quit | grep -q .; then
      fail "Course storage contains data but no installation marker. Refusing to create a fresh database; run data-preflight and adopt or recover the matching namespace."
    fi
    write_state "$installation_id" 0
    state_id=$installation_id
    initialized=0
  fi
  [[ "$state_id" == "$installation_id" ]] ||
    fail ".env identity $installation_id does not match recorded identity $state_id."
  if [[ "$initialized" == 1 ]] && ! database_volume_valid "$database_volume"; then
    fail "Recorded database volume $database_volume is missing or invalid. Refusing to initialize a replacement."
  fi
}

record_started() {
  local installation_id database_volume
  installation_id=$(read_key "$ENV_FILE" COMPOSE_PROJECT_NAME)
  validate_id "$installation_id"
  database_volume=$(volume_name "$installation_id" database-data)
  database_volume_valid "$database_volume" ||
    fail "Database volume $database_volume did not initialize correctly."
  write_state "$installation_id" 1
  printf 'Stable data identity verified: %s\n' "$installation_id"
}

copy_volume() {
  local source=$1
  local target=$2
  local project=$3
  local logical=$4
  local source_digest target_digest
  if ! volume_exists "$target"; then
    docker volume create \
      --label "com.docker.compose.project=$project" \
      --label "com.docker.compose.volume=$logical" \
      "$target" >/dev/null
  fi
  volume_nonempty "$target" && fail "Target volume $target already contains data; neither copy was changed."
  docker run --rm -v "$source:/source:ro" -v "$target:/target" --entrypoint sh "$POSTGRES_IMAGE" -c '
    test -z "$(find /target -mindepth 1 -print -quit)"
    cd /source
    tar -cf - . | tar -xpf - -C /target
  '
  source_digest=$(volume_digest "$source")
  target_digest=$(volume_digest "$target")
  [[ "$source_digest" == "$target_digest" ]] ||
    fail "Verification failed while copying $source to $target. The source remains untouched."
}

adopt() {
  local source=${LEGACY_PROJECT:-}
  local target=${INSTALLATION_ID:-}
  local source_db source_auth source_integration target_db target_auth target_integration rollback_dir rollback_root stamp source_containers
  [[ -n "$source" && -n "$target" ]] ||
    fail "Set both LEGACY_PROJECT and INSTALLATION_ID, for example: make data-adopt LEGACY_PROJECT=teacher_assistant INSTALLATION_ID=teacher_assistant"
  validate_id "$source"
  validate_id "$target"
  source_db=$(volume_name "$source" database-data)
  source_auth=$(volume_name "$source" codex-auth-data)
  source_integration=$(volume_name "$source" integration-credential-data)
  target_db=$(volume_name "$target" database-data)
  target_auth=$(volume_name "$target" codex-auth-data)
  target_integration=$(volume_name "$target" integration-credential-data)
  source_containers=$(docker ps -q --filter "label=com.docker.compose.project=$source")
  [[ -z "$source_containers" ]] ||
    fail "Stop the source installation before adoption. Run make down when it uses the current directory."
  database_volume_valid "$source_db" || fail "Source database volume $source_db is missing or invalid."

  if [[ "$source" != "$target" ]]; then
    volume_nonempty "$target_db" &&
      fail "Both source and target database volumes contain data. Choose one explicitly; no merge or deletion was attempted."
    if volume_nonempty "$target_auth"; then
      fail "The target Codex-auth volume already contains data. Sign-in can be renewed; no credentials were overwritten or merged."
    fi
    if volume_nonempty "$target_integration"; then
      fail "The target integration-credential volume already contains data. Reconnect instead; no credentials were overwritten or merged."
    fi
  fi

  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  rollback_root=$(backup_directory)
  rollback_dir="$rollback_root/migrations/$stamp-$source-to-$target"
  mkdir -p "$rollback_dir"
  chmod 700 "$rollback_root" "$rollback_root/migrations" "$rollback_dir" 2>/dev/null || true
  if [[ -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE" "$rollback_dir/env.before"
    chmod 600 "$rollback_dir/env.before"
  fi
  if [[ -f "$STATE_FILE" ]]; then
    cp "$STATE_FILE" "$rollback_dir/installation-state.before"
    chmod 600 "$rollback_dir/installation-state.before"
  fi

  if [[ "$source" != "$target" ]]; then
    copy_volume "$source_db" "$target_db" "$target" database-data
    if volume_nonempty "$source_auth"; then
      copy_volume "$source_auth" "$target_auth" "$target" codex-auth-data
    fi
    if volume_nonempty "$source_integration"; then
      copy_volume "$source_integration" "$target_integration" "$target" integration-credential-data
    fi
  fi

  write_env_key COMPOSE_PROJECT_NAME "$target"
  write_state "$target" 1
  {
    printf 'migration_time=%s\n' "$stamp"
    printf 'source_project=%s\n' "$source"
    printf 'source_database_volume=%s\n' "$source_db"
    printf 'source_codex_auth_volume=%s\n' "$source_auth"
    printf 'source_integration_credential_volume=%s\n' "$source_integration"
    printf 'target_project=%s\n' "$target"
    printf 'target_database_volume=%s\n' "$target_db"
    printf 'target_codex_auth_volume=%s\n' "$target_auth"
    printf 'target_integration_credential_volume=%s\n' "$target_integration"
    printf 'previous_env_saved=%s\n' "$([[ -f "$rollback_dir/env.before" ]] && printf true || printf false)"
    printf 'previous_state_saved=%s\n' "$([[ -f "$rollback_dir/installation-state.before" ]] && printf true || printf false)"
    printf 'old_volumes_deleted=false\n'
  } > "$rollback_dir/migration-record.txt"
  chmod 600 "$rollback_dir/migration-record.txt"
  printf 'Adopted stable identity %s from %s.\n' "$target" "$source"
  printf 'Old volumes were not deleted. Rollback metadata: %s\n' "$rollback_dir"
}

case "${1:-}" in
  preflight) preflight ;;
  init) init_installation ;;
  prepare) prepare ;;
  record-started) record_started ;;
  adopt) adopt ;;
  *) fail "Usage: $0 {preflight|init|prepare|record-started|adopt}" ;;
esac

#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
COMPOSE=(docker compose -f "$PROJECT_ROOT/compose.yml" -f "$PROJECT_ROOT/compose.dev.yml")
ENV_FILE="$PROJECT_ROOT/.env"

read_env() {
  awk -F= -v wanted="$1" '
    $1 == wanted { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; exit }
  ' "$ENV_FILE"
}

resolve_from_root() {
  local configured=$1
  if [[ "$configured" = /* ]]; then
    realpath -m "$configured"
  else
    realpath -m "$PROJECT_ROOT/$configured"
  fi
}

service_was_running() {
  grep -Fxq "$1" <<< "$RUNNING_SERVICES"
}

"$PROJECT_ROOT/scripts/data-safety.sh" prepare
INSTALLATION_ID=$(read_env COMPOSE_PROJECT_NAME)
[[ -n "${BACKUP:-}" ]] || {
  printf 'Restore error: set BACKUP to a coordinated backup directory.\n' >&2
  exit 1
}
[[ -d "$BACKUP" ]] || {
  printf 'Restore error: backup directory not found: %s\n' "$BACKUP" >&2
  exit 1
}
[[ "${CONFIRM_RESTORE:-}" == "$INSTALLATION_ID" ]] || {
  printf 'Restore error: this replaces the active database and private file stores. Re-run with CONFIRM_RESTORE=%s.\n' "$INSTALLATION_ID" >&2
  exit 1
}
BUNDLE=$(realpath "$BACKUP")

COURSE_SETTING=$(read_env COURSE_DATA_DIR)
MAIL_SETTING=$(read_env MAIL_DATA_DIR)
DOCUMENT_SETTING=$(read_env DOCUMENT_DATA_DIR)
COURSE_ROOT=$(resolve_from_root "${COURSE_SETTING:-./data/course_content}")
MAIL_ROOT=$(resolve_from_root "${MAIL_SETTING:-./data/mail_attachments}")
DOCUMENT_ROOT=$(resolve_from_root "${DOCUMENT_SETTING:-./data/document_projects}")
COURSE_PARENT=$(dirname "$COURSE_ROOT")
COURSE_NAME=$(basename "$COURSE_ROOT")
MAIL_PARENT=$(dirname "$MAIL_ROOT")
MAIL_NAME=$(basename "$MAIL_ROOT")
DOCUMENT_PARENT=$(dirname "$DOCUMENT_ROOT")
DOCUMENT_NAME=$(basename "$DOCUMENT_ROOT")
[[ "$COURSE_ROOT" != / && "$COURSE_ROOT" != "$PROJECT_ROOT" ]] || {
  printf 'Restore error: COURSE_DATA_DIR resolves to an unsafe directory.\n' >&2
  exit 1
}
[[ "$COURSE_PARENT" != / ]] || {
  printf 'Restore error: COURSE_DATA_DIR must not be a direct child of the host filesystem root.\n' >&2
  exit 1
}
mkdir -p "$COURSE_PARENT"
[[ "$MAIL_ROOT" != / && "$MAIL_ROOT" != "$PROJECT_ROOT" && "$MAIL_PARENT" != / ]] || {
  printf 'Restore error: MAIL_DATA_DIR resolves to an unsafe directory.\n' >&2
  exit 1
}
mkdir -p "$MAIL_PARENT"
[[ "$DOCUMENT_ROOT" != / && "$DOCUMENT_ROOT" != "$PROJECT_ROOT" && "$DOCUMENT_PARENT" != / ]] || {
  printf 'Restore error: DOCUMENT_DATA_DIR resolves to an unsafe directory.\n' >&2
  exit 1
}
mkdir -p "$DOCUMENT_PARENT"

BACKEND_IMAGE="$INSTALLATION_ID-backend:latest"
if ! docker image inspect "$BACKEND_IMAGE" >/dev/null 2>&1; then
  printf 'Restore error: the backend image is unavailable. Run make dev first.\n' >&2
  exit 1
fi
VERIFIED=$(docker run --rm --read-only \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$BUNDLE:/bundle:ro" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive verify-bundle --bundle /bundle)
printf 'Validated backup manifest: %s\n' "$VERIFIED"

"$PROJECT_ROOT/scripts/data-backup.sh"
printf 'A new coordinated safety backup was created before restore.\n'

RUNNING_SERVICES=$("${COMPOSE[@]}" ps --status running --services)
service_was_running backend && "${COMPOSE[@]}" stop backend >/dev/null
service_was_running frontend && "${COMPOSE[@]}" stop frontend >/dev/null
if ! service_was_running database; then
  "${COMPOSE[@]}" up -d database >/dev/null
fi

docker run --rm --read-only \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$BUNDLE:/bundle:ro" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive verify-bundle --bundle /bundle >/dev/null
"${COMPOSE[@]}" exec -T database pg_restore -l < "$BUNDLE/database.dump" >/dev/null
"${COMPOSE[@]}" exec -T database sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists --force "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
if ! "${COMPOSE[@]}" exec -T database sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' \
  < "$BUNDLE/database.dump"; then
  printf 'Restore failed while loading PostgreSQL. Services remain stopped. Use the safety backup printed above to roll back.\n' >&2
  exit 1
fi

RESTORE_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
if ! docker run --rm \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$BUNDLE:/bundle:ro" \
  -v "$COURSE_PARENT:/course-parent" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive restore-course \
  --archive /bundle/course-content.tar.gz \
  --parent /course-parent \
  --directory-name "$COURSE_NAME" \
  --rollback-suffix "$RESTORE_STAMP"; then
  printf 'Restore failed while replacing course files. Services remain stopped; the database safety backup and original course directory remain available.\n' >&2
  exit 1
fi

DOCUMENT_RESTORE_COMMAND=(restore-documents --archive /bundle/document-projects.tar.gz)
if grep -Fq '"document_archive": null' <<< "$VERIFIED"; then
  DOCUMENT_RESTORE_COMMAND=(restore-empty-documents)
fi
if ! docker run --rm \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$BUNDLE:/bundle:ro" \
  -v "$DOCUMENT_PARENT:/document-parent" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive "${DOCUMENT_RESTORE_COMMAND[@]}" \
  --parent /document-parent \
  --directory-name "$DOCUMENT_NAME" \
  --rollback-suffix "$RESTORE_STAMP"; then
  printf 'Restore failed while replacing document source files. Services remain stopped; rollback directories and the safety backup remain available.\n' >&2
  exit 1
fi

if ! docker run --rm \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$BUNDLE:/bundle:ro" \
  -v "$MAIL_PARENT:/mail-parent" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive restore-mail \
  --archive /bundle/mail-attachments.tar.gz \
  --parent /mail-parent \
  --directory-name "$MAIL_NAME" \
  --rollback-suffix "$RESTORE_STAMP"; then
  printf 'Restore failed while replacing mail attachment files. Services remain stopped; rollback directories and the safety backup remain available.\n' >&2
  exit 1
fi

"${COMPOSE[@]}" run --rm --entrypoint alembic backend upgrade head
service_was_running backend && "${COMPOSE[@]}" start backend >/dev/null
service_was_running frontend && "${COMPOSE[@]}" start frontend >/dev/null
if ! service_was_running database; then
  "${COMPOSE[@]}" stop database >/dev/null
fi
printf 'Restore completed and migrations are current. Verify Calendar, Courses, Documents, Assistant history, diagnostics, and private-file hashes.\n'
printf 'Codex authentication is installation-specific and was not restored; sign in again if needed.\n'
printf 'Mailbox credentials were not restored; reconnect the dedicated mailbox in Settings.\n'

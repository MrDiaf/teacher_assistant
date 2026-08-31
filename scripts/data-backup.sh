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

resume_services() {
  local exit_code=$?
  trap - EXIT INT TERM
  if service_was_running database; then
    :
  else
    "${COMPOSE[@]}" stop database >/dev/null 2>&1 || true
  fi
  service_was_running backend && "${COMPOSE[@]}" start backend >/dev/null 2>&1 || true
  service_was_running frontend && "${COMPOSE[@]}" start frontend >/dev/null 2>&1 || true
  exit "$exit_code"
}

"$PROJECT_ROOT/scripts/data-safety.sh" prepare

INSTALLATION_ID=$(read_env COMPOSE_PROJECT_NAME)
COURSE_SETTING=$(read_env COURSE_DATA_DIR)
BACKUP_SETTING=$(read_env BACKUP_ROOT)
COURSE_ROOT=$(resolve_from_root "${COURSE_SETTING:-./data/course_content}")
BACKUP_ROOT=$(resolve_from_root "${BACKUP_SETTING:-./backups}")
[[ -d "$COURSE_ROOT" ]] || {
  printf 'Backup error: course storage is missing: %s\n' "$COURSE_ROOT" >&2
  exit 1
}
[[ "$BACKUP_ROOT" != / && "$BACKUP_ROOT" != "$PROJECT_ROOT" ]] || {
  printf 'Backup error: BACKUP_ROOT resolves to an unsafe directory.\n' >&2
  exit 1
}

mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BUNDLE_NAME="$STAMP-$INSTALLATION_ID"
FINAL_BUNDLE="$BACKUP_ROOT/$BUNDLE_NAME"
INCOMPLETE_BUNDLE="$BACKUP_ROOT/.$BUNDLE_NAME.incomplete"
counter=1
while [[ -e "$FINAL_BUNDLE" || -e "$INCOMPLETE_BUNDLE" ]]; do
  BUNDLE_NAME="$STAMP-$INSTALLATION_ID-$counter"
  FINAL_BUNDLE="$BACKUP_ROOT/$BUNDLE_NAME"
  INCOMPLETE_BUNDLE="$BACKUP_ROOT/.$BUNDLE_NAME.incomplete"
  counter=$((counter + 1))
done
mkdir "$INCOMPLETE_BUNDLE"
chmod 700 "$INCOMPLETE_BUNDLE"

RUNNING_SERVICES=$("${COMPOSE[@]}" ps --status running --services)
trap resume_services EXIT INT TERM

service_was_running backend && "${COMPOSE[@]}" stop backend >/dev/null
service_was_running frontend && "${COMPOSE[@]}" stop frontend >/dev/null
if ! service_was_running database; then
  "${COMPOSE[@]}" up -d database >/dev/null
fi

DATABASE_DUMP="$INCOMPLETE_BUNDLE/database.dump"
COURSE_ARCHIVE="$INCOMPLETE_BUNDLE/course-content.tar.gz"
"${COMPOSE[@]}" exec -T database sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DATABASE_DUMP"
chmod 600 "$DATABASE_DUMP"
"${COMPOSE[@]}" exec -T database pg_restore -l < "$DATABASE_DUMP" >/dev/null

BACKEND_IMAGE="$INSTALLATION_ID-backend:latest"
if ! docker image inspect "$BACKEND_IMAGE" >/dev/null 2>&1; then
  printf 'Backup error: the backend image is unavailable. Run make dev first.\n' >&2
  exit 1
fi
docker run --rm --read-only \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$COURSE_ROOT:/course-content:ro" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive create-course --source /course-content \
  > "$COURSE_ARCHIVE"
chmod 600 "$COURSE_ARCHIVE"

docker run --rm --read-only \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$INCOMPLETE_BUNDLE:/bundle:ro" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive create-manifest \
  --bundle /bundle \
  --installation-id "$INSTALLATION_ID" \
  --created-at "$STAMP" \
  > "$INCOMPLETE_BUNDLE/manifest.json"
chmod 600 "$INCOMPLETE_BUNDLE/manifest.json"

docker run --rm --read-only \
  -v "$PROJECT_ROOT/backend:/app:ro" \
  -v "$INCOMPLETE_BUNDLE:/bundle:ro" \
  --entrypoint python "$BACKEND_IMAGE" \
  -m app.maintenance.data_archive verify-bundle --bundle /bundle >/dev/null
"${COMPOSE[@]}" exec -T database pg_restore -l < "$DATABASE_DUMP" >/dev/null

mv "$INCOMPLETE_BUNDLE" "$FINAL_BUNDLE"
printf 'Verified coordinated backup: %s\n' "$FINAL_BUNDLE"
printf 'Codex authentication was intentionally excluded; sign in again after a clean restore.\n'

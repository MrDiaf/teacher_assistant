#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
DRILL_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/teacher-assistant-m14.XXXXXX")
SUFFIX=$(basename "$DRILL_ROOT" | tr '[:upper:]' '[:lower:]')
SOURCE_ID="m14-source-${SUFFIX##*.}"
RESTORE_ID="m14-restore-${SUFFIX##*.}"
LEGACY_ID="m14-legacy-${SUFFIX##*.}"
ADOPTED_ID="m14-adopted-${SUFFIX##*.}"
AMBIGUOUS_ID="m14-ambiguous-${SUFFIX##*.}"
SOURCE_REPO="$DRILL_ROOT/parent-a/teacher-assistant"
MOVED_REPO="$DRILL_ROOT/parent-b/teacher-assistant"
RENAMED_REPO="$DRILL_ROOT/parent-b/teacher-assistant-renamed"
RESTORE_REPO="$DRILL_ROOT/restore/teacher-assistant"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  docker compose -p "$SOURCE_ID" -f "$PROJECT_ROOT/compose.yml" -f "$PROJECT_ROOT/compose.dev.yml" down -v --remove-orphans >/dev/null 2>&1 || true
  docker compose -p "$RESTORE_ID" -f "$PROJECT_ROOT/compose.yml" -f "$PROJECT_ROOT/compose.dev.yml" down -v --remove-orphans >/dev/null 2>&1 || true
  docker volume rm \
    "${LEGACY_ID}_database-data" "${LEGACY_ID}_codex-auth-data" \
    "${LEGACY_ID}_integration-credential-data" \
    "${ADOPTED_ID}_database-data" "${ADOPTED_ID}_codex-auth-data" \
    "${ADOPTED_ID}_integration-credential-data" \
    "${AMBIGUOUS_ID}_database-data" "${AMBIGUOUS_ID}_codex-auth-data" \
    "${AMBIGUOUS_ID}_integration-credential-data" \
    >/dev/null 2>&1 || true
  case "$DRILL_ROOT" in
    "${TMPDIR:-/tmp}"/teacher-assistant-m14.*)
      docker run --rm -v "$DRILL_ROOT:/drill" --entrypoint sh postgres:16.4-alpine \
        -c 'chmod -R a+rwX /drill' >/dev/null 2>&1 || true
      rm -rf "$DRILL_ROOT"
      ;;
    *) printf 'Refusing to remove unexpected drill directory: %s\n' "$DRILL_ROOT" >&2 ;;
  esac
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

copy_worktree() {
  local destination=$1
  mkdir -p "$destination"
  (
    cd "$PROJECT_ROOT"
    while IFS= read -r -d '' path; do
      [[ -e "$path" ]] && printf '%s\0' "$path"
    done < <(git ls-files -co --exclude-standard -z)
  ) | (
    cd "$PROJECT_ROOT"
    tar --null -T - -cf -
  ) | tar -C "$destination" -xf -
}

configure_installation() {
  local repository=$1
  local identity=$2
  local backend_port=$3
  local frontend_port=$4
  cp "$repository/.env.example" "$repository/.env"
  sed -i "s/^BACKEND_PORT=.*/BACKEND_PORT=$backend_port/" "$repository/.env"
  sed -i "s/^FRONTEND_PORT=.*/FRONTEND_PORT=$frontend_port/" "$repository/.env"
  make -C "$repository" data-init INSTALLATION_ID="$identity" >/dev/null
}

wait_for_backend() {
  local repository=$1
  local attempt
  for attempt in $(seq 1 60); do
    if compose_in "$repository" exec -T frontend \
      wget -q --spider http://backend:8000/health >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  printf 'Fixture backend did not become healthy in %s.\n' "$repository" >&2
  return 1
}

compose_in() {
  local repository=$1
  shift
  (cd "$repository" && docker compose -f compose.yml -f compose.dev.yml "$@")
}

database_fingerprint() {
  local repository=$1
  local table
  for table in \
    assistant_context_audits assistant_conversations assistant_jobs \
    assistant_messages assistant_proposal_actions assistant_proposals \
    calendars course_calendar_links course_source_text course_sources courses \
    diagnostic_audit_records diagnostic_errors events note_source_links \
    note_summaries notes mail_addresses mail_attachments mail_cleanup_audits \
    mail_integration_connections mail_messages mail_quarantines \
    document_projects document_tags; do
    compose_in "$repository" exec -T database sh -c \
      "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"select '$table=' || count(*) || ':' || coalesce(md5(string_agg(id::text, ',' order by id::text)), '') from $table\""
  done
  compose_in "$repository" exec -T database sh -c \
    "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"select 'document_project_tags=' || count(*) || ':' || coalesce(md5(string_agg(project_id::text || tag_id::text, ',' order by project_id::text, tag_id::text)), '') from document_project_tags\""
  compose_in "$repository" exec -T database sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select '\''alembic_version='\'' || version_num from alembic_version"'
}

file_fingerprint() {
  local repository=$1
  compose_in "$repository" exec -T backend sha256sum \
    /data/course_content/33333333-3333-4333-8333-333333333333/slides/44444444-4444-4444-8444-444444444444/original.pdf \
    | awk '{print $1}'
}

auth_fingerprint() {
  local repository=$1
  compose_in "$repository" exec -T backend sha256sum \
    /var/lib/teacher-assistant/codex/m14-relocation-marker | awk '{print $1}'
}

mail_fingerprint() {
  local repository=$1
  compose_in "$repository" exec -T backend sha256sum \
    /data/mail_attachments/55555555-5555-4555-8555-555555555555/66666666-6666-4666-8666-666666666666.bin \
    | awk '{print $1}'
}

document_fingerprint() {
  local repository=$1
  compose_in "$repository" exec -T backend sha256sum \
    /data/document_projects/15151515-1515-4515-8515-151515151515/source/main.tex \
    | awk '{print $1}'
}

integration_credential_fingerprint() {
  local repository=$1
  compose_in "$repository" exec -T backend sha256sum \
    /var/lib/teacher-assistant/integrations/m20-relocation-marker | awk '{print $1}'
}

assert_equal() {
  local expected=$1
  local actual=$2
  local label=$3
  if [[ "$expected" != "$actual" ]]; then
    printf '%s changed during the relocation drill.\n' "$label" >&2
    diff <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") || true
    return 1
  fi
}

test_legacy_adoption() {
  local repository="$DRILL_ROOT/adoption/teacher-assistant"
  copy_worktree "$repository"
  cp "$repository/.env.example" "$repository/.env"
  sed -i '/^COMPOSE_PROJECT_NAME=/d' "$repository/.env"
  docker volume create \
    --label "com.docker.compose.project=$LEGACY_ID" \
    --label 'com.docker.compose.volume=database-data' \
    "${LEGACY_ID}_database-data" >/dev/null
  docker volume create \
    --label "com.docker.compose.project=$LEGACY_ID" \
    --label 'com.docker.compose.volume=codex-auth-data' \
    "${LEGACY_ID}_codex-auth-data" >/dev/null
  docker volume create \
    --label "com.docker.compose.project=$LEGACY_ID" \
    --label 'com.docker.compose.volume=integration-credential-data' \
    "${LEGACY_ID}_integration-credential-data" >/dev/null
  docker run --rm \
    -v "${LEGACY_ID}_database-data:/fixture" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'mkdir -p /fixture/base; printf "16" > /fixture/PG_VERSION; printf "legacy-db" > /fixture/base/fixture' >/dev/null
  docker run --rm \
    -v "${LEGACY_ID}_codex-auth-data:/fixture" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'printf "renewable-auth-fixture" > /fixture/marker' >/dev/null
  docker run --rm \
    -v "${LEGACY_ID}_integration-credential-data:/fixture" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'printf "renewable-integration-fixture" > /fixture/marker' >/dev/null

  make -C "$repository" data-adopt \
    LEGACY_PROJECT="$LEGACY_ID" INSTALLATION_ID="$ADOPTED_ID" >/dev/null
  docker run --rm --read-only \
    -v "${LEGACY_ID}_database-data:/source:ro" \
    -v "${ADOPTED_ID}_database-data:/target:ro" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'cmp /source/PG_VERSION /target/PG_VERSION; cmp /source/base/fixture /target/base/fixture'
  docker run --rm --read-only \
    -v "${LEGACY_ID}_codex-auth-data:/source:ro" \
    -v "${ADOPTED_ID}_codex-auth-data:/target:ro" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'cmp /source/marker /target/marker'
  docker run --rm --read-only \
    -v "${LEGACY_ID}_integration-credential-data:/source:ro" \
    -v "${ADOPTED_ID}_integration-credential-data:/target:ro" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'cmp /source/marker /target/marker'
  grep -Fxq "COMPOSE_PROJECT_NAME=$ADOPTED_ID" "$repository/.env"
  grep -Fxq "installation_id=$ADOPTED_ID" "$repository/.teacher-assistant-installation"
  docker volume inspect "${LEGACY_ID}_database-data" >/dev/null

  docker volume create \
    --label "com.docker.compose.project=$AMBIGUOUS_ID" \
    --label 'com.docker.compose.volume=database-data' \
    "${AMBIGUOUS_ID}_database-data" >/dev/null
  docker run --rm \
    -v "${AMBIGUOUS_ID}_database-data:/fixture" \
    --entrypoint sh postgres:16.4-alpine \
    -c 'mkdir -p /fixture/base; printf "16" > /fixture/PG_VERSION; printf "other-db" > /fixture/base/fixture' >/dev/null
  if make -C "$repository" data-adopt \
    LEGACY_PROJECT="$LEGACY_ID" INSTALLATION_ID="$AMBIGUOUS_ID" >/dev/null 2>&1; then
    printf 'Ambiguous populated source and target volumes were accepted.\n' >&2
    exit 1
  fi
  grep -Fxq "COMPOSE_PROJECT_NAME=$ADOPTED_ID" "$repository/.env"
}

mkdir -p "$(dirname "$SOURCE_REPO")" "$(dirname "$MOVED_REPO")" "$(dirname "$RESTORE_REPO")"
test_legacy_adoption
copy_worktree "$SOURCE_REPO"
configure_installation "$SOURCE_REPO" "$SOURCE_ID" 18140 15140
make -C "$SOURCE_REPO" dev >/dev/null
wait_for_backend "$SOURCE_REPO"

compose_in "$SOURCE_REPO" exec -T database sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$SOURCE_REPO/scripts/fixtures/m14.sql" >/dev/null
compose_in "$SOURCE_REPO" exec -T backend sh -c '
  path=/data/course_content/33333333-3333-4333-8333-333333333333/slides/44444444-4444-4444-8444-444444444444
  mkdir -p "$path"
  printf "%s" "%PDF-1.4 M14 fixture upload" > "$path/original.pdf"
  chmod 600 "$path/original.pdf"
  mail_path=/data/mail_attachments/55555555-5555-4555-8555-555555555555
  mkdir -p "$mail_path"
  printf "%s" "M20 private mail attachment fixture" > "$mail_path/66666666-6666-4666-8666-666666666666.bin"
  chmod 600 "$mail_path/66666666-6666-4666-8666-666666666666.bin"
  document_path=/data/document_projects/15151515-1515-4515-8515-151515151515
  mkdir -p "$document_path/source" "$document_path/build"
  printf "%s" "\\documentclass{article} fixture" > "$document_path/source/main.tex"
  chmod 600 "$document_path/source/main.tex"
  printf "%s" "renewable-auth-volume-fixture" > /var/lib/teacher-assistant/codex/m14-relocation-marker
  printf "%s" "renewable-mail-credential-fixture" > /var/lib/teacher-assistant/integrations/m20-relocation-marker
'

BASE_DATABASE=$(database_fingerprint "$SOURCE_REPO")
BASE_FILE=$(file_fingerprint "$SOURCE_REPO")
BASE_AUTH=$(auth_fingerprint "$SOURCE_REPO")
BASE_MAIL=$(mail_fingerprint "$SOURCE_REPO")
BASE_DOCUMENT=$(document_fingerprint "$SOURCE_REPO")
BASE_INTEGRATION_CREDENTIAL=$(integration_credential_fingerprint "$SOURCE_REPO")

make -C "$SOURCE_REPO" migrate >/dev/null
make -C "$SOURCE_REPO" dev >/dev/null
wait_for_backend "$SOURCE_REPO"
assert_equal "$BASE_DATABASE" "$(database_fingerprint "$SOURCE_REPO")" 'Database IDs/counts after migrate/rebuild'
assert_equal "$BASE_FILE" "$(file_fingerprint "$SOURCE_REPO")" 'Upload hash after migrate/rebuild'
assert_equal "$BASE_AUTH" "$(auth_fingerprint "$SOURCE_REPO")" 'Auth-volume marker after migrate/rebuild'
assert_equal "$BASE_MAIL" "$(mail_fingerprint "$SOURCE_REPO")" 'Mail attachment hash after migrate/rebuild'
assert_equal "$BASE_DOCUMENT" "$(document_fingerprint "$SOURCE_REPO")" 'Document hash after migrate/rebuild'
assert_equal "$BASE_INTEGRATION_CREDENTIAL" "$(integration_credential_fingerprint "$SOURCE_REPO")" 'Integration credential after migrate/rebuild'

make -C "$SOURCE_REPO" down >/dev/null
mv "$SOURCE_REPO" "$(dirname "$MOVED_REPO")/"
make -C "$MOVED_REPO" dev >/dev/null
wait_for_backend "$MOVED_REPO"
assert_equal "$BASE_DATABASE" "$(database_fingerprint "$MOVED_REPO")" 'Database IDs/counts after same-name move'
assert_equal "$BASE_FILE" "$(file_fingerprint "$MOVED_REPO")" 'Upload hash after same-name move'
assert_equal "$BASE_AUTH" "$(auth_fingerprint "$MOVED_REPO")" 'Auth-volume marker after same-name move'
assert_equal "$BASE_MAIL" "$(mail_fingerprint "$MOVED_REPO")" 'Mail attachment hash after same-name move'
assert_equal "$BASE_DOCUMENT" "$(document_fingerprint "$MOVED_REPO")" 'Document hash after same-name move'
assert_equal "$BASE_INTEGRATION_CREDENTIAL" "$(integration_credential_fingerprint "$MOVED_REPO")" 'Integration credential after same-name move'

make -C "$MOVED_REPO" down >/dev/null
mv "$MOVED_REPO" "$RENAMED_REPO"
make -C "$RENAMED_REPO" dev >/dev/null
wait_for_backend "$RENAMED_REPO"
assert_equal "$BASE_DATABASE" "$(database_fingerprint "$RENAMED_REPO")" 'Database IDs/counts after rename'
assert_equal "$BASE_FILE" "$(file_fingerprint "$RENAMED_REPO")" 'Upload hash after rename'
assert_equal "$BASE_AUTH" "$(auth_fingerprint "$RENAMED_REPO")" 'Auth-volume marker after rename'
assert_equal "$BASE_MAIL" "$(mail_fingerprint "$RENAMED_REPO")" 'Mail attachment hash after rename'
assert_equal "$BASE_DOCUMENT" "$(document_fingerprint "$RENAMED_REPO")" 'Document hash after rename'
assert_equal "$BASE_INTEGRATION_CREDENTIAL" "$(integration_credential_fingerprint "$RENAMED_REPO")" 'Integration credential after rename'

make -C "$RENAMED_REPO" backup >/dev/null
BUNDLE=$(find "$RENAMED_REPO/backups" -mindepth 1 -maxdepth 1 -type d -name "*-$SOURCE_ID" | sort | tail -n 1)
[[ -n "$BUNDLE" ]]

copy_worktree "$RESTORE_REPO"
configure_installation "$RESTORE_REPO" "$RESTORE_ID" 18141 15141
make -C "$RESTORE_REPO" dev >/dev/null
wait_for_backend "$RESTORE_REPO"
make -C "$RESTORE_REPO" restore BACKUP="$BUNDLE" CONFIRM_RESTORE="$RESTORE_ID" >/dev/null
wait_for_backend "$RESTORE_REPO"
assert_equal "$BASE_DATABASE" "$(database_fingerprint "$RESTORE_REPO")" 'Database IDs/counts after clean restore'
assert_equal "$BASE_FILE" "$(file_fingerprint "$RESTORE_REPO")" 'Upload hash after clean restore'
assert_equal "$BASE_MAIL" "$(mail_fingerprint "$RESTORE_REPO")" 'Mail attachment hash after clean restore'
assert_equal "$BASE_DOCUMENT" "$(document_fingerprint "$RESTORE_REPO")" 'Document hash after clean restore'
if compose_in "$RESTORE_REPO" exec -T backend test -e \
  /var/lib/teacher-assistant/codex/m14-relocation-marker; then
  printf 'Codex-auth fixture was copied into a clean restore.\n' >&2
  exit 1
fi
if compose_in "$RESTORE_REPO" exec -T backend test -e \
  /var/lib/teacher-assistant/integrations/m20-relocation-marker; then
  printf 'Integration credential fixture was copied into a clean restore.\n' >&2
  exit 1
fi

SOURCE_DATABASE_VOLUME=$(compose_in "$RENAMED_REPO" config --format json | sed -n '/"database-data"/,/}/s/.*"name": "\([^"]*\)".*/\1/p' | head -n 1)
RESTORE_DATABASE_VOLUME=$(compose_in "$RESTORE_REPO" config --format json | sed -n '/"database-data"/,/}/s/.*"name": "\([^"]*\)".*/\1/p' | head -n 1)
[[ "$SOURCE_DATABASE_VOLUME" != "$RESTORE_DATABASE_VOLUME" ]]
[[ "$(realpath "$RENAMED_REPO/data/course_content")" != "$(realpath "$RESTORE_REPO/data/course_content")" ]]
[[ "$(realpath "$RENAMED_REPO/data/mail_attachments")" != "$(realpath "$RESTORE_REPO/data/mail_attachments")" ]]
[[ "$(realpath "$RENAMED_REPO/data/document_projects")" != "$(realpath "$RESTORE_REPO/data/document_projects")" ]]

CORRUPT_BUNDLE="$RESTORE_REPO/corrupt-backup"
cp -a "$BUNDLE" "$CORRUPT_BUNDLE"
printf 'corrupt' >> "$CORRUPT_BUNDLE/course-content.tar.gz"
BEFORE_CORRUPT_TEST=$(database_fingerprint "$RESTORE_REPO")
if make -C "$RESTORE_REPO" restore BACKUP="$CORRUPT_BUNDLE" CONFIRM_RESTORE="$RESTORE_ID" >/dev/null 2>&1; then
  printf 'A corrupt archive was accepted unexpectedly.\n' >&2
  exit 1
fi
assert_equal "$BEFORE_CORRUPT_TEST" "$(database_fingerprint "$RESTORE_REPO")" 'Database after corrupt restore rejection'

CORRUPT_DOCUMENT_BUNDLE="$RESTORE_REPO/corrupt-document-backup"
cp -a "$BUNDLE" "$CORRUPT_DOCUMENT_BUNDLE"
printf 'corrupt' >> "$CORRUPT_DOCUMENT_BUNDLE/document-projects.tar.gz"
if make -C "$RESTORE_REPO" restore BACKUP="$CORRUPT_DOCUMENT_BUNDLE" CONFIRM_RESTORE="$RESTORE_ID" >/dev/null 2>&1; then
  printf 'A corrupt document archive was accepted unexpectedly.\n' >&2
  exit 1
fi

printf 'M14 relocation/restore drill passed for fixture IDs %s and %s.\n' "$SOURCE_ID" "$RESTORE_ID"

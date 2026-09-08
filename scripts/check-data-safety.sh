#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)

bash -n "$PROJECT_ROOT/scripts/data-safety.sh"
bash -n "$PROJECT_ROOT/scripts/data-backup.sh"
bash -n "$PROJECT_ROOT/scripts/data-restore.sh"

if awk '
  /^[[:space:]]*(docker compose|\$\(COMPOSE\)|\$\(COMPOSE[^)]*\)).*down[[:space:]].*-v/ {
    if ($0 !~ /TEST_COMPOSE|E2E_COMPOSE/) exit 1
  }
' "$PROJECT_ROOT/Makefile"; then
  :
else
  printf 'Unsafe normal-volume deletion found in Makefile.\n' >&2
  exit 1
fi

config_a=$(
  cd "$PROJECT_ROOT"
  COMPOSE_PROJECT_NAME=m14-fixture-a COURSE_DATA_DIR=./data/m14-a \
    MAIL_DATA_DIR=./data/m20-a DOCUMENT_DATA_DIR=./data/m21-a \
    docker compose -f compose.yml -f compose.dev.yml config --format json
)
config_b=$(
  cd "$PROJECT_ROOT"
  COMPOSE_PROJECT_NAME=m14-fixture-b COURSE_DATA_DIR=./data/m14-b \
    MAIL_DATA_DIR=./data/m20-b DOCUMENT_DATA_DIR=./data/m21-b \
    docker compose -f compose.yml -f compose.dev.yml config --format json
)

grep -Fq '"name": "m14-fixture-a"' <<< "$config_a"
grep -Fq '"name": "m14-fixture-b"' <<< "$config_b"
grep -Fq '"name": "m14-fixture-a_database-data"' <<< "$config_a"
grep -Fq '"name": "m14-fixture-b_database-data"' <<< "$config_b"
grep -Fq '/data/m14-a' <<< "$config_a"
grep -Fq '/data/m14-b' <<< "$config_b"
grep -Fq 'm14-fixture-a_integration-credential-data' <<< "$config_a"
grep -Fq 'm14-fixture-b_integration-credential-data' <<< "$config_b"
grep -Fq '/data/m20-a' <<< "$config_a"
grep -Fq '/data/m20-b' <<< "$config_b"
grep -Fq '/data/m21-a' <<< "$config_a"
grep -Fq '/data/m21-b' <<< "$config_b"
if grep -Fq 'm14-fixture-b_database-data' <<< "$config_a" ||
  grep -Fq 'm14-fixture-a_database-data' <<< "$config_b"; then
  printf 'Different installation IDs resolved to shared database storage.\n' >&2
  exit 1
fi

if grep -REn '(^|[^A-Z_])(docker compose|\$\(COMPOSE\)).*down[[:space:]]+-v' \
  "$PROJECT_ROOT/README.md" "$PROJECT_ROOT/scripts" \
  | grep -Ev 'check-data-safety\.sh|m14-relocation-drill\.sh|data-durability\.md|test|e2e|explicitly isolated'; then
  printf 'Normal documentation or scripts contain docker compose down -v.\n' >&2
  exit 1
fi

printf 'Data-safety shell and isolated Compose checks passed.\n'

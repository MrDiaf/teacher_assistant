COMPOSE := docker compose -f compose.yml -f compose.dev.yml
TEST_COMPOSE := docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml
E2E_COMPOSE := docker compose -p teacher-assistant-e2e -f compose.e2e.yml

.PHONY: dev down restart logs test e2e lint format migrate backup

dev:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

test:
	@set -e; \
	trap '$(TEST_COMPOSE) down -v --remove-orphans' EXIT; \
	$(TEST_COMPOSE) run --build --rm backend pytest -q; \
	$(TEST_COMPOSE) run --build --rm --no-deps frontend npm run test

e2e:
	@set -e; \
	trap '$(E2E_COMPOSE) down -v --remove-orphans' EXIT; \
	$(E2E_COMPOSE) run --build --rm e2e

lint:
	$(COMPOSE) run --build --rm --no-deps --entrypoint ruff backend check .
	$(COMPOSE) run --build --rm --no-deps frontend npm run lint
	@set -e; \
	status=0; \
	$(E2E_COMPOSE) run --build --rm --no-deps e2e npm run lint || status=$$?; \
	$(E2E_COMPOSE) down -v --remove-orphans; \
	exit $$status

format:
	$(COMPOSE) run --build --rm --no-deps --entrypoint ruff backend format .
	$(COMPOSE) run --build --rm --no-deps frontend npm run format
	@set -e; \
	status=0; \
	$(E2E_COMPOSE) run --build --rm --no-deps e2e ./node_modules/.bin/prettier --write /source || status=$$?; \
	$(E2E_COMPOSE) down -v --remove-orphans; \
	exit $$status

migrate:
	$(COMPOSE) run --build --rm --entrypoint alembic backend upgrade head

backup:
	@set -eu; \
	mkdir -p backups; \
	chmod 700 backups; \
	backup_tmp=$$(mktemp backups/.teacher-assistant.XXXXXX); \
	trap 'rm -f "$$backup_tmp"' 0 1 2 15; \
	$(COMPOSE) exec -T database sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > "$$backup_tmp"; \
	chmod 600 "$$backup_tmp"; \
	mv "$$backup_tmp" backups/teacher-assistant.dump; \
	trap - 0 1 2 15; \
	echo "Backup written to backups/teacher-assistant.dump"

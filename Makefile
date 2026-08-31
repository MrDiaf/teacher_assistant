COMPOSE := docker compose -f compose.yml -f compose.dev.yml
TEST_COMPOSE := docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml
E2E_COMPOSE := docker compose -p teacher-assistant-e2e -f compose.e2e.yml

.PHONY: dev down restart logs test e2e lint format migrate backup restore \
	data-preflight data-init data-adopt data-guard data-record-started \
	data-safety-test data-relocation-test

data-preflight:
	@./scripts/data-safety.sh preflight

data-init:
	@./scripts/data-safety.sh init

data-adopt:
	@./scripts/data-safety.sh adopt

data-guard:
	@./scripts/data-safety.sh prepare

data-record-started:
	@./scripts/data-safety.sh record-started

dev: data-guard
	$(COMPOSE) up --build -d
	@$(MAKE) --no-print-directory data-record-started

down:
	$(COMPOSE) down

restart: data-guard
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

test:
	@set -e; \
	trap '$(TEST_COMPOSE) down -v --remove-orphans' EXIT; \
	$(TEST_COMPOSE) run --build --rm backend pytest -q; \
	$(TEST_COMPOSE) run --build --rm --no-deps frontend npm run test; \
	./scripts/check-data-safety.sh

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

migrate: data-guard
	$(COMPOSE) run --build --rm --entrypoint alembic backend upgrade head

backup: data-guard
	@./scripts/data-backup.sh

restore: data-guard
	@./scripts/data-restore.sh

data-safety-test:
	@./scripts/check-data-safety.sh

data-relocation-test:
	@./scripts/m14-relocation-drill.sh

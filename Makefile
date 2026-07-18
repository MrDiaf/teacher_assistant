COMPOSE := docker compose -f compose.yml -f compose.dev.yml
TEST_COMPOSE := docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml

.PHONY: dev down restart logs test lint format migrate

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

lint:
	$(COMPOSE) run --build --rm --no-deps --entrypoint ruff backend check .
	$(COMPOSE) run --build --rm --no-deps frontend npm run lint

format:
	$(COMPOSE) run --build --rm --no-deps --entrypoint ruff backend format .
	$(COMPOSE) run --build --rm --no-deps frontend npm run format

migrate:
	$(COMPOSE) run --build --rm --entrypoint alembic backend upgrade head

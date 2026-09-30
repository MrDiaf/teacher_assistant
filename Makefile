COMPOSE := docker compose -f compose.yml -f compose.dev.yml
TEST_COMPOSE := docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml
E2E_COMPOSE := docker compose -p teacher-assistant-e2e -f compose.e2e.yml
SUPPORTED_MODULE_HOSTS := calendar courses documents
MODULE_BACKEND_PORT ?= 18000
MODULE_FRONTEND_PORT ?= 15173
MODULE_COMPOSE = MODULE_HOST=$(MODULE) BACKEND_PORT=$(MODULE_BACKEND_PORT) \
	FRONTEND_PORT=$(MODULE_FRONTEND_PORT) docker compose \
	-p teacher-assistant-module-$(MODULE) --profile module-host \
	-f compose.yml -f compose.dev.yml -f compose.module.yml
MODULE_TEST_COMPOSE = MODULE_HOST=$(MODULE) docker compose \
	-p teacher-assistant-module-$(MODULE)-test --profile module-host \
	-f compose.yml -f compose.module.yml -f compose.test.yml \
	-f compose.module.test.yml
MODULE_E2E_COMPOSE = MODULE_HOST=$(MODULE) docker compose \
	-p teacher-assistant-module-$(MODULE)-e2e \
	-f compose.e2e.yml -f compose.module.e2e.yml \
	$(if $(wildcard compose.module.e2e.$(MODULE).yml),-f compose.module.e2e.$(MODULE).yml,)
MODULE_BACKEND_TESTS_calendar := tests/test_module_host.py tests/test_module_registration.py tests/calendar tests/courses/test_course_calendars.py tests/test_assistant_api.py
MODULE_BACKEND_TESTS_courses := tests/test_module_host.py tests/test_module_registration.py tests/courses tests/test_assistant_api.py tests/test_data_archive.py
MODULE_BACKEND_TESTS_documents := tests/test_module_host.py tests/test_module_registration.py tests/documents
MODULE_FRONTEND_TESTS_calendar := src/platform/modules/moduleHost.test.tsx src/platform/modules/contract.test.ts src/features/calendar src/features/courses/CourseCalendar.test.tsx
MODULE_FRONTEND_TESTS_courses := src/platform/modules/moduleHost.test.tsx src/platform/modules/contract.test.ts src/features/courses
MODULE_FRONTEND_TESTS_documents := src/platform/modules/moduleHost.test.tsx src/platform/modules/contract.test.ts src/features/documents
MODULE_E2E_TEST_calendar := tests/calendar.spec.ts
MODULE_E2E_TEST_courses := tests/courses.spec.ts
MODULE_E2E_TEST_documents := tests/documents.spec.ts
require-supported-module = \
	$(if $(filter 1,$(words $(strip $(MODULE)))),,$(error MODULE must name exactly one supported module: $(SUPPORTED_MODULE_HOSTS))) \
	$(if $(filter $(SUPPORTED_MODULE_HOSTS),$(strip $(MODULE))),,$(error Unsupported MODULE '$(MODULE)'; supported modules: $(SUPPORTED_MODULE_HOSTS)))

.PHONY: dev down restart logs test e2e lint format migrate backup restore check-boundaries \
	check-module-contract dev-module down-module logs-module test-module \
	data-preflight data-init data-adopt data-guard data-record-started \
	data-safety-test data-relocation-test

check-boundaries:
	$(COMPOSE) run --build --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint python backend /workspace/scripts/check-backend-boundaries.py --repo /workspace
	$(COMPOSE) run --build --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint node frontend /workspace/scripts/check-frontend-boundaries.mjs --repo /workspace
	@set -e; \
	if $(COMPOSE) run --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint python backend /workspace/scripts/check-backend-boundaries.py \
		--repo /workspace --source-root architecture/fixtures/backend \
		--allow-stale-exceptions >/dev/null 2>&1; then \
		echo "Backend invalid boundary fixture was not rejected."; exit 1; \
	else echo "Backend invalid boundary fixture rejected."; fi
	@set -e; \
	if $(COMPOSE) run --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint node frontend /workspace/scripts/check-frontend-boundaries.mjs \
		--repo /workspace --source-root architecture/fixtures/frontend/src \
		--allow-stale-exceptions >/dev/null 2>&1; then \
		echo "Frontend invalid boundary fixture was not rejected."; exit 1; \
	else echo "Frontend invalid boundary fixture rejected."; fi
	@set -e; \
	if $(COMPOSE) run --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint python backend /workspace/scripts/check-backend-boundaries.py \
		--repo /workspace --source-root architecture/fixtures/backend-platform \
		--allow-stale-exceptions >/dev/null 2>&1; then \
		echo "Backend unapproved Platform-import fixture was not rejected."; exit 1; \
	else echo "Backend unapproved Platform-import fixture rejected."; fi
	@set -e; \
	if $(COMPOSE) run --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint node frontend /workspace/scripts/check-frontend-boundaries.mjs \
		--repo /workspace --source-root architecture/fixtures/frontend-platform/src \
		--allow-stale-exceptions >/dev/null 2>&1; then \
		echo "Frontend unapproved Platform-import fixture was not rejected."; exit 1; \
	else echo "Frontend unapproved Platform-import fixture rejected."; fi

check-module-contract:
	$(COMPOSE) run --build --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint python backend /workspace/scripts/check-module-contract.py --repo /workspace
	@set -e; \
	if $(COMPOSE) run --rm --no-deps -v "$(CURDIR):/workspace:ro" \
		--entrypoint python backend /workspace/scripts/check-module-contract.py \
		--repo /workspace --simulate-frontend-drift >/dev/null 2>&1; then \
		echo "Frontend/backend identity drift was not rejected."; exit 1; \
	else echo "Frontend/backend identity drift rejected."; fi

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

dev-module:
	$(require-supported-module)
	$(MODULE_COMPOSE) up --build -d
	@printf '%s module host: http://localhost:%s (API %s)\n' \
		"$(MODULE)" "$(MODULE_FRONTEND_PORT)" "$(MODULE_BACKEND_PORT)"

down-module:
	$(require-supported-module)
	$(MODULE_COMPOSE) down

logs-module:
	$(require-supported-module)
	$(MODULE_COMPOSE) logs -f

down:
	$(COMPOSE) down

restart: data-guard
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

test: check-boundaries check-module-contract
	@set -e; \
	trap '$(TEST_COMPOSE) down -v --remove-orphans' EXIT; \
	$(TEST_COMPOSE) run --build --rm backend pytest -q; \
	$(TEST_COMPOSE) run --build --rm --no-deps frontend npm run test; \
	./scripts/check-data-safety.sh

test-module:
	$(require-supported-module)
	@set -e; \
	trap '$(MODULE_TEST_COMPOSE) down -v --remove-orphans; $(MODULE_E2E_COMPOSE) down -v --remove-orphans' EXIT; \
	$(MODULE_TEST_COMPOSE) run --build --rm backend pytest \
		-q $(MODULE_BACKEND_TESTS_$(MODULE)); \
	$(MODULE_TEST_COMPOSE) run --build --rm --no-deps frontend npm run test -- \
		$(MODULE_FRONTEND_TESTS_$(MODULE)); \
	$(MODULE_E2E_COMPOSE) run --build --rm e2e npm test -- \
		$(MODULE_E2E_TEST_$(MODULE))

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

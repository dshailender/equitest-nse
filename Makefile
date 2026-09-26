SHELL := /bin/bash

# Ensure local vendored tools and user Node are present in PATH
PATH := $(CURDIR)/bin:$(HOME)/.nvm/versions/node/v24.21.0/bin:$(HOME)/.local/bin:$(PATH)
export PATH

NODE_PATH := $(CURDIR)/frontend/node_modules
export NODE_PATH

DATA_SOURCE ?= CSV
export DATA_SOURCE

VENV := $(CURDIR)/backend/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black
NPM := npm
NPX := npx

.PHONY: all help install openapi dev run-local test test-backend test-frontend test-e2e lint clean services-up services-down services-status services-verify services-test services-build

help:
	@echo "EquiTest NSE - Quantitative Backtesting Monorepo"
	@echo ""
	@echo "Available commands:"
	@echo "  make run-local        Start backend on :8000 and frontend on :3000 (or run ./run-local)"
	@echo "  make dev              Alias for make run-local"
	@echo "  make services-up      Spin up PostgreSQL, RabbitMQ, and 6 Spring Boot microservices"
	@echo "  make services-down    Stop all microservice containers"
	@echo "  make services-status  Display health and status of microservices & infrastructure"
	@echo "  make services-verify  Run automated acceptance verification across microservices"
	@echo "  make services-test    Run Maven unit tests across all microservice modules"
	@echo "  make services-build   Package all microservice JARs"
	@echo "  make install          Install Python venv & backend dependencies, frontend npm packages"
	@echo "  make openapi          Generate OpenAPI JSON and TypeScript schema definitions"
	@echo "  make lint             Run backend ruff/black checks and frontend eslint/tsc"
	@echo "  make test             Run all test suites (backend, frontend, e2e)"
	@echo "  make test-backend     Run backend pytest with >=80% coverage check"
	@echo "  make test-frontend    Run frontend Vitest component tests with MSW"
	@echo "  make test-e2e         Run Playwright E2E integration test"
	@echo "  make clean            Clean temporary build, test, and cache files"

services-up:
	@./run-local-services up

services-down:
	@./run-local-services down

services-status:
	@./run-local-services status

services-verify:
	@./run-local-services verify

services-test:
	@./mvnw test

services-build:
	@./mvnw clean package -DskipTests

install:
	@echo "==> Setting up backend Python virtual environment..."
	@python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -e "./backend[dev]"
	@echo "==> Setting up frontend npm packages..."
	@cd frontend && $(NPM) install
	@ln -sfn frontend/node_modules node_modules
	@$(MAKE) openapi

openapi:
	@echo "==> Exporting backend OpenAPI schema..."
	@$(PYTHON) backend/app/main.py --export-openapi frontend/openapi.json
	@echo "==> Generating TypeScript schema types from OpenAPI..."
	@cd frontend && $(NPX) openapi-typescript ./openapi.json -o ./lib/schema.d.ts
	@echo "==> OpenAPI and TypeScript definitions up to date."

run-local:
	@./run-local

dev: run-local

lint:
	@echo "==> Linting backend with Ruff..."
	@$(RUFF) check backend
	@echo "==> Checking backend formatting with Black..."
	@$(BLACK) --check backend
	@echo "==> Linting & typechecking frontend (ESLint + TypeScript strict)..."
	@cd frontend && $(NPM) run lint

test-backend:
	@echo "==> Running backend unit tests with coverage gate..."
	@$(PYTEST) backend/tests

test-frontend:
	@echo "==> Running frontend Vitest unit/component tests..."
	@cd frontend && $(NPM) run test

test-e2e:
	@echo "==> Running Playwright E2E tests..."
	@bash -c '\
		export no_proxy=127.0.0.1,localhost,::1; \
		export NO_PROXY=127.0.0.1,localhost,::1; \
		echo "Checking if services are already running..."; \
		BACKEND_STARTED=0; \
		FRONTEND_STARTED=0; \
		if ! curl -s --noproxy "*" http://127.0.0.1:8000/health | grep -q "\"status\""; then \
			echo "Starting background backend service on :8000..."; \
			$(VENV)/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 > /tmp/equitest_backend_e2e.log 2>&1 & \
			BACKEND_PID=$$!; \
			BACKEND_STARTED=1; \
			for i in $$(seq 1 40); do \
				if curl -s --noproxy "*" http://127.0.0.1:8000/health | grep -q "\"status\""; then break; fi; \
				sleep 0.5; \
			done; \
		fi; \
		if ! curl -s --noproxy "*" http://127.0.0.1:3000 | grep -qi "html"; then \
			echo "Starting background frontend service on :3000..."; \
			(cd frontend && $(NPM) run dev) > /tmp/equitest_frontend_e2e.log 2>&1 & \
			FRONTEND_PID=$$!; \
			FRONTEND_STARTED=1; \
			for i in $$(seq 1 60); do \
				if curl -s --noproxy "*" http://127.0.0.1:3000 | grep -qi "html"; then break; fi; \
				sleep 0.5; \
			done; \
		fi; \
		echo "Services are ready. Executing Playwright..."; \
		(cd frontend && $(NPX) playwright test); \
		TEST_EXIT=$$?; \
		if [ $$BACKEND_STARTED -eq 1 ]; then \
			echo "Stopping background backend..."; \
			kill $$BACKEND_PID 2>/dev/null || true; \
			pkill -P $$BACKEND_PID 2>/dev/null || true; \
		fi; \
		if [ $$FRONTEND_STARTED -eq 1 ]; then \
			echo "Stopping background frontend..."; \
			kill $$FRONTEND_PID 2>/dev/null || true; \
			pkill -P $$FRONTEND_PID 2>/dev/null || true; \
		fi; \
		exit $$TEST_EXIT'

test: test-backend test-frontend test-e2e
	@echo "==> All test suites passed successfully!"

clean:
	@rm -rf backend/.venv frontend/node_modules frontend/.next .pytest_cache .coverage htmlcov test-results playwright-report
	@find . -type d -name "__pycache__" -exec rm -rf {} +

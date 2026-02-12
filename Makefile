SHELL := /bin/bash

.PHONY: dev dev-down compliance compliance-down prod prod-down \
       logs logs-dev logs-prod logs-compliance \
       test lint test-load

dev:
	docker compose up -d

dev-down:
	docker compose down

compliance:
	docker compose -f docker/compliance-compose.yml up -d

compliance-down:
	docker compose -f docker/compliance-compose.yml down

prod:
	docker compose -f docker/docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker/docker-compose.prod.yml down

# Logging targets
# Usage:
#   make logs-dev          - tail logs for the default dev stack
#   make logs-prod         - tail logs for the prod stack
#   make logs-compliance   - tail logs for the compliance stack
#   make logs              - tail logs using COMPOSE_FILE env var (defaults to dev)
#     Example: COMPOSE_FILE=docker/docker-compose.prod.yml make logs
logs:
	docker compose $(if $(COMPOSE_FILE),-f $(COMPOSE_FILE)) logs -f --tail=200

logs-dev:
	docker compose logs -f --tail=200

logs-prod:
	docker compose -f docker/docker-compose.prod.yml logs -f --tail=200

logs-compliance:
	docker compose -f docker/compliance-compose.yml logs -f --tail=200

# Testing & Quality
test:
	pytest -m "not integration" --tb=short -q

lint:
	flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics

test-load:
	./tests/load/run_benchmark.sh ci

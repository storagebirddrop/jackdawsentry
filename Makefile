SHELL := /bin/bash

.PHONY: dev dev-down compliance compliance-down prod prod-down logs

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

logs:
	docker compose logs -f --tail=200

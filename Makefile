.PHONY: help up down logs ps migrate makemigrations openapi lint-py test-py lint-js typecheck build-web

help:
	@echo "RoomSync Developer Commands:"
	@echo "  make up            - Build & start Postgres, Redis, MinIO, Django, FastAPI, Celery"
	@echo "  make down          - Stop Compose stack"
	@echo "  make migrate       - Run Django database migrations"
	@echo "  make openapi       - Validate & export OpenAPI YAML + regenerate TS contracts"
	@echo "  make test-py       - Run Django and FastAPI test suites"
	@echo "  make lint-py       - Run Ruff and mypy on backend & matching services"
	@echo "  make lint-js       - Run ESLint across JS/TS workspace"
	@echo "  make typecheck     - Run TypeScript typechecks across JS/TS workspace"
	@echo "  make build-web     - Build Vite React Web app"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	cd services/backend && uv run python manage.py migrate

makemigrations:
	cd services/backend && uv run python manage.py makemigrations

openapi:
	cd services/backend && uv run python manage.py spectacular --file openapi.yaml --validate
	pnpm contracts:generate

lint-py:
	cd services/backend && uv run ruff check . && uv run mypy .
	cd services/matching && uv run ruff check . && uv run mypy .

test-py:
	cd services/backend && uv run pytest
	cd services/matching && uv run pytest

lint-js:
	pnpm lint

typecheck:
	pnpm typecheck

build-web:
	pnpm build:web

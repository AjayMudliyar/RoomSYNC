# RoomSync

**Find your people before finding your place.**  
RoomSync is a compatibility-first roommate discovery platform for students, interns, and young professionals in India (`Bengaluru`, `Pune`, `Mumbai`, `Hyderabad`, `Delhi-NCR`).

## Architecture Overview

- **`apps/web`** — React 19 + TypeScript + Vite + Tailwind CSS + React Router + TanStack Query
- **`apps/android`** — React Native + Expo SDK 54 + Expo Router + TypeScript + SecureStore
- **`services/backend`** — Python 3.12 + Django 5.2 + Django REST Framework + `drf-spectacular` + Celery (sole owner of PostgreSQL domain data and public `/api/v1/` API)
- **`services/matching`** — Python 3.12 + FastAPI + Pydantic v2 private stateless compatibility engine (`/internal/v1/compatibility/score`, zero PostgreSQL access)
- **`packages/design-tokens`** — Canonical WCAG 2.1 AA *Warm Tech Harmony* design tokens (Tailwind CSS + React Native adapters)
- **`packages/contracts`** — OpenAPI-generated TypeScript contracts & Zod helpers
- **`packages/api-client`** — Shared typed API client (Web HttpOnly cookie+CSRF & Android Bearer+rotating refresh)
- **`packages/config`** — Shared ESLint, Prettier, and strict TypeScript configuration
- **`infrastructure/`** — Dockerfiles, MinIO bucket init, and developer helper scripts
- **`Docs/`** — Authoritative PRD, TDD, ADRs, API conventions, questionnaire proposal, screen inventory, and milestone plan
- **`Docs/Design/`** — Preserved Google Stitch visual reference exports

## Quick Start (Local Development)

1. Copy environment template and verify placeholders:
   ```bash
   cp .env.example .env
   ```
2. Start containerized backing services & Python services:
   ```bash
   docker compose up -d
   docker compose exec backend uv run python manage.py migrate
   ```
3. Install JS/TS workspace dependencies and run Web dev server:
   ```bash
   pnpm install
   pnpm dev:web
   ```
4. Launch Android Expo client:
   ```bash
   pnpm dev:android
   ```

## Quality Checks

- **Python Backend & Matching:** `uv run ruff check . && uv run mypy . && uv run pytest` (inside each service)
- **TypeScript Monorepo:** `pnpm lint && pnpm typecheck && pnpm build:web`
- **OpenAPI Schema:** `uv run python manage.py spectacular --file openapi.yaml --validate` (inside `services/backend`)

# ADR-001: Platform Architecture, Monorepo Boundaries, MVP Scope & Operations

- **Status:** Accepted (`DEC-01`, `DEC-04`, `DEC-08`, `DEC-09`, `DEC-10`, `OD-U3`, `OD-U4`, `OD-U5`)
- **Date:** 11 November 2026
- **Deciders:** Engineering Lead / Product Owner & System Architect
- **Supersedes / Reconciles:** Conflicting stack/boundary passages between `Docs/product/PRD.md` (§4.3, §12.1), `ROOMSYNC_ENGINEERING_HANDOFF.md` (§7), and `Docs/engineering/TDD.md` (§2.1–2.2, §4.1, §11.2). *(Preserves originals untouched; see [OPEN_DECISIONS.md](../engineering/OPEN_DECISIONS.md) §3.)*

---

## 1. Context

Across the initial handoff documents, three structural ambiguities needed resolution before creating the codebase:
1. **Stack vs. Monorepo Layout:** `PRD.md` §12.1 proposed `Next.js + Prisma + Supabase`, `PRD.md` §4.3 marked Android post-MVP, and `TDD.md` §4.1 placed `backend/` and `matching-service/` under `apps/` whereas `ROOMSYNC_ENGINEERING_HANDOFF.md` §7 separated `apps/` (clients) from `services/` (backends).
2. **Service Authority:** `TDD.md` §2.1–2.2 depicted an arrow from `FastAPI --> PostgreSQL`, contradicting `TDD.md` §9.7 (*"No database writes from FastAPI in MVP"*).
3. **MVP Boundary & Early Operations:** The Stitch export suite contains 85 screens spanning post-MVP features (Pods/Groups, Deposit Escrow, Rental Agreements, Splitwise, AI Simulator, 7 custom Admin screens) alongside P0/P1 flows, and the host machine currently has Python `3.14.5` + Node `v24.16.0` + Docker `29.5.3` without `uv` or `pnpm`.

---

## 2. Decision

### 2.1 Monorepo Structure (`DEC-01`)
Adopt a single monorepo organized into clear client, backend service, shared package, and infrastructure boundaries while preserving existing `Docs/`, `Docs/Design/`, and `ROOMSYNC_ENGINEERING_HANDOFF.md`:

```text
RoomSYNC/
├── apps/
│   ├── web/                 # React + TypeScript + Vite (SPA, React Router, TanStack Query)
│   └── android/             # React Native + Expo + TypeScript (Expo Router)
├── services/
│   ├── backend/             # Python 3.12 + Django + DRF modular monolith (Celery worker & beat)
│   └── matching/            # Python 3.12 + FastAPI internal stateless compute service
├── packages/
│   ├── design-tokens/       # Canonical Warm Tech Harmony JSON/TS tokens + Tailwind & RN adapters
│   ├── contracts/           # OpenAPI-derived TypeScript types & Zod schemas
│   ├── api-client/          # Shared HTTP transport (Web cookie+CSRF & Android Bearer+Refresh)
│   └── config/              # Shared ESLint, Prettier, and strict tsconfig baselines
├── infrastructure/
│   ├── docker/              # Containerfiles, MinIO init, CI support configs
│   ├── nginx/               # Same-parent-domain reverse proxy configs (when self-hosted)
│   └── scripts/             # Seed, OpenAPI export, and maintenance helpers
├── Docs/                    # Canonical product (`Docs/product/`), engineering (`Docs/engineering/`), ADRs, and design (`Docs/Design/`) documentation
├── Agents.md
└── ROOMSYNC_ENGINEERING_HANDOFF.md
```

### 2.2 Strict Backend Authority & Isolation (`DEC-01`)
- **Django + DRF (`services/backend/`) is the sole authority** for all domain models, public `/api/v1/` endpoints, authentication/authorization, rate limiting, business workflows, Celery orchestration, and PostgreSQL schema migrations.
- **FastAPI (`services/matching/`) is strictly private and stateless in MVP:**
  - Exposed only on internal Docker/private service networks (`/internal/v1/*`); never called directly by Web or Android.
  - Authenticates incoming requests from Django via internal service-token authentication (`X-Internal-Service-Token`).
  - Has **zero PostgreSQL driver/ORM access and must perform zero database writes**. Django fetches eligible user preference payloads, calls FastAPI over HTTP with a strict timeout, and persists `CompatibilitySnapshot` in PostgreSQL.
- **PostgreSQL** is the single system of record; **Redis** handles ephemeral caching, throttling counters, and Celery task brokering; **MinIO** provides local S3-compatible object storage with isolated `roomsync-public` and `roomsync-private` buckets (production S3 provider/region TBD via `OD-U7`).

### 2.3 Phased MVP Scope, Navigation & Onboarding (`DEC-04`, `OD-U3`, `OD-U4`, `OD-U5`)
Build and validate the core P0 loop before expanding marketplace or social modules:
1. **Core P0 Loop:** Register → Profile Setup → Housing Preferences → Lifestyle Questionnaire → Roommate Discovery → Compatibility Breakdown → Connection Requests → One-to-One Messaging.
2. **MVP P1 Follow-up (`OD-U5`):** Milestone 8 includes basic Accommodation Listings Search, Enquiries (`enquiry != booking`), Saved Listings, **`Create / Edit Accommodation Listing`** (`FR-047`, `FR-048`, **gated on approving a new Warm Tech Harmony design prior to implementation**), Verification Metadata (private bucket), Notifications, and Hardened Django Admin Moderation. **Defer side-by-side roommate comparison (`FR-041`) to P1.**
3. **Explicitly Deferred (Post-MVP):** Roommate Groups / Pods (`FR-053`–`060`), Compatibility Simulator (`FR-061`–`066`), AI Roommate Assistant (`FR-067`–`073`), Agreements / Shared Expenses / Splitwise / Tasks (`FR-090`–`095`), City/College Communities (`FR-096`–`100`), Reviews (`FR-108`–`112`), Payments/Subscriptions/Escrow (`FR-118`–`122`), and trained ML ranking.
4. **Canonical MVP Navigation (`OD-U3`):**
   - **Web:** Top navigation = `Discover`, `Requests`, `Messages`, `Stays` *(enabled in M8)*, with `Notifications` and `Profile / Trust / Settings` in the account menu.
   - **Android:** 5-tab bottom bar = `Discover`, `Requests`, `Chat`, `Stays` *(M8)*, `Profile` *(contains Trust & Safety + Settings)*.
   - `Groups` and `Community` remain excluded in MVP.
5. **Canonical Onboarding Progression (`OD-U4`):**
   - Standardize on **4 active steps** identically on Web and Android: `1. Basic Profile` → `2. Housing Preferences` → `3. Lifestyle Questionnaire` → `4. Review & Submit` *(followed by completion redirect to Discovery)*.

### 2.4 Messaging Delivery (`DEC-08`)
- Implement **REST APIs + smart cursor polling** (`GET /api/v1/conversations/{id}/messages?after_cursor=...`) for Milestone 6/7/9.
- Defer Django Channels / WebSockets until real pilot traffic demonstrates polling latency or server load bottlenecks. Because REST + PostgreSQL already own canonical state, adding WebSockets later as a delivery notification fanout stays additive.

### 2.5 Admin & Moderation UI (`DEC-09`)
- Use **hardened Django Admin** (staff MFA before production, custom moderation/verification action views, mandatory reason codes, append-only `AdminAuditLog`, and private signed-URL evidence viewer) for the initial pilot.
- Defer building a 7-screen custom React admin portal until operational scale exceeds Django Admin ergonomics.

### 2.6 Standardized Developer Environment (`DEC-10`)
- Standardize Python services (`services/backend/`, `services/matching/`) on **Python 3.12** managed independently via **`uv`** (separate `pyproject.toml` and `uv.lock`; no shared Python runtime imports between Django and FastAPI).
- Standardize JS/TS workspace (`apps/*`, `packages/*`) on a compatible **Node LTS** release (Node `v22`/`v24` LTS compatible with Expo SDK) and **`pnpm`** workspaces.
- Containerize PostgreSQL, Redis, MinIO, Django, FastAPI, and Celery via **Docker Compose**, verified on host prior to feature coding (resolves host Python `3.14.5` wheel fragility cleanly).

---

## 3. Consequences

- **Positive:** Zero split-brain writes; fast solo/small-team velocity; full contract sharing across Web and Android without forcing web primitives into React Native; zero pre-launch blockers on WebSockets, custom admin UIs, or payment/legal compliance modules.
- **Trade-offs:** Maintaining two backend frameworks (`Django` + `FastAPI`) and two client apps (`React` + `Expo`) increases build/CI surface, mitigated by keeping FastAPI strictly limited to pure scoring and generating TypeScript contracts automatically from OpenAPI (`drf-spectacular`).
- **Required Follow-Up:** Apply corresponding doc sync edits to `Docs/product/PRD.md` and `Docs/engineering/TDD.md` in `v1.1` once `OD-U1`–`OD-U8` are signed off (`Docs/engineering/OPEN_DECISIONS.md` §3).


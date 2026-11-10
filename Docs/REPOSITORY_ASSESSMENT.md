# RoomSync — Repository Assessment

> [!NOTE]
> **Historical Phase 0 Baseline Snapshot (Pre-Reconciliation & Pre-Subfolder Move):** Recorded prior to reconciling `DEC-01`–`DEC-10` / `OD-U1`–`OD-U8` and reorganizing `PRD.md`, `TDD.md`, `OPEN_DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, and `Design/` into `Docs/product/`, `Docs/engineering/`, and `Docs/Design/`. For current reconciled governance, links, and active plan, see [`Docs/engineering/OPEN_DECISIONS.md`](./engineering/OPEN_DECISIONS.md), [`Docs/engineering/IMPLEMENTATION_PLAN.md`](./engineering/IMPLEMENTATION_PLAN.md), and [`Docs/ADR/README.md`](./ADR/README.md).

**Date:** 11 November 2026  
**Workspace Root:** `C:\Users\Ajay Mudliyar\OneDrive\Desktop\RoomSYNC`  
**Phase:** Phase 0 — Repository Reconnaissance  
**Status:** Baseline assessment ready for review (no application code written; existing files untouched)

---

## 1. Executive Summary

RoomSync is currently a **greenfield documentation and UI design repository**. No application source code, package manifests, database migrations, container definitions, or CI pipelines exist yet. However, the workspace contains a thorough foundational document set (`ROOMSYNC_ENGINEERING_HANDOFF.md` and 6 files under `Docs/`) alongside **85 exported Google Stitch UI screens** and 3 design-token specifications under `Design/stitch_roomsync_roommate_discovery_platform/`.

Reconnaissance surfaced **4 critical categories of findings** that must be reconciled before application code generation begins:

1. **No Git repository or workspace tooling initialized yet**, and several TDD-specified developer tools (`pnpm`, `uv`/`poetry`, `psql`, `java`, `adb`) are not installed on the local machine; additionally, local Python is `3.14.5` (bleeding-edge wheel compatibility risk for Django/FastAPI/Celery/psycopg).
2. **Material conflicts between `PRD.md`, `TDD.md`, design docs, and Stitch exports** across stack choice, compatibility weights/dimensions, design token hex values, navigation architecture, onboarding step counts, and MVP vs. post-MVP scope boundaries.
3. **Missing design assets and specs**, including 11 missing `screen.png` renders, a missing owner/tenant property-listing creation flow, missing Stitch audit report file, uncatalogued screen inventory paths, and missing `API_CONVENTIONS.md` / `ADR/` docs.
4. **Policy and scope violations embedded inside Stitch HTML mocks**, including hardcoded Bengaluru locations, unimplemented UIDAI/DigiLocker/Kaveri/Corporate SSO verification badges, and post-MVP features (Pods/Groups, Deposit Escrow, Rental Agreement drafts, Splitwise/UPI settling) mixed into primary screens.

---

## 2. Existing Files, Dependencies, Frameworks & Runtime Environment

### 2.1 Workspace Inventory

| Path | Type | Size / Count | Notes |
|---|---|---|---|
| `ROOMSYNC_ENGINEERING_HANDOFF.md` | File | 277 lines (14,448 B) | Authoritative engineering handoff and Phase 0 instructions |
| `Docs/PRD.md` | File | 2,320 lines (65,153 B) | Product Requirements Document v1.0 (18 modules, FR-001–FR-128) |
| `Docs/TDD.md` | File | 2,049 lines (80,185 B) | Technical Design Document v1.0 (architecture, DB schema, APIs, matching) |
| `Docs/DESIGN_SYSTEM.md` | File | 98 lines (5,317 B) | Curated "Warm Tech Harmony" baseline & governance rules |
| `Docs/DESIGN_AUDIT.md` | File | 54 lines (3,176 B) | Provisional Stitch audit checklist & release gate |
| `Docs/SCREEN_INVENTORY.md` | File | 46 lines (3,930 B) | Module-level inventory (22 entries, all `Export reference pending`) |
| `Docs/USER_FLOWS.md` | File | 105 lines (6,107 B) | End-to-end user journeys & MVP loop priority |
| `Design/stitch_roomsync_roommate_discovery_platform/` | Directory | 86 subdirs + 2 root `.md` files | 85 exported UI screen folders + 3 design spec `.md` files (`warm_tech_harmony/DESIGN.md`, `roomsync_consolidated_design_system_tokens.md`, `roomsync_engineering_handoff_dossier_tokens_spec.md`) |

**Application code & infrastructure status:**
- `apps/`, `services/`, `packages/`, `infrastructure/`, `infra/` — **Absent**
- `package.json`, `pnpm-workspace.yaml`, `pyproject.toml`, `requirements.txt` — **Absent**
- `docker-compose.yml`, `Dockerfile`, `.env.example`, `.gitignore`, `README.md`, `Makefile`, `.github/workflows/` — **Absent**

### 2.2 Git & Version Control Status

- `git status` returned `fatal: not a git repository (or any of the parent directories): .git`.
- Note on filesystem casing & sync:
  - Existing folders are capitalized (`Docs/`, `Design/`), while `TDD.md` and `ROOMSYNC_ENGINEERING_HANDOFF.md` reference lowercase (`docs/`, `design/`). Windows NTFS is case-insensitive, but CI/Docker (Linux) is case-sensitive. We must keep paths consistent in documentation and scripts without breaking existing files.
  - `Docs/PRD.md` and `Docs/TDD.md` carry Windows `Archive, ReparsePoint` attributes (OneDrive Files On-Demand), though both are readable locally. Care should be taken in `.gitignore` and Docker volume binds when working inside OneDrive-synced directories (`node_modules`, `.venv`, Docker DB volumes should never sync via OneDrive or should be carefully excluded/stored appropriately).

### 2.3 Local Runtime & Tooling Audit

| Tool / Runtime | Status | Version / Path | Assessment |
|---|---|---|---|
| Git | Installed | `2.54.0.windows.1` (`C:\Program Files\Git\cmd\git.exe`) | Ready; repo not yet initialized |
| Python | Installed | `3.14.5` (`C:\Python314\python.exe`) | **Risk:** Python 3.14 is cutting-edge; verify prebuilt wheels for Django, DRF, `psycopg`, Celery, Pydantic, FastAPI, or target Python `3.12`/`3.13` in Docker and local `.venv` |
| pip | Installed | `26.1.1` | Available |
| `uv` / `poetry` | **Not installed** | — | Recommended by `TDD.md` §4.1; install `uv` or standardize on `venv` + `pip`/`uv` + Docker |
| Node.js | Installed | `v24.16.0` (`C:\Program Files\nodejs\node.exe`) | Ready (note LTS compatibility checks for React Native / Expo tooling on Node 24) |
| npm | Installed | `11.13.0` | Available |
| `pnpm` / `yarn` | **Not installed** | — | `TDD.md` §4.1 specifies `pnpm` workspaces; enable via `corepack enable` or `npm install -g pnpm` |
| Docker | Installed | `29.5.3` (`docker.exe`) | `docker compose` failed in sandbox (`Access is denied` reading user `.docker/config.json` and `unknown command: docker compose`); verify Docker Desktop & Compose v2 on host shell |
| `psql` | **Not installed** | — | PostgreSQL client missing locally; use Dockerized PostgreSQL (`docker compose exec db psql ...`) |
| `java` / `adb` | **Not installed** | — | Android SDK / JDK missing locally; required later for Android emulator/APK builds (Phase 5 / Milestone 9); EAS Cloud Builds remain viable without full local JDK |

---

## 3. Approved Product & Architecture Baseline

### 3.1 Product Core Loop (MVP Priority)
Per `USER_FLOWS.md` §10, `PRD.md` §13, and `ROOMSYNC_ENGINEERING_HANDOFF.md` §4:
1. **Primary MVP Loop (P0):** Register / Sign in → Complete basic profile → Set accommodation preferences → Complete lifestyle questionnaire → Discover ranked compatible roommates → Inspect explainable compatibility & category breakdown → Send/receive/accept connection request → One-to-one persisted messaging.
2. **Secondary MVP Essentials (P1):** Basic accommodation listings, media upload, search & enquiries; basic verification workflows (without fabricated badges); in-app notifications; user/listing reporting & admin moderation with immutable audit logs.
3. **Explicitly Deferred (Post-MVP):** Roommate Groups / Pods (`FR-053`–`FR-060`), Compatibility Simulator (`FR-061`–`FR-066`), AI Roommate Assistant (`FR-067`–`FR-073`), Roommate Agreements & Shared Expense/Task Management (`FR-090`–`FR-095`), Community Forums (`FR-096`–`FR-100`), Reviews (`FR-108`–`FR-112`), Subscriptions/Monetization/Escrow (`FR-118`–`FR-122`), and ML ranking models.

### 3.2 Architecture Boundaries (Confirmed Against Constraints)
- **Web Client:** React + TypeScript + Vite + React Router + TanStack Query + React Hook Form + Zod + Tailwind CSS.
- **Android Client:** React Native + Expo + Expo Router + TypeScript + Expo SecureStore.
- **Authoritative Public API & Domain Backend:** Python + Django modular monolith + Django REST Framework (`/api/v1/`) + `drf-spectacular` OpenAPI. Owns users, auth/sessions, profiles, preferences, listings, connections, conversations, permissions, moderation, notifications, and audit logs.
- **Internal Compatibility Service:** Private FastAPI + Pydantic service (`POST /internal/v1/compatibility/score`, `/health/live`, `/health/ready`). Receives minimal pseudonymous structured payloads (no names, emails, phones, exact addresses, or ID docs); performs stateless deterministic scoring; Django persists `CompatibilitySnapshot`.
- **Database & Infra:** PostgreSQL (authoritative system of record, Django ORM & migrations only; pgAdmin is strictly an optional operator tool), Redis + Celery (async notifications, media processing, scheduled cleanup), private S3-compatible object storage (separate bucket/policies for verification evidence vs. public media).

---

## 4. Missing Documents and Design Assets

### 4.1 Missing Technical & Governance Documents
1. **`Docs/API_CONVENTIONS.md`** — Referenced in `TDD.md` §4.1; does not exist.
2. **`Docs/ADR/` directory** — Architecture Decision Records directory referenced in `TDD.md` §4.1; does not exist.
3. **Actual Google Stitch Audit Report** — `Docs/DESIGN_AUDIT.md` explicitly states the Stitch audit report file was not supplied.
4. **Completed `Docs/SCREEN_INVENTORY.md` mapping** — All 22 module rows remain `Export reference pending` with no filename/path/state/MVP mapping to the 85 exported directories in `Design/`.
5. **Root project scaffolding** — `.gitignore`, `.env.example`, `README.md`, `docker-compose.yml`, `Makefile`, `.github/workflows/`.
6. **`Docs/REPOSITORY_ASSESSMENT.md`, `Docs/IMPLEMENTATION_PLAN.md`, `Docs/OPEN_DECISIONS.md`** — Missing before this Phase 0 output (created alongside this assessment).

### 4.2 Audit of Exported Google Stitch Designs (`Design/stitch_roomsync_roommate_discovery_platform/`)
- **Total screen directories inspected:** **85** (plus 1 token folder `warm_tech_harmony/DESIGN.md` and 2 spec markdowns).
- Every screen folder contains `code.html` (85/85).
- **11 of 85 screen folders are missing `screen.png`** (visual preview image absent; HTML exists):
  1. `roomsync_roommate_discovery_dashboard` *(primary desktop discovery screen)*
  2. `roomsync_mobile_accommodation_discovery_dashboard`
  3. `roomsync_mobile_lifestyle_preferences`
  4. `roomsync_mobile_lifestyle_questionnaire`
  5. `roomsync_mobile_onboarding_complete`
  6. `roomsync_mobile_onboarding_review`
  7. `roomsync_mobile_profile_setup`
  8. `roomsync_mobile_property_enquiry_visit_scheduling`
  9. `roomsync_mobile_roommate_groups_discovery`
  10. `roomsync_mobile_saved_properties_shortlist_hub`
  11. `roomsync_mobile_settings_dashboard`

### 4.3 Missing Screens Needed for PRD / TDD / Dossier Coverage
- **Create / Edit Accommodation Listing UI (Web & Mobile):** Required by `PRD` FR-047/FR-048, Journey B (`Existing Tenant Looking for a Roommate`), and `TDD` §8.2 (`POST /listings`, `PATCH /listings/{id}`, `POST /listings/{id}/media/upload-url`). Only discovery, detail, enquiry, saved-comparison, and admin approval screens exist in `Design/`.
- **Password Reset / Forgot Password Dedicated Screen:** Listed in `SCREEN_INVENTORY.md` (`AUTH-01`) and `TDD` §8.2 (`/auth/password/forgot`, `/auth/password/reset`); not exported as a dedicated screen.
- **Roommate Side-by-Side Comparison Screen:** Required by `PRD` FR-041 (`Compare Roommates`); only property comparison (`roomsync_saved_properties_comparison`) exists.
- **Mobile Property Comparison & Mobile Account Deletion Screens:** Listed in `roomsync_engineering_handoff_dossier_tokens_spec.md` §5.1, absent as standalone folders in `Design/`.
- **Mobile State Catalog Screens (Empty / Loading / Error / Success):** Only desktop state suites exist; Android needs mobile-adapted patterns.

---

## 5. Conflicts Between PRD, TDD, Design System & Stitch Designs

| # | Conflict Area | PRD / Design Spec A | TDD / Handoff / Design Spec B | Impact & Recommended Resolution |
|---|---|---|---|---|
| 1 | **Backend & Web Tech Stack** | `PRD.md` §12.1 recommends **Next.js + Prisma + Next.js API routes + Supabase** and warns against a separate Python microservice for rule-based matching. | `TDD.md` §1.3 & `HANDOFF.md` §3 mandate **React + Vite (Web) + Expo (Android) + Django/DRF + PostgreSQL + Celery + Redis + private FastAPI**. | **Follow TDD + Handoff.** Django/DRF is authoritative; FastAPI is private compute only; React Vite + Expo are separate clients. |
| 2 | **Platform Sequencing** | `PRD.md` §4.3 lists Native Android/iOS as an MVP Non-Goal ("Responsive web first"). | `TDD.md` §1.3 & `HANDOFF.md` §3 include **React Native + Expo Android** in MVP architecture. | **Follow TDD phased milestones:** Build shared API + Web MVP first, then Android MVP against the same `/api/v1/` contract. |
| 3 | **Compatibility Engine Dimensions & Weights** | `PRD.md` FR-027 & `TDD.md` §9.1 define **8 weighted categories** (`Daily routine 15, Cleanliness 15, Financial 15, Privacy 15, Social 10, Food 10, Guests 10, Work/study 10 = 100`). Note FR-026 lists 9 labels including Accommodation preferences. | `Design/.../roomsync_engineering_handoff_dossier_tokens_spec.md` §4.1 defines a **5-dimension vector** (`Circadian 25%, Cleanliness 25%, Food 20%, Work/Noise 15%, Guests 15%`), omitting Financial & Privacy. Meanwhile `roomsync_roommate_profile_compatibility_intelligence/code.html` uses the **8 TDD dimensions**. | **Use TDD's 8 categories (15/15/15/15/10/10/10/10).** Treat accommodation criteria (budget/city/move-in) as eligibility/ranking signals per TDD §9.2 & §10, and supersede the Dossier's 5-dimension formula. |
| 4 | **Design System Color Tokens** | `Docs/DESIGN_SYSTEM.md` & `roomsync_consolidated_design_system_tokens.md` define `primary: #059669` (Emerald), `accent: #4f46e5` (Indigo), `surface-low: #f8fafc`, `text-primary: #1e1b4b`, `danger: #dc2626`. Also `DESIGN_SYSTEM.md` forbids names like "Telegram Blue". | `warm_tech_harmony/DESIGN.md` & **all 85 Stitch HTML files** use Material-3 tokens: `primary: #070235`, `primary-container: #1e1b4b`, `secondary: #006a61` (or `#0D9488` in prose), `surface-container-low: #f2f3ff`, `on-surface: #131b2e`, `error: #ba1a1a`. | **Open Decision (OD-01):** Standardize the canonical token mapping in `packages/design-tokens` reconciling the Stitch palette (`#faf8ff` / `#1e1b4b` / `#006a61`–`#059669`) and audit WCAG AA contrast. |
| 5 | **Hardcoded City (Bangalore)** | `DESIGN_SYSTEM.md` §6 & `HANDOFF.md` §6 explicitly prohibit hardcoding Bangalore. | Nearly all 85 Stitch screens hardcode `Bengaluru, KA`, `Indiranagar`, `Koramangala`, `HSR Layout`, and `Kaveri 2.0` (Karnataka land registry). | **Enforce dynamic multi-city data** (`locations_city` / `locations_locality`); strip hardcoded Bengaluru defaults and fake Kaveri claims during implementation. |
| 6 | **Fake / Unimplemented Verification Badges** | `DESIGN_SYSTEM.md` §5, `DESIGN_AUDIT.md` §4, and `HANDOFF.md` §6 forbid displaying UIDAI, DigiLocker, Corporate SSO, or Kaveri badges unless real integrations exist. | Stitch screens prominently display `DigiLocker`, `Aadhaar KYC Verified`, `Swiggy Corporate SSO`, `IIT Alumni`, `LinkedIn Graph Match`, and `Kaveri 2.0 Deed Verified` badges. | **MVP uses honest verification states only** (email/phone verification + manual/admin review status if uploaded); omit third-party badges until real integrations are approved. |
| 7 | **Post-MVP Scope Embedded in Core UI** | `PRD.md` §4.3 / §13.2, `TDD.md` §1.2, and `HANDOFF.md` §4 defer Groups/Pods, Escrow/Payments, Rental Agreements, Simulator, and AI Assistant. | Stitch screens include `Roommate Groups / Pods` in primary nav, `Deposit Escrow Account`, `Rental Agreement Drafts`, `Splitwise Linked`, `Instant UPI settling`, `1800-ROOM-SYNC`, and `WhatsApp OTP`. | **Hide/exclude post-MVP nav items and links** (`Escrow`, `Agreements`, `Pods`, `Splitwise`, `WhatsApp`) in MVP builds; gate behind feature flags for later phases. |
| 8 | **Navigation & Mobile Tab Bar Inconsistency** | `PRD.md` §8.1 defines 7 desktop items (`Home, Discover, Stay, Groups, Messages, Community, Profile`). `Dossier` C1 defines mobile tabs `[Discover, Pods, Flats, Chat, Profile]`. | Desktop Stitch screens vary between 4, 5, and 6 nav items (`Requests` and `Trust & Safety` appear inconsistently). Mobile Stitch screens split between tab 5 = `Trust` (`mobile_discovery_feed`) and tab 5 = `Profile` (`mobile_settings_dashboard`). | **Open Decision (OD-02):** Define one canonical MVP navigation structure for Web and Android (e.g., Web: `Discover, Listings, Requests, Messages, Trust/Profile`; Android: `Discover, Flats, Requests, Chat, Profile`). |
| 9 | **Onboarding Step Count Mismatch** | Desktop Stitch screens show `Step 1 of 3` (`welcome_account_setup`) vs `Step 1 of 4`..`Step 4 of 4` (`basic_profile_setup`..`onboarding_review`). | Mobile Stitch screens & Dossier `H1` show `Step 1 of 5`..`Step 5 of 5`. | **Unify on a clear 4- or 5-step onboarding sequence** shared conceptually between Web and Android (`Profile → Housing Preferences → Lifestyle Questionnaire → Review → Complete`). |
| 10 | **FastAPI DB Access & Messaging Endpoints** | `TDD.md` §2.1 & §2.2 diagrams show an arrow `FastAPI --> PostgreSQL`. | `TDD.md` §9.7 states *"No database writes from FastAPI in MVP. Django persists the result."* Also `TDD.md` §8.2 omits a connection-request `/decline` endpoint required by `PRD` FR-039 & `USER_FLOWS.md` §3. | **Enforce stateless HTTP-only FastAPI in MVP** (Django fetches DB inputs and persists snapshots); add `POST /connections/requests/{id}/decline` alongside `accept` and `withdraw`. |
| 11 | **OTP Lockout Privacy Disclosure** | `DESIGN_AUDIT.md` §4 requires OTP lockout *not* to reveal whether an account exists. | `roomsync_mobile_otp_rate_limit_lockout/code.html` displays masked phone, `"Swiggy Corporate SSO"`, and `"Pixel 8 • Bangalore East"`. | **Strip account-identifying hints** (`Swiggy SSO`, device/location telemetry) from unauthenticated lockout views. |
| 12 | **Monorepo Folder Naming** | `HANDOFF.md` §7 proposes `services/django/`, `services/matching/`, `packages/{shared-types,validation,design-tokens}`, `infra/`. | `TDD.md` §4.1 proposes `apps/{web,android,backend,matching-service}`, `packages/{api-client,contracts,design-tokens,config}`, `infrastructure/`. | **Adopt unified layout** (`apps/{web,android}` + `services/{backend,matching}` + `packages/{api-client,contracts,design-tokens,config}` + `infrastructure/`) documented below. |

---

## 6. Recommended Final Monorepo Structure

To preserve existing files (`Docs/`, `Design/`, `ROOMSYNC_ENGINEERING_HANDOFF.md`) without rewriting or deleting anything, while cleanly separating JavaScript/TypeScript clients from Python backend services:

```text
RoomSYNC/
├── Design/                                   # Existing exported Google Stitch assets (preserved intact)
│   └── stitch_roomsync_roommate_discovery_platform/
├── Docs/                                     # Existing & new architectural/product documentation (preserved)
│   ├── PRD.md
│   ├── TDD.md
│   ├── DESIGN_SYSTEM.md
│   ├── DESIGN_AUDIT.md
│   ├── SCREEN_INVENTORY.md
│   ├── USER_FLOWS.md
│   ├── REPOSITORY_ASSESSMENT.md              # Created in Phase 0
│   ├── IMPLEMENTATION_PLAN.md                # Created in Phase 0
│   └── OPEN_DECISIONS.md                     # Created in Phase 0
├── ROOMSYNC_ENGINEERING_HANDOFF.md           # Existing handoff baseline (preserved)
├── apps/
│   ├── web/                                  # React + TypeScript + Vite + Tailwind + TanStack Query
│   └── android/                              # React Native + Expo + Expo Router + TypeScript
├── services/
│   ├── backend/                              # Django + DRF modular monolith (authoritative API & ORM)
│   │   ├── manage.py
│   │   ├── config/                           # settings/{base,local,test,production}.py, urls, asgi, wsgi, celery
│   │   ├── apps/                             # accounts, profiles, locations, preferences, matching,
│   │   │                                     # discovery, connections, messaging, listings,
│   │   │                                     # verification, moderation, notifications, audit
│   │   ├── common/                           # Base models, exceptions, pagination, permissions, storage
│   │   └── tests/
│   └── matching/                             # Private FastAPI + Pydantic compatibility compute service
│       ├── app/
│       │   ├── main.py                       # /health/live, /health/ready, /internal/v1/compatibility/*
│       │   ├── auth.py                       # Service-to-service token verification
│       │   ├── schemas.py                    # Strict Pydantic request/response contracts
│       │   └── engine/                       # Deterministic 8-dimension scorer, deal-breakers, explanations
│       └── tests/
├── packages/
│   ├── design-tokens/                        # Warm Tech Harmony tokens -> Tailwind preset & RN theme
│   ├── contracts/                            # OpenAPI-generated types + shared Zod validation schemas
│   ├── api-client/                           # Typed fetch client (CSRF/cookie web + bearer/refresh Android)
│   └── config/                               # Shared ESLint, Prettier, tsconfig presets
├── infrastructure/
│   ├── docker/                               # Dockerfiles for backend, matching, celery, web
│   └── scripts/                              # Seed data, schema export, local helper scripts
├── .github/workflows/                        # CI pipelines (lint, typecheck, pytest, vitest, playwright)
├── docker-compose.yml                        # db (PostgreSQL 16), redis, backend, matching, worker, optional pgadmin/minio
├── .env.example                              # Non-secret environment variable template
├── .gitignore
├── package.json                              # pnpm workspace root scripts
├── pnpm-workspace.yaml
├── Makefile                                  # Standard local dev/test/migrate commands
└── README.md
```

**Why `services/backend` & `services/matching` (vs. `apps/backend`)?**
Keeping `apps/` exclusively for `pnpm` workspace client packages (`web`, `android`) avoids mixing Node workspaces with isolated Python virtual environments (`services/backend`, `services/matching`), directly following `ROOMSYNC_ENGINEERING_HANDOFF.md` §7 and keeping `TDD.md` §4.1's Django/FastAPI internal structure intact.


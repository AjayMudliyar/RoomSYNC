# RoomSync — Phased Implementation Plan

**Date:** 11 November 2026  
**Baseline:** `Docs/product/PRD.md` v1.0, `Docs/engineering/TDD.md` v1.0, `ROOMSYNC_ENGINEERING_HANDOFF.md` v1.0, `Docs/USER_FLOWS.md` v1.0, `Docs/Design/stitch_roomsync_roommate_discovery_platform/`, **Decisions 1–10**, and **Owner Decisions `OD-U1`–`OD-U8`** (`Docs/engineering/OPEN_DECISIONS.md` / `Docs/ADR/`)  
**Strategy:** MVP Core Loop First (Phased, Milestone-Gated Execution)

---

## 1. Guiding Principles & Approved Architecture

1. **Django + DRF (`/api/v1/`) owns all public APIs, auth, permissions, and domain records (`DEC-01`).** Web (`React + Vite + TypeScript`) and Android (`React Native + Expo + TypeScript`) are separate clients sharing `packages/contracts`, `packages/api-client`, `packages/design-tokens`, and `packages/config`.
2. **FastAPI (`services/matching/`) is a private, stateless internal compute service (`DEC-01`, `DEC-02`).** It receives minimal pseudonymous structured payloads, runs deterministic 8-dimension scoring (`15/15/15/15/10/10/10/10`), and **must not write to PostgreSQL**. Django persists `CompatibilitySnapshot`.
3. **PostgreSQL is the single source of truth**, managed exclusively via Django migrations (**PostGIS deferred post-pilot** per `OD-U8`; use `City`/`Locality` FKs). Celery + Redis handle async jobs; MinIO serves local S3-compatible object storage (separate public media vs. private verification buckets).
4. **Core MVP loop first (`DEC-04`):**  
   `Register → Basic Profile → Housing Preferences → Lifestyle Questionnaire → Roommate Discovery → Compatibility Breakdown → Connection Requests → One-to-One Messaging`  
   *(Followed by Milestone 8 P1 basic accommodation listings + Create/Edit Listing, enquiries, truthful verification metadata, notifications, and hardened Django Admin moderation).*
5. **Canonical UX & Onboarding (`OD-U3`, `OD-U4`):**
   - **Web Navigation:** `Discover`, `Requests`, `Messages`, `Stays` *(M8)* + account menu (`Notifications`, `Profile / Trust / Settings`).
   - **Android Bottom Tabs:** `Discover`, `Requests`, `Chat`, `Stays` *(M8)*, `Profile` *(Trust & Safety + Settings)*.
   - **Unified 4-Step Onboarding:** `1. Basic Profile` → `2. Housing Preferences` → `3. Lifestyle Questionnaire` → `4. Review & Submit` *(followed by completion redirect)*.
6. **Strict MVP Exclusions (`DEC-04`, `DEC-08`, `DEC-09`, `OD-U5`):** Defer Groups/Pods, Community, AI Assistant, Compatibility Simulator, Deposit Escrow, Rental Agreements, Splitwise/UPI settling, Side-by-Side Roommate Comparison (`FR-041` → P1), Corporate SSO, DigiLocker/UIDAI/Kaveri badges, WebSockets (start with REST + smart polling), custom React Admin UI, and ML ranking.
7. **Design, Accessibility & Privacy-by-Design Integrity (`DEC-03`, `OD-U6`, `OD-U7`):** Preserve Warm Tech Harmony visual identity (`#faf8ff`, `#131b2e`, `#1e1b4b`, `#006a61`, `#4f46e5`, Plus Jakarta Sans) verified for WCAG 2.1 AA (`ADR-003`). Enforce privacy-by-design (redacted logs, PII filtering, env-var secrets, honest verification states) from Milestone 0 even though production vendors/legal retention remain open until Milestone 10 (`OD-U7`).

---

## 2. Final Milestone 0 Execution Checklist (Ready for Final Owner Sign-Off)

Before scaffolding product features, Milestone 0 builds a deterministic, verified monorepo, tooling, container, health, and CI foundation:

- [ ] **0.1 Host Toolchain Verification (`DEC-10`):**
  - Start and verify **Docker Desktop + `docker compose` v2** on the host shell (`docker compose version`, `docker info` — previously blocked inside restricted sandbox and daemon stopped on host).
  - Install/enable **`pnpm`** (compatible with Node `v24` LTS / Expo SDK) and **`uv`** with **Python `3.12`** cleanly accessible in host & CI shells (avoiding host Python `3.14.5` wheel issues).
- [ ] **0.2 Git Initialization & Repository Hygiene:**
  - Retain existing `.git/` (`main`), retained root configs, `Docs/`, `Docs/Design/`, `Agents.md`, and `ROOMSYNC_ENGINEERING_HANDOFF.md` untouched as baseline references.
  - Create comprehensive `.gitignore` (`.env`, `.env.local`, `.venv/`, `node_modules/`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.expo/`, local Postgres/Redis/MinIO data volumes, coverage reports).
  - Create `.env.example` documenting all required env keys cleanly with safe placeholder defaults (**zero real OAuth/DB/AWS secrets** in source control or docs per `OD-U6`), plus root `README.md` and `Makefile`.
- [ ] **0.3 Monorepo Workspace Layout (`DEC-01`):**
  - Root `package.json` + `pnpm-workspace.yaml` covering `apps/*` (`web`, `android`) and `packages/*` (`design-tokens`, `contracts`, `api-client`, `config`).
  - Independent `pyproject.toml` + `uv.lock` (Python `3.12` pinned) in `services/backend/` and `services/matching/` — zero Python package imports across service boundaries.
- [ ] **0.4 Containerized Local Infrastructure (`docker-compose.yml` & `infrastructure/docker/`):**
  - `db` (`postgres:16-alpine`), `redis` (`redis:7-alpine`), `minio` (`minio/minio` + one-shot `minio-init` creating `roomsync-public` and `roomsync-private` buckets), `backend` (Django), `matching` (FastAPI internal-only network/port), `worker` (Celery worker), and optional `pgadmin` (`profiles: ["tools"]`, bound strictly to `127.0.0.1`).
- [ ] **0.5 Backend & Matching Service Skeletons (`API_CONVENTIONS.md`, `OD-U7` Privacy Baseline):**
  - **`services/backend/`:** Django 5.2 + DRF + `drf-spectacular`, split settings (`base`, `local`, `test`, `production`), custom UUID `accounts.User` (`AUTH_USER_MODEL`) from migration `0001`, `GET /health/live` & `GET /health/ready` (checking DB & Redis without exposing secrets), standard error envelope (`error.code`, `message`, `field_errors`, `request_id`), `X-Request-ID` middleware, and PII-redacted structured JSON logger.
  - **`services/matching/`:** FastAPI + Pydantic v2 (`Python 3.12`), constant-time `X-Internal-Service-Token` dependency on `/internal/v1/*`, `GET /health/live` & `GET /health/ready`, zero database drivers/ORM dependencies.
- [ ] **0.6 Client & Shared Package Skeletons (`ADR-003`):**
  - `packages/config/`: Shared ESLint, Prettier, and strict `tsconfig.base.json`.
  - `packages/design-tokens/`: Canonical WCAG AA Warm Tech Harmony tokens (JSON/TS source + Tailwind v4/CSS theme variables + React Native theme object implementing `ADR-003` — `#006a61` accessible teal, `#1e1b4b` navy, `#faf8ff` canvas).
  - `packages/contracts/` & `packages/api-client/`: Initial OpenAPI-to-TS generation script (`drf-spectacular` YAML → TS types) and base fetch wrapper stub (`X-Request-ID`, cookie+CSRF / Bearer support).
  - `apps/web/`: Vite + React + TypeScript + Tailwind + React Router + TanStack Query verified shell screen rendering canonical tokens and health check connectivity.
  - `apps/android/`: Expo + Expo Router + TypeScript verified shell screen consuming `design-tokens`.
- [ ] **0.7 Quality Gates, Automated Tests & CI (`.github/workflows/ci.yml`):**
  - Configure `ruff` + `mypy` (`services/*`), `eslint` + `prettier` + `tsc --noEmit` (`apps/*`, `packages/*`), and `vitest` / `pytest` / `manage.py test` baselines.
  - Wire `.github/workflows/ci.yml` to validate formatting, linting, typechecking, OpenAPI schema determinism (`--validate` + no drift), Django tests against PostgreSQL, FastAPI pytest suite, and Web production build.

**Milestone 0 Exit Gate:** `docker compose up -d` starts Postgres, Redis, MinIO (`roomsync-public` + `roomsync-private`), Django, FastAPI, and Celery cleanly; `manage.py migrate` runs cleanly; `/health/live` and `/health/ready` return `200`; `pnpm install` + Web build + TS typecheck + Android typecheck succeed; OpenAPI schema exports cleanly; CI checks pass locally.

---

## 3. Implementation Milestones (Milestones 1–10) & Acceptance Criteria

### Milestone 1 — Identity, Authentication, Sessions & Account Lifecycle
**Goal:** Dual-client authentication (`P0`: Email/Password + env-var Google OAuth), session security (`Web`: HttpOnly cookie + CSRF; `Android`: `SecureStore` + rotating refresh JWT with reuse detection), password recovery, anti-enumeration rate-limit lockout, and account lifecycle (`FR-001`–`FR-007`, `AUTH-01`, `STATE-05`).  
**Dependencies:** Milestone 0; runtime Google OAuth credentials supplied via `.env` before live OAuth E2E testing (`OD-U6`).

**Deliverables:**
- `accounts` app: Custom `User` (`uuid` PK, normalized `email`, `status`, capabilities flags, `email_verified_at`, `phone_verified_at`, `terms_accepted_at`, `deletion_requested_at`), `OAuthIdentity`, `RefreshSession` (token family tracking for reuse detection), `PasswordResetToken`.
- Endpoints: `GET /api/v1/auth/csrf`, `POST /auth/register`, `/login`, `/google`, `/refresh`, `/logout`, `/password/forgot`, `/password/reset`, `GET/PATCH /me`, `POST /me/deletion-request`, `GET /me/data-export`.
- Redis-backed rate limiting on auth/reset returning anti-enumeration `429 RATE_LIMITED` (`retry_after_seconds` only — zero device/employer/city/phone hints).
- `audit` app recording immutable auth/lifecycle events; `packages/api-client` supporting Web cookie+CSRF (`credentials: 'include'`) and Android `Bearer` + single-flight refresh rotation.

**Acceptance Criteria:**
- [ ] Email/password registration and server-verified Google OAuth create/authenticate accounts with `18+` terms acceptance required; zero credentials in repo.
- [ ] Web uses HttpOnly, Secure, SameSite cookies with CSRF enforcement; Android stores rotating refresh tokens in `SecureStore` and detects refresh-token reuse by revoking the token family.
- [ ] Logout revokes active session/family; password reset invalidates other active sessions.
- [ ] Lockout (`429`) and password-reset responses never reveal whether an account exists.
- [ ] Automated tests verify registration, Google token validation failure, refresh reuse revocation, CSRF enforcement, and anti-enumeration lockout.

---

### Milestone 2 — Profiles, 5-City Locations, Privacy & MinIO Media Pipeline
**Goal:** Structured user profiles, database-driven locations seeded with the **5 approved Indian cities** (`OD-U1`), field-level visibility enforcement, and signed-URL MinIO/S3 avatar pipeline (`FR-008`, `FR-011`–`FR-014`, `FR-082`, `ONB-01`, `PROF-01`).  
**Dependencies:** Milestone 1 + **Curated starter locality list reviewed** (`OD-U1` follow-up). *(PostGIS stays deferred per `OD-U8`.)*

**Deliverables:**
- `locations` app: `City` & `Locality` tables (`OD-U8`: no PostGIS columns yet) + idempotent seed management command for **Bengaluru, Pune, Mumbai, Hyderabad, and Delhi-NCR** and curated starter localities.
- `profiles` app: `Profile` (`display_name`, private `date_of_birth`, derived age/bracket, `occupation_type`, `institution_or_employer`, `bio`, `avatar_object_key`, `current_city`, `profile_visibility`, `field_visibility_json`, `completion_percent`).
- Endpoints: `GET /locations/cities`, `GET /locations/localities`, `GET/PATCH /me/profile`, `GET /me/profile/preview`, `GET /profiles/{id}`, `POST /me/profile/avatar/upload-url`, `POST /me/profile/avatar/confirm`.
- Celery media task: downloads object from `roomsync-public`, validates magic bytes/dimensions, strips EXIF/GPS metadata, re-encodes WebP/JPEG, updates `avatar_object_key`.

**Acceptance Criteria:**
- [ ] `/api/v1/locations/*` serves all 5 approved cities and curated localities dynamically; zero hardcoded cities in code defaults.
- [ ] `GET /profiles/{id}` enforces `discoverable` / `connections_only` / `hidden` and hides private PII (`date_of_birth`, `email`, `phone`, hidden workplace/college) across all serializers.
- [ ] `GET /me/profile/preview` matches public candidate rendering; `completion_percent` stays accurate across edits.
- [ ] Avatar pipeline verifies MIME/signature, strips EXIF GPS coordinates via Celery, and stores opaque object keys only.

---

### Milestone 3 — 20-Question Preferences & Stateless FastAPI Compatibility Engine
**Goal:** Versioned `v1` 20-question lifestyle questionnaire (supporting `flexible`/`not_sure`, question-type-configurable deal-breakers, and non-exclusion `Unknown` display per `OD-U2`), minor-unit housing preferences, and deterministic 8-dimension FastAPI scoring (`FR-009`–`FR-010`, `FR-015`–`FR-031`, `PREF-01`, `LIFE-01`, `COMP-01`).  
**Dependencies:** Milestone 2 + **Separate owner review & approval of [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md)** before coding question fixtures & scorers!

**Deliverables:**
- `preferences` app: `Question` (`v1`, 20 structured items across the 8 categories, `supports_deal_breaker` configurable flag, `flexible` + `not_sure` options), `Answer` (`answer jsonb`, `importance`, `is_deal_breaker` enforced by DB `CheckConstraint`), `AccommodationPreference` (`*_paise`, normalized `AccommodationPreferenceLocality` join table), `preferences_version` / input fingerprint generator.
- `services/matching/` (FastAPI, **zero PostgreSQL access**):
  - `POST /internal/v1/compatibility/score` accepting two pseudonymous IDs + structured question responses + versions.
  - Exact 8 TDD category weights (`15, 15, 15, 15, 10, 10, 10, 10 = 100`).
  - Scorers for circular 24h time, asymmetric guest/habit pairs, categorical maps, `flexible` handling, and explicit `not_sure` / unanswered handling (`coverage` ratio + **`Unknown / Not answered`** display without excluding candidates).
  - Configurable deal-breaker evaluation returning `blocked_by_dealbreaker` only on known hard conflicts, or `unknown_deal_breakers` when candidate did not answer.
- `matching` app (Django): authenticated HTTP client with strict timeout & fallback handling, `CompatibilitySnapshot` caching (`user_low_id < user_high_id`), and `GET /api/v1/profiles/{id}/compatibility`.

**Acceptance Criteria:**
- [ ] FastAPI performs stateless pure computation with zero database dependencies and enforces internal service-token authentication.
- [ ] Exact approved 20 questions seed cleanly with `flexible` and `not_sure` support and DB-enforced deal-breaker eligibility by question type.
- [ ] Unanswered candidate answers surface explicitly as `Unknown / Not answered` in API breakdown metadata and never automatically exclude that candidate.
- [ ] Confirmed bidirectional deal-breaker conflict returns `blocked_by_dealbreaker` and cannot be overridden by high partial scores.
- [ ] Unit + contract suite passes all `TDD.md` §19.2 cases (circular midnight wraparound, asymmetric pairs, missing data/coverage, timeout fallback, zero PII in logs).

---

### Milestone 4 — Roommate Discovery Feed, Filters, Bookmarks & Feedback
**Goal:** Paginated, block-aware, privacy-aware roommate discovery feed with dynamic filters, bookmarks, and match feedback (`FR-032`–`FR-036`, `FR-040`, `DISC-01`). *(Side-by-side roommate comparison `FR-041` deferred to P1 per `OD-U5`.)*  
**Dependencies:** Milestone 3.

**Deliverables:**
- `discovery` app: `GET /api/v1/discover/roommates` with cursor pagination (`<= 50`), allowlisted sorting, and filters (`city`, `locality`, `budget_min_paise`, `budget_max_paise`, `move_in_from`, `move_in_to`, `occupation_type`, `room_sharing`, `verified_only`).
- Excludes self, non-active accounts, `hidden`/`connections_only` profiles, and bidirectional blocks; **retains candidates with unanswered lifestyle questions** clearly marked via `coverage` / `unknown` indicators (`OD-U2`).
- `SavedProfile` endpoints (`GET/POST/DELETE /saved/profiles`) and `MatchFeedback` endpoint (`POST /profiles/{id}/compatibility/feedback`).

**Acceptance Criteria:**
- [ ] Discovery excludes blocked, hidden, and suspended/deleted users while returning compatible or partial-coverage eligible candidates cleanly.
- [ ] Candidate cards surface score, `coverage` indicator, top aligned/discussion dimensions, unknown/not-answered indicators, and visibility-permitted fields only.
- [ ] Query-count assertion tests confirm no N+1 queries on paginated feeds.
- [ ] Bookmarks and feedback enforce object-level permissions (cannot save self or blocked user).

---

### Milestone 5 — Mutual Connections, Request Lifecycle & Safety Controls
**Goal:** Atomic connection requests (`accept`/`decline`/`withdraw`), mutual match creation, blocks, and user reporting (`FR-037`–`FR-039`, `FR-042`, `FR-079`, `CONN-01`).  
**Dependencies:** Milestone 4.

**Deliverables:**
- `connections` app: `Like` (directional, unique active pair), `Connection` (canonical `user_low_id < user_high_id`), `Block` (directional check + bidirectional query exclusion).
- Endpoints: `POST /connections/likes` (`Idempotency-Key`, atomic `select_for_update`), `GET /connections/requests`, `POST /connections/requests/{id}/accept`, `/decline`, `/withdraw`, `GET /connections`, `POST/DELETE /blocks`.
- `moderation` app: `POST /reports` for user/profile safety reports with immutable target snapshot.

**Acceptance Criteria:**
- [ ] Concurrent reciprocal likes or duplicate `Idempotency-Key` retries produce **one** `Connection` + one `Conversation` without race conditions.
- [ ] Only request recipient can accept/decline (`403` otherwise); only sender can withdraw pending requests.
- [ ] Blocking immediately blocks discovery, likes, and conversation read/write access in both directions.
- [ ] Reporting writes audit-safe records without leaking reporter identity.

---

### Milestone 6 — One-to-One Messaging (REST + Polling) & Notifications
**Goal:** Authorized 1-on-1 persisted chat via REST + smart polling (`DEC-08`) and transactional in-app notifications (`FR-084`–`FR-089`, `FR-101`–`FR-107`, `CHAT-01`, `NOTIF-01`).  
**Dependencies:** Milestone 5.

**Deliverables:**
- `messaging` app: `Conversation`, `ConversationMember`, `Message` (`body <= 4000`), cursor pagination `(created_at, id)` (`?after_cursor=` for smart polling), and discussion prompt suggestions derived from compatibility friction / `Unknown / Not answered` items.
- Endpoints: `GET/POST /conversations`, `GET/POST /conversations/{id}/messages`, `POST /conversations/{id}/read`.
- `notifications` app: `Notification`, `NotificationPreference`, transactional outbox + Celery dispatch (redacted payloads/logs).
- Endpoints: `GET /notifications`, `PATCH /notifications/{id}`, `GET/PATCH /me/notification-preferences`.

**Acceptance Criteria:**
- [ ] Non-members and blocked/closed connections cannot list conversations or read/write messages (`403/404`).
- [ ] Message writes with `Idempotency-Key` prevent duplicates on network retries.
- [ ] Cursor polling returns stable ordering; message bodies never appear in logs or notification previews.
- [ ] Notification preferences suppress opted-out delivery channels while keeping accurate in-app state.

---

### Milestone 7 — Web MVP Application (Core Loop End-to-End)
**Goal:** Deliver the React + Vite Web MVP covering the complete P0 user journey against live Django + FastAPI + PostgreSQL (`USER_FLOWS.md` §10, `DESIGN_AUDIT.md`, `ADR-003`, `OD-U3`, `OD-U4`).  
**Dependencies:** Milestones 1–6; runtime Google OAuth credentials in `.env` (`OD-U6`).

**Deliverables:**
- Tokenized Warm Tech Harmony UI (`Plus Jakarta Sans`, WCAG AA `ADR-003` palette, keyboard focus rings).
- Navigation (`OD-U3`): `Discover`, `Requests`, `Messages`, `Stays` *(placeholder/teaser disabled until M8 or enabled alongside M8)* + account menu (`Notifications`, `Profile / Trust / Settings`). No `Groups` or `Community` links.
- Unified **4-step onboarding (`OD-U4`)**: `1. Basic Profile` → `2. Housing Preferences` → `3. Lifestyle Questionnaire` (20 questions + `flexible`/`not_sure` + deal-breaker controls) → `4. Review & Submit`.
- Discovery feed with dynamic 5-city/locality selector (`/locations/*`), Compatibility breakdown clearly showing **`Unknown / Not answered`** without penalizing or hiding unanswered candidates (`OD-U2`), Requests inbox, 1-on-1 Chat with smart polling + prompts, Settings/Privacy/Notifications/Block/Report, genuine-only verification badges (`OD-U6`), and Loading/Empty/Error/Success states.
- Vitest component tests + Playwright E2E suite.

**Acceptance Criteria:**
- [ ] Playwright E2E passes end-to-end: register → 4-step onboard → discover → compatibility breakdown (including `Unknown / Not answered` & `coverage` rendering) → connect/accept → smart-polling chat → block/report.
- [ ] Zero hardcoded Bengaluru strings, zero fake DigiLocker/UIDAI/SSO/Kaveri badges, zero Pods/Escrow/Agreement/Splitwise links, zero P1 roommate-comparison clutter (`OD-U5`).
- [ ] Automated accessibility checks pass across desktop (`1280px`) and mobile web (`390px`).

---

### Milestone 8 — Accommodation Listings (incl. Create/Edit), Verification & Hardened Django Admin (P1)
**Goal:** Implement basic accommodation listings (search, details, **Create/Edit Listing** per `OD-U5`, enquiries, saved listings), private-bucket verification workflows, and hardened Django Admin moderation (`FR-043`–`FR-052`, `FR-074`–`FR-083`, `FR-123`–`FR-128`, `PROP-01`, `TRUST-01`, `ADMIN-01`).  
**Dependencies:** Milestone 7 + **New Warm Tech Harmony Create/Edit Accommodation Listing UI design approved before frontend coding (`OD-U5`)**.

**Deliverables:**
- `listings` app: `Listing` (INR minor units, `city_id`/`locality_id` FK per `OD-U8`, approximate locality masking, lifecycle statuses), `ListingMedia` (signed URL + EXIF strip), `SavedListing`, `ListingEnquiry`.
- Endpoints: `GET/POST /listings`, `GET/PATCH/DELETE /listings/{id}`, `POST /listings/{id}/media/upload-url`, `POST /listings/{id}/media/confirm`, `POST /listings/{id}/enquiries`, `GET /me/enquiries`, `GET/POST/DELETE /saved/listings`.
- `verification` app: `VerificationCase` (`email`, `phone` [P1 when enabled], `student`, `property`), private MinIO/S3 bucket + staff-audited short-lived signed URLs, accurate `Pending` / `Under review` / `Approved` / `Rejected` states (`OD-U6`).
- Hardened **Django Admin (`DEC-09`)**: staff MFA setup, custom moderation actions (reports, listing approvals/suspensions, verification review queue) with mandatory reason codes and append-only `AdminAuditLog`.
- Web UI pages: `Stays` Discovery, Property Details, Saved Listings, Enquiry flow (`"Enquiry is not a booking"`), Trust Centre (genuine badges only), and the **newly designed Create / Edit Listing workflow (`OD-U5`)**.

**Acceptance Criteria:**
- [ ] Authorized owners/existing tenants complete the Create / Edit Listing workflow cleanly (upload photos → EXIF strip → submit for review/publish); unauthorized edits return `403`.
- [ ] Listing search uses relational `City`/`Locality` filtering (`OD-U8`), excludes suspended/occupied entries, and masks exact address pre-enquiry.
- [ ] Every admin moderation/verification action writes an immutable `AdminAuditLog` entry.
- [ ] Genuine-only badge audit passes (`Email Verified`, optional `Student/Property Reviewed`; zero fabricated KYC/SSO claims).

---

### Milestone 9 — Android MVP (Expo React Native)
**Goal:** Deliver Android MVP parity for onboarding, discovery, compatibility, connections, chat, listings (incl. Create/Edit Listing), trust/safety, and notifications (`apps/android/`).  
**Dependencies:** Milestones 6 & 8 + Android emulator / EAS config.

**Deliverables:**
- Expo Router navigation matching approved 5-tab bar (`Discover`, `Requests`, `Chat`, `Stays`, `Profile` per `OD-U3`) and unified **4-step onboarding (`OD-U4`)**, sharing `packages/design-tokens`, `packages/contracts`, and `packages/api-client` (`Expo SecureStore` adapter + rotating refresh).
- Native UX compliance: `SafeAreaView`, `KeyboardAvoidingView`, `>= 44px` touch targets, sticky CTA bottom padding (`DESIGN_AUDIT.md` C2), Camera Permission Denied sheet (`STATE-05`), anti-enumeration lockout UI (`STATE-05` fixed), Account Deletion UI (`POST /me/deletion-request`), and Expo Notifications integration.
- React Native Testing Library tests + Android emulator/device E2E verification.

**Acceptance Criteria:**
- [ ] Android client completes register → 4-step onboard → discover → compatibility breakdown → connect → message → browse/create/enquire listings against live `/api/v1/`.
- [ ] Tokens reside strictly in `SecureStore` (never `AsyncStorage`); refresh rotation + reuse detection work cleanly.
- [ ] Verified on Android emulator/physical device for safe-area insets, system back behavior, keyboard clearance, and touch-target sizing.

---

### Milestone 10 — Production Preparation, DPDP Compliance & Pilot Release Readiness
**Goal:** Lock `OD-U7` production vendor/legal decisions, verify performance, security, DPDP data-deletion/export workflows, backups, observability, and staging/production release gates (`TDD.md` §19–§20, §23).  
**Dependencies:** Milestones 7–9 + **Owner sign-off on `OD-U7` open production items** (cloud hosting, prod S3 storage & region, email/SMS vendors, data residency rule, DPDP retention schedule, legal counsel approval of Terms/Privacy notice).

**Deliverables:**
- `OD-U7` vendor & legal lock-in: bind chosen production S3 provider, transactional email (SPF/DKIM/DMARC verified) + optional P1 SMS/DLT provider, managed PostgreSQL/Redis, and configured DPDP scheduled retention/purge Celery beat tasks.
- Performance benchmarks (API read p95 < 500 ms, compatibility scoring p95 < 1 s, query-count tests under synthetic data).
- Security & privacy audit: full IDOR matrix tests, CSRF/CORS/CSP verification, rate-limit verification, log redaction verification, verified Google OAuth + cookie domain behavior on production URLs.
- Observability & ops: Sentry alerting, structured JSON log shipping, uptime monitors, PostgreSQL backup + isolated restore drill, rollback runbook, Expo EAS production/internal release build.

**Acceptance Criteria:**
- [ ] All `OD-U7` vendor, residency, retention, and legal sign-off items closed and configured via secrets manager.
- [ ] All checks in `TDD.md` §23 and `DESIGN_AUDIT.md` §4–§5 pass with zero unresolved critical/high issues.
- [ ] PostgreSQL restore drill succeeds cleanly onto an isolated instance.
- [ ] Staging/production smoke tests pass cleanly across both Web and Android.

---

## 4. P1 Follow-Ups & Post-MVP Backlog

### P1 Follow-Ups (Post-Core MVP Launch)
1. Side-by-Side Roommate Comparison (`FR-041`, deferred per `OD-U5`).
2. Phone Number + OTP Auth (`DEC-05`, after TRAI DLT & SMS vendor selection in `OD-U7`).

### Deferred Post-MVP Modules (`DEC-04`, `DEC-08`, `DEC-09`, `OD-U8`)
1. Roommate Groups / Pods (`FR-053`–`FR-060`) & Pod Admin Governance.
2. Compatibility Simulator (`FR-061`–`FR-066`) & AI Roommate Assistant (`FR-067`–`FR-073`).
3. Roommate Agreements, Shared Expenses & Household Tasks (`FR-090`–`FR-095`).
4. College / City Communities (`FR-096`–`FR-100`) & Reviews/Reputation (`FR-108`–`FR-112`).
5. Payments, Subscriptions, Provider Plans & Escrow (`FR-118`–`FR-122`).
6. PostGIS Geographic Radius / Map Discovery (`FR-114`–`FR-117`, `OD-U8`), Real DigiLocker / Corporate SSO integrations, Django Channels WebSockets, Custom React Admin UI, and ML compatibility ranking.

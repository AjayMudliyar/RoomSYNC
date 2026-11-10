# RoomSync — Decisions & Open Questions Log

**Date:** 11 November 2026  
**Status:** Architectural baseline (`DEC-01`–`DEC-10`) and owner policy decisions (`OD-U1`–`OD-U8`) reconciled; specific **proposed** pre-implementation artefacts and production-prep items are isolated explicitly in Section 2.  
**Related ADRs:** [Docs/ADR/README.md](../ADR/README.md)

---

## 1. Approved Decisions Baseline

All core engineering direction (`DEC-01`–`DEC-10`) and product policy decisions (`OD-U1`–`OD-U8`) approved by the owner / engineering lead are locked below. *(Note: Operational/catalogue sub-items that remain **proposed** or **open until production prep** are intentionally separated in Section 2.)*

### 1.1 Architecture & Engineering Baseline (`DEC-01` – `DEC-10`)

| Decision ID | Area | Approved Decision | Rationale & Guardrails | Related ADR |
|---|---|---|---|---|
| **DEC-01** | **Architecture & Stack** | **Web:** React + TypeScript + Vite<br>**Android:** React Native + Expo + TypeScript<br>**Backend:** Django + DRF (`/api/v1/`)<br>**Internal Compute:** FastAPI (stateless, private)<br>**DB:** PostgreSQL<br>**Jobs:** Celery + Redis<br>**Storage:** MinIO locally (prod vendor open via `OD-U7`)<br>**Repo:** Monorepo (`apps/`, `services/`, `packages/`, `infrastructure/`) | Preserves single domain authority in Django/PostgreSQL, prevents split-brain writes from FastAPI, enables Web + Android contract reuse cleanly, and keeps local object storage portable. | [ADR-001](../ADR/ADR-001-platform-architecture-and-boundaries.md) |
| **DEC-02** | **Compatibility Matching** | Use the **8 TDD categories & weights**:<br>• Daily routine: `15`<br>• Cleanliness: `15`<br>• Financial expectations: `15`<br>• Privacy & boundaries: `15`<br>• Social lifestyle: `10`<br>• Food preferences: `10`<br>• Guest preferences: `10`<br>• Work/study environment: `10`<br>*(Reject the 5-category dossier variant)* | Aligns directly with `PRD.md` FR-027, `TDD.md` §9.1, and `roomsync_roommate_profile_compatibility_intelligence`. Preserves financial & privacy dimensions vital for Indian co-living. | [ADR-002](../ADR/ADR-002-compatibility-engine-and-weights.md) |
| **DEC-03** | **Design System & WCAG AA** | Use exported Stitch HTML/CSS & Warm Tech Harmony (`#faf8ff` / `#1e1b4b` / `#006a61`) as visual reference; reconcile conflicting tokens into one canonical spec verified for **WCAG 2.1 AA**. | Preserves visual identity across 85 Stitch screens while fixing contrast failures (`#059669` 3.77:1 and `#94a3b8` 2.56:1 on white) using `#006a61` (6.49:1) and `#47464f` (8.83:1). | [ADR-003](../ADR/ADR-003-design-system-token-reconciliation.md) |
| **DEC-04** | **MVP Scope** | Prioritize core loop:<br>`Register → Profile → Housing Prefs → Lifestyle Questionnaire → Discovery → Compatibility → Connection Requests → 1-on-1 Messaging` (+ P1 basic listings/moderation/notifications).<br>Defer Groups/Pods, Community, AI Assistant, Compatibility Simulator, Escrow, Rental Agreements, Splitwise, and ML ranking. | Validates the central compatibility hypothesis before adding multi-party governance, legal/financial custody, or ML complexity without outcome data. | [ADR-001](../ADR/ADR-001-platform-architecture-and-boundaries.md) |
| **DEC-05** | **Authentication** | **P0:** Email/Password + Google OAuth.<br>**P1:** Phone OTP.<br>**Deferred:** Corporate SSO, DigiLocker/UIDAI, Kaveri integrations. | Unblocks Milestone 1 immediately without TRAI/DLT SMS vendor blockers or unapproved KYC/SSO integrations; forbids fabricated trust badges. | [ADR-004](../ADR/ADR-004-auth-sessions-locations-and-privacy.md) |
| **DEC-06** | **Sessions & Tokens** | **Web:** HttpOnly, Secure, SameSite cookies + CSRF (same-parent-domain deployment).<br>**Android:** `Expo SecureStore` + short-lived JWT access + rotating refresh tokens with reuse detection. | Eliminates XSS token theft on Web while providing revocable, hardware-backed refresh sessions on Android. | [ADR-004](../ADR/ADR-004-auth-sessions-locations-and-privacy.md) |
| **DEC-07** | **Locations** | Database-driven `City` & `Locality` tables; seed initial **5 major Indian cities** (`OD-U1`); zero hardcoded city logic in frontends. | Satisfies `DESIGN_SYSTEM.md` §6 and `HANDOFF.md` §6 while supporting multi-city launch readiness. | [ADR-004](../ADR/ADR-004-auth-sessions-locations-and-privacy.md) |
| **DEC-08** | **Messaging Delivery** | Start with **REST APIs + smart polling**. Defer WebSockets / Django Channels until pilot demand justifies realtime infra. | Keeps Milestone 6 reliable and free of premature ASGI scaling overhead while maintaining canonical PostgreSQL persistence. | [ADR-001](../ADR/ADR-001-platform-architecture-and-boundaries.md) |
| **DEC-09** | **Admin / Moderation** | Use **hardened Django Admin** (staff MFA + custom moderation actions + mandatory `AdminAuditLog`) for the initial pilot. Defer custom React Admin UI. | Delivers P1 operational safety and DPDP audit trails quickly without duplicating 7 custom admin frontend screens in MVP. | [ADR-001](../ADR/ADR-001-platform-architecture-and-boundaries.md) |
| **DEC-10** | **Developer Environment** | Standardize on **Python 3.12**, compatible **Node LTS**, **`pnpm`**, **`uv`**, and **Docker Compose** (verified on host before coding). | Prevents Python 3.14 wheel fragility (`psycopg`, `pydantic`, `celery`) and ensures deterministic monorepo builds across host and CI. | [ADR-001](../ADR/ADR-001-platform-architecture-and-boundaries.md) |

### 1.2 Approved Product Policy Decisions (`OD-U1` – `OD-U8`)

| ID | Area | Status | Approved Decision & Guardrails | Follow-Up Gate |
|---|---|---|---|---|
| **OD-U1** | **Launch Cities & Localities** | **APPROVED** *(Seed list curated before M2)* | Approve **Bengaluru, Pune, Mumbai, Hyderabad, and Delhi-NCR** as the initial 5 cities. Use curated, database-driven `City` and `Locality` records. **Never** hardcode city or locality logic in Web or Android code. | Curated starter locality list per city reviewed cleanly before Milestone 2 seed. |
| **OD-U2** | **Questionnaire Policy** | **FRAMEWORK APPROVED** *(Exact catalog `PROPOSED`)* | Approve a **20-question `v1` questionnaire** across the **8 existing compatibility categories**. Support **`flexible`** and **`not_sure`** answers. Make **`is_deal_breaker` eligibility configurable by question type** (`CheckConstraint`). Unanswered candidate responses **must render as `Unknown / Not answered`** and **must not** automatically exclude that candidate. | Exact 20-Q catalog & deal-breaker rules drafted in [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md) require separate owner review before **Milestone 3**. |
| **OD-U3** | **Canonical Navigation** | **APPROVED** | **Web:** `Discover`, `Requests`, `Messages`, `Stays` *(enabled in M8)*, with `Notifications` and `Profile / Trust / Settings` in the account area.<br>**Android:** `Discover`, `Requests`, `Chat`, `Stays` *(enabled in M8)*, `Profile` *(contains Trust & Safety + Settings)*.<br>`Groups` and `Community` remain deferred (`DEC-04`). | Implemented directly in **Milestone 7** (Web) and **Milestone 9** (Android). |
| **OD-U4** | **Onboarding Progression** | **APPROVED** | Standardize on **4 active steps** across Web and Android:<br>`1. Basic Profile` → `2. Housing Preferences` → `3. Lifestyle Questionnaire` → `4. Review & Submit` *(followed by completion redirect to Discovery)*. | Implemented identically across Web (`M7`) and Android (`M9`), reconciling Stitch's `3`/`4`/`5` step discrepancies. |
| **OD-U5** | **Compare vs. Create Listing Scope** | **APPROVED** *(New UI design gate before M8)* | **Defer** side-by-side roommate comparison (`FR-041`) to **P1**. **Include** `Create / Edit Accommodation Listing` (`FR-047`, `FR-048`) in **Milestone 8**, with a **new Warm Tech Harmony design required and reviewed before implementation**. | Design & review Create/Edit Listing screen prior to **Milestone 8** UI coding. |
| **OD-U6** | **Google OAuth & Genuine Badges** | **APPROVED** | Keep **Google OAuth** in **P0**. Use **environment variables** for all credentials — never write secrets into documentation or source control. Render **only genuine verification states** backed by implemented integrations (`Email Verified` in P0; `Phone Verified` [when DLT/SMS added] and `Manual Student / Property Review` in P1). | Inject non-committed OAuth Client IDs/Secrets via `.env` / secrets manager before live **M1/M7** E2E verification. |
| **OD-U7** | **Production Vendors & Legal** | **DELIBERATELY OPEN UNTIL PROD PREP** | Keep **hosting provider, production storage vendor, email/SMS vendors, data residency policy, exact retention schedules, and final legal approval** open until **Milestone 10** (production preparation). **Privacy-by-design and secure data handling remain mandatory from Milestone 0** (PII masking, private buckets, EXIF strip, redacted logs, deletion/export mechanics). | Revisit & lock before **Milestone 10** staging/production launch gate. |
| **OD-U8** | **PostGIS Timing** | **APPROVED** | **Defer PostGIS** (`geography(Point, 4326)`) until geographic radius or distance search (`FR-115`, `FR-117`) is scheduled post-pilot. Use normalized **`City` and `Locality` relationships** for the MVP. | Revisit post-pilot alongside interactive map discovery (`roomsync_mobile_map_based_property_discovery`). |

---

## 2. Summary: Approved vs. Proposed / Pending Review

To maintain strict traceability between **locked policy** and **items awaiting separate sign-off**:

| Classification | Item | Timing / Gate | Reference |
|---|---|---|---|
| **Approved (Ready)** | Decisions `DEC-01`–`DEC-10`, `OD-U1` (5 cities), `OD-U2` (20-Q + `flexible`/`not_sure` + `Unknown` display policy), `OD-U3` (Web/Android Nav), `OD-U4` (4-step onboarding), `OD-U5` (scope split), `OD-U6` (env-var OAuth + real badges), `OD-U8` (defer PostGIS) | Active baseline from **Milestone 0** | [ADR/README.md](../ADR/README.md) |
| **Proposed (Needs Separate Review)** | **Exact 20-question `v1` catalog, canonical keys/options, and asymmetric deal-breaker evaluation rules** (`OD-U2` part 2) | Approve **before Milestone 3** | [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md) |
| **Proposed (Needs Pre-M2 Check)** | Curated starter **localities** per city (`Bengaluru`, `Pune`, `Mumbai`, `Hyderabad`, `Delhi-NCR`) for initial DB seed migration (`OD-U1`) | Approve **before Milestone 2** | `services/backend/apps/locations/` seed plan |
| **Design Required (Pre-M8 Gate)** | New Warm Tech Harmony **Create / Edit Accommodation Listing** Web & Android UI (`FR-047`, `FR-048`, `OD-U5`) — no Stitch export exists | Design & approve **before Milestone 8 UI** | [SCREEN_INVENTORY.md](../SCREEN_INVENTORY.md) |
| **Credentials Needed (Pre-M1/M7 E2E)** | Non-committed Google OAuth Web + Android Client IDs/Secrets injected via runtime `.env` (`OD-U6`) | Before live OAuth E2E in **M1/M7** | `.env.example` / host `.env` |
| **Intentionally Open (Prod Prep)** | Cloud hosting, S3 production storage & region, email/SMS providers, geographic residency mandate, DPDP retention durations, legal counsel review (`OD-U7`) | Lock **before Milestone 10** release | [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) M10 |

---

## 3. Synchronization Changes Needed in `PRD.md` & `TDD.md` (Originals Preserved Untouched)

Per instructions, [PRD.md](../product/PRD.md) and [TDD.md](./TDD.md) have **not** been modified. Apply the following non-breaking synchronization updates in a future controlled `v1.1` documentation pass:

### 3.1 Proposed Sync Updates to `Docs/product/PRD.md`
1. **§4.3 Non-Goals & §13.1 Platform Priority:** `PRD.md` §4.3 lists *"Native Android and iOS applications"* as an initial MVP non-goal. Update to clarify that **Web (`React + Vite`) and Android (`React Native + Expo`)** share the `/api/v1/` API in phased MVP milestones (`M7` Web first, `M9` Android next), while iOS remains deferred.
2. **§12.1 Recommended Technology Stack:** Replace the superseded `Next.js + Prisma + Supabase` suggestion with the approved `TDD.md` stack (`React + Vite + Expo + Django/DRF + private FastAPI + PostgreSQL + Celery/Redis`).
3. **§6 Module 3 (`FR-015`–`024`) & Module 4 (`FR-026` vs. `FR-027`):**
   - Document the **20-question `v1` structure**, support for `flexible` / `not_sure`, and the rule that unanswered candidate items render as **`Unknown / Not answered`** without automatic exclusion (`OD-U2`).
   - Clarify `FR-026`'s 9th bullet (*"Accommodation preferences"*) operates as eligibility filtering and secondary ranking signals (`FR-031`), keeping lifestyle weights strictly at **100 across the 8 `FR-027` categories**.
4. **§6 Module 5 (`FR-041`):** Mark `Compare Roommates` (`FR-041`) as **deferred to P1** (`OD-U5`).
5. **§6 Module 16 (`FR-113`–`117`) & Initial Markets:** Record the **5 approved initial cities** (`Bengaluru`, `Pune`, `Mumbai`, `Hyderabad`, `Delhi-NCR`) using normalized `City`/`Locality` records, and mark `FR-114/115/117` (map/radius/distance) as **post-pilot (`OD-U8`)**.
6. **§8.1 Primary Navigation:** Align top-level nav to `Discover, Requests, Messages, Stays` (+ account `Notifications`, `Profile/Trust/Settings`), marking `Groups` and `Community` as deferred (`OD-U3`).

### 3.2 Proposed Sync Updates to `Docs/engineering/TDD.md`
1. **§2.1 & §2.2 Architecture Diagrams:** Remove the `FastAPI --> PostgreSQL` (`MATCH --> DB`) arrow to reflect stateless HTTP-only FastAPI (`DEC-01`, §9.7).
2. **§4.1 Monorepo Layout:** Align `apps/backend` + `apps/matching-service` to `services/backend` + `services/matching` + `infrastructure`, preserving `Docs/` and `Docs/Design/`.
3. **§6.3.3 (`locations_locality`) & §6.3.12 (`listings_listing`):** Mark `geography(Point, 4326)` / PostGIS columns as **deferred post-pilot** (`OD-U8`); retain normalized `city_id` / `locality_id` relationships.
4. **§6.3.4 (`preferences_question` / `preferences_answer`):** Document `v1` 20-question budget, `flexible`/`not_sure` sentinels, `supports_deal_breaker` configurability, and `Unknown / Not answered` non-exclusion rule (`OD-U2`).
5. **§8.2 Endpoint Inventory:** Add missing required routes (`API_CONVENTIONS.md` §6):
   - `GET /auth/csrf` and `POST /auth/google` (`DEC-05`/`06`, `OD-U6`)
   - `POST /connections/requests/{id}/decline` (`FR-039`, `USER_FLOWS.md` §3)
   - `POST /me/deletion-request` and `GET /me/data-export` (`FR-006`)
   - `GET /me/profile/preview` (`FR-014`)
   - `POST /me/profile/avatar/upload-url` and `POST /me/profile/avatar/confirm` (`FR-008`)
   - `GET/POST/DELETE /saved/profiles` and `GET/POST/DELETE /saved/listings` (`FR-040`, `FR-050`)
   - `POST /profiles/{id}/compatibility/feedback` (`FR-032`)
   - `GET /locations/cities` and `GET /locations/localities` (`FR-113`)
   - `GET /me/enquiries` and `GET /me/verification` / `POST /me/verification/cases` (`FR-049`, `FR-076`–`078`)
6. **§11.2, §17.2, & §24 (Open Decisions):** Record resolved decisions (`DEC-05`–`DEC-10`, `OD-U1`–`OD-U8`), update toolchain notes to **Python `3.12` + `uv` + `pnpm` + MinIO (local S3)**, and narrow §24 open items strictly to **`OD-U7` production vendor/legal/retention selection** + `OD-U2` catalog approval.

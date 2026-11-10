# RoomSync — Engineering Handoff

> [!NOTE]
> **Repository Path Note:** Original handoff references below to `docs/` and `design/` map in this repository to [`Docs/product/PRD.md`](./Docs/product/PRD.md), [`Docs/engineering/TDD.md`](./Docs/engineering/TDD.md), `Docs/*.md`, and [`Docs/Design/stitch_roomsync_roommate_discovery_platform/`](./Docs/Design/stitch_roomsync_roommate_discovery_platform/). Reconciled decisions and open questions live in [`Docs/engineering/OPEN_DECISIONS.md`](./Docs/engineering/OPEN_DECISIONS.md).

**Version:** 1.0  
**Date:** 11 November 2026  
**Purpose:** Baseline handoff for implementing RoomSync in Antigravity.

## 1. Product summary

**RoomSync** — “Find your people before finding your place.”

RoomSync is a compatibility-first roommate discovery and shared-accommodation product for students, interns, young professionals, existing tenants, and (in a later marketplace phase) accommodation providers. It helps people assess lifestyle compatibility before connecting, form roommate groups, and discover suitable shared accommodation.

The initial market is India.

### Product principles
1. Compatibility over convenience.
2. Trust and privacy by design.
3. Explainable recommendations rather than opaque scores.
4. Roommate discovery is the core product; accommodation discovery supports it.

## 2. Source-of-truth documents and assets

Keep these files in the repository under `docs/`:

- `docs/PRD.md` — product scope, personas, requirements, user journeys, acceptance criteria.
- `docs/TDD.md` — architecture, data model, API design, security, deployment and technical decisions.
- `docs/DESIGN_SYSTEM.md` — export the approved Warm Tech Harmony design tokens and component rules from Google Stitch.
- `docs/DESIGN_AUDIT.md` — final Stitch audit, issues, and resolution status.
- `docs/SCREEN_INVENTORY.md` — complete screen list, platform, module, state coverage and export filename/path.
- `docs/USER_FLOWS.md` — approved end-to-end user journeys.
- `design/` — exported Google Stitch screens and assets, organized by module/platform.

Do not assume the design exports are available until the files are visible in the Antigravity workspace. Preserve original filenames and add a screen inventory rather than renaming assets blindly.

## 3. Approved technology baseline

### Client applications
- Web: React + TypeScript + Vite.
- Android: React Native + Expo + TypeScript.
- Web routing: React Router.
- Android navigation: Expo Router.
- Web server state: TanStack Query.
- Forms: React Hook Form + Zod.
- Web styling: Tailwind CSS and accessible web primitives.
- Share platform-agnostic types, validation schemas, API contracts and design tokens where practical. Do not force web-only components into React Native.

### Backend and data
- Main backend: Python + Django.
- Public API: Django REST Framework, versioned under `/api/v1/`.
- Database: PostgreSQL; Django ORM and migrations are authoritative.
- Internal compute service: FastAPI + Pydantic for compatibility computation and later AI/ML workloads.
- Async jobs: Celery + Redis.
- Media: private S3-compatible object storage; keep verification evidence separate from ordinary profile media.
- API schema: OpenAPI, e.g. drf-spectacular.
- Tests: pytest/Django tests, Vitest, React Native Testing Library, Playwright.
- Operations: Docker Compose for local development, GitHub Actions for CI, structured logs and Sentry/error monitoring.

### Architecture boundaries
- Use a **modular monolith** for the Django domain backend.
- Django is the source of truth for users, profiles, preferences, listings, connections, groups, conversations, permissions and moderation.
- Web and Android call Django DRF; they do not call FastAPI directly.
- FastAPI is a private internal compute service. It must not become a second public API or own core product records.
- Django sends FastAPI the minimum matching payload needed; exclude names, email addresses, phone numbers, exact addresses and identity documents.
- PostgreSQL is the system of record.
- Redis, PostgreSQL, FastAPI, pgAdmin and internal workers must not be publicly exposed.
- pgAdmin is an operator tool, not the database or an application dependency.

## 4. MVP scope — build in this order

The PRD describes a broader product vision. The TDD defines the narrower first implementation. Do not try to implement every designed screen in the first release.

### MVP must-have
1. Authentication and account lifecycle.
2. User profile and privacy-aware profile visibility.
3. Lifestyle questionnaire and accommodation preferences.
4. Deterministic, explainable roommate compatibility scoring.
5. Roommate discovery, filters and profile details.
6. Mutual connection requests.
7. Basic one-to-one messaging after the intended connection/permission rule.
8. Basic accommodation listings/search/enquiry only to the level explicitly included in the TDD.
9. Admin/moderation essentials needed to operate the MVP.
10. Notifications needed for the above flows.

### Defer until the core loop works
- Advanced group matching and group accommodation planning.
- Compatibility simulator and AI roommate assistant.
- Full payments, rent collection or deposit custody.
- Rental agreement execution.
- Automated background checks.
- Predictive personality/behaviour claims.
- Complex property management and full community features.
- Trained ML ranking. Do not train an ML model before sufficient outcome data exists.

A screen appearing in the design library does not automatically make its feature MVP scope. Mark each screen as `MVP`, `POST_MVP`, or `ADMIN/OPS` in the screen inventory.

## 5. Compatibility engine rules

Use a deterministic, versioned rule-based scoring engine for the MVP.

Initial category weights from the TDD:
- Daily routine: 15
- Cleanliness: 15
- Financial expectations: 15
- Privacy/boundaries: 15
- Social lifestyle: 10
- Food preferences: 10
- Guest preferences: 10
- Work/study environment: 10

Requirements:
- Apply deal-breakers explicitly and consistently.
- Treat unanswered, unknown, flexible and “prefer not to say” answers according to documented semantics; do not silently treat missing answers as conflicts.
- Return an overall score, category-level scores, coverage/completeness, explanation reasons, deal-breaker outcomes, algorithm version and input fingerprint.
- Make explanations understandable to users and avoid claims that the score guarantees a successful living arrangement.
- Add unit tests for boundary cases, missing answers, flexible answers, deal-breakers, symmetry/directionality and version changes.
- Group compatibility, if implemented later, must evaluate all-member compatibility and conflicts; it must not be a simple average of pairwise scores.

## 6. Design implementation rules

Use the exported Google Stitch designs as visual references, not as permission to invent missing behaviour.

Approved design direction: **Warm Tech Harmony**
- Canvas: `#faf8ff`
- Primary text: `#1e1b4b`
- Emerald: `#059669` (use a darker accessible shade such as `#047857` for normal-size text on white where required)
- Indigo: `#4f46e5`
- Plus Jakarta Sans
- 4px/8px spacing grid
- Buttons/inputs approximately 12px radius; cards 16px; dialogs/drawers 24px
- Maintain accessible contrast, visible focus, keyboard support on web, touch targets of at least 44px on mobile, and safe-area/keyboard-aware layouts on Android.

Do not:
- hardcode a city such as Bangalore as the user's location;
- show UIDAI, DigiLocker or corporate verification badges unless the integration is real and approved;
- claim a listing is available or verified without evidence;
- imply enquiry equals booking;
- imply submitted identity evidence is approved;
- expose private lifestyle answers by default.

Implement shared tokens and platform-appropriate component systems. Tailwind classes do not directly apply to React Native.

## 7. Suggested monorepo layout

```text
roomsync/
├── apps/
│   ├── web/                 # React + Vite
│   └── android/             # Expo + React Native
├── services/
│   ├── django/              # Django + DRF domain backend
│   └── matching/            # Private FastAPI compute service
├── packages/
│   ├── shared-types/        # Shared TypeScript contracts
│   ├── validation/          # Shared Zod schemas where suitable
│   └── design-tokens/       # Platform-neutral design tokens
├── docs/
│   ├── PRD.md
│   ├── TDD.md
│   ├── DESIGN_SYSTEM.md
│   ├── DESIGN_AUDIT.md
│   ├── SCREEN_INVENTORY.md
│   ├── USER_FLOWS.md
│   └── IMPLEMENTATION_PLAN.md
├── design/
│   ├── web/
│   ├── android/
│   └── shared-states/
├── infra/
│   └── docker/
├── .github/workflows/
├── .env.example
├── .gitignore
└── README.md
```

This is a proposed organization. Inspect the existing repository before creating or moving anything. If a repository already exists, preserve its conventions unless there is a clear reason to change them.

## 8. Implementation phases and exit criteria

### Phase 0 — Repository reconnaissance and setup
- Inspect current directory, Git status, existing files, package managers, framework versions and environment.
- Read PRD, TDD, design system, audit report and screen inventory.
- Identify missing documents/assets and conflicts between PRD, TDD and screens.
- Propose a minimal implementation plan and confirm the repository structure.
- Create `.env.example`; never commit secrets.
- Add formatting, linting, type checking and baseline CI.
**Exit:** documented repo map, runnable local skeleton, clean baseline checks.

### Phase 1 — Backend foundation
- Django project and modular apps.
- PostgreSQL connection and initial migrations.
- Environment configuration and health endpoint.
- DRF versioning, OpenAPI schema, error format, pagination and permission conventions.
- Authentication decision and secure session/token implementation.
- Audit logging for sensitive actions.
**Exit:** backend starts locally, migrations run, health check and API schema work, tests pass.

### Phase 2 — Core domain and APIs
- Users/auth, profiles, questionnaire answers, accommodation preferences.
- Privacy and visibility permissions.
- Connections and request lifecycle.
- Listings and enquiries only within MVP scope.
- Admin/moderation essentials.
**Exit:** models, migrations, serializers, permissions and API tests cover core use cases.

### Phase 3 — Compatibility service
- Define a versioned internal request/response contract.
- Implement deterministic scoring and explanation generation.
- Add deal-breaker and missing-answer semantics.
- Add golden test fixtures and edge-case tests.
- Django orchestrates calls and persists result snapshots.
**Exit:** repeatable scores for same inputs/version; no sensitive identifiers sent to FastAPI; documented contract.

### Phase 4 — Web MVP
- Build tokenized design system and reusable components.
- Implement authentication, onboarding, questionnaire, discovery, profile, compatibility, connections and basic messaging.
- Connect to real APIs; use explicit loading/empty/error/success states.
- Add responsive behaviour and accessibility checks.
**Exit:** primary web user journey works end-to-end against backend.

### Phase 5 — Android MVP
- Implement equivalent core flows in Expo/React Native.
- Reuse shared types, validation and tokens; use native components/navigation.
- Handle safe areas, keyboard, permissions, deep links and offline/network errors.
**Exit:** core Android journey works on emulator and a physical device.

### Phase 6 — Hardening and release readiness
- End-to-end tests, security review, rate limits and abuse prevention.
- Backups/restore test, monitoring, crash/error reporting.
- Privacy review, data retention/deletion workflows and legal review for India.
- Performance checks and deployment runbooks.
**Exit:** release checklist passed; no unresolved critical/high issues.

## 9. Engineering quality gates

Every feature must include:
- Acceptance criteria mapped to PRD requirement IDs.
- API contract and authorization rules.
- Server-side validation; client validation is not a security boundary.
- Unit/integration tests for business logic and permissions.
- Loading, empty, error, success, disabled and pending states as applicable.
- Accessibility and responsive/mobile review.
- Privacy/security review for personal data.
- Logs that avoid passwords, OTPs, tokens, message bodies and identity-document contents.
- Documentation updates when contracts or decisions change.

Never:
- put secrets in source control or client bundles;
- trust client-supplied compatibility scores or permissions;
- expose FastAPI, PostgreSQL or Redis publicly;
- store passwords or OTPs in logs;
- upload identity documents to public buckets;
- fabricate user, property, verification or rating data;
- silently change PRD scope or matching weights.

## 10. First Antigravity task — copy/paste prompt

You are the senior engineer responsible for starting implementation of RoomSync.

Read `docs/PRD.md`, `docs/TDD.md`, `docs/DESIGN_SYSTEM.md`, `docs/DESIGN_AUDIT.md`, `docs/SCREEN_INVENTORY.md`, `docs/USER_FLOWS.md`, and the exported design assets under `design/` if present.

**Do not immediately generate the whole application. First perform repository reconnaissance.**

1. Inspect the existing workspace, Git status, files, package managers, installed dependencies, runtime versions and any existing code. Do not overwrite or delete existing work.
2. Confirm which handoff documents and design assets are present. Report missing files rather than inventing their contents.
3. Compare the PRD, TDD, audit report and screens. Identify contradictions, ambiguous requirements, MVP vs post-MVP scope, and unresolved technical decisions.
4. Recommend the smallest viable monorepo structure consistent with the TDD and the existing repository.
5. Produce:
   - `docs/REPOSITORY_ASSESSMENT.md`
   - `docs/IMPLEMENTATION_PLAN.md`
   - `docs/OPEN_DECISIONS.md`
   - a proposed phased task breakdown with dependencies and acceptance criteria.
6. Do not implement product features yet. Do not change architecture, stack, matching weights or product scope without documenting the reason and asking for approval.
7. At the end, summarize the exact commands to run locally and the first implementation milestone.

Follow the TDD boundaries: Django/DRF owns public APIs and core domain data; FastAPI is private matching computation only; PostgreSQL is the source of truth; React web and React Native Android are separate clients. Prefer a modular monolith. Build the MVP core loop before post-MVP features.

Wait for review of the repository assessment and implementation plan before proceeding to code generation.

# ROOMSYNC

## Technical Design Document (TDD)

**Document version:** 1.0\
**Status:** Engineering baseline for MVP implementation\
**Product:** RoomSync --- "Find your people before finding your place."\
**Market:** India initially\
**Source of truth:** RoomSync PRD v1.0\
**Client platforms:** Responsive web + Android\
**Primary stack:** React + TypeScript, Django + Django REST Framework,
FastAPI, PostgreSQL\
**Repository strategy:** Monorepo\
**Architecture:** Modular monolith with a bounded internal FastAPI
compute service

------------------------------------------------------------------------

# 1. Purpose, scope, and design decisions

This document translates the RoomSync PRD into an
implementation-oriented engineering blueprint. It defines the system
boundaries, runtime components, data model, APIs, matching algorithm,
security controls, deployment model, and delivery sequence.

The PRD remains the authority for product scope and user-facing
requirements. This TDD is the authority for the technical
implementation. If product behaviour changes, update the PRD and then
reconcile this document.

## 1.1 Goals

-   Deliver a maintainable MVP for roommate discovery, explainable
    compatibility, mutual connections, basic messaging, and initial
    accommodation listings.
-   Support web and Android clients from the same backend.
-   Keep the core system simple enough for a small team or solo
    developer to operate.
-   Keep compatibility scoring deterministic, testable, explainable, and
    independently optimizable.
-   Protect personal profiles, location information, messages, and
    verification material.
-   Provide clear seams for later group matching, AI assistance,
    advanced search, and ML ranking.

## 1.2 Non-goals for MVP

The first release will not implement payment processing, rent/deposit
custody, legally binding rental agreements, predictive personality
profiling, automated background checks, complex property management,
full community forums, or a trained ML recommendation model. These
remain future capabilities from the PRD.

## 1.3 Confirmed decisions and recommended implementation

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Frontend                            React + TypeScript for web; React
                                      Native with Expo for Android

  Backend                             Django as the authoritative domain
                                      backend

  Public API                          Django REST Framework (DRF),
                                      versioned REST API

  FastAPI                             Private internal service for
                                      compatibility computation and later
                                      AI/ML workloads; not a second
                                      competing public backend

  Database                            PostgreSQL; pgAdmin is an
                                      administration client, not the
                                      database

  Architecture                        Modular monolith, with FastAPI as a
                                      narrowly scoped internal compute
                                      service

  Matching                            Deterministic rule-based weighted
                                      scoring for MVP; ML only after
                                      outcome data exists

  Repository                          Monorepo with separately deployable
                                      web, Android, Django, and FastAPI
                                      apps

  Async work                          Celery workers + Redis; use for
                                      notifications, media processing,
                                      scheduled tasks, and expensive
                                      recomputation

  File storage                        S3-compatible object storage;
                                      private buckets for verification
                                      evidence

  Web hosting                         Vercel or Cloudflare Pages for
                                      React web

  API hosting                         Render initially for Django,
                                      FastAPI, and worker processes; move
                                      to AWS when operational needs
                                      justify it

  Database hosting                    Managed PostgreSQL with automated
                                      backups; keep pgAdmin local or
                                      behind a secure private network

  Android delivery                    Expo EAS build and Google Play
                                      internal testing, then production

  Observability                       Structured logs, Sentry, health
                                      checks, uptime monitoring
  -----------------------------------------------------------------------

**Important boundary:** Django owns authentication integration, users,
profiles, preferences, listings, connections, groups, conversations,
permissions, moderation, and transactional data. FastAPI does not
independently own users or write core product records. Django calls
FastAPI for matching calculations and receives a versioned result. This
avoids split-brain business logic and duplicate APIs.

## 1.4 Architecture decision records

### ADR-001: Modular monolith instead of microservices

A modular Django application is the primary product backend. Modules
have explicit boundaries but share one PostgreSQL database and one
deployment unit. This reduces deployment, debugging, and data
consistency complexity. Extract a module only when scaling, team
ownership, or reliability requirements demonstrate a real need.

### ADR-002: Django REST Framework as the public API

DRF provides authentication integration, serializers, permissions,
throttling, pagination, browsable API support, and a mature ecosystem.
React web and React Native clients consume the same `/api/v1/` contract.

### ADR-003: FastAPI is a private compute service

FastAPI is used where its lightweight ASGI interface and typed
request/response models are useful: compatibility calculations, batch
scoring, and future AI inference. It is internal-only at first. It must
not become a parallel source of truth or expose private user records
directly to the internet.

### ADR-004: React web + React Native Android

React web and React Native share TypeScript types, validation schemas,
API client utilities, design tokens, and selected platform-agnostic
components. Do not force web-only components into React Native. Expo
provides a practical Android build and release workflow.

### ADR-005: PostgreSQL is the system of record

PostgreSQL stores transactional and relational data. pgAdmin is used by
developers/operators to inspect and administer PostgreSQL; it is not an
application dependency and must not be publicly exposed.

### ADR-006: Rule-based matching first

The PRD explicitly states that initial weights are hypotheses and that a
proprietary training dataset does not yet exist. A deterministic scoring
engine is the correct MVP choice. Log user feedback and eventual
roommate outcomes so a future ranking model can be evaluated
responsibly.

------------------------------------------------------------------------

# 2. System context and architecture

## 2.1 Logical context

``` mermaid
flowchart LR
    U[Users] --> W[React Web]
    U --> A[React Native Android]
    W --> G[HTTPS API]
    A --> G
    G --> D[Django + DRF]
    D --> P[(PostgreSQL)]
    D --> R[(Redis)]
    D --> F[FastAPI internal matching]
    D --> O[Object Storage]
    D --> C[Celery workers]
    C --> P
    C --> R
    C --> N[Email / Push providers]
    F --> P
    D --> S[Maps / OTP / Email providers]
```

## 2.2 Deployment view

``` mermaid
flowchart TB
    subgraph Clients
      WEB[React Web - CDN]
      AND[Android App - Play Store]
    end
    subgraph Cloud
      EDGE[HTTPS Edge / WAF]
      API[Django DRF API]
      MATCH[FastAPI Internal Service]
      WORKER[Celery Worker]
      BEAT[Celery Beat]
      REDIS[(Managed Redis)]
      DB[(Managed PostgreSQL)]
      OBJ[(S3-compatible Storage)]
    end
    WEB --> EDGE
    AND --> EDGE
    EDGE --> API
    API --> DB
    API --> REDIS
    API --> MATCH
    API --> OBJ
    REDIS --> WORKER
    REDIS --> BEAT
    WORKER --> DB
    WORKER --> OBJ
    MATCH --> DB
```

## 2.3 Request ownership

-   Web and Android clients make HTTPS requests to Django DRF only.
-   Django authenticates the user, validates input, applies permissions,
    performs domain operations, and persists state.
-   Django may call FastAPI over a private network using a service
    credential and short timeout.
-   FastAPI computes compatibility from a minimal, explicit payload. It
    should not receive names, phone numbers, email addresses, exact
    addresses, or identity documents.
-   Django persists the returned compatibility result and explanation
    snapshot.
-   Celery performs non-interactive work such as notifications, image
    processing, and large compatibility refresh batches.
-   PostgreSQL is the authoritative record store.
-   Object storage holds images and private evidence. The database
    stores object keys and metadata, not binary files.

## 2.4 Network zones

1.  **Public zone:** web client, Android client, CDN, public HTTPS API.
2.  **Application zone:** Django, Celery workers, FastAPI.
3.  **Data zone:** PostgreSQL, Redis, object storage.
4.  **Operator zone:** private admin access, pgAdmin, deployment
    console, secrets manager.

Only HTTPS endpoints intended for users are public. FastAPI, Redis,
PostgreSQL, and pgAdmin must not be exposed to the public internet.

------------------------------------------------------------------------

# 3. Technology stack

  -----------------------------------------------------------------------
  Layer                   Technology              Rationale
  ----------------------- ----------------------- -----------------------
  Web                     React + TypeScript +    User-requested React;
                          Vite                    fast SPA development

  Web routing             React Router            Client-side routing

  Web server-state        TanStack Query          Caching, retries,
                                                  invalidation,
                                                  pagination

  Web forms               React Hook Form + Zod   Typed forms and
                                                  validation

  Styling                 Tailwind CSS            Consistent responsive
                                                  UI

  UI primitives           Accessible component    Reusable accessible
                          library (e.g. shadcn/ui components
                          for web)                

  Android                 React Native + Expo +   Android app using React
                          TypeScript              ecosystem

  Android navigation      Expo Router             File-based navigation

  Backend                 Python + Django         Mature domain framework
                                                  and admin

  Public API              Django REST Framework   Versioned REST
                                                  endpoints

  API schema              drf-spectacular /       Contract generation
                          OpenAPI                 

  Internal compute API    FastAPI + Pydantic      Typed internal scoring
                                                  service

  Database                PostgreSQL              Relational integrity
                                                  and robust indexing

  DB admin                pgAdmin                 Human-operated database
                                                  administration only

  ORM/migrations          Django ORM + Django     One authoritative
                          migrations              schema migration system

  Cache / broker          Redis                   Cache, Celery broker,
                                                  throttling support

  Background jobs         Celery                  Notifications and
                                                  deferred processing

  Realtime                Django Channels or      Do not build custom
                          managed push/realtime   realtime infrastructure
                          provider, phased        prematurely

  Media                   S3-compatible object    Separate media from
                          storage                 database

  Testing                 pytest, Django test     Unit through end-to-end
                          tools, Vitest, React    
                          Native Testing Library, 
                          Playwright              

  CI/CD                   GitHub Actions          Automated checks and
                                                  deployments

  Monitoring              Sentry + structured     Error visibility
                          application logs        

  Containerization        Docker + Docker Compose Reproducible local
                                                  environment
  -----------------------------------------------------------------------

Pin dependency versions and upgrade deliberately. Avoid adopting every
optional service in the first sprint.

------------------------------------------------------------------------

# 4. Repository and code organization

## 4.1 Recommended monorepo

``` text
roomsync/
├── apps/
│   ├── web/                       # React web application
│   ├── android/                   # Expo / React Native app
│   ├── backend/                   # Django + DRF authoritative backend
│   └── matching-service/          # FastAPI internal compute service
├── packages/
│   ├── api-client/                # Generated/typed API client
│   ├── contracts/                 # Shared TypeScript schemas and types
│   ├── design-tokens/             # Shared colors, spacing, typography
│   └── config/                    # Shared lint/format/TS configuration
├── infrastructure/
│   ├── docker/
│   ├── nginx/                     # Only if self-hosting reverse proxy
│   └── scripts/
├── docs/
│   ├── PRD.md
│   ├── TDD.md
│   ├── API_CONVENTIONS.md
│   └── ADR/
├── .github/workflows/
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile
```

Use `pnpm` workspaces for JavaScript/TypeScript packages and `uv` or
Poetry for Python dependency management. Keep Python environments
isolated per service. Do not share Python runtime code between Django
and FastAPI through imports; share only a small, versioned matching-core
package if it is genuinely useful and tested independently.

## 4.2 Branching strategy

-   `main`: production-ready, protected.
-   `develop`: optional integration branch if multiple contributors need
    it; solo development can use short-lived feature branches directly
    from `main`.
-   `feat/<short-name>`: feature work.
-   `fix/<short-name>`: bug fixes.
-   Pull requests should pass CI before merge.
-   Use conventional commit messages if useful,
    e.g. `feat(matching): add deal-breaker evaluation`.

## 4.3 Code quality

-   TypeScript strict mode.
-   Python type hints on service boundaries.
-   Ruff for Python lint/format; mypy or pyright for critical typed
    modules.
-   ESLint + Prettier for TypeScript.
-   Pre-commit hooks for formatting and basic checks.
-   No secrets in source control.
-   Every module has a README or clear package-level documentation when
    its responsibilities are not obvious.

------------------------------------------------------------------------

# 5. Backend domain architecture

## 5.1 Django project layout

``` text
apps/backend/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/
│   ├── profiles/
│   ├── preferences/
│   ├── matching/
│   ├── discovery/
│   ├── connections/
│   ├── messaging/
│   ├── listings/
│   ├── groups/
│   ├── verification/
│   ├── moderation/
│   ├── notifications/
│   ├── reviews/
│   ├── shared_living/
│   └── audit/
├── common/
│   ├── models.py
│   ├── permissions.py
│   ├── pagination.py
│   ├── exceptions.py
│   └── storage.py
└── tests/
```

Each Django app should own its models, serializers, selectors/query
services, domain services, API views/viewsets, permissions, tasks, and
tests. Keep business rules out of serializers and views. Views
coordinate; services implement use cases; selectors encapsulate complex
reads.

## 5.2 Domain module responsibilities

  -----------------------------------------------------------------------
  Module                              Responsibility
  ----------------------------------- -----------------------------------
  accounts                            User identity, authentication
                                      linkage, account status, sessions

  profiles                            Public/private profile fields,
                                      visibility, profile completion

  preferences                         Questionnaire definitions, answers,
                                      deal-breakers, housing preferences

  matching                            Match orchestration, score
                                      snapshots, explanations, feedback

  discovery                           Candidate filtering, pagination,
                                      ranking and feed

  connections                         Likes, requests, mutual connection
                                      state, blocks

  messaging                           Conversations, membership,
                                      messages, read state

  listings                            Accommodation listing lifecycle,
                                      media metadata, enquiries

  groups                              Group lifecycle, invitations,
                                      membership, votes, group
                                      compatibility

  verification                        Verification cases and status
                                      metadata

  moderation                          Reports, case handling, suspension
                                      decisions

  notifications                       In-app notification records and
                                      delivery preferences

  reviews                             Eligible reviews and moderation

  shared_living                       Informal agreements, expenses,
                                      tasks (later phase)

  audit                               Immutable administrative audit
                                      events
  -----------------------------------------------------------------------

## 5.3 Domain service rules

-   Do not allow one app to write another app's tables directly in
    arbitrary view code.
-   Cross-module operations should call an explicit service function.
-   Use database transactions for multi-record state transitions.
-   Use `select_related` and `prefetch_related` to prevent N+1 queries.
-   Avoid signals for critical business workflows; explicit service
    calls are easier to reason about.
-   Use an outbox pattern for reliable external notifications where
    delivery must not be lost.
-   Never accept user IDs, owner IDs, or admin privileges from the
    client without deriving/authorizing them server-side.

------------------------------------------------------------------------

# 6. Database design

## 6.1 Conventions

-   PostgreSQL 16+ (or currently supported managed version at
    deployment).
-   Primary keys: UUID (`uuid`); generated server-side.
-   Timestamps: `timestamptz`, stored in UTC.
-   Currency: integer minor units (`rent_amount_paise`,
    `deposit_amount_paise`) plus ISO currency code (`INR`), avoiding
    floating-point arithmetic.
-   Text: bounded `varchar` for constrained fields; `text` for
    descriptions.
-   Enumerations: Django `TextChoices`/validated strings; use database
    constraints for critical finite states.
-   Soft deletion: only where retention/audit requirements justify it;
    do not soft-delete everything by default.
-   Every mutable business entity has `created_at` and `updated_at`.
-   Use `JSONB` only for flexible, versioned questionnaire answers or
    metadata---not as a substitute for relational columns used in
    filters and joins.
-   Add indexes based on actual query patterns and verify with
    `EXPLAIN ANALYZE`.
-   Use migrations as the only schema change mechanism. Never manually
    edit production schema through pgAdmin.

## 6.2 Entity relationship diagram

``` mermaid
erDiagram
    USER ||--o| PROFILE : has
    USER ||--o{ LIFESTYLE_RESPONSE : answers
    QUESTION ||--o{ LIFESTYLE_RESPONSE : receives
    USER ||--o| ACCOMMODATION_PREFERENCE : sets
    USER ||--o{ VERIFICATION_CASE : submits
    USER ||--o{ LIKE : sends
    USER ||--o{ LIKE : receives
    USER ||--o{ CONNECTION : participates
    CONNECTION ||--o| CONVERSATION : opens
    CONVERSATION ||--o{ CONVERSATION_MEMBER : contains
    USER ||--o{ CONVERSATION_MEMBER : joins
    CONVERSATION ||--o{ MESSAGE : contains
    USER ||--o{ MESSAGE : sends
    USER ||--o{ LISTING : owns
    LISTING ||--o{ LISTING_MEDIA : has
    LISTING ||--o{ LISTING_ENQUIRY : receives
    USER ||--o{ LISTING_ENQUIRY : creates
    USER ||--o{ ROOMMATE_GROUP : creates
    ROOMMATE_GROUP ||--o{ GROUP_MEMBER : contains
    USER ||--o{ GROUP_MEMBER : joins
    ROOMMATE_GROUP ||--o{ GROUP_INVITATION : issues
    USER ||--o{ SAVED_PROFILE : saves
    USER ||--o{ SAVED_LISTING : saves
    USER ||--o{ REPORT : submits
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ BLOCK : blocks
    USER ||--o{ COMPATIBILITY_SNAPSHOT : subject
```

## 6.3 Core schema

The following is the logical schema baseline. Implement these as Django
models with explicit constraints and indexes. Field names are
snake_case. Optional fields are nullable; required fields should be
non-null.

### 6.3.1 accounts_user

  -----------------------------------------------------------------------
  Field                   Type                    Rules
  ----------------------- ----------------------- -----------------------
  id                      uuid                    PK

  email                   citext / varchar(254)   unique when present;
                                                  normalized

  phone_e164              varchar(20)             unique when
                                                  verified/present;
                                                  normalized

  password                varchar                 Django password hash
                                                  only; nullable if
                                                  external auth only

  status                  varchar(20)             active, pending,
                                                  suspended, deleted

  is_staff                boolean                 Django admin access;
                                                  tightly controlled

  is_superuser            boolean                 break-glass only

  email_verified_at       timestamptz             nullable

  phone_verified_at       timestamptz             nullable

  last_login              timestamptz             nullable

  created_at / updated_at timestamptz             required
  -----------------------------------------------------------------------

Use a custom Django user model from the first migration
(`AUTH_USER_MODEL`). Email/phone authentication policy must be finalized
before launch. Do not store OTP values in plaintext.

### 6.3.2 profiles_profile

  -------------------------------------------------------------------------
  Field                     Type                    Rules
  ------------------------- ----------------------- -----------------------
  id                        uuid                    PK

  user_id                   uuid                    FK accounts_user,
                                                    unique

  display_name              varchar(80)             required

  date_of_birth             date                    private; derive age
                                                    range where possible

  occupation_type           varchar(30)             student, intern,
                                                    professional, other

  institution_or_employer   varchar(160)            optional and
                                                    visibility-controlled

  bio                       varchar(500)            optional

  avatar_object_key         varchar(512)            optional

  current_city_id           uuid                    FK locations_city,
                                                    nullable

  profile_visibility        varchar(20)             discoverable,
                                                    connections_only,
                                                    hidden

  completion_percent        smallint                0--100,
                                                    derived/recomputed

  created_at / updated_at   timestamptz             required
  -------------------------------------------------------------------------

Never expose date of birth, email, phone, exact location, or
verification evidence in public profile serialization.

### 6.3.3 locations_city and locations_locality

`locations_city`: `id uuid PK`, `name varchar(100)`,
`state varchar(100)`, `country_code char(2)`, `slug varchar(140)`,
`is_active boolean`, timestamps. Unique `(slug, country_code)`.

`locations_locality`: `id uuid PK`, `city_id uuid FK`,
`name varchar(120)`, optional centroid `geography(Point,4326)` if
PostGIS is enabled, `slug varchar(160)`, timestamps. Unique
`(city_id, slug)`.

Use a curated locality dataset initially. Do not store a user's exact
home address as a public discovery field. Enable PostGIS only when
radius/distance queries justify it.

### 6.3.4 preferences_question and preferences_answer

`preferences_question`: `id uuid PK`, `key varchar(80) unique`,
`category varchar(40)`, `prompt varchar(300)`,
`answer_type varchar(20)`, `options jsonb`, `is_required boolean`,
`is_active boolean`, `version integer`, `display_order integer`,
timestamps.

`preferences_answer`: `id uuid PK`, `user_id uuid FK`,
`question_id uuid FK`, `answer jsonb`, `importance varchar(20)`
(must_have, important, flexible), `is_deal_breaker boolean`,
`updated_at timestamptz`. Unique `(user_id, question_id)`. Check
constraint: `is_deal_breaker` can only be true for supported question
types.

Store canonical answer values, not display labels. Version questions so
historical score snapshots remain interpretable. Do not change the
meaning of a question key in place; create a new version/key.

### 6.3.5 preferences_accommodation

`id uuid PK`, `user_id uuid FK unique`, `city_id uuid FK`,
`preferred_locality_ids uuid[]` (or normalized join table),
`budget_min_paise bigint`, `budget_max_paise bigint`,
`preferred_move_in_date date`, `stay_duration_months smallint`,
`property_types varchar[]`, `room_sharing_preference varchar(30)`,
`furnishing_preference varchar(20)`, `needs_ac boolean`,
`needs_private_bathroom boolean`, `updated_at timestamptz`.

For locality filtering and referential integrity at scale, prefer
normalized
`accommodation_preference_localities(preference_id, locality_id)` over
an array.

### 6.3.6 verification_case

`id uuid PK`, `user_id uuid FK`, `verification_type varchar(30)` (email,
phone, student, identity, property), `status varchar(20)` (pending,
approved, rejected, expired), `provider_reference varchar(160)`,
`evidence_object_key varchar(512)` nullable,
`reviewed_by_id uuid FK user nullable`, `reviewed_at timestamptz`,
`rejection_reason_code varchar(60)` nullable, timestamps.

Sensitive evidence belongs in a private bucket with short-lived signed
URLs and strict staff authorization. Store minimal metadata; define
deletion/retention rules before collecting identity documents.

### 6.3.7 matching_compatibility_snapshot

`id uuid PK`, `user_low_id uuid FK`, `user_high_id uuid FK`,
`score numeric(5,2)`, `status varchar(20)` (eligible,
blocked_by_dealbreaker, insufficient_data), `category_scores jsonb`,
`explanations jsonb`, `algorithm_version varchar(40)`,
`weights_version varchar(40)`, `input_fingerprint varchar(64)`,
`computed_at timestamptz`.

Canonicalize pair ordering (`user_low_id < user_high_id`) and unique
`(user_low_id, user_high_id, algorithm_version, input_fingerprint)`.
Store score inputs/version metadata sufficient to reproduce or explain a
result. Do not expose raw private answers; persist safe explanation
codes and rendered text.

### 6.3.8 connections_like

`id uuid PK`, `sender_id uuid FK`, `recipient_id uuid FK`,
`status varchar(20)` (active, withdrawn, rejected, expired),
`created_at`, `updated_at`. Check sender != recipient. Unique active
directional pair via partial unique index or enforce in transaction. A
mutual like creates/activates a connection.

### 6.3.9 connections_connection

`id uuid PK`, `user_low_id uuid FK`, `user_high_id uuid FK`,
`status varchar(20)` (active, closed), `created_at`, `closed_at`. Check
canonical order and users differ. Unique pair. Create atomically when
reciprocal active likes exist.

### 6.3.10 connections_block

`id uuid PK`, `blocker_id uuid FK`, `blocked_id uuid FK`,
`reason_code varchar(40)` nullable, `created_at`. Check users differ.
Unique `(blocker_id, blocked_id)`. All discovery, connection, and
messaging queries must exclude either-direction blocks.

### 6.3.11 messaging_conversation and messaging_message

`messaging_conversation`: `id uuid PK`, `connection_id uuid FK unique`,
`status varchar(20)`, `last_message_at timestamptz`, timestamps.

`messaging_conversation_member`: `id uuid PK`,
`conversation_id uuid FK`, `user_id uuid FK`,
`last_read_at timestamptz`, `muted_until timestamptz`, unique
`(conversation_id, user_id)`.

`messaging_message`: `id uuid PK`, `conversation_id uuid FK`,
`sender_id uuid FK`, `message_type varchar(20)` (text initially),
`body varchar(4000)`, `created_at`, `edited_at`, `deleted_at`. Index
`(conversation_id, created_at DESC)`. Validate sender is a conversation
member and connection remains eligible.

### 6.3.12 listings_listing

`id uuid PK`, `owner_id uuid FK`, `title varchar(140)`,
`description text`, `property_type varchar(30)`, `city_id uuid FK`,
`locality_id uuid FK`, `approximate_location geography(Point,4326)`
optional, `rent_amount_paise bigint`, `deposit_amount_paise bigint`,
`maintenance_amount_paise bigint`, `currency char(3) default INR`,
`available_occupancy smallint`, `available_from date`,
`furnishing varchar(20)`, `amenities jsonb` or normalized amenities
table, `rules jsonb`, `status varchar(20)` (draft, pending_review,
published, occupied, rejected, suspended, archived),
`verification_status varchar(20)`, timestamps.

Public results should show approximate location only. Exact
address/contact details should be shared only through an authorized
enquiry flow. Add database checks for non-negative money and positive
occupancy.

### 6.3.13 listings_media and listings_enquiry

`listings_media`: `id uuid PK`, `listing_id uuid FK`,
`object_key varchar(512)`, `media_type varchar(20)`,
`sort_order smallint`, `moderation_status varchar(20)`, `created_at`.

`listings_enquiry`: `id uuid PK`, `listing_id uuid FK`,
`user_id uuid FK`, `message varchar(1000)`, `status varchar(20)`,
timestamps. Unique or deduplicate repeated active enquiries according to
product policy.

### 6.3.14 groups

`roommate_group`: `id uuid PK`, `created_by_id uuid FK`,
`name varchar(100)`, `city_id uuid FK`,
`target_locality_id uuid FK nullable`, `budget_total_paise bigint`,
`target_member_count smallint`, `move_in_date date`,
`visibility varchar(20)`, `status varchar(20)`, timestamps.

`group_member`: `id uuid PK`, `group_id uuid FK`, `user_id uuid FK`,
`role varchar(20)`, `status varchar(20)`, `joined_at timestamptz`,
unique `(group_id, user_id)`.

`group_invitation`: `id uuid PK`, `group_id uuid FK`,
`inviter_id uuid FK`, `invitee_id uuid FK`, `token_hash varchar(128)`
nullable, `status varchar(20)`, `expires_at timestamptz`, timestamps.

Group membership and invitation acceptance must be transactional. Never
trust a client-provided group role.

### 6.3.15 saved items, reports, notifications, audit

`saved_profile(user_id, profile_user_id, created_at)` with composite
unique key and self-save prohibited.

`saved_listing(user_id, listing_id, created_at)` with composite unique
key.

`report`: `id uuid PK`, `reporter_id uuid FK`,
`target_type varchar(30)`, `target_id uuid`, `reason_code varchar(50)`,
`details varchar(2000)`, `status varchar(20)`,
`assigned_to_id uuid FK nullable`, timestamps. Because `target_id` is
polymorphic, validate the target in the service layer and retain an
immutable evidence snapshot where appropriate.

`notification`: `id uuid PK`, `user_id uuid FK`, `type varchar(60)`,
`payload jsonb`, `read_at timestamptz`, `created_at`. Payload must not
contain secrets or unnecessary personal data.

`admin_audit_log`: `id uuid PK`, `actor_id uuid FK`,
`action varchar(80)`, `target_type varchar(60)`, `target_id uuid`,
`reason varchar(500)`, `metadata jsonb`, `created_at`,
`request_id varchar(64)`. Append-only for normal application roles.

### 6.3.16 Future tables

Add only when corresponding features are approved: `review`,
`review_eligibility`, `roommate_agreement`, `shared_expense`,
`expense_split`, `household_task`, `subscription`, `payment_event`,
`group_property_vote`, `community`, and `community_post`.

## 6.4 Relationship cardinality summary

-   User 1:1 Profile.
-   User 1:1 AccommodationPreference (current active preference set).
-   User 1:N LifestyleAnswer.
-   Question 1:N LifestyleAnswer.
-   User 1:N VerificationCase.
-   User 1:N Like as sender and 1:N Like as recipient.
-   User pair 1:0..1 Connection.
-   Connection 1:0..1 Conversation.
-   Conversation 1:N ConversationMember and 1:N Message.
-   User 1:N Listing; Listing 1:N ListingMedia and 1:N ListingEnquiry.
-   Group 1:N GroupMember and 1:N GroupInvitation.
-   User N:M Group through GroupMember.
-   User N:M saved profiles and listings through join tables.
-   User 1:N Reports and Notifications.

## 6.5 Index strategy

Create indexes for actual access patterns, not every field.

  -------------------------------------------------------------------------------------------
  Table                               Index
  ----------------------------------- -------------------------------------------------------
  user                                unique normalized email; unique phone where present;
                                      `(status, created_at)`

  profile                             unique `user_id`;
                                      `(profile_visibility, current_city_id)` where useful

  lifestyle_answer                    unique `(user_id, question_id)`;
                                      `(question_id, updated_at)`

  accommodation_preference            `(city_id, budget_max_paise, preferred_move_in_date)`

  compatibility_snapshot              unique pair/version/fingerprint;
                                      `(user_low_id, computed_at DESC)` and
                                      `(user_high_id, computed_at DESC)`

  like                                unique directional pair;
                                      `(recipient_id, status, created_at DESC)`

  connection                          unique canonical pair; `(user_low_id, status)` and
                                      `(user_high_id, status)`

  block                               unique blocker/blocked; indexes both directions

  conversation                        unique connection; `(last_message_at DESC)`

  message                             `(conversation_id, created_at DESC, id DESC)`

  listing                             `(city_id, status, available_from)`;
                                      `(locality_id, status)`; `(rent_amount_paise)`

  listing_enquiry                     `(listing_id, status, created_at DESC)`;
                                      `(user_id, created_at DESC)`

  group_member                        unique `(group_id, user_id)`; `(user_id, status)`

  notification                        `(user_id, read_at, created_at DESC)`

  report                              `(status, created_at)`; `(target_type, target_id)`
  -------------------------------------------------------------------------------------------

Use GIN indexes for JSONB only when querying JSONB keys frequently. For
location-radius queries, use PostGIS geography with GiST index. Review
query plans after representative seed data is loaded.

## 6.6 Data integrity and transactions

-   Use `UniqueConstraint`, `CheckConstraint`, and foreign keys for
    invariant enforcement.
-   Use `transaction.atomic()` for mutual match creation, group
    invitation acceptance, and listing state transitions.
-   Use row-level locking (`select_for_update`) where concurrent
    requests could create duplicate state.
-   Use idempotency keys for retryable write endpoints where duplicate
    submission would be harmful.
-   Use database constraints as the final guard; application validation
    alone is insufficient.

## 6.7 Data lifecycle

Define retention by data category before public launch: -
Account/profile data: retained while account active;
deletion/anonymization workflow on valid request. - Messages:
user-visible retention policy; preserve only what is legally and
operationally necessary. - Verification evidence: shortest justified
retention; private storage and scheduled deletion. - Audit records:
restricted access and documented retention. - Analytics: aggregate or
pseudonymize wherever possible. - Backups: expire according to a
documented schedule; deletion from backups may occur on backup expiry,
which must be explained in the privacy notice.

------------------------------------------------------------------------

# 7. Authentication, authorization, and identity

## 7.1 Recommended authentication design

Use Django as the identity authority. For web, prefer secure, HttpOnly,
Secure, SameSite cookies with CSRF protection when using same-site web
deployment. For Android, use short-lived access tokens and rotating
refresh tokens stored in platform-secure storage (Expo SecureStore). Do
not store tokens in AsyncStorage.

If Google login is supported, validate provider tokens server-side and
map the verified provider subject to the RoomSync user. Do not trust
client-supplied email claims.

## 7.2 Authorization model

Use role/capability checks plus object-level permissions.

-   Anonymous: public marketing pages and explicitly public
    listings/profiles only.
-   Authenticated user: own profile, own preferences, discovery, saved
    items.
-   Connected users: permitted profile details and conversation access.
-   Listing owner: manage own listings and enquiries.
-   Group member: access group details permitted by membership.
-   Moderator: review assigned reports and verification cases.
-   Admin: privileged operations with audit logs.
-   Superuser: tightly restricted operational account, not a routine
    product role.

Every endpoint must enforce permissions on the server. Hiding a button
in React is not authorization.

## 7.3 Important security rules

-   Users may only edit their own profile and preferences.
-   A user may not read a conversation unless they are a current member.
-   A blocked pair cannot send new connection requests or messages.
-   Listing mutation requires owner or authorized staff permission.
-   Verification evidence requires a specific permission and access
    audit.
-   Admin actions require a reason for high-impact actions such as
    suspension or verification override.
-   Rate-limit login, OTP, password reset, connection requests,
    messaging, and report creation.

## 7.4 Session and token lifecycle

-   Access tokens should be short-lived.
-   Refresh tokens should rotate and be revocable.
-   Logout revokes the refresh token/session.
-   Password changes invalidate other active sessions where appropriate.
-   Detect refresh-token reuse and revoke the token family.
-   Use MFA for staff/admin accounts.
-   Keep service-to-service credentials separate from user credentials.

------------------------------------------------------------------------

# 8. API design

## 8.1 Public API conventions

Base URL: `/api/v1/`

-   HTTPS only.
-   JSON request/response bodies.
-   UUID resource identifiers.
-   ISO-8601 UTC timestamps.
-   Pagination for all potentially large collections.
-   Consistent error envelope.
-   OpenAPI schema generated from DRF.
-   Never expose Django model internals directly.
-   API changes must be backward-compatible within a version; breaking
    changes require a new version.

### Success response example

``` json
{
  "data": {
    "id": "uuid",
    "status": "active"
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

### Paginated response example

``` json
{
  "data": [],
  "pagination": {
    "next_cursor": "opaque-cursor-or-null",
    "has_more": false
  }
}
```

### Error response example

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "field_errors": {
      "budget_max": ["Must be greater than or equal to minimum budget."]
    },
    "request_id": "req_..."
  }
}
```

Do not return stack traces, SQL errors, secret values, or internal
service details.

## 8.2 Endpoint inventory

  ---------------------------------------------------------------------------------------
  Method                  Endpoint                                Purpose
  ----------------------- --------------------------------------- -----------------------
  POST                    `/auth/register`                        Register account

  POST                    `/auth/login`                           Login

  POST                    `/auth/refresh`                         Rotate refresh token

  POST                    `/auth/logout`                          Revoke session

  POST                    `/auth/password/forgot`                 Request password reset

  POST                    `/auth/password/reset`                  Complete reset

  GET/PATCH               `/me`                                   Current account summary

  GET/PATCH               `/me/profile`                           Read/update own profile

  GET                     `/profiles/{id}`                        Authorized profile view

  GET                     `/preferences/questions`                Active questionnaire

  GET/PUT                 `/me/preferences/lifestyle`             Read/replace own
                                                                  answers

  GET/PUT                 `/me/preferences/accommodation`         Read/update housing
                                                                  preferences

  GET                     `/discover/roommates`                   Filtered, ranked
                                                                  roommate feed

  GET                     `/profiles/{id}/compatibility`          Explain compatibility
                                                                  with profile

  POST                    `/connections/likes`                    Express interest

  GET                     `/connections/requests`                 Incoming/outgoing
                                                                  requests

  POST                    `/connections/requests/{id}/accept`     Accept request

  POST                    `/connections/requests/{id}/withdraw`   Withdraw request

  GET                     `/connections`                          Active connections

  POST/DELETE             `/blocks`                               Block/unblock user

  GET/POST                `/conversations`                        List/create eligible
                                                                  conversations

  GET/POST                `/conversations/{id}/messages`          Read/send messages

  POST                    `/listings`                             Create listing

  GET                     `/listings`                             Search listings

  GET/PATCH/DELETE        `/listings/{id}`                        Read/update/archive
                                                                  listing

  POST                    `/listings/{id}/enquiries`              Enquire

  POST                    `/listings/{id}/media/upload-url`       Request signed upload
                                                                  URL

  POST                    `/groups`                               Create group

  GET                     `/groups`                               Discover/list own
                                                                  groups

  POST                    `/groups/{id}/invitations`              Invite member

  POST                    `/groups/invitations/{id}/accept`       Accept invite

  POST                    `/reports`                              Submit report

  GET                     `/notifications`                        List notifications

  PATCH                   `/notifications/{id}`                   Mark read

  GET/PATCH               `/me/notification-preferences`          Notification
                                                                  preferences
  ---------------------------------------------------------------------------------------

The endpoint inventory is a contract plan, not permission to implement
every PRD feature in the MVP. Build P0 endpoints first.

## 8.3 API validation and pagination

-   Validate all inputs with DRF serializers.
-   Set explicit maximum page sizes (e.g. 50).
-   Use cursor pagination for feeds and messages where stable ordering
    matters.
-   Use allowlisted sort fields; never pass arbitrary ORM ordering from
    the client.
-   Normalize phone numbers, email addresses, city/locality slugs, and
    enum values.
-   Reject unknown fields on sensitive write serializers where
    practical.

## 8.4 Idempotency and concurrency

For connection requests, group invitations, and listing creation, define
duplicate-submission behaviour. Use an `Idempotency-Key` header for
operations likely to be retried by mobile clients. Persist key, user,
route, request hash, response status, and expiry. Enforce unique
constraints in the database as well.

------------------------------------------------------------------------

# 9. Compatibility and recommendation engine

## 9.1 MVP strategy

Use a deterministic rule-based engine. The PRD's starting category
weights are:

  Category                   Initial weight
  ------------------------ ----------------
  Daily routine                          15
  Cleanliness                            15
  Financial expectations                 15
  Privacy and boundaries                 15
  Social lifestyle                       10
  Food preferences                       10
  Guest preferences                      10
  Work/study environment                 10
  **Total**                         **100**

These are initial product hypotheses. Store weights in versioned
configuration, not scattered constants.

## 9.2 Calculation pipeline

1.  Candidate eligibility filtering.
2.  Block and account-status exclusion.
3.  Hard deal-breaker evaluation.
4.  Per-question compatibility calculation.
5.  Category aggregation.
6.  Missing-data confidence calculation.
7.  Weighted overall score.
8.  Explanation-code generation.
9.  Ranking with non-compatibility filters such as budget, city, move-in
    date, and verification signals.

A deal-breaker is a veto and must never be overridden by a high score.

## 9.3 Question-level scoring

Each question has a scorer appropriate to its answer type: - Exact
categorical match: 100 for compatible, 0 for incompatible, or a defined
partial score. - Numeric/range preference: normalize distance against a
documented tolerance. - Time-of-day preference: use circular time
distance where midnight wraparound matters. - Multi-select: use Jaccard
similarity only when set overlap meaningfully represents
compatibility. - Boolean: map to explicit compatibility rules. - Free
text: exclude from numeric scoring in MVP.

Do not use a generic string-equality comparison for every question.

## 9.4 Weighted score and confidence

For answered, comparable categories:

`overall_score = sum(category_score × category_weight) / sum(weights_of_scored_categories)`

`coverage = sum(weights_of_scored_categories) / sum(all_applicable_category_weights)`

Return both score and coverage. A score of 90 with low coverage must not
look equivalent to a score of 90 with complete data. Product UI should
say "High compatibility based on limited information" when coverage is
low. Set a minimum coverage threshold for inclusion in the ranked feed;
tune it with pilot data.

The engine must define how asymmetric preferences are handled. For
mutual roommate fit, compare both users' expectations: an answer from
user A must be evaluated against user B's preference, and vice versa.
For example, one person's tolerance for guests is not enough; the
other's guest frequency and boundaries must also be considered.

## 9.5 Deal-breaker logic

-   A user may mark only supported preference questions as
    non-negotiable.
-   Evaluate both directions.
-   Missing answers do not automatically pass or fail; return `unknown`
    and apply the configured policy.
-   If a known hard conflict exists, status is `blocked_by_dealbreaker`;
    do not rank as a normal match.
-   Provide a neutral explanation such as "Your stated quiet-hour
    requirements may conflict."
-   Never expose sensitive answer values beyond the other user's
    visibility settings.

## 9.6 Result contract

``` json
{
  "algorithm_version": "roomsync-rule-v1",
  "weights_version": "weights-2026-01",
  "status": "eligible",
  "overall_score": 84.5,
  "coverage": 0.91,
  "category_scores": {
    "daily_routine": 90,
    "cleanliness": 80,
    "financial_expectations": 100
  },
  "explanation_codes": [
    "SLEEP_SCHEDULE_CLOSE",
    "CLEANING_EXPECTATIONS_DIFFER",
    "BUDGETS_OVERLAP"
  ],
  "computed_at": "2026-01-01T00:00:00Z"
}
```

Example values are illustrative, not actual user results.

## 9.7 FastAPI internal interface

`POST /internal/v1/compatibility/score`

Input contains: - Request ID. - Two pseudonymous user IDs. - Versioned,
minimal structured preference payloads. - Question schema version. -
Weight configuration version.

Output follows the result contract above.

Security: - Private network only. - Service-to-service authentication
(rotating secret or signed service JWT). - Request size limit. - Strict
Pydantic validation. - No public CORS. - Short timeout; Django handles
timeout/failure gracefully. - Do not log raw preference payloads. - No
database writes from FastAPI in MVP. Django persists the result.

FastAPI endpoints: - `GET /health/live` - `GET /health/ready` -
`POST /internal/v1/compatibility/score` -
`POST /internal/v1/compatibility/batch` (later, protected and bounded)

## 9.8 Recalculation and cache invalidation

Preference changes increment a `preferences_version` or update a
fingerprint. A result is reusable only when both users' input
fingerprints, algorithm version, question version, and weights version
match. Recompute on demand for MVP and enqueue background refresh for
frequently surfaced candidates later.

## 9.9 Evaluation and future ML

Collect explicit feedback: useful/not useful, connection accepted,
conversation initiated, mutually selected, move-in confirmed, and
post-move-in satisfaction (opt-in). Treat these as distinct labels, not
interchangeable. Before ML: - establish consent and retention policy; -
check sample size and label quality; - evaluate offline against a
baseline; - test fairness across relevant cohorts; - use a shadow
deployment; - retain explainability and user controls; - never infer
protected traits or use them as compatibility proxies.

------------------------------------------------------------------------

# 10. Discovery and ranking

Candidate generation should be inexpensive and privacy-aware: 1. Active,
discoverable profiles only. 2. Exclude self, suspended/deleted users,
blocked pairs, and users who opted out. 3. Apply hard accommodation
constraints (city, budget overlap, move-in window) when supplied. 4.
Fetch compatibility snapshots or compute a bounded set. 5. Rank by
compatibility plus product relevance signals. 6. Apply pagination and
stable tie-breaking.

Do not make verification a proxy for personality or compatibility.
Verification can be a separate trust indicator or a clearly documented
ranking signal, with user research and fairness review.

Avoid exposing the full candidate list through unbounded APIs. Prevent
scraping with authentication, throttling, pagination, anomaly detection,
and privacy-aware fields.

------------------------------------------------------------------------

# 11. Messaging and notifications

## 11.1 Messaging MVP

-   One conversation per active connection.
-   Text-only messages initially.
-   Conversation membership is checked for every read and write.
-   Blocked or closed connections cannot create new messages.
-   Message length limit and basic abuse controls.
-   Cursor pagination by `(created_at, id)`.
-   Do not expose email/phone automatically in chat.
-   Report and block controls available from conversation UI.

## 11.2 Realtime decision

Start with polling or a managed realtime provider if real-time delivery
is essential to the MVP. If self-hosting realtime, use Django Channels
with Redis channel layer and ASGI deployment. WebSocket handshake must
authenticate the user and authorize conversation membership. REST
remains the source of truth; WebSockets are a delivery channel, not a
separate message database.

## 11.3 Notifications

Create notification records transactionally. Deliver push/email
asynchronously through Celery. Use a transactional outbox for critical
notifications so a database commit cannot succeed while the event is
silently lost. Respect per-user preferences and avoid sending sensitive
profile details in push notification previews.

Android push: Expo Notifications initially; later consider direct FCM
integration if required. Email provider should be selected before
production and configured with SPF, DKIM, and DMARC.

------------------------------------------------------------------------

# 12. Media and file handling

-   Use direct-to-object-storage uploads via short-lived signed URLs.
-   Django authorizes the upload and issues a constrained URL; the
    client uploads directly.
-   Validate file extension, MIME type, actual file signature, file
    size, and image dimensions.
-   Re-encode public listing/profile images and strip EXIF metadata,
    especially GPS coordinates.
-   Malware-scan files where supported.
-   Keep identity/verification files in a separate private bucket with
    stricter policies.
-   Use opaque object keys; do not use user-provided filenames as
    storage paths.
-   Serve public images through CDN; private evidence only through
    authorized short-lived signed URLs.
-   Store object metadata and ownership in PostgreSQL.
-   Delete orphaned uploads with a scheduled cleanup task.

------------------------------------------------------------------------

# 13. Frontend architecture

## 13.1 Web app structure

``` text
apps/web/src/
├── app/
├── routes/
├── features/
│   ├── auth/
│   ├── onboarding/
│   ├── profile/
│   ├── preferences/
│   ├── discover/
│   ├── compatibility/
│   ├── connections/
│   ├── messages/
│   ├── listings/
│   └── settings/
├── components/
├── hooks/
├── lib/
│   ├── api/
│   ├── auth/
│   └── validation/
├── styles/
└── tests/
```

## 13.2 Android app structure

``` text
apps/android/
├── app/                           # Expo Router routes
├── src/
│   ├── features/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── theme/
├── assets/
└── tests/
```

## 13.3 Client state rules

-   TanStack Query owns server state and cache invalidation.
-   Local component state owns temporary UI state.
-   Avoid duplicating server records in a global state store.
-   Persist only necessary client preferences.
-   Never persist private tokens in unencrypted local storage.
-   API client attaches credentials, request IDs, and handles refresh
    safely.
-   Generate API types from OpenAPI where practical; avoid manually
    duplicating backend contracts.

## 13.4 Shared design system

Share design tokens, typography scale, spacing, color semantics, icons
mapping, validation schemas, and API types. Use platform-specific
components for navigation, modals, keyboard handling, file selection,
and accessibility. Test both platforms independently.

------------------------------------------------------------------------

# 14. Security and privacy engineering

## 14.1 Threat model

  -----------------------------------------------------------------------
  Threat                              Controls
  ----------------------------------- -----------------------------------
  Account takeover                    Secure password hashing, MFA for
                                      staff, refresh rotation, rate
                                      limits

  Profile scraping                    Authenticated discovery,
                                      pagination, throttling, minimal
                                      public fields

  IDOR / broken object authorization  Object-level permission checks and
                                      negative tests

  Fake listings                       Moderation workflow, evidence,
                                      reports, verification labels

  Verification document leak          Private bucket, short-lived URLs,
                                      strict staff access, audit

  Message harassment                  Block/report, rate limits,
                                      moderation escalation

  SQL injection                       ORM parameterization, input
                                      validation, least-privilege DB role

  XSS                                 Output escaping, safe rendering,
                                      CSP

  CSRF                                CSRF protection for
                                      cookie-authenticated web requests

  Token theft                         Secure storage on Android, short
                                      access TTL, rotation/revocation

  File upload abuse                   MIME/signature validation, size
                                      caps, re-encoding, scanning

  Admin misuse                        MFA, least privilege, audit trail,
                                      reason codes

  Service spoofing                    Private networking and
                                      service-to-service authentication
  -----------------------------------------------------------------------

## 14.2 Data protection

-   TLS in transit.
-   Managed database encryption at rest.
-   Secrets stored in hosting secrets manager.
-   Separate production credentials from development.
-   Database roles: migration owner, application runtime, read-only
    analytics; runtime role should not be superuser.
-   Redact tokens, OTPs, passwords, private answers, and identity data
    from logs.
-   Minimize collection and define purpose for every personal field.
-   Implement access, correction, deletion, consent withdrawal, and
    grievance workflows required by applicable Indian law at launch.
-   Have privacy notices and consent language reviewed by qualified
    counsel; this document is not legal advice.

## 14.3 Application security checklist

-   Django `DEBUG=False` in production.
-   `ALLOWED_HOSTS` restricted.
-   Secure cookies and HSTS after HTTPS is correctly configured.
-   CORS allowlist only; never wildcard with credentials.
-   CSRF trusted origins explicitly configured.
-   DRF default permission is deny-by-default.
-   Rate limits on sensitive endpoints.
-   Admin path protected and MFA enabled.
-   PostgreSQL and Redis private.
-   FastAPI internal-only.
-   Dependency and container vulnerability scans in CI.
-   Backups encrypted and restore-tested.
-   Security tests include IDOR and privilege escalation.

------------------------------------------------------------------------

# 15. Background jobs, caching, and performance

## 15.1 Celery use cases

-   Email and push notification delivery.
-   Image post-processing.
-   Compatibility batch refresh after preference changes.
-   Expired invitation cleanup.
-   Listing expiry reminders.
-   Orphaned media cleanup.
-   Analytics aggregation.
-   Scheduled retention/deletion workflows.

Tasks must be idempotent, bounded, retried with exponential backoff, and
have dead-letter/error visibility. Do not use Celery for ordinary
synchronous CRUD.

## 15.2 Cache strategy

Cache only data that can safely be stale: - Static questionnaire
definitions. - Public city/locality metadata. - Read-heavy listing
search fragments where invalidation is clear. - Compatibility results
keyed by input fingerprint and algorithm version.

Do not cache private data without user/permission-aware keys. Never use
a cached result to bypass authorization. Redis is an optimization, not
the source of truth.

## 15.3 Initial performance budgets

These are targets to validate, not guarantees: - Common API reads: p95
below 500 ms under pilot load. - Compatibility calculation for a pair:
p95 below 1 second. - Feed endpoints: paginated, bounded query count. -
Web initial load: optimize for mobile networks and Core Web Vitals. -
Android startup: measure release builds on representative mid-range
devices.

Use load tests with realistic synthetic data before public growth
campaigns.

------------------------------------------------------------------------

# 16. Reliability, observability, and operations

## 16.1 Health endpoints

Django: - `/health/live`: process is running. - `/health/ready`: app can
reach required dependencies.

FastAPI: - `/health/live` - `/health/ready`

Do not expose dependency details or secrets in public health responses.

## 16.2 Logging

Use structured JSON logs with: - timestamp, - severity, - service, -
environment, - request_id, - trace_id where available, -
route/template, - status code, - latency, - safe actor identifier.

Do not log full request bodies by default.

## 16.3 Monitoring

Track: - API request rate, latency, and error rate. - Database
connections, slow queries, CPU, storage. - Redis memory and queue
depth. - Celery task failures/retries/age. - FastAPI timeouts and
scoring errors. - Authentication failures and suspicious activity. -
Connection creation, successful matches, report rate, and moderation
backlog.

Use Sentry for exception reporting. Add uptime checks for public API and
web app. Set alerts based on actionable thresholds, not every transient
error.

## 16.4 Backup and recovery

-   Managed PostgreSQL automated backups and point-in-time recovery if
    available.
-   Define RPO and RTO before production. Initial suggested targets: RPO
    24 hours or better; RTO 8 hours or better for early pilot, then
    tighten as usage grows.
-   Test a restore to a separate environment at least quarterly and
    before major migrations.
-   Back up configuration and infrastructure definitions.
-   Object storage versioning/lifecycle policies for important assets.
-   Document incident response contacts and credential rotation.

------------------------------------------------------------------------

# 17. Environments, configuration, and secrets

## 17.1 Environments

-   Local: Docker Compose, synthetic data.
-   Test/CI: ephemeral or isolated database.
-   Staging: production-like configuration, non-production data.
-   Production: restricted access, managed services, backups,
    monitoring.

Never copy production personal data into local development. Use
anonymized or synthetic fixtures.

## 17.2 Example environment variables

``` dotenv
# Django
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://roomsync:roomsync@db:5432/roomsync
REDIS_URL=redis://redis:6379/0
FASTAPI_BASE_URL=http://matching-service:8001
INTERNAL_SERVICE_TOKEN=replace-me
WEB_ORIGIN=http://localhost:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173

# Storage
S3_ENDPOINT_URL=
S3_BUCKET_PUBLIC=
S3_BUCKET_PRIVATE=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=

# React web
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Expo
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Only public, non-secret configuration may use `VITE_` or `EXPO_PUBLIC_`
prefixes. Never put service tokens, storage secrets, Django secret key,
or database credentials in client environment variables. For Android
physical-device development, use the developer machine's reachable LAN
address rather than `10.0.2.2`.

------------------------------------------------------------------------

# 18. Local development with Docker Compose

Local Compose should provide PostgreSQL, Redis, Django, FastAPI, and
Celery. Web and Android can run through their native development
commands.

Illustrative services: - `db`: PostgreSQL with a named volume. -
`redis`: Redis. - `backend`: Django development server. -
`matching-service`: FastAPI/Uvicorn. - `worker`: Celery worker. -
`beat`: Celery beat only when scheduled tasks are implemented. -
Optional `pgadmin`: local-only profile, bound to localhost.

Do not expose pgAdmin or database ports on a public host. Use a local
admin profile and strong credentials. Apply Django migrations with
`python manage.py migrate`; create an admin user with `createsuperuser`.

Typical developer commands (adapt to the actual Makefile):

``` bash
docker compose up -d db redis
cd apps/backend && python manage.py migrate
cd apps/backend && python manage.py runserver
cd apps/matching-service && uvicorn app.main:app --reload --port 8001
cd apps/web && pnpm dev
cd apps/android && npx expo start
```

------------------------------------------------------------------------

# 19. Testing strategy

## 19.1 Backend tests

-   Model constraints and migrations.
-   Serializer validation.
-   Service-layer unit tests.
-   API permission tests for every sensitive resource.
-   Transaction/concurrency tests for likes, mutual connections, groups.
-   Query-count tests for feed and listing endpoints.
-   Contract tests for Django-to-FastAPI request/response.
-   Celery task retry/idempotency tests.

## 19.2 Matching test matrix

-   Identical preferences.
-   Compatible but non-identical preferences.
-   Opposing preferences.
-   Deal-breaker in either direction.
-   Missing data and low coverage.
-   Asymmetric preference combinations.
-   Different weight versions.
-   Question version changes.
-   Stable deterministic output.
-   No private answer leakage in explanation.
-   Invalid or malformed payloads.
-   FastAPI timeout/unavailable behaviour.

## 19.3 Frontend tests

-   Component tests for forms, profile cards, score explanations, empty
    states.
-   API error and loading states.
-   Authentication/session expiry.
-   Responsive web layouts.
-   React Native navigation and secure token storage.
-   Accessibility checks.
-   End-to-end journeys on web and Android emulator/device.

## 19.4 Critical end-to-end tests

1.  Register → complete profile → answer questionnaire → discover
    candidates.
2.  Candidate score includes category details and coverage.
3.  Send like → recipient accepts/likes back → one connection is
    created.
4.  Connection opens conversation → authorized users exchange messages.
5.  Block user → discovery and messaging are denied.
6.  Create listing → upload images → publish → search → enquire.
7.  Submit report → moderator reviews → action is audited.
8.  Android user performs the same core API journeys as web.

## 19.5 Release gates

-   CI passes.
-   No unresolved critical/high security issues.
-   Database migration tested against staging snapshot.
-   Backup restore process verified.
-   Core journeys pass.
-   Error monitoring and alerts active.
-   Privacy and safety copy reviewed.
-   Rollback plan documented.

------------------------------------------------------------------------

# 20. CI/CD and deployment

## 20.1 Recommended initial hosting

For a cost-conscious MVP: - React web: Vercel or Cloudflare Pages. -
Django API: Render web service. - FastAPI matching service: Render
private/internal service. - Celery worker: Render background worker. -
PostgreSQL: managed PostgreSQL from the same provider or a reputable
managed PostgreSQL provider. - Redis: managed Redis. - Media:
S3-compatible object storage such as Cloudflare R2 or AWS S3. - Android:
Expo EAS builds, Google Play internal testing.

Select providers based on current regional availability, pricing,
private networking, backup guarantees, and data residency needs before
launch. Keep the architecture portable with Docker images and
environment configuration. Do not assume free tiers are suitable for
production personal data.

## 20.2 GitHub Actions pipeline

On pull request: 1. Install pinned dependencies. 2. Lint and type-check
web/Android. 3. Run frontend unit tests. 4. Run Python lint/type checks.
5. Run Django tests against PostgreSQL. 6. Run FastAPI tests. 7.
Validate OpenAPI schema. 8. Build Docker images. 9. Run
dependency/security scans.

On merge to main: 1. Build immutable images. 2. Deploy to staging. 3.
Run smoke tests and migration checks. 4. Require approval for
production. 5. Run backward-compatible migrations. 6. Deploy application
services. 7. Run health checks. 8. Monitor error rate and rollback if
necessary.

## 20.3 Database migration policy

-   Migrations are reviewed code.
-   Avoid destructive schema changes in the same release that stops
    using a column.
-   Use expand → migrate data → switch reads/writes → contract.
-   Take/verify backups before risky migrations.
-   Never run `makemigrations` or migrations automatically from every
    web worker at startup.
-   One controlled release job applies migrations.

## 20.4 Rollback

-   Keep previous container image available.
-   Prefer backward-compatible schema changes.
-   Roll back application first if safe; database rollback is not always
    safe.
-   Use forward-fix migrations for irreversible data changes.
-   Feature flags can disable new modules without redeploying.
-   Document incident owner and user communication procedure.

------------------------------------------------------------------------

# 21. Implementation roadmap

This is a recommended build order. It is intentionally narrower than the
full PRD.

## Phase 0 --- Engineering foundation

-   Monorepo, branch protection, linting, formatting.
-   Docker Compose with PostgreSQL and Redis.
-   Django custom user model and settings split.
-   FastAPI skeleton with internal auth and health endpoints.
-   React web and Expo Android skeletons.
-   CI pipeline and OpenAPI generation.

**Exit:** all four apps run locally; CI is green; database migrations
work.

## Phase 1 --- Identity and profiles

-   Registration/login/session lifecycle.
-   User account status and profile.
-   City/locality reference data.
-   Profile privacy and completion.
-   Android secure token storage.
-   Basic admin access with MFA before production.

**Exit:** web and Android can create, read, and update authorized
profiles.

## Phase 2 --- Preferences and compatibility

-   Versioned questionnaire definitions.
-   Lifestyle and accommodation preferences.
-   Deal-breaker representation.
-   FastAPI scoring endpoint.
-   Django orchestration and score snapshots.
-   Explainability and coverage.
-   Matching unit and contract tests.

**Exit:** deterministic, explainable scores with deal-breakers and
missing-data handling.

## Phase 3 --- Discovery and connections

-   Candidate filters and pagination.
-   Profile cards and detail permissions.
-   Like/request lifecycle.
-   Atomic mutual connection creation.
-   Block/report.
-   Saved profiles.

**Exit:** two test users can discover and mutually connect without
duplicate or unauthorized state.

## Phase 4 --- Messaging

-   Conversation creation from connection.
-   Message REST endpoints.
-   Notification records.
-   Push/email delivery through Celery.
-   Realtime only if pilot feedback demands it.

**Exit:** only eligible connection members can communicate.

## Phase 5 --- Listings and pilot moderation

-   Listing CRUD and search.
-   Media upload pipeline.
-   Listing enquiry.
-   Verification metadata and report workflow.
-   Admin audit trail.

**Exit:** core RoomSync journey from profile to roommate connection and
accommodation enquiry works.

## Phase 6 --- Pilot hardening and Android release

-   Performance/load testing.
-   Privacy/security review.
-   Android release build and internal testing.
-   Backup restore test.
-   Analytics and success metrics.
-   Closed beta with a focused city/college cohort.

**Exit:** PRD Definition of Done for the MVP is satisfied and pilot
feedback is collected.

------------------------------------------------------------------------

# 22. Risks, trade-offs, and mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Django + FastAPI creates            Keep FastAPI private and limited to
  unnecessary complexity              compute; do not duplicate domain
                                      APIs

  Web + Android doubles UI work       Share contracts, tokens,
                                      validation, API client; keep
                                      platform UI separate

  Sparse user network produces weak   Start with one city/college cohort;
  matches                             show coverage and avoid false
                                      precision

  Initial weights are arbitrary       Version weights; validate with user
                                      feedback and actual outcomes

  Sensitive lifestyle answers leak    Minimal payloads, strict
                                      serializers, access tests, redacted
                                      logs

  Listing fraud                       Report flow, moderation, clear
                                      verification labels, safe meeting
                                      guidance

  Realtime adds operational cost      Start with REST/polling or managed
                                      provider; add Channels only when
                                      justified

  Solo developer overload             Implement only P0/P1 essentials;
                                      defer group matching, AI assistant,
                                      communities, payments

  Vendor lock-in                      Standard PostgreSQL, Docker,
                                      S3-compatible storage, OpenAPI
                                      contracts
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 23. Definition of technical completion

The MVP engineering baseline is complete when:

-   [ ] React web and Android clients use the same versioned Django API.
-   [ ] Django owns all core product records and business rules.
-   [ ] FastAPI is private, authenticated, documented, and limited to
    compatibility compute.
-   [ ] PostgreSQL schema is migrated through Django migrations.
-   [ ] pgAdmin is not exposed publicly and is not required at runtime.
-   [ ] User/profile/preference privacy and object-level authorization
    tests pass.
-   [ ] Compatibility score, category scores, coverage, deal-breakers,
    and explanations are deterministic and versioned.
-   [ ] Discovery is filtered, paginated, and block-aware.
-   [ ] Mutual connection creation is atomic and duplicate-safe.
-   [ ] Messaging authorization is tested.
-   [ ] Basic listings, media upload, enquiries, reporting, and
    moderation are functional.
-   [ ] Celery jobs are idempotent and observable.
-   [ ] CI, staging, production deployment, secrets management, and
    rollback are documented.
-   [ ] Backups and restore are tested.
-   [ ] Monitoring and error reporting are active.
-   [ ] Core web and Android end-to-end journeys pass.

------------------------------------------------------------------------

# 24. Open decisions to resolve before production

These do not block creating the architecture, but they must be finalized
before the relevant implementation/release:

1.  Authentication providers: email/password, Google, phone OTP, or a
    staged combination.
2.  Whether web uses cookie sessions or bearer tokens; recommended web
    cookie session and Android rotating refresh tokens.
3.  Realtime messaging: polling/managed provider first or Django
    Channels.
4.  Exact object-storage provider and region.
5.  Email, SMS/OTP, and push providers.
6.  Initial launch city and locality reference dataset.
7.  Final questionnaire questions, answer semantics, and deal-breaker
    eligibility.
8.  Privacy retention periods and legal review for Indian DPDP
    requirements.
9.  Whether PostGIS is needed in MVP or can wait until radius-based
    discovery.
10. Hosting provider selection after checking pricing, private service
    networking, backups, and region.

------------------------------------------------------------------------

# 25. Final engineering recommendation

Build RoomSync as a **React + TypeScript web client and React
Native/Expo Android client**, backed by **one authoritative Django +
Django REST Framework modular monolith** and **one private FastAPI
compatibility service**. Use **PostgreSQL** as the system of record,
**Redis + Celery** for background work, and object storage for media.
Manage PostgreSQL through migrations and use pgAdmin only as a secured
operator tool.

This arrangement honours the requested stack without turning the product
into a collection of loosely coordinated services. It keeps the first
release buildable by a small team, makes web and Android clients share
one stable API, and leaves a clean path to scale matching and AI
independently when real product data justifies it.

# RoomSync — API & Service Contract Conventions

**Version:** 1.0 (Phase 0 Reconciled Baseline)  
**Date:** 11 November 2026  
**Authority:** Django + DRF (`services/backend/`) owns the public API. FastAPI (`services/matching/`) owns private internal compute only.  
**Related:** [TDD.md](./engineering/TDD.md) §8–§9, [OPEN_DECISIONS.md](./engineering/OPEN_DECISIONS.md), [ADR-001](./ADR/ADR-001-platform-architecture-and-boundaries.md), [ADR-004](./ADR/ADR-004-auth-sessions-locations-and-privacy.md)

---

## 1. Base URLs & Network Exposure

| Surface | Base Path | Audience | Transport / Exposure |
|---|---|---|---|
| **Public API (Django + DRF)** | `/api/v1/` | Web (`apps/web`), Android (`apps/android`) | HTTPS only in staging/prod; HTTP allowed strictly on localhost dev |
| **Operational Health (Django)** | `/health/live`, `/health/ready` | Load balancer / Compose healthcheck | Internal/LB only; zero secret or topology leakage |
| **Internal Compute (FastAPI)** | `/internal/v1/` | **Django backend only** | Private network only; **never** publicly exposed; zero CORS |
| **Operational Health (FastAPI)** | `/health/live`, `/health/ready` | Docker / container orchestrator | Private network only |

---

## 2. Authentication, Headers & Client Modes (`DEC-05`, `DEC-06`)

Django supports both client modes behind one unified `/api/v1/` contract:

| Header / Mechanism | Web (`apps/web`) | Android (`apps/android`) | Notes |
|---|---|---|---|
| `X-Client-Platform` | `web` (default) | `android` (required on `/auth/*`) | Instructs `/auth/*` whether to set HttpOnly cookies (`web`) or return rotated tokens in JSON body (`android`) |
| Credentials | `HttpOnly`, `Secure`, `SameSite=Lax` cookies (`rs_access`, `rs_refresh`) | `Authorization: Bearer <access_jwt>` (from `Expo SecureStore`) | Never store tokens in `localStorage` or `AsyncStorage` |
| CSRF Protection | `X-CSRFToken` header on unsafe methods (`POST`, `PUT`, `PATCH`, `DELETE`) fetched via `GET /api/v1/auth/csrf` | Exempt when Bearer header present without auth cookies | Enforced via Django `CsrfViewMiddleware` + strict `CSRF_TRUSTED_ORIGINS` |
| Correlation | `X-Request-ID` (optional inbound UUID, always echoed in response header & `meta.request_id` / `error.request_id`) | Same | Logged in structured JSON logs without bodies/PII |
| Retries | `Idempotency-Key: <uuid-v4>` | `Idempotency-Key: <uuid-v4>` | Required/recommended on retried mutations (`likes`, `messages`, `listings`, `enquiries`) |

### Session & Refresh Rules
- Access token TTL: **15 minutes**.
- Refresh token TTL: **14 days** (rolling up to 30 days max), rotated on every `POST /api/v1/auth/refresh`.
- Presenting an already-rotated or revoked refresh token immediately **revokes the entire `RefreshSession.family_id`**, returns `401 AUTH_REFRESH_REUSE_DETECTED`, and logs an immutable `audit` event.
- Single-flight refresh lock must be implemented in `packages/api-client`.

---

## 3. Data Types, Serialization & Normalization

1. **Identifiers:** All primary entity IDs are canonical UUIDv4 strings (`uuid`), generated server-side.
2. **Timestamps:** `ISO-8601` UTC strings ending in `Z` (e.g., `2026-11-11T09:30:00Z`). Stored as `timestamptz` in PostgreSQL.
3. **Currency (`INR`):** Always represented in integer minor units (`paise`, i.e., ₹1 = `100` paise) suffixed with `_paise` (`rent_amount_paise`, `deposit_amount_paise`, `budget_min_paise`, `budget_max_paise`) alongside ISO currency code (`currency: "INR"`). Clients format `₹` strings locally; APIs never accept or return floats for money.
4. **Field Naming:** JSON keys use `snake_case` matching OpenAPI schemas cleanly. Unknown fields on sensitive write endpoints are rejected (`400 VALIDATION_ERROR`).
5. **Input Normalization (Server-Side):**
   - `email`: Unicode NFKC trimmed + lowercased.
   - `phone_e164`: Strict E.164 (`+91...`) normalization.
   - City/locality query parameters: lowercase URL slugs (`bengaluru`, `indiranagar`).
6. **Private Fields Guardrail:** Public/candidate serializers (`GET /discover/roommates`, `GET /profiles/{id}`, `GET /listings`) **must never expose** `date_of_birth`, `email`, `phone_e164`, exact home address, verification document keys/URLs, or lifestyle answers restricted by visibility settings.

---

## 4. Standard Response Envelopes

### 4.1 Single Resource / Action Success
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active"
  },
  "meta": {
    "request_id": "req_01JCDX7W9M4V..."
  }
}
```
- Deletes with no body return `204 No Content` with `X-Request-ID` header.
- Async/accepted lifecycle triggers (e.g. `POST /auth/password/forgot`, `POST /me/deletion-request`) return `202 Accepted` with generic non-enumerating status inside `data`.

### 4.2 Cursor-Paginated Collection
All feeds and message histories use opaque Base64 cursor pagination (`limit` default `20`, hard cap `50`):
```json
{
  "data": [],
  "pagination": {
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0xMS0xMVQwOTowMDowMFoiLCJpZCI6IjU1MGUuLi4ifQ==",
    "has_more": true
  },
  "meta": {
    "request_id": "req_01JCDX7W9M4V..."
  }
}
```
- Static/bounded reference catalogs (e.g., `/locations/cities`, `/preferences/questions`) may still wrap `{ "data": [...], "meta": { "request_id": "..." } }`.
- Sorting uses allowlisted query parameters (`?sort=compatibility` | `recent` | `budget_asc`) mapped explicitly in selectors — never raw ORM column strings from client input.

### 4.3 Standard Error Envelope
Every non-2xx response (4xx/5xx) uses one canonical DRF custom exception handler shape:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "field_errors": {
      "budget_max_paise": ["Must be greater than or equal to minimum budget."]
    },
    "details": {},
    "request_id": "req_01JCDX7W9M4V..."
  }
}
```
Never return Python tracebacks, SQL errors, Django template errors, raw Redis keys, internal hosts (`http://matching:8001`), or account existence hints.

### 4.4 Canonical Error Codes

| HTTP Status | `error.code` | Usage |
|---:|---|---|
| `400` | `VALIDATION_ERROR` | Schema, range, enum, or unknown-field serializer failure (`field_errors` populated) |
| `400` | `IDEMPOTENCY_CONFLICT` | Same `Idempotency-Key` reused with a different request payload hash |
| `401` | `AUTH_REQUIRED` / `AUTH_INVALID_CREDENTIALS` / `AUTH_REFRESH_REUSE_DETECTED` | Unauthenticated or invalid/expired/reused credential |
| `403` | `PERMISSION_DENIED` / `CSRF_FAILED` / `USER_BLOCKED` | Authorization, ownership, block rule, or CSRF failure |
| `404` | `NOT_FOUND` | Missing or authorization-masked resource (`hidden` profile / non-member conversation) |
| `409` | `STATE_CONFLICT` | Invalid state transition (e.g., accepting an already withdrawn request) |
| `413` | `PAYLOAD_TOO_LARGE` | Request or media metadata exceeds ceiling |
| `422` | `UNPROCESSABLE_ENTITY` | Domain invariant violation (e.g., self-like, incomplete minimum profile for action) |
| `429` | `RATE_LIMITED` | Lockout/throttle triggered; `error.details` contains only `retry_after_seconds` *(anti-enumeration safe)* |
| `500` | `INTERNAL_ERROR` | Unhandled server failure |
| `503` | `SERVICE_UNAVAILABLE` | Internal dependency unavailable (e.g. FastAPI timeout when no fallback snapshot exists) |

---

## 5. Idempotency & Rate-Limiting Rules

1. **Idempotency (`Idempotency-Key`):**
   - Scoped uniquely per `(user_id, method, path, idempotency_key)` and persisted in Redis/PostgreSQL for 24 hours with a SHA-256 request body digest.
   - Re-sending the exact same key + payload while processing returns `409` or replays the stored response once completed; reusing the key with a different payload returns `400 IDEMPOTENCY_CONFLICT`.
   - Applies to: `POST /connections/likes`, `POST /conversations/{id}/messages`, `POST /listings`, `POST /listings/{id}/enquiries`, `POST /reports`.
2. **Rate Limiting (Anti-Enumeration Lockout):**
   - Throttled endpoints (`/auth/register`, `/auth/login`, `/auth/google`, `/auth/password/forgot`, `/auth/otp/*` in P1, `/connections/likes`, `/conversations/{id}/messages`, `/reports`) return `429 RATE_LIMITED` with standard `Retry-After` HTTP header + `{ "error": { "code": "RATE_LIMITED", "message": "Too many attempts. Please try again later.", "details": { "retry_after_seconds": 600 }, "request_id": "..." } }`.
   - **Prohibited in 401/404/429 responses:** Masked phones/emails, `"No account found"`, employer/SSO links, device names, or city history.

---

## 6. Reconciled MVP + P1 Public Endpoint Matrix (`/api/v1/`)

Reconciles `TDD.md` §8.2 with endpoints required by `PRD.md` (`FR-006`, `FR-014`, `FR-032`, `FR-039`, `FR-040`, `FR-050`, `FR-113`), `USER_FLOWS.md`, and `Decisions 1–10`:

| Domain / Milestone | Method & Path | Purpose | Origin / Scope |
|---|---|---|---|
| **Auth (M1)** | `GET /auth/csrf` | Set CSRF cookie for Web SPA | P0 (`DEC-06`) |
| **Auth (M1)** | `POST /auth/register` | Email/password sign-up (`18+` terms required) | P0 (`FR-001`, `FR-007`) |
| **Auth (M1)** | `POST /auth/login` | Email/password login | P0 (`FR-002`) |
| **Auth (M1)** | `POST /auth/google` | Verify Google ID token / OAuth exchange | P0 (`FR-001/002`, `DEC-05`) |
| **Auth (M1)** | `POST /auth/refresh` | Rotate refresh token (cookie or body) | P0 (`DEC-06`) |
| **Auth (M1)** | `POST /auth/logout` | Revoke active refresh session / clear cookies | P0 (`FR-006`) |
| **Auth (M1)** | `POST /auth/password/forgot` | Generic `202` password reset request | P0 (`FR-003`) |
| **Auth (M1)** | `POST /auth/password/reset` | Complete reset + revoke sibling sessions | P0 (`FR-003`) |
| **Auth (M1)** | `GET / PATCH /me` | Account summary & settings update | P0 (`FR-004/006`) |
| **Auth (M1/M10)** | `POST /me/deletion-request`, `GET /me/data-export` | Initiate DPDP deletion / request export *(missing from TDD §8.2)* | P0/M10 (`FR-006`) |
| **Locations (M2)** | `GET /locations/cities` | List active seeded cities (`DEC-07`) *(missing from TDD §8.2)* | P0 (`FR-113`) |
| **Locations (M2)** | `GET /locations/localities?city=<slug>` | Curated localities for city *(missing from TDD §8.2)* | P0 (`FR-113`) |
| **Profiles (M2)** | `GET / PATCH /me/profile` | Read/update own profile + visibility flags | P0 (`FR-008`, `FR-012`, `FR-013`) |
| **Profiles (M2)** | `GET /me/profile/preview` | Public-view preview *(missing from TDD §8.2)* | P0 (`FR-014`) |
| **Profiles (M2)** | `POST /me/profile/avatar/upload-url`, `POST /me/profile/avatar/confirm` | Presigned MinIO/S3 avatar upload + confirm *(missing from TDD §8.2)* | P0 (`FR-008`) |
| **Profiles (M2)** | `GET /profiles/{id}` | Privacy-filtered candidate profile view | P0 (`FR-012`, `FR-035`) |
| **Preferences (M3)** | `GET /preferences/questions` | Versioned (`v1`) 20-Q 8-category questionnaire (`flexible`/`not_sure` + `supports_deal_breaker` flags, `OD-U2`) | P0 (`FR-015`–`023`) |
| **Preferences (M3)** | `GET / PUT /me/preferences/lifestyle` | Read/replace questionnaire answers & deal-breakers | P0 (`FR-010`, `FR-028`) |
| **Preferences (M3)** | `GET / PUT /me/preferences/accommodation` | Housing budget (`paise`), city, localities, move-in | P0 (`FR-009`, `FR-024`) |
| **Discovery & Match (M3–M4)** | `GET /discover/roommates` | Cursor-paginated, block-aware ranked candidates | P0 (`FR-031`, `FR-033`, `FR-034`, `FR-036`) |
| **Discovery & Match (M3–M4)** | `GET /profiles/{id}/compatibility` | 8-category breakdown, coverage, deal-breakers, explanation codes | P0 (`FR-025`–`030`, `DEC-02`) |
| **Discovery & Match (M4)** | `POST /profiles/{id}/compatibility/feedback` | Match usefulness feedback *(missing from TDD §8.2)* | P0 (`FR-032`) |
| **Discovery & Match (M4)** | `GET / POST /saved/profiles`, `DELETE /saved/profiles/{profile_user_id}` | Save/bookmark candidates *(missing from TDD §8.2)* | P0 (`FR-040`) |
| **Connections & Safety (M5)** | `POST /connections/likes` | Express interest (`Idempotency-Key`, mutual atomic match) | P0 (`FR-037`, `FR-038`) |
| **Connections & Safety (M5)** | `GET /connections/requests` | Filter `?direction=incoming\|outgoing&status=pending` | P0 (`FR-039`) |
| **Connections & Safety (M5)** | `POST /connections/requests/{id}/accept`, `/decline`, `/withdraw` | Recipient accept/decline *(decline missing from TDD §8.2)*; sender withdraw | P0 (`FR-038`, `FR-039`) |
| **Connections & Safety (M5)** | `GET /connections` | Active mutual connections | P0 (`FR-038`) |
| **Connections & Safety (M5)** | `POST /blocks`, `DELETE /blocks/{user_id}` | Directional block (`GET /blocks` to manage) | P0 (`FR-042`) |
| **Connections & Safety (M5)** | `POST /reports` | Report user or listing safely (`Idempotency-Key`) | P0 (`FR-042`, `FR-079`, `FR-080`) |
| **Messaging (M6)** | `GET / POST /conversations` | List eligible conversations; open conversation for active connection | P0 (`FR-084`, `DEC-08`) |
| **Messaging (M6)** | `GET / POST /conversations/{id}/messages` | Cursor read (`?after_cursor=` for smart polling) & send text message | P0 (`FR-084`, `FR-085`, `FR-089`) |
| **Messaging (M6)** | `POST /conversations/{id}/read` | Mark conversation read up to message timestamp | P0 (`FR-088`) |
| **Notifications (M6)** | `GET /notifications`, `PATCH /notifications/{id}` | Activity hub & mark-read (`POST /notifications/read-all` optional) | P0 (`FR-101`–`104`) |
| **Notifications (M6)** | `GET / PATCH /me/notification-preferences` | Channel & category toggles | P0 (`FR-107`) |
| **Listings & Verify (M8)** | `GET / POST /listings`, `GET / PATCH / DELETE /listings/{id}` | Accommodation search & owner CRUD | P1 (`FR-043`–`048`) |
| **Listings & Verify (M8)** | `POST /listings/{id}/media/upload-url`, `POST /listings/{id}/media/confirm` | Presigned listing photo upload + EXIF scrub | P1 (`FR-047`) |
| **Listings & Verify (M8)** | `POST /listings/{id}/enquiries`, `GET /me/enquiries` | Submit/view enquiries (`enquiry != booking`) | P1 (`FR-049`) |
| **Listings & Verify (M8)** | `GET / POST /saved/listings`, `DELETE /saved/listings/{listing_id}` | Saved listings shortlist *(missing from TDD §8.2)* | P1 (`FR-050`) |
| **Verification (M8)** | `GET /me/verification`, `POST /me/verification/cases` | View truthful verification status & submit evidence to private bucket | P1 (`FR-074`–`078`) |

*(Deferred Endpoints — Side-by-side roommate comparison `/discover/compare` [P1 per `OD-U5`], Phone OTP `/auth/otp/*` [P1], Groups/Pods `/groups/*`, Agreements/Splitwise, Reviews, Subscriptions [Post-MVP] — are excluded from Milestone 1–9 routers until promoted.)*

---

## 7. Private FastAPI Contract (`/internal/v1/compatibility/score`)

Django is the sole caller of FastAPI (`FASTAPI_BASE_URL`). Requests carry:
- Header: `X-Internal-Service-Token: <shared-rotating-secret>`
- Header: `X-Request-ID: <correlation-uuid>`
- Strict client timeout (e.g., `1.5s` connect / `3.0s` read).

### Request Shape (Minimal Pseudonymous Payload — Zero PII)
```json
{
  "request_id": "req_01JCDX7W9M4V...",
  "algorithm_version": "roomsync-rule-v1",
  "weights_version": "weights-2026-01",
  "question_schema_version": 1,
  "user_a": {
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "answers": [
      {
        "question_key": "q_wake_time",
        "category": "daily_routine",
        "answer_type": "time_of_day",
        "value": "07:00",
        "importance": "important",
        "is_deal_breaker": false
      }
    ]
  },
  "user_b": {
    "user_id": "550e8400-e29b-41d4-a716-446655440002",
    "answers": []
  }
}
```
**Forbidden inside FastAPI payload/logs:** `display_name`, `email`, `phone_e164`, `date_of_birth`, bios, street addresses, or uploaded files.

### Response Shape
Matches `TDD.md` §9.6 + `ADR-002` explicitly:
```json
{
  "algorithm_version": "roomsync-rule-v1",
  "weights_version": "weights-2026-01",
  "status": "eligible",
  "overall_score": 84.5,
  "coverage": 0.91,
  "deal_breaker_conflicts": [],
  "unknown_deal_breakers": [],
  "category_scores": {
    "daily_routine": 90.0,
    "cleanliness": 80.0,
    "financial_expectations": 100.0,
    "privacy_and_boundaries": 85.0,
    "social_lifestyle": 75.0,
    "food_preferences": 90.0,
    "guest_preferences": 70.0,
    "work_study_environment": 85.0
  },
  "explanation_codes": [
    "SLEEP_SCHEDULE_CLOSE",
    "BUDGET_SPLIT_ALIGNED",
    "GUEST_FREQUENCY_DISCUSS"
  ],
  "computed_at": "2026-11-11T09:30:00Z"
}
```

---

## 8. OpenAPI & Contract Pipeline

1. Django (`drf-spectacular`) exports `services/backend/openapi.yaml` via CI command (`manage.py spectacular --file openapi.yaml --validate`).
2. `packages/contracts/` generates TypeScript types from `openapi.yaml` so Web (`apps/web`) and Android (`apps/android`) never duplicate response DTOs by hand.
3. CI fails on uncommitted schema drift whenever Django serializers change without regenerating `packages/contracts/`.


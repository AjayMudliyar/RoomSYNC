# ADR-004: Authentication Staged Policy, Dual-Client Sessions, DB Locations & Anti-Enumeration Privacy

- **Status:** Accepted (`DEC-05`, `DEC-06`, `DEC-07`, `OD-U1`, `OD-U6`, `OD-U7`, `OD-U8`)
- **Date:** 11 November 2026
- **Deciders:** Engineering Lead / Product Owner & System Architect
- **Reconciles:** `Docs/product/PRD.md` (`FR-001`, `FR-074`–`078`, `FR-113`), `Docs/engineering/TDD.md` (§6.3.1, §6.3.3, §7.1–7.4, §24), and `Docs/DESIGN_AUDIT.md` (§4).

---

## 1. Context

Several Stitch exports and specification passages introduced conflicting auth providers, token-storage risks, city hardcoding, and lockout information leaks:
1. Stitch exports display `Swiggy Corporate SSO`, `DigiLocker`, `UIDAI/Aadhaar`, `WhatsApp OTP`, and `Kaveri 2.0` badges that are unimplemented and legally/technically unapproved for MVP.
2. Web SPA and Android native mobile require distinct session security patterns that still share one Django DRF `/api/v1/` backend.
3. Nearly all 85 Stitch screens hardcode `Bengaluru, KA`, `Indiranagar`, `Koramangala`, and `HSR Layout`.
4. `roomsync_mobile_otp_rate_limit_lockout` displays masked phone hints, an employer SSO link, and device/location strings (`"Pixel 8 • Bangalore East"`), creating an account-enumeration vulnerability prohibited by `DESIGN_AUDIT.md` §4.

---

## 2. Decision

### 2.1 Staged Authentication Providers (`DEC-05`)
- **P0 (Milestone 1 — Launch Critical, `DEC-05`, `OD-U6`):**
  - **Email + Password:** Normalized lowercase email (`citext` / unique normalized `varchar(254)`), strong server-side password validation, email verification token workflow, and password reset invalidating other sessions.
  - **Google OAuth 2.0 / OIDC:** Keep in P0 (`OD-U6`). Client obtains Google ID token / auth code; Django verifies token signature, `aud` (allowlisted Web/Android client IDs supplied strictly via environment variables), `iss`, and `exp` server-side before linking or creating `OAuthIdentity` mapped to `provider_sub`. Never commit OAuth secrets into docs or source control, and never trust client-supplied email claims.
- **P1 (Post-Core Loop / Milestone 8+ once SMS & TRAI DLT approved):**
  - **Phone Number + OTP (`+91` E.164 normalization):** OTP hashed (`HMAC-SHA256`), short TTL (`5 min`), single-use, attempt-limited, Redis throttled. Zero plaintext OTPs stored or logged.
- **Explicitly Deferred:** Corporate SSO (`SAML`/`Work Email Domain`), DigiLocker / Aadhaar / UIDAI verification, Kaveri property registry APIs. Verification badges rendered in UI **must reflect genuine implemented verification states only** (`Email Verified` in P0; `Phone Verified` [when DLT/SMS enabled] and `Manual Student & Property Review` in P1).

### 2.2 Dual-Client Session Architecture (`DEC-06`)
Django (`accounts`) owns identity and issues client-appropriate credentials behind the same `/api/v1/auth/*` contract:

- **Web (`apps/web/`):**
  - Authenticates via **HttpOnly, Secure (`true` outside local HTTP), `SameSite=Lax` cookies** (`rs_access`, `rs_refresh`) paired with **CSRF double-submit / Django CSRF token (`X-CSRFToken`)** on all unsafe (`POST`/`PUT`/`PATCH`/`DELETE`) requests.
  - Requires **same-parent-domain deployment** in staging/production (e.g., `app.roomsync.in` + `api.roomsync.in` or single-origin reverse proxy `/api/`), avoiding third-party cookie blocking and eliminating `localStorage`/`sessionStorage` token exposure to XSS.
  - Strictly allowlisted `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` (`ALLOW_CREDENTIALS = True`); never wildcard `*`.
- **Android (`apps/android/`):**
  - Requests token-body mode explicitly (`X-Client-Platform: android`) on `/auth/register`, `/auth/login`, `/auth/google`, and `/auth/refresh`.
  - Receives short-lived **JWT access token** (15 min TTL) + opaque **rotating refresh token** (14–30 day TTL), stored **exclusively inside `Expo SecureStore`** (hardware-backed Keystore on Android). Storing tokens in `AsyncStorage` is prohibited.
  - **`RefreshSession` Family & Reuse Detection:** Refresh tokens belong to a `family_id` tracked in PostgreSQL with `token_hash` and `rotated_at` / `revoked_at`. Presenting a previously rotated refresh token is treated as token theft: **revoke the entire `family_id` immediately**, deny the request (`401 AUTH_REFRESH_REUSE_DETECTED`), and record an `audit` security event.
  - `packages/api-client` enforces a **single-flight refresh mutex** so concurrent 401 responses on Android trigger only one `/auth/refresh` call.

### 2.3 Database-Driven Multi-City Locations (`DEC-07`, `OD-U1`, `OD-U8`)
- Store supported markets in relational PostgreSQL tables (`locations_city`, `locations_locality`) managed via Django Admin/migrations and queried publicly via `/api/v1/locations/cities` and `/api/v1/locations/localities?city=<slug>`.
- Seed the **5 approved initial Indian cities (`OD-U1`)**: **Bengaluru, Pune, Mumbai, Hyderabad, and Delhi-NCR**, populated with curated starter localities. Web and Android frontends must never hardcode city/locality logic, defaults, or validation enums.
- **Defer PostGIS (`OD-U8`):** Do not enable `PostGIS` / `geography(Point, 4326)` columns during MVP; use normalized `City` and `Locality` relationships until geographic radius or distance search (`FR-115`, `FR-117`) is scheduled post-pilot.

### 2.4 Anti-Enumeration & Privacy-by-Design Controls (`OD-U7`)
- Auth failure (`401`), password-reset confirmation (`202` generic message whether email exists or not), and Redis-backed lockout responses (`429 RATE_LIMITED`) **must never disclose account existence, masked phone/email addresses (except to an already-authenticated user on their own security page), employer SSO options, or prior login devices**.
- Private profile fields (`date_of_birth`, `email`, `phone_e164`, exact address, hidden institution/employer, raw lifestyle answers outside visibility policy, and private verification documents) must never be serialized into discovery feeds, public compatibility explanations, or notification push previews.
- **Privacy-by-design from Milestone 0 (`OD-U7`):** Even though production cloud hosting, S3 storage vendor, email/SMS providers, geographic residency mandate, final DPDP retention periods, and legal counsel sign-off remain intentionally open until **Milestone 10** (production preparation), all services must implement log redaction, private/public bucket isolation, EXIF stripping, least-privilege permissions, and deletion/export hooks from day 1.

---

## 3. Consequences

- **Positive:** Protects Web against XSS session hijacking and Android against replay/token theft; unblocks Milestone 1–7 development without SMS vendor, PostGIS, or KYC regulatory delays; supports 5-city Indian rollout natively from day 1.
- **Operational Constraint:** Production deployment of Web + Django API **must** share a common registrable parent domain (`SameSite=Lax` / `Strict` compatible) and enforce HTTPS before setting `Secure` cookies in production.
- **Required Follow-Up:** Review curated locality seed list before Milestone 2; inject runtime Google OAuth client env vars before live M1/M7 E2E; finalize `OD-U7` production vendor/legal/retention items before Milestone 10.


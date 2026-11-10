# RoomSync Screen Inventory
**Version:** 1.0 — Initial inventory  
**Status:** Module-level baseline (lines 10–33) preserved from initial handoff; full 85-screen Stitch export catalogue reconciled below (`DEC-04`, `DEC-09`).

> **Scope Reminder:** A screen existing inside `Docs/Design/` does **not** place its feature in MVP scope (`ROOMSYNC_ENGINEERING_HANDOFF.md` §4, `DEC-04`). Do not infer implemented APIs or approved integrations from Stitch copy (`BLR` city strings, `DigiLocker`/`UIDAI`/`SSO` badges, `Pods`, `Escrow`, `Splitwise`).

## Status legend
- `Reported generated` — original handoff status before filesystem catalogue completion.
- `MVP` — in core loop (`Milestones 1–7, 9`: Auth, Onboarding, Prefs, Questionnaire, Discovery, Compatibility, Connections, 1:1 Chat, Settings, Safety, Core States).
- `MVP (P1)` — Milestone 8 / 9 P1 slice (Basic Listings, Enquiries, Saved Listings, Truthful Verification Metadata, Trust Centre).
- `POST_MVP` — deferred per `DEC-04` (Groups/Pods, Map/Radius PostGIS UI unless approved later).
- `ADMIN/OPS` — custom React admin exports; deferred in pilot per `DEC-09` (replaced by hardened Django Admin).

| ID | Module / screen group | Platform | Coverage | Initial scope |
|---|---|---|---|---|
| AUTH-01 | Welcome, registration, login, password recovery | Web + Android | Reported generated; export reference pending | MVP |
| ONB-01 | Basic profile and onboarding | Web + Android | Reported generated; export reference pending | MVP |
| PREF-01 | Accommodation preferences | Web + Android | Reported generated; export reference pending | MVP |
| LIFE-01 | Lifestyle questionnaire, review and edit | Web + Android | Reported generated; export reference pending | MVP |
| DISC-01 | Roommate discovery dashboard and filters | Web + Android | Reported generated; export reference pending | MVP |
| PROF-01 | Roommate profile and profile editing | Web + Android | Reported generated; export reference pending | MVP |
| COMP-01 | Compatibility details and category breakdown | Web + Android | Reported generated; export reference pending | MVP |
| CONN-01 | Sent/received connection requests | Web + Android | Reported generated; export reference pending | MVP |
| CHAT-01 | Conversation list and one-to-one messaging | Web + Android | Reported generated; export reference pending | MVP |
| GROUP-01 | Group discovery, create, details, invites and group chat | Web + Android | Reported generated; export reference pending | Post-MVP unless TDD explicitly includes a narrow slice |
| GROUP-02 | Group compatibility and group accommodation planning | Web + Android | Reported generated; export reference pending | Post-MVP |
| PROP-01 | Property discovery, filters, map/list and details | Web + Android | Reported generated; export reference pending | Limited MVP / expand later per TDD |
| PROP-02 | Saved properties, enquiry and comparison | Web + Android | Reported generated; export reference pending | Confirm exact MVP slice against TDD |
| TRUST-01 | Trust Centre, verification and safety | Web + Android | Reported generated; export reference pending | MVP essentials only |
| SET-01 | Settings, profile, privacy and security | Web + Android | Reported generated; export reference pending | MVP essentials |
| NOTIF-01 | Notification centre and preferences | Web + Android | Reported generated; export reference pending | MVP essentials |
| ADMIN-01 | Admin dashboard, user/report/listing moderation | Web | Reported generated; export reference pending | Admin/ops |
| STATE-01 | Empty states | Web + Android | Reported generated; export reference pending | MVP states |
| STATE-02 | Loading states / skeletons | Web + Android | Reported generated; export reference pending | MVP states |
| STATE-03 | Error states | Web + Android | Reported generated; export reference pending | MVP states |
| STATE-04 | Success and confirmation states | Web + Android | Reported generated; export reference pending | MVP states |
| STATE-05 | Permission-denied and OTP lockout | Android/mobile and relevant web flows | User reports generated; export reference pending | MVP |

---

## Export catalogue (All 85 Stitch Screen Directories)

- **Export Root:** `Docs/Design/stitch_roomsync_roommate_discovery_platform/`
- **Totals Verified:** **85** screen directories + `warm_tech_harmony/DESIGN.md` + 2 token specs (`roomsync_consolidated_design_system_tokens.md`, `roomsync_engineering_handoff_dossier_tokens_spec.md`).
- **Asset Availability:** `85/85` have `code.html`; **`74/85`** have `screen.png`; **`11/85`** are missing `screen.png` (explicitly marked `PNG MISSING`).
- **Stitch Project URL:** Not embedded in local export metadata (`unavailable locally`).
- **Scope Breakdown:** **`47 MVP`**, **`15 MVP (P1)`**, **`16 POST_MVP`**, **`7 ADMIN/OPS`** (`= 85` total; note many `MVP` exports still contain design-time cleanup gaps listed in Notes).

### Legend for Known Design Audit / Cleanup Flags
- `BLR`: Hardcodes `Bengaluru` / `Indiranagar` / `Koramangala` / `HSR Layout` -> replace with DB-driven city selector (`DEC-07`).
- `KYC/SSO`: Displays unimplemented `DigiLocker`, `UIDAI/Aadhaar`, `Corporate SSO`, or `Kaveri` badges -> replace with real verification states (`DEC-05`).
- `POST_MVP_REF`: Contains nav links/cards referencing deferred features (`Pods`, `Escrow`, `Rental Agreement`, `Splitwise`, `WhatsApp OTP`) -> strip for MVP (`DEC-04`).
- `LEAK`: Violates `DESIGN_AUDIT.md` anti-enumeration rule by showing device/city/employer hints.

### Complete Catalogue Table

| # | Module | Export Folder (Relative to `Docs/Design/stitch_roomsync_roommate_discovery_platform/`) | Platform & Viewport (`shell-type`) | Assets | State Coverage | PRD IDs | Scope | Known Audit / Alignment Notes |
|---:|---|---|---|---|---|---|---|---|
| 1 | `AUTH-01` | `roomsync_welcome_account_setup` (`code.html`, `screen.png`) | Web (`web_standard`, 1280px) | `HTML + PNG` | Default / Form | `FR-001`–`004`, `FR-007` | **MVP** | Uses `Step 1 of 3` header; `BLR`, `KYC/SSO`, `POST_MVP_REF`; Google+Email P0 only |
| 2 | `AUTH-01` | `roomsync_mobile_welcome_auth` (`code.html`, `screen.png`) | Android (`mobile_blank`, 390px) | `HTML + PNG` | Default / Auth | `FR-001`–`004`, `FR-007` | **MVP** | `KYC/SSO` copy; align auth options with Email + Google (P0) & Phone OTP (P1) |
| 3 | `ONB-01` | `roomsync_basic_profile_setup` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Form | `FR-005`, `FR-008`, `FR-011` | **MVP** | Uses `Step 1 of 4`; `BLR`, `KYC/SSO` |
| 4 | `ONB-01` | `roomsync_mobile_profile_setup` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Default / Form | `FR-005`, `FR-008`, `FR-011` | **MVP** | Uses `Step 1 of 5` (reconcile via `OD-U4`); `BLR`; verify touch targets & keyboard padding |
| 5 | `PREF-01` | `roomsync_accommodation_preferences_1` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Form (`Step 2 of 4`) | `FR-009`, `FR-024`, `FR-113` | **MVP** | Onboarding budget & locality selector; `BLR`, `KYC/SSO` -> wire `/locations/*` |
| 6 | `PREF-01` | `roomsync_accommodation_preferences_2` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Edit | `FR-009`, `FR-013`, `FR-024` | **MVP** | Post-onboarding housing preferences edit view; `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 7 | `PREF-01` | `roomsync_mobile_housing_preferences` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default / Form (`Step 2 of 5`) | `FR-009`, `FR-024` | **MVP** | `POST_MVP_REF`; reconcile step count (`OD-U4`) |
| 8 | `LIFE-01` | `roomsync_lifestyle_compatibility_questionnaire` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Form (`Step 3 of 4`) | `FR-015`–`023`, `FR-028` | **MVP** | Onboarding questionnaire; `BLR`, `KYC/SSO`, `POST_MVP_REF`; align with 8 TDD categories |
| 9 | `LIFE-01` | `roomsync_lifestyle_preferences` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Edit | `FR-010`, `FR-013`, `FR-015`–`023` | **MVP** | Settings questionnaire edit & match impact view; `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 10 | `LIFE-01` | `roomsync_mobile_lifestyle_questionnaire` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Default / Form (`Step 3 of 5`) | `FR-015`–`023`, `FR-028` | **MVP** | `BLR`; verify 44px option controls & sticky CTA clearance |
| 11 | `LIFE-01` | `roomsync_mobile_lifestyle_preferences` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Default / Edit | `FR-010`, `FR-013` | **MVP** | `BLR`, `POST_MVP_REF` |
| 12 | `ONB-01` | `roomsync_onboarding_review_profile_completion` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Review (`Step 4 of 4`) | `FR-005`, `FR-011`, `FR-014` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 13 | `ONB-01` | `roomsync_mobile_onboarding_review` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Review (`STEP 4 OF 5`) | `FR-005`, `FR-011`, `FR-014` | **MVP** | `BLR`, `KYC/SSO` |
| 14 | `ONB-01` | `roomsync_mobile_onboarding_complete` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Success (`STEP 5 OF 5`) | `FR-005`, `FR-011` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; align completion step (`OD-U4`) |
| 15 | `DISC-01` | `roomsync_roommate_discovery_dashboard` (`code.html`) | Web (`web_standard`) | `HTML only` (**PNG MISSING**) | Default / Feed | `FR-031`, `FR-033`, `FR-034`, `FR-036` | **MVP** | Has good 8 TDD modal breakdown; strips `BLR` selector + Group nav pill (`OD-U3`) |
| 16 | `DISC-01` | `roomsync_mobile_discovery_feed` (`code.html`, `screen.png`) | Android (`mobile_tab`) | `HTML + PNG` | Default / Feed | `FR-031`, `FR-033`, `FR-034`, `FR-036` | **MVP** | Clean visual reference (`#006a61`); remove `DigiLocker`/`Work SSO` fake badges + `BLR` + `Pods` tab |
| 17 | `PROF-01` | `roomsync_edit_personal_profile` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Edit | `FR-008`, `FR-012`–`014` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 18 | `PROF-01` | `roomsync_mobile_personal_profile_management` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default / Edit | `FR-008`, `FR-012`–`014` | **MVP** | `BLR`, `KYC/SSO` |
| 19 | `COMP-01` | `roomsync_roommate_profile_compatibility_intelligence` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Breakdown | `FR-025`–`030`, `FR-032`, `FR-035` | **MVP** | Canonical 8-category TDD UI reference; remove `BLR`, `KYC/SSO`, enforce field visibility |
| 20 | `COMP-01` | `roomsync_mobile_roommate_profile_compatibility` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default / Breakdown | `FR-025`–`030`, `FR-032`, `FR-035` | **MVP** | `BLR`; verify coverage qualifier display for incomplete questionnaires |
| 21 | `CONN-01` | `roomsync_connection_requests_inbox` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / List | `FR-037`, `FR-039` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; ensure accept/decline/withdraw actions map to API |
| 22 | `CONN-01` | `roomsync_connection_request_details` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Detail | `FR-037`–`039` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 23 | `CONN-01` | `roomsync_connection_success_mutual_handshake` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Success / Handshake | `FR-038` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` (remove agreement/pod next-step promos) |
| 24 | `CHAT-01` | `roomsync_messaging_coliving_chat` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Active Chat | `FR-084`–`089` | **MVP** | Has stray `Step 2 of 3` string, `BLR`, `KYC/SSO`, `POST_MVP_REF`; wire to REST + smart polling (`DEC-08`) |
| 25 | `CHAT-01` | `roomsync_mobile_coliving_direct_chat` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default / Active Chat | `FR-084`–`089` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; text-only + discussion prompts in MVP |
| 26 | `SET-01` | `roomsync_settings_overview` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-006`, `FR-013`, `FR-082` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 27 | `SET-01` | `roomsync_mobile_settings_dashboard` (`code.html`) | Android (`mobile_tab`) | `HTML only` (**PNG MISSING**) | Default | `FR-006`, `FR-013`, `FR-082` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; bottom tab `Profile` vs `Trust` (`OD-U3`) |
| 28 | `SET-01` | `roomsync_account_security` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-002`, `FR-003`, `FR-006` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; remove unimplemented hardware-key/SSO rows |
| 29 | `SET-01` | `roomsync_privacy_settings` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-012`, `FR-082` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; keep `discoverable`/`connections_only`/`hidden` accurate |
| 30 | `SET-01` | `roomsync_privacy_controls_data_management` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-006`, `FR-012`, `FR-082` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; consolidate overlapping controls with `privacy_settings` |
| 31 | `SET-01` | `roomsync_mobile_privacy_and_security` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default | `FR-006`, `FR-012`, `FR-082` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 32 | `SET-01` | `roomsync_data_consent_management` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-006`, DPDP | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; ensure deletion/export request never claims instant completion |
| 33 | `SET-01` | `roomsync_mobile_help_and_support` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default | `FR-083`, `FR-006` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; remove fake `"24/7 Safety Concierge"`, `"1800-ROOM-SYNC"`, `"Escrow"` claims |
| 34 | `NOTIF-01` | `roomsync_notifications_centre_activity_hub` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default + Unread | `FR-101`–`104` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 35 | `NOTIF-01` | `roomsync_notification_details_contextual_action` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Detail | `FR-101`–`104` | **MVP** | Uses `"sync living pods"` copy (`POST_MVP_REF`) + `BLR`, `KYC/SSO` |
| 36 | `NOTIF-01` | `roomsync_notification_dropdown_empty_states` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Empty / Dropdown | `FR-101`–`104` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 37 | `NOTIF-01` | `roomsync_notification_preferences` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-107` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; keep only email + in-app + Android push toggles for MVP |
| 38 | `NOTIF-01` | `roomsync_notification_preferences_dispatch_matrix` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Matrix | `FR-107` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; consolidate cleanly with `notification_preferences` |
| 39 | `NOTIF-01` | `roomsync_mobile_notifications_centre` (`code.html`, `screen.png`) | Android (`mobile_tab`) | `HTML + PNG` | Default | `FR-101`–`104` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 40 | `NOTIF-01` | `roomsync_mobile_notification_preferences` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default | `FR-107` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 41 | `STATE-01` | `roomsync_empty_states_design_system_component_catalog` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Empty catalog | `FR-033`, `FR-039`, `FR-046` | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; adapt card patterns to Android too (no native empty export) |
| 42 | `STATE-02` | `roomsync_loading_states_skeleton_loaders` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Loading skeletons | Cross-cutting | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF`; replicate skeleton anatomy on Android |
| 43 | `STATE-03` | `roomsync_error_states_system_recovery_component_suite` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Error / Recovery | Cross-cutting | **MVP** | `BLR`, `KYC/SSO`; ensure empty search results stay visually distinct from 5xx errors |
| 44 | `STATE-04` | `roomsync_success_confirmation_states_component_suite` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Success modals/toasts | Cross-cutting | **MVP** | `BLR`, `KYC/SSO`, `POST_MVP_REF` (remove `"Escrow"`/`"Pod"` success banners) |
| 45 | `STATE-05` | `roomsync_mobile_camera_permission_denied_sheet` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Permission Denied | `FR-008`, `FR-076` | **MVP** | Clean modal pattern + gallery fallback; strip `DigiLocker`/`KYC` framing (`KYC/SSO`) |
| 46 | `STATE-05` | `roomsync_mobile_otp_rate_limit_lockout` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Locked / `429` | `FR-001`–`003`, `DESIGN_AUDIT` | **MVP** | **CRITICAL (`LEAK`):** Reveals masked phone, `"Swiggy Corporate SSO"`, `"Pixel 8 • Bangalore East"` -> strip all identifying hints! Apply to Email/Login lockout too |
| 47 | `TRUST-01` | `roomsync_report_block_member` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Modal / Action | `FR-042`, `FR-079`, `FR-080` | **MVP** | Needed in M5/M7 core safety (`Report`/`Block` user); strip `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 48 | `PROP-01` | `roomsync_accommodation_discovery` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Search | `FR-043`–`046` | **MVP (P1)** | M8 slice; `BLR`, `KYC/SSO`, `POST_MVP_REF`; no fabricated availability |
| 49 | `PROP-01` | `roomsync_mobile_accommodation_discovery_dashboard` (`code.html`) | Android (`mobile_tab`) | `HTML only` (**PNG MISSING**) | Default / Feed | `FR-043`–`046` | **MVP (P1)** | M9 slice; `BLR`, `KYC/SSO`, `POST_MVP_REF`; align tab icon/label (`OD-U3`) |
| 50 | `PROP-01` | `roomsync_mobile_accommodation_search_filters` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Filter Sheet | `FR-046`, `FR-113` | **MVP (P1)** | M9 slice; `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 51 | `PROP-01` | `roomsync_property_details` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Detail | `FR-045`, `FR-049`, `FR-052` | **MVP (P1)** | M8; mask exact street/owner phone pre-enquiry; `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 52 | `PROP-01` | `roomsync_mobile_property_details` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Default / Detail | `FR-045`, `FR-049`, `FR-052` | **MVP (P1)** | M9; verify sticky bottom `"Enquire"` CTA clearance (`DESIGN_AUDIT.md`) |
| 53 | `PROP-02` | `roomsync_property_enquiry_visit_scheduling` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Form / Enquire | `FR-049` | **MVP (P1)** | M8; explicitly label `"Enquiry is not a booking"`; `BLR`, `KYC/SSO`, `POST_MVP_REF` |
| 54 | `PROP-02` | `roomsync_mobile_property_enquiry_visit_scheduling` (`code.html`) | Android (`mobile_stack`) | `HTML only` (**PNG MISSING**) | Form / Enquire | `FR-049` | **MVP (P1)** | M9; strip booking/escrow wording |
| 55 | `PROP-02` | `roomsync_mobile_saved_properties_shortlist_hub` (`code.html`) | Android (`mobile_tab`) | `HTML only` (**PNG MISSING**) | Default / Shortlist | `FR-050` | **MVP (P1)** | M9 saved listings + saved profiles entry; strip `Pods`/`Escrow` copy |
| 56 | `PROP-02` | `roomsync_saved_properties_comparison` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Compare | `FR-050` | **MVP (P1)** | Saved listings shortlist; property comparison optional/secondary inside M8 |
| 57 | `TRUST-01` | `roomsync_trust_centre_dashboard` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Mixed states | `FR-074`–`078`, `FR-083` | **MVP (P1)** | M8; strip fake DigiLocker/UIDAI/SSO/Kaveri badges (`KYC/SSO`) & `Escrow` |
| 58 | `TRUST-01` | `roomsync_mobile_trust_centre_verification` (`code.html`, `screen.png`) | Android (`mobile_tab`) | `HTML + PNG` | Default | `FR-074`–`078`, `FR-083` | **MVP (P1)** | M9; fold under `Profile` or `Settings` if nav slots reduce (`OD-U3`) |
| 59 | `TRUST-01` | `roomsync_identity_verification_flow` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Form / Upload | `FR-076`, `FR-077` | **MVP (P1)** | M8 student/property evidence upload to private bucket (`KYC/SSO`: no DigiLocker/Aadhaar claim) |
| 60 | `TRUST-01` | `roomsync_verification_status_state_matrix` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Pending / Approved / Rejected | `FR-074`–`078` | **MVP (P1)** | Useful state-transition reference; ensure `Submitted != Approved` (`USER_FLOWS` §7) |
| 61 | `TRUST-01` | `roomsync_profile_trust_indicators_guide` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Educational Guide | `FR-078` | **MVP (P1)** | Must document **only** real badges active in MVP (`Email`, `Phone` P1, `Student`/`Listing Reviewed`) |
| 62 | `TRUST-01` | `roomsync_safety_coliving_guidelines` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Static Guide | `FR-083` | **MVP (P1)** | Keep practical safety guidance; remove `BLR` / fake helpline / `Escrow` references |
| 63 | `PROP-01` | `roomsync_mobile_map_based_property_discovery` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Map View | `FR-114`, `FR-115`, `FR-117` | **POST_MVP** | Interactive map/radius search deferred with PostGIS (`OD-U8`); preserve as reference |
| 64 | `GROUP-01` | `roomsync_roommate_groups_dashboard` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default | `FR-058` | **POST_MVP** | Groups/Pods explicitly deferred per `DEC-04` |
| 65 | `GROUP-01` | `roomsync_create_a_roommate_group` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Form | `FR-053`, `FR-057` | **POST_MVP** | Deferred per `DEC-04` |
| 66 | `GROUP-01` | `roomsync_invite_members_to_group` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Modal / Flow | `FR-054` | **POST_MVP** | Deferred per `DEC-04` |
| 67 | `GROUP-01` | `roomsync_group_details_dashboard` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Detail | `FR-055`, `FR-060` | **POST_MVP** | Deferred per `DEC-04` |
| 68 | `GROUP-01` | `roomsync_group_chat` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Default / Chat | `FR-059` | **POST_MVP** | Deferred per `DEC-04` |
| 69 | `GROUP-02` | `roomsync_group_compatibility_analysis` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Breakdown Matrix | `FR-056` | **POST_MVP** | Must evaluate all-member conflicts, not pairwise average (`HANDOFF` §5) |
| 70 | `GROUP-02` | `roomsync_group_accommodation_search` (`code.html`, `screen.png`) | Web (`web_standard`) | `HTML + PNG` | Search / Votes | `FR-058`, `FR-060` | **POST_MVP** | Deferred per `DEC-04` |
| 71 | `GROUP-01` | `roomsync_mobile_roommate_groups_discovery` (`code.html`) | Android (`mobile_tab`) | `HTML only` (**PNG MISSING**) | Default | `FR-058` | **POST_MVP** | Deferred per `DEC-04` |
| 72 | `GROUP-01` | `roomsync_mobile_create_roommate_group` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Form | `FR-053`, `FR-057` | **POST_MVP** | Deferred per `DEC-04` |
| 73 | `GROUP-01` | `roomsync_mobile_group_invitations_membership` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Invites List | `FR-054`, `FR-055` | **POST_MVP** | Deferred per `DEC-04` |
| 74 | `GROUP-01` | `roomsync_mobile_group_details_governance` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Detail / Admin | `FR-055`, `FR-060` | **POST_MVP** | Deferred per `DEC-04` |
| 75 | `GROUP-01` | `roomsync_mobile_pod_group_chat_planning` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Group Chat | `FR-059` | **POST_MVP** | Deferred per `DEC-04` |
| 76 | `GROUP-02` | `roomsync_mobile_group_compatibility_conflict_resolution` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Matrix | `FR-056` | **POST_MVP** | Deferred per `DEC-04` |
| 77 | `GROUP-02` | `roomsync_mobile_group_accommodation_discovery` (`code.html`, `screen.png`) | Android (`mobile_tab`) | `HTML + PNG` | Feed | `FR-058`, `FR-060` | **POST_MVP** | Deferred per `DEC-04` |
| 78 | `GROUP-02` | `roomsync_mobile_group_accommodation_planning` (`code.html`, `screen.png`) | Android (`mobile_stack`) | `HTML + PNG` | Planning | `FR-060` | **POST_MVP** | Deferred per `DEC-04` |
| 79 | `ADMIN-01` | `roomsync_admin_executive_overview_platform_operations` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Dashboard | `FR-123`, `FR-127` | **ADMIN/OPS** | Replaced in pilot by **hardened Django Admin (`DEC-09`)** |
| 80 | `ADMIN-01` | `roomsync_admin_user_management_member_governance` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Table | `FR-124` | **ADMIN/OPS** | Replaced by Django Admin user/status moderation (`DEC-09`) |
| 81 | `ADMIN-01` | `roomsync_admin_identity_verification_kyc_queue` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Queue | `FR-076`, `FR-077`, `FR-123` | **ADMIN/OPS** | Replaced by Django Admin private verification review action (`DEC-09`) |
| 82 | `ADMIN-01` | `roomsync_admin_property_listing_approvals` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Queue | `FR-052`, `FR-125` | **ADMIN/OPS** | Replaced by Django Admin listing moderation (`DEC-09`) |
| 83 | `ADMIN-01` | `roomsync_admin_reports_incident_moderation` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Queue | `FR-081`, `FR-126` | **ADMIN/OPS** | Replaced by Django Admin report moderation (`DEC-09`) |
| 84 | `ADMIN-01` | `roomsync_admin_activity_audit_logs_dpdp_compliance` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Audit | `FR-128`, DPDP | **ADMIN/OPS** | Replaced by read-only `AdminAuditLog` view inside Django Admin (`DEC-09`) |
| 85 | `ADMIN-01` | `roomsync_admin_roommate_groups_pod_governance` (`code.html`, `screen.png`) | Web (`web_dashboard`) | `HTML + PNG` | Admin Groups | `FR-053`–`060`, `FR-123` | **ADMIN/OPS** | Groups deferred (`DEC-04`) + custom admin deferred (`DEC-09`) |

---

## Gaps: Missing Screens Required by PRD / TDD (Not Exported in Stitch)

The following required workflows have **no dedicated Stitch export** and follow approved scope rules (`OD-U5`):

1. **Create / Edit Accommodation Listing (Web + Android — `PRD` FR-047/048, `TDD` §8.2 `POST /listings`, Milestone 8/9 — APPROVED IN SCOPE, `OD-U5`):** Owner/existing tenant flow to post room details, INR rent/deposit, city/locality, house rules, and upload listing media. **New Warm Tech Harmony design required & approved before Milestone 8 UI implementation.**
2. **Dedicated Forgot / Reset Password Flow (Web + Android — `AUTH-01`, `PRD` FR-003, `TDD` §8.2 `/auth/password/forgot` & `/reset`, Milestone 7/9):** Not separated from welcome screens in current Stitch exports.
3. **Mobile Connection Requests Inbox (`CONN-01`, `OD-U3`, `PRD` FR-037–039, Milestone 9):** Required for Android MVP parity under the approved 5-tab bar (`Discover`, `Requests`, `Chat`, `Stays`, `Profile`); adapt card states from Web `roomsync_connection_requests_inbox` & `request_details`.
4. **Side-by-Side Roommate Comparison (`PRD` FR-041 — DEFERRED TO P1, `OD-U5`):** No Stitch export exists (`roomsync_saved_properties_comparison` is properties only); deferred to P1 after core MVP launch.
5. **Dedicated Mobile Account Deletion Flow (`Dossier` §5.1, `PRD` FR-006, Milestone 9):** Referenced in mobile architecture notes (`roomsync_mobile_account_deletion`) but omitted from the exported Stitch zip; implement under Android `Profile → Privacy & Security` using `POST /api/v1/me/deletion-request`.
6. **Mobile Empty / Loading / Error / Success State Suites (`STATE-01`–`STATE-04`, Milestone 9):** Only Web component sheets were exported; mirror state semantics cleanly in React Native (`apps/android`).

Do not infer that a feature is implemented just because a design exists.

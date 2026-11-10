# ADR-002: Deterministic 8-Dimension Compatibility Engine & Scoring Semantics

- **Status:** Accepted (`DEC-02`, `OD-U2` Framework; Exact 20-Q Catalog `PROPOSED` in [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md))
- **Date:** 11 November 2026
- **Deciders:** Engineering Lead / Product Owner & System Architect
- **Supersedes / Reconciles:** Rejects the 5-category weighting formula (`25/25/20/15/15`) found in `Docs/Design/stitch_roomsync_roommate_discovery_platform/roomsync_engineering_handoff_dossier_tokens_spec.md` §3.1; resolves the 9-vs-8 bullet discrepancy in `Docs/product/PRD.md` FR-026 vs. FR-027.

---

## 1. Context

Two competing compatibility formulas appeared in Phase 0 artifacts:
- **Approved `PRD.md` FR-027 & `TDD.md` §9.1 Formula:** 8 weighted lifestyle categories totaling 100 (`Daily routine: 15`, `Cleanliness: 15`, `Financial expectations: 15`, `Privacy and boundaries: 15`, `Social lifestyle: 10`, `Food preferences: 10`, `Guest preferences: 10`, `Work/study environment: 10`). Also reflected directly in `roomsync_roommate_profile_compatibility_intelligence/code.html` (*"8 Core TDD Lifestyle Dimensions"*).
- **Stitch Handoff Dossier §3.1 Variant:** 5 macro categories (`Sleep & Routine 25%`, `Cleanliness & Chores 25%`, `Social & Guests 20%`, `Dietary & Kitchen 15%`, `Work/WFH & Noise 15%`), which omitted **Financial expectations** (`15%`) and **Privacy & boundaries** (`15%`).
- Additionally, `PRD.md` FR-026 lists `"Accommodation preferences"` as a 9th descriptive bullet even though `FR-027` weights sum to 100 across the 8 lifestyle categories.

---

## 2. Decision

1. **Authoritative Category Weights (`weights-2026-01`, `DEC-02`):**  
   Standardize exclusively on the **8 TDD categories** in `services/matching/`:

   | Key (`category`) | Display Label | Weight | Notes |
   |---|---|---:|---|
   | `daily_routine` | Daily routine | **15** | Wake/sleep times (`circular time distance`), quiet hours |
   | `cleanliness` | Cleanliness | **15** | Shared space tidiness, chore frequency, sink/kitchen discipline |
   | `financial_expectations` | Financial expectations | **15** | Rent/utility split fairness, bill timing, shared consumables |
   | `privacy_and_boundaries` | Privacy and boundaries | **15** | Personal space, room entry, borrowing items, communication style |
   | `social_lifestyle` | Social lifestyle | **10** | Introvert/extrovert home energy, weekend social vibe |
   | `food_preferences` | Food preferences | **10** | Dietary kitchen compatibility (veg/non-veg/eggetarian, cooking overlap) |
   | `guest_preferences` | Guest preferences | **10** | Friend/family visit frequency, overnight guest tolerance |
   | `work_study_environment` | Work/study environment | **10** | WFH/study schedule, call noise tolerance, desk space |
   | **Total** | | **100** | Versioned in config (`weights-2026-01`), never scattered constants |

2. **Separation of Accommodation Preferences from Lifestyle Score:**  
   Hard constraints (`city`, `locality`, `budget_min_paise`–`budget_max_paise`, `preferred_move_in_date`, `room_sharing_preference`) live in `preferences_accommodation` and act as **eligibility filters and secondary ranking signals** (`TDD.md` §9.2 step 9, §10), **not** as a 9th weight inside the 100-point lifestyle compatibility score.

3. **Deterministic 20-Question `v1` Framework, Missing Answers & Scoring Rules (`OD-U2`, `TDD.md` §9.3–§9.5):**
   - **`v1` Scope:** Standardize on **20 structured questions** distributed across the 8 categories (`[QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md)`), requiring explicit owner sign-off before Milestone 3 coding.
   - **`flexible` & `not_sure` Answer Support:** Every structured question explicitly supports **`flexible`** and **`not_sure`** responses alongside primary canonical options.
   - **Scorer Dispatch:** Use question-type-specific scorers: circular time-of-day distance (24h wraparound so `23:30` vs `00:30` scores close, not distant), normalized numeric distance, directional asymmetric matrix (e.g., Guest frequency *A* vs. Guest tolerance *B*, and *B* vs. *A*), multi-select Jaccard where meaningful, and categorical compatibility maps. Never compare every question by naive string equality.
   - **Canonical Pairwise Score (`overall_score`) & `coverage`:**
     $$\text{overall\_score} = \frac{\sum_{c \in \text{scored}} \text{score}_c \times w_c}{\sum_{c \in \text{scored}} w_c}, \qquad \text{coverage} = \frac{\sum_{c \in \text{scored}} w_c}{\sum_{c \in \text{applicable}} w_c}$$
   - **Missing Data & `Unknown / Not answered` Non-Exclusion Rule (`OD-U2`):** Unanswered or `"not_sure"` candidate answers **lower `coverage` (`0.00–1.00`)**, **must render cleanly as `Unknown / Not answered`**, and **must NEVER automatically exclude a candidate or fabricate incompatibility/100% scores**.
   - **Configurable Deal-Breaker Veto (`OD-U2`):** `supports_deal_breaker` is configurable per question/answer type (`preferences_question` metadata enforced by DB `CheckConstraint` on `preferences_answer`). Deal-breakers evaluate bidirectionally: a confirmed direct conflict sets `status = "blocked_by_dealbreaker"` and is never masked by high overall scores; if a deal-breaker item is unanswered or `"not_sure"` on either side, return `unknown_deal_breakers` and keep the candidate visible (`Unknown / Not answered` indicator).

4. **Strict Payload & Snapshot Privacy (`TDD.md` §9.6–§9.7):**
   - Django sends FastAPI pseudonymous UUIDs and canonical answer codes only — zero names, emails, phones, bios, or addresses.
   - Explanations return curated, non-leaking `explanation_codes` (e.g., `SLEEP_SCHEDULE_CLOSE`, `CLEANING_EXPECTATIONS_DIFFER`) + high-level discussion prompts rather than exposing raw private answers beyond the target user's visibility permissions.
   - Every persisted `CompatibilitySnapshot` stores `algorithm_version`, `weights_version`, `input_fingerprint`, and canonical `user_low_id < user_high_id` so score computation is 100% reproducible and cache-invalidated deterministically when answers change.

---

## 3. Consequences

- **Positive:** Preserves critical Indian shared-housing predictors (`financial_expectations` and `privacy_and_boundaries`, 30% combined weight); prevents deceptive "95% match" artifacts or unfair zero-shot exclusions on incomplete profiles; aligns Stitch UI compatibility breakdowns (`roomsync_roommate_profile_compatibility_intelligence`) 1:1.
- **Required Follow-Up:** Complete separate owner review and sign-off on [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md) (exact 20 keys/options and deal-breaker rules) prior to **Milestone 3** implementation.


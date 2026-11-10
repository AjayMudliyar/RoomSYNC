# RoomSync — Proposed v1 Lifestyle Questionnaire Catalog & Deal-Breaker Rules

- **Status:** **PROPOSED — Requires Separate Owner Review & Approval Before Milestone 3 Implementation**
- **Parent Policy (`OD-U2` — Approved):**
  - **20 structured questions** across the **8 approved TDD compatibility categories** (`ADR-002`).
  - Explicit support for **`flexible`** and **`not_sure`** (*"prefer not to say" / unsure*) answers.
  - **`is_deal_breaker` eligibility is configurable per question/answer type** (`preferences_question.supports_deal_breaker` enforced via DB `CheckConstraint` on `preferences_answer`).
  - **Unanswered Candidate Display Rule:** An unanswered question on a candidate's profile MUST render as **`Unknown / Not answered`** and MUST **NOT** automatically exclude that candidate from discovery or penalize compatibility percentage (`coverage` reflects completeness).

---

## 1. Category Weight & Question Allocation Summary (`weights-2026-01`)

| # | Category Key | Category Label | Approved Weight | Proposed Questions (`v1`) | Deal-Breaker-Eligible Questions |
|---|---|---|---:|---:|---:|
| 1 | `daily_routine` | Daily routine | `15` | 3 | 1 (`q_quiet_hours`) |
| 2 | `cleanliness` | Cleanliness | `15` | 3 | 1 (`q_dish_wash_timing`) |
| 3 | `financial_expectations` | Financial expectations | `15` | 2 | 0 |
| 4 | `privacy_and_boundaries` | Privacy and boundaries | `15` | 3 | 2 (`q_smoking_policy`, `q_pets_policy`) |
| 5 | `social_lifestyle` | Social lifestyle | `10` | 2 | 1 (`q_alcohol_policy`) |
| 6 | `food_preferences` | Food preferences | `10` | 2 | 1 (`q_kitchen_diet_rule`) |
| 7 | `guest_preferences` | Guest preferences | `10` | 3 | 1 (`q_overnight_guest_policy`) |
| 8 | `work_study_environment` | Work/study environment | `10` | 2 | 1 (`q_daytime_call_noise_sensitivity`) |
| | **Total** | | **100** | **20** | **8 configurable** *(max recommended user deal-breakers: 3–4)* |

---

## 2. Proposed 20-Question Catalog (`version = 1`)

Every single-choice question includes canonical options plus standardized meta-options **`flexible`** (`"Flexible / Adaptable"`) and **`not_sure`** (`"Not sure / Prefer not to decide yet"`). Time/range fields allow an explicit `"flexible"` or `"not_sure"` sentinel state alongside structured values.

### Category 1 — `daily_routine` (Weight: 15)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 1 | `q_wake_time` | What time do you usually wake up on weekdays? | `time_of_day` | `HH:MM` (24h, 30-min increments) + `flexible`, `not_sure` | `false` | Circular 24h time distance (tolerance `<= 1.5h` high, `>= 5h` low) |
| 2 | `q_sleep_time` | What time do you usually go to sleep on weekdays? | `time_of_day` | `HH:MM` (24h wraparound, e.g., `22:30`–`02:30`) + `flexible`, `not_sure` | `false` | Circular 24h time distance (handles midnight wraparound cleanly) |
| 3 | `q_quiet_hours` | How strict do you need shared quiet hours after 11:00 PM on weeknights? | `single_select` | `strict_quiet` (silence/headphones), `moderate_quiet` (low TV/calls in room), `relaxed` (no strict curfew), `flexible`, `not_sure` | **`true`** | Ordinal distance matrix |

### Category 2 — `cleanliness` (Weight: 15)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 4 | `q_common_tidiness` | How tidy do you keep shared living spaces (living room, hallway, dining)? | `single_select` | `spotless_daily`, `tidy_weekly_reset`, `lived_in_casual`, `flexible`, `not_sure` | `false` | Ordinal compatibility matrix |
| 5 | `q_dish_wash_timing` | When should dirty dishes and cookware be cleared from the kitchen sink? | `single_select` | `immediately_after_use`, `same_day_by_night`, `within_24_hours`, `flexible`, `not_sure` | **`true`** | Ordinal compatibility matrix |
| 6 | `q_cleaning_method` | How do you prefer household chores and cleaning to be handled? | `single_select` | `hire_shared_maid`, `rotating_chore_schedule`, `clean_as_needed_together`, `flexible`, `not_sure` | `false` | Categorical compatibility map (`hire_shared_maid` compatible with `rotating` partially, etc.) |

### Category 3 — `financial_expectations` (Weight: 15)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 7 | `q_shared_expense_style` | How should shared recurring utilities (electricity, Wi-Fi, cook/maid, water) be split? | `single_select` | `equal_split_all`, `usage_weighted_ac_extras`, `separate_consumables_equal_utilities`, `flexible`, `not_sure` | `false` | Categorical compatibility map |
| 8 | `q_bill_settlement_timing` | How do you prefer shared rent and monthly bills to be settled? | `single_select` | `upfront_before_due_date`, `within_3_days_of_bill`, `monthly_end_reconciliation`, `flexible`, `not_sure` | `false` | Ordinal compatibility matrix |

### Category 4 — `privacy_and_boundaries` (Weight: 15)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 9 | `q_personal_space_style` | How much interaction vs. personal privacy do you prefer with roommates at home? | `single_select` | `high_privacy_independent`, `friendly_balanced`, `close_hangout_often`, `flexible`, `not_sure` | `false` | Ordinal compatibility matrix |
| 10 | `q_smoking_policy` | What is your habit and expectation regarding smoking or vaping at home? | `single_select` | `strict_no_smoking`, `balcony_outside_only`, `smoke_inside_ok`, `flexible`, `not_sure` | **`true`** | Asymmetric habit-vs-tolerance matrix |
| 11 | `q_pets_policy` | What is your situation and comfort level with pets in the flat? | `single_select` | `bring_pet`, `no_pet_happy_with_pets`, `no_pets_preferred`, `allergic_no_pets`, `flexible`, `not_sure` | **`true`** | Asymmetric ownership-vs-allergy matrix |

### Category 5 — `social_lifestyle` (Weight: 10)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 12 | `q_home_social_vibe` | What kind of weekend atmosphere do you prefer in the flat? | `single_select` | `quiet_recharging`, `occasional_dinners_games`, `lively_social_hub`, `flexible`, `not_sure` | `false` | Ordinal compatibility matrix |
| 13 | `q_alcohol_policy` | How do you feel about alcohol consumption in shared common areas? | `single_select` | `no_alcohol_in_flat`, `in_private_room_only`, `common_areas_ok_responsibly`, `flexible`, `not_sure` | **`true`** | Ordinal boundary compatibility |

### Category 6 — `food_preferences` (Weight: 10)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 14 | `q_kitchen_diet_rule` | What dietary and shared-kitchen arrangement works for you? | `single_select` | `strict_veg_only_kitchen`, `veg_prefer_separate_utensils`, `eggetarian_nonveg_ok_no_smell`, `all_foods_ok`, `flexible`, `not_sure` | **`true`** | Asymmetric kitchen rule compatibility |
| 15 | `q_cooking_sharing_habit` | How do you expect cooking, groceries, or maid meals to work? | `single_select` | `completely_independent`, `shared_cook_or_staples`, `cook_together_often`, `rarely_cook`, `flexible`, `not_sure` | `false` | Categorical compatibility map |

### Category 7 — `guest_preferences` (Weight: 10)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 16 | `q_guest_visit_frequency` | How often do you personally expect to host friends or family at the flat? | `single_select` | `rarely_never`, `few_times_a_month`, `weekly_or_more`, `flexible`, `not_sure` | `false` | Evaluated asymmetrically against partner's `q_guest_visit_tolerance` |
| 17 | `q_guest_visit_tolerance` | How comfortable are you when your roommate hosts daytime guests? | `single_select` | `prefer_no_guests`, `with_advance_notice`, `frequent_guests_welcome`, `flexible`, `not_sure` | `false` | Evaluated asymmetrically against partner's `q_guest_visit_frequency` |
| 18 | `q_overnight_guest_policy` | What is your boundary for overnight guests staying in the flat? | `single_select` | `no_overnight_guests`, `rare_with_prior_consent`, `occasional_weekends_ok`, `open_policy`, `flexible`, `not_sure` | **`true`** | Bidirectional boundary check |

### Category 8 — `work_study_environment` (Weight: 10)

| # | Key | Prompt | Answer Type | Canonical Options / Range | Deal-Breaker Eligible? | Scoring Mode |
|---:|---|---|---|---|---|---|
| 19 | `q_work_study_schedule` | What best describes your typical weekday work or class location? | `single_select` | `on_site_campus_daily`, `hybrid_2_3_days_home`, `mostly_wfh_or_remote_study`, `night_shift_or_variable`, `flexible`, `not_sure` | `false` | Categorical matrix (space/utility overlap alignment) |
| 20 | `q_daytime_call_noise_sensitivity` | How sensitive are you to daytime work/study calls or ambient noise during 9 AM – 7 PM? | `single_select` | `need_quiet_study_zone`, `moderate_normal_calls_ok`, `unbothered_headphones`, `flexible`, `not_sure` | **`true`** | Cross-evaluated with `q_work_study_schedule` |

---

## 3. Proposed Deal-Breaker & Missing-Answer Rules (For Owner Sign-Off)

### 3.1 Question-Type Configurability (`CheckConstraint`)
1. Only questions with `supports_deal_breaker = True` (explicitly `single_select` boundary/habit questions with unambiguous conflict states; **never** continuous `time_of_day` clocks or `multi_select` tags) can have `preferences_answer.is_deal_breaker = True`.
2. Database-level `CheckConstraint` prevents clients from forging deal-breakers on unsupported questions or combining `answer = "flexible"` / `answer = "not_sure"` with `is_deal_breaker = True`.
3. Product UI cap recommendation (configurable): allow users to mark up to **4 active deal-breakers** initially so feeds remain viable in early cohorts.

### 3.2 Bidirectional Deal-Breaker Evaluation Matrix
When evaluating candidate pair `(Viewer A, Candidate B)`:
1. **Mutual Hard Conflict:** If either A's or B's non-negotiable threshold directly conflicts with the other's declared answer (for example: A sets `q_smoking_policy = strict_no_smoking` with `is_deal_breaker = true`, while B selects `smoke_inside_ok` or `balcony_outside_only`), return:
   - `status = "blocked_by_dealbreaker"`
   - `deal_breaker_conflicts = ["SMOKING_POLICY_CONFLICT"]` *(neutral, non-shaming explanation code)*
   - Excluded from top `"Recommended Matches"` default sort or clearly gated per feed filter; never masked by high score in other categories.
2. **Viewer Sets Deal-Breaker + Candidate Selected `flexible`:**
   - Because `"flexible"` means willingness to adapt, this resolves as **compatible (`100` / no veto)** while keeping `"Candidate marked Flexible"` visible in explanation metadata so expectations are confirmed in chat.
3. **Viewer Sets Deal-Breaker + Candidate Selected `not_sure` OR Question Unanswered:**
   - **Per approved `OD-U2`:** Do **NOT** fail the match or auto-hide the candidate!
   - Return `unknown_deal_breakers = ["SMOKING_POLICY_UNKNOWN"]` alongside `status = "eligible"` (unless blocked by another known conflict).
   - Product UI displays `"Unknown / Not answered"` badge on that breakdown row and encourages confirming in chat; `coverage` decreases proportionally because the category weight/question lacked concrete data.
4. **Importance Weighting Within Category:**
   - Answers tagged `importance = must_have` (`1.5x`), `important` (`1.0x`), or `flexible` (`0.5x`) adjust relative intra-category weight while **category weights (`15/15/15/15/10/10/10/10`)** remain fixed under `weights-2026-01`.

---

## 4. Owner Review Sign-Off Checklist (Before Milestone 3)

- [ ] Approve or adjust the exact 20 question keys and wording for urban Indian students, interns, and young professionals.
- [ ] Approve the **8 questions** flagged `supports_deal_breaker = True` (and whether `importance = must_have` cap of 4 deal-breakers is desired).
- [ ] Approve asymmetric pair rules (`q_guest_visit_frequency` vs. `q_guest_visit_tolerance`, and `q_smoking_policy` balcony tolerance edge cases).
- [ ] Confirm minimum `coverage` threshold (e.g., `>= 0.40`, or show all active eligible profiles sorted by confidence + score) for pilot launch feeds.

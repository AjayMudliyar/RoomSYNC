# RoomSync User Flows
**Version:** 1.0 — Product journey baseline  
**Source:** RoomSync PRD and TDD. Validate each step against final Stitch exports and actual API contracts.

## 1. New user onboarding
1. User opens RoomSync.
2. User chooses registration or sign-in.
3. User completes supported authentication and accepts applicable terms/privacy notices.
4. User enters basic profile information.
5. User selects preferred city/locality and accommodation requirements.
6. User completes the lifestyle questionnaire.
7. User reviews answers and can edit categories.
8. User submits; onboarding progress is saved.
9. User reaches roommate discovery when the minimum required profile data is complete.

**Rules:** Support save/resume. Clearly mark required and optional fields. Do not treat unanswered answers as incompatibilities. Keep private answers private by default.

## 2. Roommate discovery and compatibility
1. Authenticated user opens discovery.
2. System retrieves eligible candidate profiles using location and other permitted filters.
3. System calculates or retrieves a versioned compatibility result.
4. User sees candidate cards with score and concise, grounded explanation.
5. User opens a profile.
6. User reviews visible profile and lifestyle details.
7. User opens compatibility breakdown to understand category-level alignment and discussion points.
8. User may save or dismiss a candidate where supported.

**Rules:** Scores must be explainable, based on declared inputs and versioned weights. Do not expose hidden profile fields. A score is not a guarantee of a successful living arrangement.

## 3. Connection request
1. User opens a candidate profile.
2. User sends a connection request.
3. System validates eligibility, duplicate/pending state and rate limits.
4. Recipient receives an in-app notification.
5. Recipient accepts or declines.
6. If accepted, the connection becomes active and the permitted communication flow becomes available.
7. Both users see the correct request/connection state.

**Rules:** Never show a request as accepted before recipient action. Prevent duplicate requests and unauthorized state changes.

## 4. One-to-one messaging
1. User opens an eligible active connection.
2. User opens or starts the conversation.
3. User sends a message.
4. System persists the message and returns its canonical state.
5. Recipient sees the message and receives an appropriate notification.
6. Failed sends show a retry action without duplicating already accepted messages.

**Rules:** Enforce conversation membership on every read/write. Do not expose message content in logs. Realtime delivery can be phased; reliable persisted messaging is the baseline.

## 5. Accommodation discovery and enquiry
1. User opens accommodation discovery.
2. User searches by city/locality and applies available filters.
3. User views listing cards and opens a property detail page.
4. User reviews rent, deposit, amenities, location and owner-provided details.
5. User saves the property or submits an enquiry.
6. System confirms enquiry submission and records its status.
7. User can view enquiry status where supported.

**Rules:** Listing information must be labelled according to its source. Never invent availability or verification. An enquiry is not a booking and does not transfer money.

## 6. Roommate group journeys — phased
1. User creates a group and sets its intended location, budget and move-in preferences.
2. User invites eligible connections or users.
3. Invitees accept or decline.
4. Group members review group requirements and potential conflicts.
5. Group explores suitable accommodation and discusses options.

**Rules:** Group compatibility must consider all members and multi-person conflicts; it must not be a simple average of pairwise scores. Treat this as post-MVP unless the implementation plan approves a narrow initial slice.

## 7. Trust, safety and verification
1. User opens Trust Centre.
2. User reviews safety guidance and available trust indicators.
3. If verification is supported, user sees the actual provider/process and submits required evidence through a secure flow.
4. System shows `Submitted` / `Under review` until a real review decision is recorded.
5. Authorized reviewer approves, rejects or requests more information.
6. User sees the accurate outcome and next steps.
7. User can report or block another user through available safety controls.

**Rules:** Submission is not approval. Never display provider badges or imply integrations that do not exist. Restrict verification evidence to authorized workflows and private storage.

## 8. Settings, privacy and account lifecycle
1. User opens settings.
2. User edits profile, lifestyle preferences, accommodation preferences or notification preferences.
3. User adjusts visibility and privacy settings.
4. User may request data export or account deletion where supported.
5. System confirms a request separately from completion.
6. User logs out or manages sessions.

**Rules:** Explain visibility choices clearly. Do not claim account deletion is complete until the backend confirms completion.

## 9. Admin / operations flow
1. Authorized administrator signs in through a protected admin workflow.
2. Admin views permitted user/listing/report queues.
3. Admin opens a specific case and reviews only the data needed for that task.
4. Admin records an action with reason and audit trail.
5. System updates status and notifies affected users where appropriate.

**Rules:** Enforce least privilege, audit sensitive actions, and do not expose identity evidence in general user tables.

## 10. MVP journey priority
Build and test this end-to-end loop first:
**Register → complete profile → answer questionnaire → discover candidates → inspect compatibility → send/receive request → accept connection → start basic conversation.**

Accommodation listings/enquiries and admin moderation follow according to the TDD's MVP sequencing. Group matching, advanced group accommodation planning, simulator and AI assistant remain later phases unless scope is explicitly revised.

# RoomSync — Engineering Handoff Dossier & Design Tokens Specification
**Version:** 2.4.0-PROD  
**Design System:** Warm Tech Harmony (`#faf8ff` / `#1e1b4b` / `#059669`)  
**Target Platforms:** React Web (Tailwind CSS 3.4+) & React Native (iOS / Android 360px–430px)  
**Compliance Standards:** India DPDP Act 2023, WCAG 2.1 AA, Kaveri 2.0 Land Records Standard  

---

## 1. Executive Summary & Design System Foundations

RoomSync is a compatibility-first shared living and roommate discovery platform built on deterministic behavioral vectors, verified trust credentials (DigiLocker Government ID + Corporate SSO), and collective pod governance.

### 1.1 Core Semantic Color Tokens

```json
{
  "color": {
    "canvas": {
      "base": "#faf8ff",
      "surface": "#faf8ff",
      "surface-container-lowest": "#ffffff",
      "surface-container-low": "#f8fafc",
      "surface-container-high": "#f1f5f9",
      "surface-dim": "#e2e8f0"
    },
    "text": {
      "primary": "#1e1b4b",
      "secondary": "#475569",
      "muted": "#94a3b8",
      "inverse": "#ffffff"
    },
    "brand": {
      "primary": "#059669",
      "primary-hover": "#047857",
      "primary-tint": "#ecfdf5",
      "accent": "#4f46e5",
      "accent-hover": "#4338ca",
      "accent-tint": "#eef2ff"
    },
    "state": {
      "success": "#059669",
      "success-surface": "#ecfdf5",
      "warning": "#d97706",
      "warning-surface": "#fffbeb",
      "danger": "#dc2626",
      "danger-surface": "#fef2f2",
      "info": "#0284c7",
      "info-surface": "#f0f9ff"
    },
    "border": {
      "subtle": "#e2e8f0",
      "strong": "#cbd5e1",
      "focus": "#059669"
    }
  }
}
```

### 1.2 Tailwind CSS Configuration (`tailwind.config.js`)

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        canvas: '#faf8ff',
        'navy-950': '#1e1b4b',
        'slate-subtle': '#475569',
        'emerald-brand': '#059669',
        'indigo-accent': '#4f46e5',
        'border-dim': '#e2e8f0',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'card': '0 4px 14px 0 rgba(30, 27, 75, 0.05)',
        'modal': '0 20px 40px -15px rgba(30, 27, 75, 0.16)',
        'elevated': '0 8px 24px -4px rgba(30, 27, 75, 0.08)',
      }
    }
  }
}
```

---

## 2. Typography & Spatial Layout System

### 2.1 Type Scale (Plus Jakarta Sans)
- **`display-xl`**: `36px / 44px`, font-weight `800`, tracking `-0.025em` (Mobile Hero Headers)
- **`heading-lg`**: `24px / 32px`, font-weight `700`, tracking `-0.015em` (Section Anchors)
- **`heading-md`**: `20px / 28px`, font-weight `600`, tracking `-0.01em` (Card Titles)
- **`heading-sm`**: `18px / 26px`, font-weight `600`, tracking `0em` (Module Subheads)
- **`body-lg`**: `16px / 24px`, font-weight `500` (Bio text, lead paras)
- **`body-md`**: `14px / 20px`, font-weight `400` & `500` (Default label & field text)
- **`body-sm`**: `12px / 18px`, font-weight `500` (Meta timestamps, tags, subtitles)
- **`badge-caption`**: `11px / 14px`, font-weight `700`, tracking `+0.03em`, uppercase (Status pills)

### 2.2 Layout Rules & Touch Accessibility
- **Minimum Touch Target**: 44px × 44px on all interactive inputs and icon buttons.
- **Sticky CTA Safe Areas**: Containers with sticky floating buttons must enforce `pb-32` (`8rem` / `128px`) on mobile scroll views.
- **Mobile Navigation Bar**: Persistent 5-tab bar height `64px` with safe area bottom inset.

---

## 3. UI Component State Matrix

### 3.1 Button Hierarchy
1. **Primary Action**: `bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-semibold rounded-xl px-5 py-3 shadow-sm`
2. **Secondary Neutral**: `bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 font-medium rounded-xl px-4 py-3`
3. **Indigo Accent Action**: `bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl px-5 py-3`
4. **Destructive Action**: `bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl px-5 py-3`
5. **Disabled State**: `opacity-50 cursor-not-allowed pointer-events-none`

### 3.2 Badges & Indicators
- **Tier-1 DigiLocker Aadhaar**: Emerald tag (`bg-emerald-50 text-emerald-800 border border-emerald-200/60 rounded-full px-2.5 py-1 text-xs font-semibold`)
- **Tier-2 Corporate SSO**: Indigo tag (`bg-indigo-50 text-indigo-700 border border-indigo-200/60 rounded-full px-2.5 py-1 text-xs font-semibold`)
- **90%+ Synergy Indicator**: Mint badge with pulsing dot and radial score ring.
- **Under Review / Deed Pending**: Amber tag (`bg-amber-50 text-amber-700 border border-amber-200/80 rounded-full px-2.5 py-1 text-xs font-medium`)

---

## 4. Key Behavioral Algorithms & Privacy Specifications

### 4.1 5-Dimension Compatibility Vector
The matchmaking algorithm calculates composite affinity $S_{total}$ using normalized weights:
1. **Circadian / Sleep Schedule ($W = 0.25$)**: Bedtime/wake-up chronotype alignment.
2. **Cleanliness & Chores ($W = 0.25$)**: Hygiene frequency and shared maid policies.
3. **Food & Kitchen Protocol ($W = 0.20$)**: Dietary habits and cookware separation preferences.
4. **Work Commute & Noise ($W = 0.15$)**: WFH schedule and call quietness standards.
5. **Guests & Social Policy ($W = 0.15$)**: Overnight visitor protocols.

*Rule:* Unanswered questions must register as `NEUTRAL` and not penalize synergy scores.

### 4.2 DPDP Act 2023 Statutory Privacy Compliance
- Phone numbers and WhatsApp identities are cryptographically masked (`+91 98450 •••••`) until both parties accept a mutual handshake.
- Compensation is never displayed in absolute numbers; only verified budget corridors are exposed (e.g., `₹20k–₹28k`).
- Account deletion enforces a 2-step SMS OTP verification and a 24-hour revocable cooldown period before permanent non-custodial record scrub.

---

## 5. Screen Inventory & Flow Architecture

### 5.1 Mobile Application Screens (Android 390px base)
- **Authentication & Auth Cooldown**:
  - `RoomSync Mobile — Welcome & Auth`
  - `RoomSync Mobile — OTP Rate-Limit Lockout` (Rate-limit 15-min cooldown & security snapshot)
  - `RoomSync Mobile — Camera Permission Denied Sheet` (Hardware permission recovery sheet)
- **Onboarding Flow (Linear 5-Step)**:
  - `RoomSync Mobile — Profile Setup` (Step 1 of 5)
  - `RoomSync Mobile — Housing Preferences` (Step 2 of 5)
  - `RoomSync Mobile — Lifestyle Questionnaire` (Step 3 of 5)
  - `RoomSync Mobile — Onboarding Review` (Step 4 of 5)
  - `RoomSync Mobile — Onboarding Complete` (Step 5 of 5)
- **Core Active Roommate Journey**:
  - `RoomSync Mobile — Discovery Feed` (5-Tab: Discover active)
  - `RoomSync Mobile — Roommate Profile & Compatibility` (Individual compatibility breakdown)
  - `RoomSync Mobile — Coliving Direct Chat` (1-on-1 end-to-end messaging)
  - `RoomSync Mobile — Trust Centre & Verification` (Tier 1 & 2 credentials & audit log)
- **Roommate Groups & Pod Governance**:
  - `RoomSync Mobile — Roommate Groups Discovery` (5-Tab: Pods active)
  - `RoomSync Mobile — Create Roommate Group` (Pod formation flow)
  - `RoomSync Mobile — Group Details & Governance` (Roster & consensus agreements)
  - `RoomSync Mobile — Group Compatibility & Conflict Resolution` (Multi-member vector overlap)
  - `RoomSync Mobile — Group Invitations & Membership` (Invite links & QR codes)
  - `RoomSync Mobile — Pod Group Chat & Planning` (Pod group messaging & polls)
  - `RoomSync Mobile — Group Accommodation Planning` (Shared property shortlist)
- **Accommodation & Flats Discovery**:
  - `RoomSync Mobile — Accommodation Discovery Dashboard` (5-Tab: Flats active)
  - `RoomSync Mobile — Accommodation Search & Filters` (Budget, BHK, Kaveri 2.0 filters)
  - `RoomSync Mobile — Map-Based Property Discovery` (Bangalore tech corridors)
  - `RoomSync Mobile — Property Details` (Room breakdown & amenity matrix)
  - `RoomSync Mobile — Saved Properties & Shortlist Hub` (Shortlists & compare drawers)
  - `RoomSync Mobile — Property Comparison` (Side-by-side room comparison)
  - `RoomSync Mobile — Property Enquiry & Visit Scheduling` (Slot booking & dossier sharing)
  - `RoomSync Mobile — Group Accommodation Discovery` (Multi-tenant property search)
- **Settings, Notifications & Account Governance**:
  - `RoomSync Mobile — Settings Dashboard` (5-Tab: Profile active, with radial score ring)
  - `RoomSync Mobile — Personal Profile Management` (Edit profile & locality anchors)
  - `RoomSync Mobile — Lifestyle Preferences` (Recalculate habit vectors)
  - `RoomSync Mobile — Privacy and Security` (DPDP masking & session control)
  - `RoomSync Mobile — Notifications Centre` (Activity hub & handshake notifications)
  - `RoomSync Mobile — Notification Preferences` (Circadian DND & dispatch matrix)
  - `RoomSync Mobile — Help and Support` (24/7 SOS safety concierge & FAQ accordions)
  - `RoomSync Mobile — Account Management & Deletion` (Export dossier & verified account purge)

### 5.2 Desktop & Admin Screens (1280px Web)
- `RoomSync — Roommate Discovery Dashboard`
- `RoomSync — Roommate Profile Detail & Compatibility Matrix`
- Complete Desktop Onboarding Flow (5 Screens)
- Complete Connection Requests & Messaging Flow (4 Screens)
- Complete Roommate Groups Flow (6 Screens)
- Complete Accommodation Discovery Flow (5 Screens)
- Complete Trust, Verification & Safety Flow (8 Screens)
- Complete Settings & Account Management Flow (8 Screens)
- Complete Notifications & Activity Hub Flow (4 Screens)
- Comprehensive States Suites:
  - `RoomSync — Empty States Design System & Component Catalog`
  - `RoomSync — Loading States & Skeleton Loaders`
  - `RoomSync — Error States & System Recovery Component Suite`
  - `RoomSync — Success & Confirmation States Component Suite`
- Internal Admin Operations Suite:
  - `RoomSync Admin — Executive Overview & Platform Operations`
  - `RoomSync Admin — User Management & Member Governance`
  - `RoomSync Admin — Identity Verification & KYC Queue`
  - `RoomSync Admin — Property Listing Approvals`
  - `RoomSync Admin — Reports & Incident Moderation`
  - `RoomSync Admin — Roommate Groups & Pod Governance`
  - `RoomSync Admin — Activity Audit Logs & DPDP Compliance`

---

## 6. Audit Resolution & Handoff Checklist

| Item | Description | Status | Verification Detail |
|---|---|---|---|
| **C1** | Mobile 5-Tab Bar Standardization | **PASSED** | Normalized to `[Discover, Pods, Flats, Chat, Profile]`. |
| **C2** | Mobile Sticky CTA Padding | **PASSED** | Added `pb-32` clearance on all floating action forms. |
| **H1** | Onboarding Step Numerator Sync | **PASSED** | Fixed linear progression `Step 1 of 5` through `Step 5 of 5`. |
| **H2** | Radial Trust Score Ring Gauge | **PASSED** | Unified SVG progress ring applied to Settings profile hero. |
| **M1** | Permission-Denied Recovery Sheet | **PASSED** | Delivered camera denial sheet with clear DPDP rationale. |
| **M2** | OTP Cooldown & Lockout Screen | **PASSED** | Delivered 15-min rate-limit screen with WhatsApp/SSO fast paths. |
| **P1** | Zero Unmasked Identifiers | **PASSED** | All phone numbers & emails masked until mutual handshake. |

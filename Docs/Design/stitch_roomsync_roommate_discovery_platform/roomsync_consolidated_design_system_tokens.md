# RoomSync Design System & Component Token Specification
**Source of Truth: Warm Tech Harmony (`#faf8ff` / `#1e1b4b` / `#059669`)**
**Platforms: React Web (Tailwind CSS) & React Native (iOS / Android)**

---

## 1. Color Palette & Semantic Design Tokens

### 1.1 Brand & Neutral Foundation
- **Canvas / Surface Background**: `#faf8ff` (Soft warm lavender-white tint)
- **Surface Dim / Border Stroke**: `#e2e8f0` / `#ede9fe`
- **Surface Container Lowest (Pure White Cards)**: `#ffffff`
- **Surface Container Low**: `#f8fafc`
- **Surface Container High (Tinted Section / Badges)**: `#f1f5f9` / `#e0e7ff`
- **Primary Navy / High-Emphasis Text**: `#1e1b4b` (Deep Indigo-Navy, 100% contrast)
- **Secondary Neutral Text**: `#475569` (Slate 600, WCAG AAA compliant)
- **Muted / Placeholder Text**: `#94a3b8` (Slate 400)
- **Divider / Subtle Borders**: `#e2e8f0` (1px solid border-slate-200)

### 1.2 Semantic Intent & Accent Tokens
- **Emerald Primary / Verified Trust**: `#059669` (Emerald 600), Hover: `#047857` (Emerald 700), Light Tint: `#ecfdf5` (Emerald 50)
- **Royal Indigo / Brand Accent**: `#4f46e5` (Indigo 600), Hover: `#4338ca`, Light Tint: `#eef2ff`
- **Warning / Amber Notice**: `#d97706` (Amber 600), Background: `#fffbeb`
- **Critical / Scam Red**: `#dc2626` (Red 600), Background: `#fef2f2`, Border: `#fecaca`
- **Info / Telegram Blue**: `#0284c7` (Sky 600), Background: `#f0f9ff`

---

## 2. Typography Scale (Plus Jakarta Sans)

| Token Name | Font Size | Line Height | Font Weight | Letter Spacing | CSS Utility / React Native Equivalent |
|---|---|---|---|---|---|
| `display-xl` | 36px | 44px | 800 (Extrabold) | -0.025em | `text-4xl font-extrabold tracking-tight` |
| `display-lg` | 30px | 38px | 700 (Bold) | -0.02em | `text-3xl font-bold tracking-tight` |
| `heading-lg` | 24px | 32px | 700 (Bold) | -0.015em | `text-2xl font-bold` |
| `heading-md` | 20px | 28px | 600 (Semibold) | -0.01em | `text-xl font-semibold` |
| `heading-sm` | 18px | 26px | 600 (Semibold) | 0em | `text-lg font-semibold` |
| `body-lg` | 16px | 24px | 500 (Medium) | 0em | `text-base font-medium` |
| `body-md` | 14px | 20px | 400 / 500 | 0em | `text-sm font-normal / font-medium` |
| `body-sm` | 12px | 18px | 500 / 600 | +0.01em | `text-xs font-medium` |
| `badge-caption` | 11px | 14px | 700 (Bold) | +0.03em | `text-[11px] font-bold uppercase tracking-wider` |

---

## 3. Spacing & Elevation Rhythm

- **Grid Base Unit**: 4px / 8px linear grid
- **Paddings**:
  - Compact Cards: `p-4` (16px)
  - Standard Section Cards: `p-6` (24px)
  - Hero / Container Blocks: `p-8` (32px)
- **Radii**:
  - Interactive Buttons / Inputs: `rounded-xl` (12px)
  - Containers / Feed Cards: `rounded-2xl` (16px)
  - Modals / Flyout Drawers: `rounded-3xl` (24px)
  - Badges / Pill Switches: `rounded-full` (9999px)
- **Shadows**:
  - `shadow-sm`: `0 1px 2px 0 rgb(0 0 0 / 0.05)`
  - `shadow-card`: `0 4px 14px 0 rgba(30, 27, 75, 0.06)`
  - `shadow-modal`: `0 20px 40px -15px rgba(30, 27, 75, 0.16)`

---

## 4. UI Component Patterns & State Matrix

### 4.1 Buttons
- **Primary Action (Verified Emerald)**: `bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-5 rounded-xl transition duration-150 shadow-sm active:scale-[0.98]`
- **Brand Action (Indigo Accent)**: `bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-5 rounded-xl`
- **Secondary / Ghost Neutral**: `bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 font-medium py-2.5 px-4 rounded-xl`
- **Destructive Action**: `bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 px-5 rounded-xl`
- **Disabled State**: `opacity-50 cursor-not-allowed pointer-events-none`

### 4.2 Form Controls & Inputs
- **Text / Number Input**: `w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition`
- **Active / Focused Input**: Emerald outer halo (`ring-4 ring-emerald-500/10 border-emerald-600`)
- **Error Input**: `border-red-500 ring-2 ring-red-500/10 text-red-900 placeholder:text-red-300`

### 4.3 Status Badges
- **UIDAI / DigiLocker Verified**: Emerald badge (`bg-emerald-50 text-emerald-800 border border-emerald-200/60 font-semibold px-2.5 py-1 rounded-full text-xs flex items-center gap-1.5`)
- **Corporate SSO Verified (Tier-2)**: Indigo badge (`bg-indigo-50 text-indigo-700 border border-indigo-200/60`)
- **Harmonic Compatibility (90%+)**: Mint / Emerald highlight pill with pulse dot
- **Disputed / Flagged**: Crimson alert badge (`bg-red-50 text-red-700 border border-red-200`)
- **Under Review / In Progress**: Amber badge (`bg-amber-50 text-amber-700 border border-amber-200`)

---

## 5. Responsive Breakpoint Rules
- **Mobile (`<640px` / 390px base)**: Single column stack, sticky bottom tab navigation (`h-16 bg-white border-t border-slate-200`), touch targets minimum `44px` height, horizontal swiping carousel for multi-property cards.
- **Tablet (`640px – 1024px`)**: Dual-column responsive grid, collapsible sidebar.
- **Desktop (`>=1024px` / 1280px standard)**: Top persistent navigation with Bangalore micro-market selector + profile dropdown, dual-column analytical splits (60/40), sticky action drawers.

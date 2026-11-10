# ADR-003: Canonical Warm Tech Harmony Design System & WCAG 2.1 AA Reconciliation

- **Status:** Accepted (`DEC-03`)
- **Date:** 11 November 2026
- **Deciders:** Engineering Lead / Product Owner & System Architect
- **Reconciles:** `Docs/DESIGN_SYSTEM.md` v1.0, `Docs/Design/.../warm_tech_harmony/DESIGN.md`, `Docs/Design/.../roomsync_consolidated_design_system_tokens.md`, and inline Tailwind configurations embedded inside all 85 Stitch `code.html` exports.

---

## 1. Context

Four visual design artifacts existed with conflicting color tokens, spacing units, and WCAG 2.1 AA contrast compliance issues:
1. **Emerald brand/action color:** `DESIGN_SYSTEM.md` defined `primary: #059669` (`3.77:1` with white text — fails AA normal text), `warm_tech_harmony/DESIGN.md` prose cited `#0D9488` (`3.74:1` — fails AA normal text), while `warm_tech_harmony/DESIGN.md` YAML + all 85 Stitch `code.html` exports used `secondary: #006a61` (`6.49:1` with white — passes AA everywhere).
2. **Primary role inversion:** `DESIGN_SYSTEM.md` used `primary = emerald (#059669)` and `text-primary = navy (#1e1b4b)`, whereas Stitch HTML/YAML defined `primary = #070235`, `primary-container = #1e1b4b`, and `secondary = #006a61`.
3. **Neutrals & Muted Text:** `DESIGN_SYSTEM.md` defined `text-muted: #94a3b8` (`2.56:1` on white — severe fail) and Slate neutrals (`#f8fafc`, `#f1f5f9`), whereas Stitch HTML used lavender-tinted Warm Tech Harmony surfaces (`#faf8ff`, `#f2f3ff`, `#eaedff`, `#e2e7ff`, `#dae2fd`) with `#131b2e` (`on-surface`) and `#47464f` (`on-surface-variant`).
4. **Warning / Danger / Info tokens:** `warning` (`#d97706` on `#fffbeb` = `3.07:1`), `info` (`#0284c7` on `#f0f9ff` = `3.84:1`), and `danger` (`#dc2626` on `#fef2f2` = `4.41:1`) failed strict `4.5:1` AA normal-text thresholds on light alert banners, whereas darkened shades + Stitch `error` / `tertiary-fixed` pairs pass.

---

## 2. Decision

Adopt a single platform-agnostic canonical token specification stored in `packages/design-tokens/` (implemented identically via Tailwind CSS variables for `apps/web` and a typed React Native theme for `apps/android`) that preserves the Stitch Warm Tech Harmony visual identity while enforcing **WCAG 2.1 AA (`>= 4.5:1` normal text, `>= 3.0:1` large text & UI boundaries)** on every text/background pairing.

### 2.1 Canonical Surface & Neutral Scale (Warm Tech Harmony)

| Semantic Token | Hex Value | Source Basis | Usage Rule |
|---|---|---|---|
| `surface.canvas` | `#faf8ff` | Both specs (`surface` / `canvas`) | App canvas / page background |
| `surface.card` | `#ffffff` | Both specs (`surface-container-lowest`) | Elevated cards, modals, inputs |
| `surface.low` | `#f2f3ff` | Stitch HTML (`surface-container-low`) | Subtle inset strips, secondary containers |
| `surface.base` | `#eaedff` | Stitch HTML (`surface-container`) | Tinted chips, grouped rows, hover states |
| `surface.high` | `#e2e7ff` | Stitch HTML (`surface-container-high`) | Selected secondary surface, nav pills |
| `surface.highest` | `#dae2fd` | Stitch HTML (`surface-container-highest`) | Track backgrounds, active subtle fills |
| `surface.dim` | `#d2d9f4` | Stitch HTML (`surface-dim`) | Recessed panels |
| `border.subtle` | `#e2e8f0` | `DESIGN_SYSTEM.md` | Crisp hairline borders on white cards |
| `border.variant` | `#c8c5d0` | Stitch HTML (`outline-variant`) | Standard Warm Tech dividers |
| `border.focus` | `#006a61` | Reconciled accessible teal | Active input/keyboard focus outline (`>= 3:1`) |
| `text.primary` | `#131b2e` | Stitch HTML (`on-surface`) | Default high-emphasis body/heading ink |
| `text.brand` | `#1e1b4b` | Both (`primary-container` / `text-primary`) | Primary midnight-indigo headers, nav pills |
| `text.secondary` | `#47464f` | Stitch HTML (`on-surface-variant`) | Secondary labels, metadata, descriptions |
| `text.muted` | `#5c5b66` | Adjusted neutral *(replaces `#94a3b8` & `#787680` for small copy)* | Placeholder/caption text passing `>= 4.5:1` across canvas & low surfaces |
| `outline.icon` | `#787680` | Stitch HTML (`outline`) | Decorative icons, disabled borders, large `>= 18px` labels **only** |

### 2.2 Canonical Brand & Semantic Action Colors

| Semantic Token | Hex Value | Light Surface Fill | Text on Fill / Fill with White | WCAG AA Status | Usage Rule |
|---|---|---|---|---|---|
| `brand.navy` | `#1e1b4b` | `#e3dfff` (`primary-fixed`) | `#ffffff` (`15.99:1`) / `#181445` on fixed (`13.28:1`) | **AA (AAA)** | Primary institutional headers, active nav pills, structural buttons |
| `brand.navyDeep` | `#070235` | — | `#ffffff` (`19.64:1`) | **AA (AAA)** | High-contrast dark emphasis & avatars |
| `action.teal` | **`#006a61`** | `#ecfdf5` or `#86f2e4` (`secondary-container`) | `#ffffff` (`6.49:1`) / `#006a61` on `#faf8ff` (`6.16:1`) / `#006a61` on `#f2f3ff` (`5.89:1`) | **AA Everywhere** | **Canonical interactive emerald-teal** for CTA buttons (`Connect`, `Submit`), active toggles, normal-size teal links & badges |
| `action.tealHover` | `#005049` | `#89f5e7` (`secondary-fixed`) | `#ffffff` (`9.40:1`) / `#005049` on fixed (`7.26:1`) | **AA (AAA)** | Hover/pressed state & dark badge text on mint pills |
| `accent.emeraldDecorative` | `#059669` | — | `#ffffff` (`3.77:1` — AA Large only) | Large/Graphic Only | Reserved **only** for compatibility ring strokes, >= 24px icons, and progress fills — **never** normal text or white-label button fill |
| `accent.indigo` | `#4f46e5` | `#eef2ff` | `#ffffff` (`6.29:1`) / `#4f46e5` on tint (`5.62:1`) | **AA** | Secondary brand accent, links, active step accents |
| `status.warning` | **`#b45309`** *(replaces `#d97706` for text)* | `#fffbeb` | `#b45309` on `#fffbeb` (`4.84:1`) | **AA** | Warning/pending banners & text labels |
| `status.warningFixed` | `#653e00` | `#ffddb8` (`tertiary-fixed`) | `#653e00` on `#ffddb8` (`7.26:1`) | **AA (AAA)** | Stitch amber-gold verification/alert pill |
| `status.danger` | **`#ba1a1a`** | `#fef2f2` or `#ffdad6` | `#ffffff` on `#ba1a1a` (`6.46:1`) / `#93000a` on `#ffdad6` (`7.24:1`) | **AA** | Destructive buttons (`Block`, `Report`, `Delete`), field validation errors (`#ba1a1a` on `#faf8ff` = `6.13:1`) |
| `status.info` | **`#0369a1`** *(replaces `#0284c7` for text)* | `#f0f9ff` | `#0369a1` on `#f0f9ff` (`5.57:1`) | **AA** | Informational banners & help callouts (never name `"Telegram Blue"`) |

### 2.3 Verified WCAG 2.1 Contrast Audit Matrix

| Pair Evaluated | Contrast Ratio | WCAG 2.1 Level | Decision |
|---|---:|---|---|
| `#131b2e` (`on-surface`) on `#faf8ff` (`surface`) | `16.29:1` | AA / AAA | Retained |
| `#1e1b4b` (`primary-container`) on `#ffffff` | `15.99:1` | AA / AAA | Retained |
| `#47464f` (`on-surface-variant`) on `#faf8ff` / `#f2f3ff` / `#eaedff` | `8.83:1` / `8.44:1` / `8.00:1` | AA / AAA | Retained |
| `#006a61` (`action.teal`) on `#ffffff` / `#faf8ff` / `#f2f3ff` / `#eaedff` | `6.49:1` / `6.16:1` / `5.89:1` / `5.58:1` | AA | **Promoted to canonical teal** |
| `#006f66` on `#86f2e4` (`secondary-container`) | `4.57:1` | AA | Retained (borderline; keep `>= 600` weight or prefer `#005049`) |
| `#005049` on `#89f5e7` (`secondary-fixed`) | `7.26:1` | AA / AAA | Retained |
| `#5c5b66` on `#eaedff` / `#5c5b66` on `#faf8ff` (`#63616e` = `5.75:1`) | `5.74:1` | AA | **Replaces `#94a3b8` (`2.56:1` FAIL)** |
| `#b45309` on `#fffbeb` (`warning`) | `4.84:1` | AA | **Replaces `#d97706` (`3.07:1` AA-Large)** |
| `#0369a1` on `#f0f9ff` (`info`) | `5.57:1` | AA | **Replaces `#0284c7` (`3.84:1` AA-Large)** |
| `#93000a` on `#ffdad6` / `#ffffff` on `#ba1a1a` (`danger`) | `7.24:1` / `6.46:1` | AA | **Replaces `#dc2626` on `#fef2f2` (`4.41:1` FAIL for normal text)** |
| `#059669` (`3.77:1`) & `#0d9488` (`3.74:1`) with white | `< 4.5:1` | AA-Large Only | **Prohibited for normal text or white-label CTA fills** |
| `#94a3b8` on `#ffffff` | `2.56:1` | **FAIL** | **Removed for all text roles** |

### 2.4 Typography, Radii & Spacing Reconciliation
- **Font Family:** `Plus Jakarta Sans` across Web (`Google Fonts` / self-hosted) and Android (`@expo-google-fonts/plus-jakarta-sans`). Compatibility scores and budgets always enable tabular lining figures (`tabular-nums`).
- **Typography Scale:** Standardize semantic token names mapping `DESIGN_SYSTEM.md` and `warm_tech_harmony/DESIGN.md` cleanly (`display-lg` 36/44, `display-xl` 48/56 optional hero, `headline-lg` 28/36 desktop / 24/32 mobile, `headline-md` 22/30, `headline-sm` 18/26, `title-md` 16/24, `title-sm` 14/20, `body-lg` 16/26, `body-md` 14/22, `body-sm` 12/18, `label-lg` 14/20, `label-md` 12/16, `label-sm` 11/14 uppercase/tracking `+0.03em` *(raised from Stitch's tiny `10px` to `11px` minimum for legibility)*, `metric-display` 32/36 `800`).
- **Spacing & Radii (`4px` / `8px` grid):** Buttons & inputs = `12px` (`radius.md`), Cards = `16px` (`radius.lg`), Modals & drawers = `24px` (`radius.xl`), Pills/Chips/Avatars = `9999px` (`radius.full`). Minimum interactive touch target on Android & mobile web = `44x44px`.

---

## 3. Consequences

- **Positive:** Preserves 100% of the visual craft from the 85 Stitch HTML/CSS screens while eliminating every contrast defect before any component is built.
- **Guardrail:** All Stitch copy artifacts (`Bengaluru` hardcoding, fake `DigiLocker`/`UIDAI`/`SSO`/`Kaveri` badges, post-MVP links) remain stripped when translating Stitch layouts into React / React Native components (`DESIGN_SYSTEM.md` §8, `DESIGN_AUDIT.md` §4).


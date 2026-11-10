# RoomSync Design System
**Version:** 1.0 — Historical baseline (superseded for exact token values & contrast pairs by [`ADR-003`](./ADR/ADR-003-design-system-token-reconciliation.md))  
**Source:** User-provided Google Stitch “Warm Tech Harmony” specification.  
**Status:** Reconciled; **[`Docs/ADR/ADR-003-design-system-token-reconciliation.md`](./ADR/ADR-003-design-system-token-reconciliation.md) is the canonical approved token specification** governing `packages/design-tokens/`. Where historical values below fail WCAG 2.1 AA (`#059669`, `#94a3b8`, `#d97706`, `#dc2626`, `#0284c7`), implementers must use the `ADR-003` tokens (`#006a61`, `#5c5b66`, `#b45309`, `#ba1a1a`, `#0369a1`, and Stitch surface ramp `#faf8ff`/`#f2f3ff`/`#eaedff`/`#e2e7ff`).

> [!IMPORTANT]
> Do not implement `#059669` or `#0d9488` for normal-size text or button fills, and never use `#94a3b8` for text. Follow [`ADR-003`](./ADR/ADR-003-design-system-token-reconciliation.md) for all colors implemented in `packages/design-tokens/`.

## 1. Design direction
Warm Tech Harmony: approachable, trustworthy, calm, modern. The same visual language should be maintained across responsive web and Android, while using platform-appropriate components.

## 2. Historical baseline color tokens *(See ADR-003 for canonical WCAG AA values)*

| Token | Historical Value | Canonical `ADR-003` Value / Rule |
|---|---|---|
| `canvas` (`surface.canvas`) | `#faf8ff` | `#faf8ff` (Retained) |
| `surface` (`surface.card`) | `#ffffff` | `#ffffff` (Retained) |
| `surface-low` | `#f8fafc` | `#f2f3ff` (`surface.low` Stitch ramp) |
| `surface-high` | `#f1f5f9` | `#eaedff` / `#e2e7ff` (`surface.base` / `surface.high`) |
| `surface-indigo` | `#e0e7ff` | `#e3dfff` / `#e2e7ff` |
| `border` | `#e2e8f0` | `#e2e8f0` (`border.subtle`) / `#c8c5d0` (`border.variant`) |
| `border-soft` | `#ede9fe` | `#ede9fe` / `#c8c5d0` |
| `text-primary` | `#1e1b4b` | `#131b2e` (`text.primary`) & `#1e1b4b` (`text.brand`) |
| `text-secondary` | `#475569` | `#47464f` (`text.secondary`, 8.83:1 on canvas) |
| `text-muted` | `#94a3b8` *(FAIL 2.56:1)* | **`#5c5b66`** (`text.muted`, passes AA `>= 4.5:1`) |
| `primary` (interactive teal) | `#059669` *(3.77:1 AA-Large only)* | **`#006a61`** (`action.teal`, 6.49:1 on white); `#059669` decorative/ring strokes only |
| `primary-hover` | `#047857` | **`#005049`** (`action.tealHover`, 9.40:1 on white) |
| `primary-tint` | `#ecfdf5` | `#ecfdf5` / `#86f2e4` (`secondary-container`) |
| `accent` | `#4f46e5` | `#4f46e5` (`accent.indigo`) |
| `accent-hover` | `#4338ca` | `#4338ca` |
| `accent-tint` | `#eef2ff` | `#eef2ff` |
| `warning` | `#d97706` *(3.07:1 fail on `#fffbeb`)* | **`#b45309`** (`status.warning`, 4.84:1 on `#fffbeb`) / `#653e00` on `#ffddb8` |
| `warning-bg` | `#fffbeb` | `#fffbeb` / `#ffddb8` |
| `danger` | `#dc2626` *(4.41:1 fail on `#fef2f2`)* | **`#ba1a1a`** (`status.danger`, 6.46:1 white text) / `#93000a` on `#ffdad6` |
| `danger-bg` | `#fef2f2` | `#fef2f2` / `#ffdad6` |
| `danger-border` | `#fecaca` | `#fecaca` |
| `info` | `#0284c7` *(3.84:1 fail on `#f0f9ff`)* | **`#0369a1`** (`status.info`, 5.57:1 on `#f0f9ff`) |
| `info-bg` | `#f0f9ff` | `#f0f9ff` |

## 3. Typography
Typeface: **Plus Jakarta Sans**.

| Style | Size / line height | Weight | Tracking |
|---|---:|---:|---:|
| Display XL | 36 / 44 px | 800 | -0.025em |
| Display LG | 30 / 38 px | 700 | -0.02em |
| Heading LG | 24 / 32 px | 700 | -0.015em |
| Heading MD | 20 / 28 px | 600 | -0.01em |
| Heading SM | 18 / 26 px | 600 | — |
| Body LG | 16 / 24 px | 500 | — |
| Body MD | 14 / 20 px | 400 or 500 | — |
| Body SM | 12 / 18 px | 500 or 600 | — |
| Badge caption | 11 / 14 px | 700 | +0.03em |

## 4. Spacing, shape and elevation
- Use a 4px base / 8px rhythm.
- Compact card padding: 16px.
- Standard section padding: 24px.
- Hero padding: 32px.
- Button/input radius: 12px.
- Card radius: 16px.
- Modal/drawer radius: 24px.
- Pill controls: fully rounded.
- Small shadow: `0 1px 2px 0 rgb(0 0 0 / 0.05)`.
- Card shadow: `0 4px 14px 0 rgba(30,27,75,0.06)`.
- Modal shadow: `0 20px 40px -15px rgba(30,27,75,0.16)`.

## 5. Component semantics
- Primary action: emerald; use accessible contrast and clear focus/pressed/disabled states.
- Brand/accent action: indigo, used selectively.
- Secondary action: white surface with slate border.
- Destructive action: red, only for destructive operations.
- Disabled controls: visibly disabled; the original spec suggests 0.5 opacity, but verify text contrast and state clarity.
- Inputs: white surface, slate border, visible focus ring, clear validation error.
- Badges must reflect actual system state. Do not show UIDAI, DigiLocker, corporate SSO or other provider verification badges unless the corresponding integration is implemented and authorized.
- Use semantic names such as `info` or `info-blue`, not arbitrary names such as “Telegram Blue”.

## 6. Responsive behaviour
- Mobile breakpoint: below 640px; design reference width 390px.
- Tablet: 640–1024px; dual-column layouts where appropriate and collapsible navigation.
- Desktop: 1024px and above; reference width 1280px.
- Mobile: single-column content, consistent bottom navigation, minimum 44px touch targets, horizontal property carousel only where useful.
- Desktop location selector must be dynamic; do not hardcode Bangalore.
- Respect Android safe areas, keyboard insets and system navigation.
- Sticky bottom actions must include safe-area padding and must not obscure scrollable content.

## 7. Platform implementation
Maintain platform-neutral token names and map them separately:
- Web: CSS variables / Tailwind theme.
- Android: React Native theme object and native components.
Tailwind classes do not apply directly to React Native. Share tokens, types and validation where practical; do not force web-only UI primitives into native screens.

## 8. Design governance
- Stitch exports are the visual reference; PRD defines product behaviour and TDD defines architecture.
- A design screen does not automatically mean its feature is in MVP scope.
- Do not invent property availability, ratings, verification, integrations or user data.
- Keep unanswered questionnaire responses distinct from incompatibility.
- Show pending, submitted and approved states accurately.
- Update this file when the approved Stitch design changes.

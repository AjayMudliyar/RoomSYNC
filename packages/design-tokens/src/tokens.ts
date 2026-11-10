/**
 * Canonical Warm Tech Harmony Design Tokens — WCAG 2.1 AA Reconciled.
 * Authoritative reference: Docs/ADR/ADR-003-design-system-token-reconciliation.md
 */

export const colors = {
  surface: {
    canvas: "#faf8ff",
    card: "#ffffff",
    low: "#f2f3ff",
    base: "#eaedff",
    high: "#e2e7ff",
    highest: "#dae2fd",
    dim: "#d2d9f4",
  },
  border: {
    subtle: "#e2e8f0",
    variant: "#c8c5d0",
    focus: "#006a61",
  },
  text: {
    primary: "#131b2e",
    brand: "#1e1b4b",
    secondary: "#47464f",
    muted: "#5c5b66",
    onDark: "#ffffff",
  },
  outline: {
    icon: "#787680",
  },
  brand: {
    navy: "#1e1b4b",
    navyDeep: "#070235",
    primaryFixed: "#e3dfff",
    onPrimaryFixed: "#181445",
  },
  action: {
    teal: "#006a61",
    tealHover: "#005049",
    tealContainer: "#86f2e4",
    tealFixed: "#89f5e7",
    tealTint: "#ecfdf5",
  },
  accent: {
    /** Reserved ONLY for large graphics / progress ring strokes (>= 24px), never normal text or button fills */
    emeraldDecorative: "#059669",
    indigo: "#4f46e5",
    indigoHover: "#4338ca",
    indigoTint: "#eef2ff",
  },
  status: {
    warning: "#b45309",
    warningBg: "#fffbeb",
    warningFixed: "#653e00",
    warningFixedBg: "#ffddb8",
    danger: "#ba1a1a",
    dangerBg: "#fef2f2",
    dangerFixed: "#93000a",
    dangerFixedBg: "#ffdad6",
    dangerBorder: "#fecaca",
    info: "#0369a1",
    infoBg: "#f0f9ff",
  },
} as const;

export const typography = {
  fontFamily: {
    webSans:
      "'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    nativeRegular: "PlusJakartaSans_400Regular",
    nativeMedium: "PlusJakartaSans_500Medium",
    nativeSemiBold: "PlusJakartaSans_600SemiBold",
    nativeBold: "PlusJakartaSans_700Bold",
    nativeExtraBold: "PlusJakartaSans_800ExtraBold",
  },
  scale: {
    displayXl: { fontSize: 48, lineHeight: 56, fontWeight: "800", letterSpacing: -0.025 },
    displayLg: { fontSize: 36, lineHeight: 44, fontWeight: "800", letterSpacing: -0.025 },
    headlineLg: { fontSize: 28, lineHeight: 36, fontWeight: "700", letterSpacing: -0.015 },
    headlineMd: { fontSize: 22, lineHeight: 30, fontWeight: "700", letterSpacing: -0.01 },
    headlineSm: { fontSize: 18, lineHeight: 26, fontWeight: "600", letterSpacing: 0 },
    titleMd: { fontSize: 16, lineHeight: 24, fontWeight: "600", letterSpacing: 0 },
    titleSm: { fontSize: 14, lineHeight: 20, fontWeight: "600", letterSpacing: 0 },
    bodyLg: { fontSize: 16, lineHeight: 26, fontWeight: "400", letterSpacing: 0 },
    bodyMd: { fontSize: 14, lineHeight: 22, fontWeight: "400", letterSpacing: 0 },
    bodySm: { fontSize: 12, lineHeight: 18, fontWeight: "500", letterSpacing: 0 },
    labelLg: { fontSize: 14, lineHeight: 20, fontWeight: "600", letterSpacing: 0 },
    labelMd: { fontSize: 12, lineHeight: 16, fontWeight: "600", letterSpacing: 0.01 },
    labelSm: { fontSize: 11, lineHeight: 14, fontWeight: "700", letterSpacing: 0.03 },
    metricDisplay: { fontSize: 32, lineHeight: 36, fontWeight: "800", letterSpacing: -0.02 },
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  cardCompact: 16,
  lg: 20,
  section: 24,
  hero: 32,
  xl: 40,
} as const;

export const radii = {
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
} as const;

export const shadows = {
  small: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
  card: "0 4px 14px 0 rgba(30, 27, 75, 0.06)",
  modal: "0 20px 40px -15px rgba(30, 27, 75, 0.16)",
} as const;

export const touchTarget = {
  minPx: 44,
} as const;

export const tokens = {
  colors,
  typography,
  spacing,
  radii,
  shadows,
  touchTarget,
} as const;

export type DesignTokens = typeof tokens;

import { colors, radii, spacing, touchTarget, typography } from "./tokens";

/**
 * Platform-specific React Native theme object mapped from canonical ADR-003 tokens.
 * Tailwind web classes are intentionally excluded from native styling.
 */
export const nativeTheme = {
  colors,
  spacing,
  radii,
  touchTarget,
  typography: {
    fonts: {
      regular: typography.fontFamily.nativeRegular,
      medium: typography.fontFamily.nativeMedium,
      semiBold: typography.fontFamily.nativeSemiBold,
      bold: typography.fontFamily.nativeBold,
      extraBold: typography.fontFamily.nativeExtraBold,
    },
    scale: typography.scale,
  },
  elevation: {
    small: {
      shadowColor: "#1e1b4b",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 1,
    },
    card: {
      shadowColor: "#1e1b4b",
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.06,
      shadowRadius: 14,
      elevation: 3,
    },
    modal: {
      shadowColor: "#1e1b4b",
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.16,
      shadowRadius: 24,
      elevation: 8,
    },
  },
} as const;

export type NativeTheme = typeof nativeTheme;
export { colors, radii, spacing, touchTarget, typography } from "./tokens";

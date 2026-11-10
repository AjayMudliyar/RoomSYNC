import { describe, expect, it } from "vitest";
import { colors, touchTarget, typography } from "../src/index";

function relativeLuminance(hex: string): number {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const toLinear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const bright = Math.max(l1, l2);
  const dark = Math.min(l1, l2);
  return (bright + 0.05) / (dark + 0.05);
}

describe("ADR-003 Warm Tech Harmony WCAG 2.1 AA tokens", () => {
  it("meets >= 4.5:1 AA contrast across all canonical text and action pairs", () => {
    expect(contrastRatio(colors.text.primary, colors.surface.canvas)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.brand, colors.surface.card)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.secondary, colors.surface.base)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.muted, colors.surface.canvas)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.muted, colors.surface.low)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.onDark, colors.action.teal)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.action.teal, colors.surface.canvas)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.action.tealHover, colors.action.tealFixed)).toBeGreaterThanOrEqual(
      4.5,
    );
    expect(contrastRatio(colors.text.onDark, colors.brand.navy)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.status.warning, colors.status.warningBg)).toBeGreaterThanOrEqual(
      4.5,
    );
    expect(
      contrastRatio(colors.status.warningFixed, colors.status.warningFixedBg),
    ).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.text.onDark, colors.status.danger)).toBeGreaterThanOrEqual(4.5);
    expect(
      contrastRatio(colors.status.dangerFixed, colors.status.dangerFixedBg),
    ).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(colors.status.info, colors.status.infoBg)).toBeGreaterThanOrEqual(4.5);
  });

  it("prohibits failed #94a3b8 muted text and enforces 11px min caption & 44px touch targets", () => {
    const serialized = JSON.stringify(colors).toLowerCase();
    expect(serialized).not.toContain("#94a3b8");
    expect(colors.action.teal).toBe("#006a61");
    expect(typography.scale.labelSm.fontSize).toBeGreaterThanOrEqual(11);
    expect(touchTarget.minPx).toBeGreaterThanOrEqual(44);
  });
});

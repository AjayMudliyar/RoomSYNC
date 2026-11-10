import { describe, expect, it } from "vitest";
import { nativeTheme } from "@roomsync/design-tokens/native";
import { MATCHING_BASELINE } from "@roomsync/contracts";

describe("Android M0 Foundation", () => {
  it("consumes canonical ADR-003 native theme and 44px touch target floor", () => {
    expect(nativeTheme.colors.surface.canvas).toBe("#faf8ff");
    expect(nativeTheme.colors.action.teal).toBe("#006a61");
    expect(nativeTheme.colors.brand.navy).toBe("#1e1b4b");
    expect(nativeTheme.touchTarget.minPx).toBeGreaterThanOrEqual(44);
    expect(Object.values(MATCHING_BASELINE.weights).reduce((a, b) => a + b, 0)).toBe(100);
  });
});

import { describe, expect, it } from "vitest";
import { MATCHING_BASELINE } from "../src/index";

describe("Matching baseline constants (TDD.md §9.1 & §9.6)", () => {
  it("uses grounded TDD matching identifiers and 8 categories totaling 100", () => {
    expect(MATCHING_BASELINE.algorithmVersion).toBe("roomsync-rule-v1");
    expect(MATCHING_BASELINE.weightsVersion).toBe("weights-2026-01");
    expect(MATCHING_BASELINE.questionSchemaVersion).toBe(1);

    const values = Object.values(MATCHING_BASELINE.weights);
    expect(values).toHaveLength(8);
    expect(values.reduce((acc, w) => acc + w, 0)).toBe(100);
  });
});

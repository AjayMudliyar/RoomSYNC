export type ClientPlatform = "web" | "android";

export type CompatibilityCategoryKey =
  | "daily_routine"
  | "cleanliness"
  | "financial_expectations"
  | "privacy_and_boundaries"
  | "social_lifestyle"
  | "food_preferences"
  | "guest_preferences"
  | "work_study_environment";

/** Grounded baseline compatibility constants from TDD.md §9.1 / §9.6 & ADR-002 */
export const MATCHING_BASELINE = {
  algorithmVersion: "roomsync-rule-v1",
  weightsVersion: "weights-2026-01",
  questionSchemaVersion: 1,
  weights: {
    daily_routine: 15,
    cleanliness: 15,
    financial_expectations: 15,
    privacy_and_boundaries: 15,
    social_lifestyle: 10,
    food_preferences: 10,
    guest_preferences: 10,
    work_study_environment: 10,
  },
} as const satisfies {
  algorithmVersion: string;
  weightsVersion: string;
  questionSchemaVersion: number;
  weights: Record<CompatibilityCategoryKey, number>;
};

export interface HealthResponse {
  status: "ok" | "unavailable";
}

export interface SystemStatusData {
  service: string;
  status: string;
  api_version: string;
}

export interface ApiSuccessEnvelope<T> {
  data: T;
  meta: {
    request_id: string;
  };
}

export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors: Record<string, string[]>;
  details: Record<string, unknown>;
  request_id: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorBody;
}

export type * from "./generated/openapi";

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
import type { components } from "./generated/openapi";

export type SchemaComponents = components["schemas"];
export type AuthUser = SchemaComponents["AuthUser"];
export type AuthTokens = SchemaComponents["AuthTokens"];
export type AuthSessionData = SchemaComponents["AuthSessionData"];
export type CsrfTokenData = SchemaComponents["CsrfTokenData"];
export type UserCapabilities = SchemaComponents["UserCapabilities"];
export type UserSessionItem = SchemaComponents["UserSessionItem"];
export type DataExportData = SchemaComponents["DataExportData"];
export type EmailVerifyResponseData = SchemaComponents["EmailVerifyResponseData"];
export type GenericAcceptedData = SchemaComponents["GenericAcceptedData"];
export type LogoutResponseData = SchemaComponents["LogoutResponseData"];
export type PasswordResetResponseData = SchemaComponents["PasswordResetResponseData"];
export type PasswordChangeResponseData = SchemaComponents["PasswordChangeResponseData"];
export type DeletionRequestResponseData = SchemaComponents["DeletionRequestResponseData"];

export type RegisterRequest = SchemaComponents["RegisterRequestRequest"];
export type LoginRequest = SchemaComponents["LoginRequestRequest"];
export type GoogleAuthRequest = SchemaComponents["GoogleAuthRequestRequest"];
export type GoogleLinkRequest = SchemaComponents["GoogleLinkRequestRequest"];
export type RefreshRequest = SchemaComponents["RefreshRequestRequest"];
export type LogoutRequest = SchemaComponents["LogoutRequestRequest"];
export type EmailVerifyRequest = SchemaComponents["EmailVerifyRequestRequest"];
export type EmailResendRequest = SchemaComponents["EmailResendRequestRequest"];
export type PasswordForgotRequest = SchemaComponents["PasswordForgotRequestRequest"];
export type PasswordResetRequest = SchemaComponents["PasswordResetRequestRequest"];
export type PasswordChangeRequest = SchemaComponents["PasswordChangeRequestRequest"];
export type MeUpdateRequest = SchemaComponents["PatchedMeUpdateRequestRequest"];
export type DeletionRequest = SchemaComponents["DeletionRequestRequest"];

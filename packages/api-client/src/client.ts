import type {
  ApiErrorBody,
  ApiErrorEnvelope,
  ApiSuccessEnvelope,
  ClientPlatform,
  HealthResponse,
  SystemStatusData,
} from "@roomsync/contracts";

export class RoomSyncApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: Record<string, string[]>;
  readonly details: Record<string, unknown>;
  readonly requestId: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "RoomSyncApiError";
    this.status = status;
    this.code = body.code;
    this.fieldErrors = body.field_errors;
    this.details = body.details;
    this.requestId = body.request_id;
  }
}

export interface ApiClientConfig {
  /** Base origin (e.g. "http://localhost:8000"), without trailing slash. */
  baseOrigin: string;
  platform: ClientPlatform;
  fetchImpl?: typeof fetch;
  /** Optional CSRF token provider for Web unsafe methods. */
  getCsrfToken?: () => string | null | undefined;
  /** Optional Bearer token provider for Android mobile sessions. */
  getAccessToken?: () => Promise<string | null> | string | null;
  /** Single-flight token refresh callback for Android Bearer 401 handling. */
  refreshAccessToken?: () => Promise<string | null>;
}

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function createRequestId(): string {
  if (
    typeof globalThis.crypto !== "undefined" &&
    typeof globalThis.crypto.randomUUID === "function"
  ) {
    return globalThis.crypto.randomUUID();
  }
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

function isErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof (payload as ApiErrorEnvelope).error === "object" &&
    (payload as ApiErrorEnvelope).error !== null
  );
}

export class RoomSyncApiClient {
  private readonly baseOrigin: string;
  private readonly platform: ClientPlatform;
  private readonly fetchImpl: typeof fetch;
  private readonly getCsrfToken?: () => string | null | undefined;
  private readonly getAccessToken?: () => Promise<string | null> | string | null;
  private readonly refreshAccessToken?: () => Promise<string | null>;
  private inflightRefresh: Promise<string | null> | null = null;

  constructor(config: ApiClientConfig) {
    this.baseOrigin = config.baseOrigin.replace(/\/+$/, "");
    this.platform = config.platform;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.getCsrfToken = config.getCsrfToken;
    this.getAccessToken = config.getAccessToken;
    this.refreshAccessToken = config.refreshAccessToken;
  }

  private async runSingleFlightRefresh(): Promise<string | null> {
    if (!this.refreshAccessToken) {
      return null;
    }
    if (!this.inflightRefresh) {
      this.inflightRefresh = this.refreshAccessToken().finally(() => {
        this.inflightRefresh = null;
      });
    }
    return this.inflightRefresh;
  }

  async request<T>(
    path: string,
    init: RequestInit = {},
    allowRetryAfterRefresh = true,
  ): Promise<T> {
    const method = (init.method ?? "GET").toUpperCase();
    const requestId = createRequestId();
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    headers.set("X-Client-Platform", this.platform);
    headers.set("X-Request-ID", requestId);

    if (init.body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (this.platform === "web" && UNSAFE_METHODS.has(method)) {
      const csrfToken = this.getCsrfToken?.();
      if (csrfToken) {
        headers.set("X-CSRFToken", csrfToken);
      }
    }

    if (this.platform === "android" && this.getAccessToken) {
      const token = await this.getAccessToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    const response = await this.fetchImpl(`${this.baseOrigin}${path}`, {
      ...init,
      method,
      headers,
      credentials: this.platform === "web" ? "include" : "omit",
    });

    if (
      response.status === 401 &&
      this.platform === "android" &&
      this.refreshAccessToken &&
      allowRetryAfterRefresh
    ) {
      const refreshedToken = await this.runSingleFlightRefresh();
      if (refreshedToken) {
        const retryHeaders = new Headers(init.headers);
        retryHeaders.set("Authorization", `Bearer ${refreshedToken}`);
        return this.request<T>(path, { ...init, headers: retryHeaders }, false);
      }
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const responseRequestId = response.headers.get("X-Request-ID") ?? requestId;
    const rawText = await response.text();
    let parsed: unknown = null;
    if (rawText) {
      try {
        parsed = JSON.parse(rawText) as unknown;
      } catch {
        parsed = null;
      }
    }

    if (!response.ok) {
      if (isErrorEnvelope(parsed)) {
        throw new RoomSyncApiError(response.status, {
          ...parsed.error,
          request_id: parsed.error.request_id || responseRequestId,
        });
      }
      throw new RoomSyncApiError(response.status, {
        code: response.status >= 500 ? "INTERNAL_ERROR" : "HTTP_ERROR",
        message: response.statusText || "Request failed.",
        field_errors: {},
        details: {},
        request_id: responseRequestId,
      });
    }

    return parsed as T;
  }

  getHealthLive(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health/live");
  }

  getHealthReady(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health/ready");
  }

  getSystemStatus(): Promise<ApiSuccessEnvelope<SystemStatusData>> {
    return this.request<ApiSuccessEnvelope<SystemStatusData>>("/api/v1/system/status/");
  }
}

import type {
  ApiErrorBody,
  ApiErrorEnvelope,
  ApiSuccessEnvelope,
  AuthSessionData,
  AuthUser,
  ClientPlatform,
  CsrfTokenData,
  DataExportData,
  DeletionRequest,
  DeletionRequestResponseData,
  EmailResendRequest,
  EmailVerifyRequest,
  EmailVerifyResponseData,
  GenericAcceptedData,
  GoogleAuthRequest,
  GoogleLinkRequest,
  HealthResponse,
  LoginRequest,
  LogoutRequest,
  LogoutResponseData,
  MeUpdateRequest,
  PasswordChangeRequest,
  PasswordChangeResponseData,
  PasswordForgotRequest,
  PasswordResetRequest,
  PasswordResetResponseData,
  RefreshRequest,
  RegisterRequest,
  SystemStatusData,
  UserSessionItem,
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

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface RefreshAccessTokenContext {
  generation: number;
}

export interface SessionInvalidationContext {
  generation: number;
  guardContext?: unknown;
}

export interface ApiClientConfig {
  /** Base origin (e.g. "http://localhost:8000"), without trailing slash. */
  baseOrigin: string;
  platform: ClientPlatform;
  fetchImpl?: FetchLike;
  /** Optional CSRF token provider for Web unsafe methods. */
  getCsrfToken?: () => string | null | undefined;
  /** Optional Bearer token provider for Android mobile sessions. */
  getAccessToken?: () => Promise<string | null> | string | null;
  /** Single-flight token refresh callback for Android Bearer 401 handling. */
  refreshAccessToken?: (context: RefreshAccessTokenContext) => Promise<string | null>;
  /** Called when an authenticated session cannot be refreshed or reuse is detected. */
  onSessionInvalidated?: (
    error: RoomSyncApiError,
    context: SessionInvalidationContext,
  ) => Promise<void> | void;
  /** Optional synchronous snapshot hook captured at cycle/refresh entry for conditional storage checks. */
  captureSessionGuard?: () => unknown;
}

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const AUTH_NON_REFRESHABLE_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/refresh",
  "/api/v1/auth/google",
  "/api/v1/auth/google/link",
  "/api/v1/auth/email/verify",
  "/api/v1/auth/email/resend",
  "/api/v1/auth/password/forgot",
  "/api/v1/auth/password/reset",
]);

interface RefreshCycle {
  generation: number;
  promise: Promise<string | null>;
  invalidatedLatched: boolean;
  invalidatedNotified: boolean;
  invalidationPromise: Promise<void> | null;
  guardContext?: unknown;
}

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

function stripQuery(path: string): string {
  const idx = path.indexOf("?");
  return idx === -1 ? path : path.slice(0, idx);
}

export class RoomSyncApiClient {
  private readonly baseOrigin: string;
  private readonly platform: ClientPlatform;
  private readonly fetchImpl: FetchLike;
  private readonly csrfTokenProvider?: () => string | null | undefined;
  private readonly accessTokenProvider?: () => Promise<string | null> | string | null;
  private readonly refreshTokenHandler?: (
    context: RefreshAccessTokenContext,
  ) => Promise<string | null>;
  private readonly sessionInvalidatedHandler?: (
    error: RoomSyncApiError,
    context: SessionInvalidationContext,
  ) => Promise<void> | void;
  private readonly sessionGuardFactory?: () => unknown;
  private inflightRefreshCycle: RefreshCycle | null = null;
  private invalidationSeq = 0;
  private sessionGeneration = 0;

  constructor(config: ApiClientConfig) {
    this.baseOrigin = config.baseOrigin.replace(/\/+$/, "");
    this.platform = config.platform;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.csrfTokenProvider = config.getCsrfToken;
    this.accessTokenProvider = config.getAccessToken;
    this.refreshTokenHandler = config.refreshAccessToken;
    this.sessionInvalidatedHandler = config.onSessionInvalidated;
    this.sessionGuardFactory = config.captureSessionGuard;
  }

  getSessionGeneration(): number {
    return this.sessionGeneration;
  }

  /**
   * Advance the active session generation and detach any in-flight refresh cycle so
   * obsolete requests or async finally blocks cannot overwrite or clear newer sessions.
   */
  resetSessionCycle(): number {
    this.sessionGeneration += 1;
    this.invalidationSeq += 1;
    this.inflightRefreshCycle = null;
    return this.sessionGeneration;
  }

  private latchCycleInvalidation(cycle: RefreshCycle | null, expectedGeneration?: number): void {
    const targetGeneration = expectedGeneration ?? cycle?.generation;
    if (targetGeneration !== undefined && this.sessionGeneration !== targetGeneration) {
      return;
    }
    if (cycle) {
      if (!cycle.invalidatedLatched) {
        cycle.invalidatedLatched = true;
        this.invalidationSeq += 1;
      }
      return;
    }
    this.invalidationSeq += 1;
  }

  private releaseRefreshCycle(cycle: RefreshCycle | null): void {
    if (cycle && this.inflightRefreshCycle === cycle) {
      this.inflightRefreshCycle = null;
    }
  }

  private async notifySessionInvalidatedOnce(
    error: RoomSyncApiError,
    cycle: RefreshCycle | null,
    expectedGeneration: number,
    fallbackGuardContext?: unknown,
  ): Promise<void> {
    if (this.sessionGeneration !== expectedGeneration) {
      return;
    }
    const guardContext = cycle ? cycle.guardContext : fallbackGuardContext;
    if (cycle) {
      if (cycle.invalidatedNotified) {
        if (cycle.invalidationPromise) {
          await cycle.invalidationPromise;
        }
        return;
      }
      cycle.invalidatedNotified = true;
      this.latchCycleInvalidation(cycle, expectedGeneration);
      const pending = Promise.resolve().then(() => {
        if (this.sessionGeneration !== expectedGeneration) {
          return undefined;
        }
        return this.sessionInvalidatedHandler?.(error, {
          generation: expectedGeneration,
          guardContext,
        });
      });
      cycle.invalidationPromise = pending;
      try {
        await pending;
      } finally {
        this.releaseRefreshCycle(cycle);
      }
      return;
    }
    this.latchCycleInvalidation(null, expectedGeneration);
    if (this.sessionGeneration !== expectedGeneration) {
      return;
    }
    await this.sessionInvalidatedHandler?.(error, {
      generation: expectedGeneration,
      guardContext,
    });
  }

  private runSingleFlightRefresh(expectedGeneration: number): {
    cycle: RefreshCycle | null;
    promise: Promise<string | null>;
  } {
    const refreshHandler = this.refreshTokenHandler;
    if (!refreshHandler || this.sessionGeneration !== expectedGeneration) {
      return { cycle: null, promise: Promise.resolve(null) };
    }
    if (!this.inflightRefreshCycle || this.inflightRefreshCycle.generation !== expectedGeneration) {
      const cycle: RefreshCycle = {
        generation: expectedGeneration,
        promise: Promise.resolve(null),
        invalidatedLatched: false,
        invalidatedNotified: false,
        invalidationPromise: null,
        guardContext: this.sessionGuardFactory?.(),
      };
      let rawRefreshPromise: Promise<string | null>;
      try {
        rawRefreshPromise = Promise.resolve(refreshHandler({ generation: expectedGeneration }));
      } catch (refreshError: unknown) {
        rawRefreshPromise = Promise.reject(refreshError);
      }
      cycle.promise = rawRefreshPromise.then(
        (token) => {
          if (this.sessionGeneration !== cycle.generation) {
            this.releaseRefreshCycle(cycle);
            return null;
          }
          if (token) {
            this.releaseRefreshCycle(cycle);
            return token;
          }
          // Latch invalidation before releasing the cycle; the active caller keeps
          // `inflightRefreshCycle` pinned across async error-body parsing and
          // invalidation cleanup until `notifySessionInvalidatedOnce` settles.
          this.latchCycleInvalidation(cycle, cycle.generation);
          return null;
        },
        (refreshError: unknown) => {
          if (this.sessionGeneration !== cycle.generation) {
            this.releaseRefreshCycle(cycle);
            throw refreshError;
          }
          if (refreshError instanceof RoomSyncApiError && refreshError.status === 401) {
            this.latchCycleInvalidation(cycle, cycle.generation);
          } else {
            this.releaseRefreshCycle(cycle);
          }
          throw refreshError;
        },
      );
      this.inflightRefreshCycle = cycle;
    }
    return {
      cycle: this.inflightRefreshCycle,
      promise: this.inflightRefreshCycle.promise,
    };
  }

  private async parseErrorFromResponse(
    response: Response,
    fallbackRequestId: string,
  ): Promise<RoomSyncApiError> {
    const responseRequestId = response.headers.get("X-Request-ID") ?? fallbackRequestId;
    const rawText = await response.text();
    let parsed: unknown = null;
    if (rawText) {
      try {
        parsed = JSON.parse(rawText) as unknown;
      } catch {
        parsed = null;
      }
    }
    if (isErrorEnvelope(parsed)) {
      return new RoomSyncApiError(response.status, {
        ...parsed.error,
        request_id: parsed.error.request_id || responseRequestId,
      });
    }
    return new RoomSyncApiError(response.status, {
      code: response.status >= 500 ? "INTERNAL_ERROR" : "HTTP_ERROR",
      message: response.statusText || "Request failed.",
      field_errors: {},
      details: {},
      request_id: responseRequestId,
    });
  }

  async request<T>(
    path: string,
    init: RequestInit = {},
    allowRetryAfterRefresh = true,
  ): Promise<T> {
    const method = (init.method ?? "GET").toUpperCase();
    const requestId = createRequestId();
    const startGeneration = this.sessionGeneration;
    const startInvalidationSeq = this.invalidationSeq;
    const startGuardContext =
      stripQuery(path) === "/api/v1/auth/refresh" ? this.sessionGuardFactory?.() : undefined;
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    headers.set("X-Client-Platform", this.platform);
    headers.set("X-Request-ID", requestId);

    if (init.body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (this.platform === "web" && UNSAFE_METHODS.has(method)) {
      const csrfToken = this.csrfTokenProvider?.();
      if (csrfToken) {
        headers.set("X-CSRFToken", csrfToken);
      }
    }

    // Never clobber an explicit Authorization header (e.g. from a 401 refresh retry)
    // with a potentially stale token from getAccessToken().
    if (
      this.platform === "android" &&
      allowRetryAfterRefresh &&
      !headers.has("Authorization") &&
      this.accessTokenProvider
    ) {
      const token = await this.accessTokenProvider();
      if (token && this.sessionGeneration === startGeneration) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    const response = await this.fetchImpl(`${this.baseOrigin}${path}`, {
      ...init,
      method,
      headers,
      credentials: this.platform === "web" ? "include" : "omit",
    });

    const cleanPath = stripQuery(path);
    if (
      response.status === 401 &&
      this.platform === "android" &&
      this.refreshTokenHandler &&
      allowRetryAfterRefresh &&
      !AUTH_NON_REFRESHABLE_PATHS.has(cleanPath)
    ) {
      // A concurrent session transition or invalidation cycle already superseded this request.
      if (
        this.sessionGeneration !== startGeneration ||
        this.invalidationSeq !== startInvalidationSeq
      ) {
        throw await this.parseErrorFromResponse(response, requestId);
      }

      const { cycle, promise } = this.runSingleFlightRefresh(startGeneration);
      let refreshedToken: string | null = null;
      try {
        refreshedToken = await promise;
      } catch (refreshError) {
        if (this.sessionGeneration !== startGeneration) {
          this.releaseRefreshCycle(cycle);
          throw await this.parseErrorFromResponse(response, requestId);
        }
        try {
          if (refreshError instanceof RoomSyncApiError && refreshError.status === 401) {
            await this.notifySessionInvalidatedOnce(refreshError, cycle, startGeneration);
          }
        } finally {
          this.releaseRefreshCycle(cycle);
        }
        throw refreshError;
      }

      if (this.sessionGeneration !== startGeneration) {
        this.releaseRefreshCycle(cycle);
        throw await this.parseErrorFromResponse(response, requestId);
      }

      if (refreshedToken) {
        const retryHeaders = new Headers(init.headers);
        retryHeaders.set("Authorization", `Bearer ${refreshedToken}`);
        return this.request<T>(path, { ...init, headers: retryHeaders }, false);
      }

      try {
        const unauthError = await this.parseErrorFromResponse(response, requestId);
        await this.notifySessionInvalidatedOnce(unauthError, cycle, startGeneration);
        throw unauthError;
      } finally {
        this.releaseRefreshCycle(cycle);
      }
    }

    if (response.status === 204) {
      return undefined as T;
    }

    if (!response.ok) {
      const apiError = await this.parseErrorFromResponse(response, requestId);
      if (
        this.sessionGeneration === startGeneration &&
        response.status === 401 &&
        (apiError.code === "AUTH_REFRESH_REUSE_DETECTED" || cleanPath === "/api/v1/auth/refresh")
      ) {
        const activeCycle =
          this.inflightRefreshCycle && this.inflightRefreshCycle.generation === startGeneration
            ? this.inflightRefreshCycle
            : null;
        await this.notifySessionInvalidatedOnce(
          apiError,
          activeCycle,
          startGeneration,
          startGuardContext,
        );
      }
      throw apiError;
    }

    const rawText = await response.text();
    if (!rawText) {
      return undefined as T;
    }
    return JSON.parse(rawText) as T;
  }

  getHealthLive(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health/live");
  }

  getHealthReady(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health/ready");
  }

  getSystemStatus(): Promise<ApiSuccessEnvelope<SystemStatusData>> {
    return this.request<ApiSuccessEnvelope<SystemStatusData>>("/api/v1/system/status");
  }

  getCsrfToken(): Promise<ApiSuccessEnvelope<CsrfTokenData>> {
    return this.request<ApiSuccessEnvelope<CsrfTokenData>>("/api/v1/auth/csrf");
  }

  register(payload: RegisterRequest): Promise<ApiSuccessEnvelope<AuthSessionData>> {
    this.resetSessionCycle();
    return this.request<ApiSuccessEnvelope<AuthSessionData>>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  login(payload: LoginRequest): Promise<ApiSuccessEnvelope<AuthSessionData>> {
    this.resetSessionCycle();
    return this.request<ApiSuccessEnvelope<AuthSessionData>>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  loginWithGoogle(payload: GoogleAuthRequest): Promise<ApiSuccessEnvelope<AuthSessionData>> {
    this.resetSessionCycle();
    return this.request<ApiSuccessEnvelope<AuthSessionData>>("/api/v1/auth/google", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  linkGoogleAccount(payload: GoogleLinkRequest): Promise<ApiSuccessEnvelope<AuthSessionData>> {
    this.resetSessionCycle();
    return this.request<ApiSuccessEnvelope<AuthSessionData>>("/api/v1/auth/google/link", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  refreshSession(payload: RefreshRequest = {}): Promise<ApiSuccessEnvelope<AuthSessionData>> {
    return this.request<ApiSuccessEnvelope<AuthSessionData>>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async logout(payload: LogoutRequest = {}): Promise<ApiSuccessEnvelope<LogoutResponseData>> {
    const logoutGeneration = this.resetSessionCycle();
    try {
      return await this.request<ApiSuccessEnvelope<LogoutResponseData>>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } finally {
      if (this.sessionGeneration === logoutGeneration) {
        this.resetSessionCycle();
      }
    }
  }

  verifyEmail(payload: EmailVerifyRequest): Promise<ApiSuccessEnvelope<EmailVerifyResponseData>> {
    return this.request<ApiSuccessEnvelope<EmailVerifyResponseData>>("/api/v1/auth/email/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  resendVerificationEmail(
    payload: EmailResendRequest = {},
  ): Promise<ApiSuccessEnvelope<GenericAcceptedData>> {
    return this.request<ApiSuccessEnvelope<GenericAcceptedData>>("/api/v1/auth/email/resend", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  forgotPassword(payload: PasswordForgotRequest): Promise<ApiSuccessEnvelope<GenericAcceptedData>> {
    return this.request<ApiSuccessEnvelope<GenericAcceptedData>>("/api/v1/auth/password/forgot", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  resetPassword(
    payload: PasswordResetRequest,
  ): Promise<ApiSuccessEnvelope<PasswordResetResponseData>> {
    return this.request<ApiSuccessEnvelope<PasswordResetResponseData>>(
      "/api/v1/auth/password/reset",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  changePassword(
    payload: PasswordChangeRequest,
  ): Promise<ApiSuccessEnvelope<PasswordChangeResponseData>> {
    return this.request<ApiSuccessEnvelope<PasswordChangeResponseData>>(
      "/api/v1/auth/password/change",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  getMe(): Promise<ApiSuccessEnvelope<AuthUser>> {
    return this.request<ApiSuccessEnvelope<AuthUser>>("/api/v1/me");
  }

  updateMe(payload: MeUpdateRequest): Promise<ApiSuccessEnvelope<AuthUser>> {
    return this.request<ApiSuccessEnvelope<AuthUser>>("/api/v1/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  getMySessions(): Promise<ApiSuccessEnvelope<UserSessionItem[]>> {
    return this.request<ApiSuccessEnvelope<UserSessionItem[]>>("/api/v1/me/sessions");
  }

  revokeMySession(sessionId: string): Promise<void> {
    return this.request<void>(`/api/v1/me/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
  }

  requestAccountDeletion(
    payload: DeletionRequest,
  ): Promise<ApiSuccessEnvelope<DeletionRequestResponseData>> {
    return this.request<ApiSuccessEnvelope<DeletionRequestResponseData>>(
      "/api/v1/me/deletion-request",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  exportMyData(): Promise<ApiSuccessEnvelope<DataExportData>> {
    return this.request<ApiSuccessEnvelope<DataExportData>>("/api/v1/me/data-export");
  }
}

import { describe, expect, it, vi } from "vitest";
import { RoomSyncApiClient, RoomSyncApiError } from "../src/index";

describe("RoomSyncApiClient", () => {
  it("attaches X-Request-ID, X-Client-Platform, and CSRF token on unsafe web requests", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json", "X-Request-ID": "srv-123" },
      }),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "web",
      fetchImpl: fetchMock,
      getCsrfToken: () => "csrf-abc",
    });

    const res = await client.request<{ status: string }>("/api/v1/test", {
      method: "POST",
      body: JSON.stringify({ ok: true }),
    });

    expect(res).toEqual({ status: "ok" });
    const [, options] = fetchMock.mock.calls[0]!;
    const headers = options?.headers as Headers;
    expect(headers.get("X-Client-Platform")).toBe("web");
    expect(headers.get("X-CSRFToken")).toBe("csrf-abc");
    expect(headers.get("X-Request-ID")).toBeTruthy();
    expect(options?.credentials).toBe("include");
  });

  it("calls slashless /api/v1/system/status for getSystemStatus", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: { service: "roomsync-backend", status: "ok", api_version: "v1" },
          meta: { request_id: "sys-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "web",
      fetchImpl: fetchMock,
    });

    await client.getSystemStatus();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/api/v1/system/status");
  });

  it("coerces backend error envelopes into RoomSyncApiError", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "SERVICE_UNAVAILABLE",
            message: "Database check failed.",
            field_errors: {},
            details: {},
            request_id: "req-err-1",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "web",
      fetchImpl: fetchMock,
    });

    await expect(client.getHealthReady()).rejects.toMatchObject({
      name: "RoomSyncApiError",
      status: 503,
      code: "SERVICE_UNAVAILABLE",
      requestId: "req-err-1",
    });
  });

  it("uses single-flight refresh lock and preserves refreshed Authorization header even if getAccessToken returns stale value", async () => {
    const getAccessTokenMock = vi.fn(async () => "stale-token");
    const refreshMock = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 10));
      return "fresh-token";
    });

    const authHeadersSeen: string[] = [];
    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      const headers = init?.headers as Headers;
      const auth = headers.get("Authorization") ?? "";
      authHeadersSeen.push(auth);
      if (auth === "Bearer stale-token") {
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Expired",
              field_errors: {},
              details: {},
              request_id: "r1",
            },
          }),
          { status: 401 },
        );
      }
      return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: getAccessTokenMock,
      refreshAccessToken: refreshMock,
    });

    const [r1, r2] = await Promise.all([client.getHealthReady(), client.getHealthReady()]);
    expect(r1).toEqual({ status: "ok" });
    expect(r2).toEqual({ status: "ok" });
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(authHeadersSeen).toEqual([
      "Bearer stale-token",
      "Bearer stale-token",
      "Bearer fresh-token",
      "Bearer fresh-token",
    ]);
    expect(RoomSyncApiError).toBeDefined();
  });

  it("does not loop 401 refresh on login/refresh endpoints and invokes onSessionInvalidated on reuse", async () => {
    const refreshMock = vi.fn(async () => "should-not-run");
    const invalidatedMock = vi.fn();

    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_REFRESH_REUSE_DETECTED",
            message: "Refresh token reuse detected.",
            field_errors: {},
            details: {},
            request_id: "r-reuse",
          },
        }),
        { status: 401 },
      ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    await expect(client.refreshSession({ refresh_token: "rsr_old" })).rejects.toMatchObject({
      code: "AUTH_REFRESH_REUSE_DETECTED",
      status: 401,
    });
    expect(refreshMock).not.toHaveBeenCalled();
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("invokes onSessionInvalidated when Android 401 refresh returns null", async () => {
    const invalidatedMock = vi.fn();
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Session expired.",
            field_errors: {},
            details: {},
            request_id: "r-exp",
          },
        }),
        { status: 401 },
      ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "expired-token",
      refreshAccessToken: async () => null,
      onSessionInvalidated: invalidatedMock,
    });

    await expect(client.getMe()).rejects.toMatchObject({
      code: "AUTH_INVALID_CREDENTIALS",
      status: 401,
    });
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("invokes onSessionInvalidated strictly once across concurrent 401s sharing one failed refresh cycle", async () => {
    const invalidatedMock = vi.fn();
    let clientRef: RoomSyncApiClient | null = null;
    const refreshMock = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 10));
      await clientRef!.refreshSession({ refresh_token: "rsr_dead" });
      return "unreachable";
    });

    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const target = url.toString();
      if (target.endsWith("/api/v1/auth/refresh")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Session revoked.",
              field_errors: {},
              details: {},
              request_id: "r-ref-401",
            },
          }),
          { status: 401 },
        );
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Expired.",
            field_errors: {},
            details: {},
            request_id: "r-api-401",
          },
        }),
        { status: 401 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "expired-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });
    clientRef = client;

    const settled = await Promise.allSettled([
      client.getMe(),
      client.getMySessions(),
      client.getHealthReady(),
    ]);
    expect(settled.every((res) => res.status === "rejected")).toBe(true);
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("invokes onSessionInvalidated strictly once across concurrent 401s when refresh returns null", async () => {
    const invalidatedMock = vi.fn();
    const refreshMock = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 10));
      return null;
    });
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Expired.",
              field_errors: {},
              details: {},
              request_id: "r-null",
            },
          }),
          { status: 401 },
        ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "expired-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    const settled = await Promise.allSettled([client.getMe(), client.getMySessions()]);
    expect(settled.every((res) => res.status === "rejected")).toBe(true);
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("does not invoke onSessionInvalidated on non-401 refresh outages or non-refreshable auth 401s", async () => {
    const refreshMock = vi.fn(async () => {
      throw new RoomSyncApiError(503, {
        code: "SERVICE_UNAVAILABLE",
        message: "Redis temporarily down.",
        field_errors: {},
        details: {},
        request_id: "r-503",
      });
    });
    const invalidatedMock = vi.fn();

    const outageFetch = vi.fn<typeof fetch>().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Expired.",
            field_errors: {},
            details: {},
            request_id: "r-401",
          },
        }),
        { status: 401 },
      ),
    );

    const outageClient = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: outageFetch,
      getAccessToken: () => "expired-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    await expect(outageClient.getMe()).rejects.toMatchObject({
      status: 503,
      code: "SERVICE_UNAVAILABLE",
    });
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).not.toHaveBeenCalled();

    const nonRefreshRefreshMock = vi.fn(async () => "should-never-run");
    const nonRefreshInvalidatedMock = vi.fn();
    const nonRefreshFetch = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Invalid verification or reset token.",
              field_errors: {},
              details: {},
              request_id: "r-tok",
            },
          }),
          { status: 401 },
        ),
    );
    const nonRefreshClient = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: nonRefreshFetch,
      getAccessToken: () => "active-token",
      refreshAccessToken: nonRefreshRefreshMock,
      onSessionInvalidated: nonRefreshInvalidatedMock,
    });

    await expect(nonRefreshClient.verifyEmail({ token: "rsv_bad" })).rejects.toMatchObject({
      status: 401,
      code: "AUTH_INVALID_CREDENTIALS",
    });
    await expect(
      nonRefreshClient.resendVerificationEmail({ email: "a@example.com" }),
    ).rejects.toMatchObject({ status: 401 });
    await expect(nonRefreshClient.forgotPassword({ email: "a@example.com" })).rejects.toMatchObject(
      { status: 401 },
    );
    await expect(
      nonRefreshClient.resetPassword({ token: "rsp_bad", new_password: "ValidPassword#2026" }),
    ).rejects.toMatchObject({ status: 401 });

    expect(nonRefreshRefreshMock).not.toHaveBeenCalled();
    expect(nonRefreshInvalidatedMock).not.toHaveBeenCalled();
  });

  it("still refreshes expired Android tokens on protected logout requests", async () => {
    const refreshMock = vi.fn(async () => "fresh-token");
    const invalidatedMock = vi.fn();
    const authHeadersSeen: string[] = [];

    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      const headers = init?.headers as Headers;
      const auth = headers.get("Authorization") ?? "";
      authHeadersSeen.push(auth);
      if (auth === "Bearer stale-token") {
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Expired.",
              field_errors: {},
              details: {},
              request_id: "r-l1",
            },
          }),
          { status: 401 },
        );
      }
      return new Response(
        JSON.stringify({ data: { logged_out: true }, meta: { request_id: "r-l2" } }),
        { status: 200 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "stale-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    const res = await client.logout({ refresh_token: "rsr_valid_token_123" });
    expect(res.data.logged_out).toBe(true);
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).not.toHaveBeenCalled();
    expect(authHeadersSeen).toEqual(["Bearer stale-token", "Bearer fresh-token"]);
  });

  it("suppresses duplicate refresh/invalidation from slower staggered in-flight 401s", async () => {
    const invalidatedMock = vi.fn();
    let clientRef: RoomSyncApiClient | null = null;
    const refreshMock = vi.fn(async () => {
      await clientRef!.refreshSession({ refresh_token: "rsr_dead" });
      return null;
    });

    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const target = url.toString();
      if (target.endsWith("/api/v1/me/sessions")) {
        await new Promise((r) => setTimeout(r, 30));
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: target.endsWith("/api/v1/auth/refresh") ? "Revoked" : "Expired",
            field_errors: {},
            details: {},
            request_id: "r-stag",
          },
        }),
        { status: 401 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "expired-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });
    clientRef = client;

    const settled = await Promise.allSettled([client.getMe(), client.getMySessions()]);
    expect(settled.every((res) => res.status === "rejected")).toBe(true);
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("keeps refresh/invalidation single-flight across a null-refresh body-parse pause and allows a new session afterwards", async () => {
    let activeToken: string | null = "expired-session-1";
    let notifyBodyParseStarted!: () => void;
    const bodyParseStarted = new Promise<void>((resolve) => {
      notifyBodyParseStarted = resolve;
    });
    let releaseBodyParse!: () => void;
    const bodyParseGate = new Promise<void>((resolve) => {
      releaseBodyParse = resolve;
    });

    const invalidatedMock = vi.fn(async () => {
      activeToken = null;
    });

    let refreshCallCount = 0;
    const refreshMock = vi.fn(async () => {
      refreshCallCount += 1;
      if (refreshCallCount === 1) {
        return null;
      }
      activeToken = "fresh-session-2";
      return "fresh-session-2";
    });

    const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
      const target = url.toString();
      const auth = (init?.headers as Headers).get("Authorization") ?? "";
      if (target.endsWith("/api/v1/me") && auth === "Bearer expired-session-1") {
        const pausedResp = new Response(null, { status: 401 });
        Object.defineProperty(pausedResp, "text", {
          value: async () => {
            notifyBodyParseStarted();
            await bodyParseGate;
            return JSON.stringify({
              error: {
                code: "AUTH_INVALID_CREDENTIALS",
                message: "Session 1 expired (paused body).",
                field_errors: {},
                details: {},
                request_id: "r-null-race-1",
              },
            });
          },
        });
        return pausedResp;
      }
      if (auth === "Bearer fresh-session-2") {
        return new Response(
          JSON.stringify({ data: { id: "u-recovered" }, meta: { request_id: "r-ok-2" } }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Expired.",
            field_errors: {},
            details: {},
            request_id: "r-null-race-2",
          },
        }),
        { status: 401 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => activeToken,
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    const firstReq = client.getMe();
    await bodyParseStarted;

    // Start a second protected request while request 1 is paused after null refresh inside response.text().
    const secondReq = client.getMySessions();
    await expect(secondReq).rejects.toMatchObject({
      status: 401,
      code: "AUTH_INVALID_CREDENTIALS",
    });

    releaseBodyParse();
    await expect(firstReq).rejects.toMatchObject({
      status: 401,
      code: "AUTH_INVALID_CREDENTIALS",
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
    expect(activeToken).toBeNull();

    // Establish a genuinely new session on the same client instance and confirm refresh works normally.
    activeToken = "expired-session-2";
    const recovered = await client.getMe();
    expect((recovered.data as { id: string }).id).toBe("u-recovered");
    expect(refreshMock).toHaveBeenCalledTimes(2);
    expect(invalidatedMock).toHaveBeenCalledTimes(1);
  });

  it("ignores stale refresh resolving a token after login/register/google transitions", async () => {
    const authTransitions: Array<(client: RoomSyncApiClient) => Promise<unknown>> = [
      (c) => c.login({ email: "b@example.com", password: "ValidPassword#2026" }),
      (c) =>
        c.register({
          email: "b@example.com",
          password: "ValidPassword#2026",
          accept_terms: true,
          confirm_adult: true,
        }),
      (c) =>
        c.loginWithGoogle({
          id_token: "id-tok-b",
          nonce: "n".repeat(24),
          accept_terms: true,
          confirm_adult: true,
        }),
      (c) =>
        c.linkGoogleAccount({
          link_challenge_token: "rsl_chal",
          confirm_link: true,
          password: "ValidPassword#2026",
        }),
    ];

    for (const runTransition of authTransitions) {
      let activeToken = "session-a-expired";
      let notifyRefreshStarted!: () => void;
      const refreshStarted = new Promise<void>((resolve) => {
        notifyRefreshStarted = resolve;
      });
      let resolveStaleRefresh!: (value: string | null) => void;
      const staleRefreshGate = new Promise<string | null>((resolve) => {
        resolveStaleRefresh = resolve;
      });

      const refreshMock = vi.fn(async ({ generation }: { generation: number }) => {
        if (generation === 0) {
          notifyRefreshStarted();
          return staleRefreshGate;
        }
        return "session-b-refreshed";
      });
      const invalidatedMock = vi.fn();
      const authHeadersSeen: Array<{ url: string; auth: string }> = [];

      const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
        const target = url.toString();
        const auth = (init?.headers as Headers).get("Authorization") ?? "";
        authHeadersSeen.push({ url: target, auth });
        if (target.includes("/api/v1/auth/")) {
          activeToken = "session-b-access";
          return new Response(
            JSON.stringify({
              data: { user: { id: "u-b" }, platform: "android", session_id: "s-b" },
              meta: { request_id: "r-auth" },
            }),
            { status: 200 },
          );
        }
        if (auth === "Bearer session-b-access") {
          return new Response(
            JSON.stringify({ data: { id: "u-b" }, meta: { request_id: "r-b" } }),
            {
              status: 200,
            },
          );
        }
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Expired.",
              field_errors: {},
              details: {},
              request_id: "r-401",
            },
          }),
          { status: 401 },
        );
      });

      const client = new RoomSyncApiClient({
        baseOrigin: "http://localhost:8000",
        platform: "android",
        fetchImpl: fetchMock,
        getAccessToken: () => activeToken,
        refreshAccessToken: refreshMock,
        onSessionInvalidated: invalidatedMock,
      });

      expect(client.getSessionGeneration()).toBe(0);
      const staleReq = client.getMe();
      await refreshStarted;

      const genBefore = client.getSessionGeneration();
      const transitionPromise = runTransition(client);
      expect(client.getSessionGeneration()).toBe(genBefore + 1);
      await transitionPromise;

      resolveStaleRefresh("stale-session-a-rotated");
      await expect(staleReq).rejects.toMatchObject({ status: 401 });
      expect(authHeadersSeen.some((entry) => entry.auth === "Bearer stale-session-a-rotated")).toBe(
        false,
      );
      expect(invalidatedMock).not.toHaveBeenCalled();

      const okB = await client.getMe();
      expect((okB.data as { id: string }).id).toBe("u-b");
    }
  });

  it("ignores stale refresh returning null or throwing 401 after login() without invalidating Session B", async () => {
    for (const staleOutcome of ["null", "401"] as const) {
      let activeToken = "session-a-expired";
      let notifyRefreshStarted!: () => void;
      const refreshStarted = new Promise<void>((resolve) => {
        notifyRefreshStarted = resolve;
      });
      let resolveStaleRefresh!: (value: string | null) => void;
      let rejectStaleRefresh!: (err: unknown) => void;
      const staleRefreshGate = new Promise<string | null>((resolve, reject) => {
        resolveStaleRefresh = resolve;
        rejectStaleRefresh = reject;
      });

      const refreshMock = vi.fn(async ({ generation }: { generation: number }) => {
        if (generation === 0) {
          notifyRefreshStarted();
          return staleRefreshGate;
        }
        activeToken = "session-b-fresh";
        return "session-b-fresh";
      });
      const invalidatedMock = vi.fn();

      const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
        const target = url.toString();
        const auth = (init?.headers as Headers).get("Authorization") ?? "";
        if (target.endsWith("/api/v1/auth/login")) {
          activeToken = "session-b-expired";
          return new Response(
            JSON.stringify({
              data: { user: { id: "u-b" }, platform: "android", session_id: "s-b" },
              meta: { request_id: "r-login" },
            }),
            { status: 200 },
          );
        }
        if (auth === "Bearer session-b-fresh") {
          return new Response(
            JSON.stringify({ data: { id: "u-b" }, meta: { request_id: "r-ok-b" } }),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Expired.",
              field_errors: {},
              details: {},
              request_id: "r-401",
            },
          }),
          { status: 401 },
        );
      });

      const client = new RoomSyncApiClient({
        baseOrigin: "http://localhost:8000",
        platform: "android",
        fetchImpl: fetchMock,
        getAccessToken: () => activeToken,
        refreshAccessToken: refreshMock,
        onSessionInvalidated: invalidatedMock,
      });

      const staleReq = client.getMe();
      await refreshStarted;

      await client.login({ email: "b@example.com", password: "ValidPassword#2026" });
      if (staleOutcome === "null") {
        resolveStaleRefresh(null);
      } else {
        rejectStaleRefresh(
          new RoomSyncApiError(401, {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Stale session revoked.",
            field_errors: {},
            details: {},
            request_id: "r-stale-401",
          }),
        );
      }

      await expect(staleReq).rejects.toMatchObject({ status: 401 });
      expect(invalidatedMock).not.toHaveBeenCalled();

      // Session B must still be able to enter its own normal 401 -> refresh -> 200 cycle.
      const resB = await client.getMe();
      expect((resB.data as { id: string }).id).toBe("u-b");
      expect(refreshMock).toHaveBeenCalledTimes(2);
      expect(invalidatedMock).not.toHaveBeenCalled();
    }
  });

  it("drops obsolete pre-logout 401 across logout() -> login() without refreshing Session B", async () => {
    let activeToken = "session-a-access";
    let notifyOldFetchStarted!: () => void;
    const oldFetchStarted = new Promise<void>((resolve) => {
      notifyOldFetchStarted = resolve;
    });
    let releaseOldFetch!: (resp: Response) => void;
    const oldFetchGate = new Promise<Response>((resolve) => {
      releaseOldFetch = resolve;
    });

    const refreshMock = vi.fn(async () => "should-never-refresh-for-obsolete-401");
    const invalidatedMock = vi.fn();

    const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
      const target = url.toString();
      const auth = (init?.headers as Headers).get("Authorization") ?? "";
      if (target.endsWith("/api/v1/auth/logout")) {
        activeToken = "";
        return new Response(
          JSON.stringify({ data: { logged_out: true }, meta: { request_id: "r-out" } }),
          { status: 200 },
        );
      }
      if (target.endsWith("/api/v1/auth/login")) {
        activeToken = "session-b-access";
        return new Response(
          JSON.stringify({
            data: { user: { id: "u-b" }, platform: "android", session_id: "s-b" },
            meta: { request_id: "r-in" },
          }),
          { status: 200 },
        );
      }
      if (auth === "Bearer session-a-access") {
        notifyOldFetchStarted();
        return oldFetchGate;
      }
      return new Response(JSON.stringify({ data: { id: "u-b" }, meta: { request_id: "r-b" } }), {
        status: 200,
      });
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => activeToken || null,
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    const staleReq = client.getMe();
    await oldFetchStarted;

    await client.logout({ refresh_token: "rsr_a" });
    await client.login({ email: "b@example.com", password: "ValidPassword#2026" });

    releaseOldFetch(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Old Session A expired.",
            field_errors: {},
            details: {},
            request_id: "r-old-401",
          },
        }),
        { status: 401 },
      ),
    );

    await expect(staleReq).rejects.toMatchObject({ status: 401 });
    expect(refreshMock).not.toHaveBeenCalled();
    expect(invalidatedMock).not.toHaveBeenCalled();
  });

  it("ignores async getAccessToken() resolution if session generation advances while awaiting token", async () => {
    let notifyTokenReadStarted!: () => void;
    const tokenReadStarted = new Promise<void>((resolve) => {
      notifyTokenReadStarted = resolve;
    });
    let releaseTokenRead!: (token: string | null) => void;
    const tokenReadGate = new Promise<string | null>((resolve) => {
      releaseTokenRead = resolve;
    });

    let readCount = 0;
    const authHeadersSeen: Array<string | null> = [];
    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      authHeadersSeen.push((init?.headers as Headers).get("Authorization"));
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Unauthorized",
            field_errors: {},
            details: {},
            request_id: "r-leak",
          },
        }),
        { status: 401 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: async () => {
        readCount += 1;
        if (readCount === 1) {
          notifyTokenReadStarted();
          return tokenReadGate;
        }
        return "session-b-secret-token";
      },
    });

    const staleReq = client.getMe();
    await tokenReadStarted;
    client.resetSessionCycle();
    releaseTokenRead("session-b-secret-token");

    await expect(staleReq).rejects.toMatchObject({ status: 401 });
    expect(authHeadersSeen).toEqual([null]);
  });

  it("suppresses onSessionInvalidated on stale direct refreshSession() and preserves newer refresh cycles", async () => {
    const invalidatedMock = vi.fn();
    let releaseDirectRefresh!: (resp: Response) => void;
    const directRefreshGate = new Promise<Response>((resolve) => {
      releaseDirectRefresh = resolve;
    });

    let notifyGen0RefreshStarted!: () => void;
    const gen0RefreshStarted = new Promise<void>((resolve) => {
      notifyGen0RefreshStarted = resolve;
    });
    let releaseGen0Refresh!: () => void;
    const gen0RefreshGate = new Promise<string | null>((resolve) => {
      releaseGen0Refresh = () => resolve(null);
    });
    let releaseGen1Refresh!: (token: string | null) => void;
    const gen1RefreshGate = new Promise<string | null>((resolve) => {
      releaseGen1Refresh = resolve;
    });

    const refreshMock = vi.fn(async ({ generation }: { generation: number }) => {
      if (generation === 1) {
        notifyGen0RefreshStarted();
        return gen0RefreshGate;
      }
      return gen1RefreshGate;
    });

    let gen2Calls = 0;
    const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
      const target = url.toString();
      const auth = (init?.headers as Headers).get("Authorization") ?? "";
      if (target.endsWith("/api/v1/auth/refresh")) {
        return directRefreshGate;
      }
      if (auth === "Bearer gen2-fresh") {
        gen2Calls += 1;
        return new Response(JSON.stringify({ data: { id: "u-gen2", gen2Calls } }), { status: 200 });
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Expired.",
            field_errors: {},
            details: {},
            request_id: "r-exp",
          },
        }),
        { status: 401 },
      );
    });

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "android",
      fetchImpl: fetchMock,
      getAccessToken: () => "expired-token",
      refreshAccessToken: refreshMock,
      onSessionInvalidated: invalidatedMock,
    });

    // 1. Direct refreshSession from gen 0 -> superseded by resetSessionCycle (gen 1).
    const directRefreshPromise = client.refreshSession({ refresh_token: "rsr_old_session" });
    client.resetSessionCycle();
    releaseDirectRefresh(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_REFRESH_REUSE_DETECTED",
            message: "Reuse detected.",
            field_errors: {},
            details: {},
            request_id: "r-reuse-stale",
          },
        }),
        { status: 401 },
      ),
    );
    await expect(directRefreshPromise).rejects.toMatchObject({
      code: "AUTH_REFRESH_REUSE_DETECTED",
    });
    expect(invalidatedMock).not.toHaveBeenCalled();

    // 2. Gen 1 refresh cycle starts -> gen 2 starts -> gen 1 finishes cleanly without detaching gen 2's cycle.
    const reqGen1 = client.getMe();
    await gen0RefreshStarted;
    client.resetSessionCycle(); // now gen 2

    const reqGen2First = client.getMe();
    await Promise.resolve();
    releaseGen0Refresh();
    await expect(reqGen1).rejects.toMatchObject({ status: 401 });

    // Concurrent request in gen 2 must join gen 2's still-active single-flight cycle (not call refreshMock again).
    const reqGen2Second = client.getMySessions();
    releaseGen1Refresh("gen2-fresh");
    const [res2a, res2b] = await Promise.all([reqGen2First, reqGen2Second]);
    expect((res2a as { data: { id: string } }).data.id).toBe("u-gen2");
    expect((res2b as { data: { id: string } }).data.id).toBe("u-gen2");
    expect(refreshMock).toHaveBeenCalledTimes(2);
    expect(invalidatedMock).not.toHaveBeenCalled();
  });
});

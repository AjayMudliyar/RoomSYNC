import { beforeEach, describe, expect, it, vi } from "vitest";

const backingMap = new Map<string, string>();

vi.mock("expo-secure-store", () => ({
  getItemAsync: vi.fn(async (key: string) => backingMap.get(key) ?? null),
  setItemAsync: vi.fn(async (key: string, value: string) => {
    backingMap.set(key, value);
  }),
  deleteItemAsync: vi.fn(async (key: string) => {
    backingMap.delete(key);
  }),
}));

import * as SecureStore from "expo-secure-store";
import type { FetchLike } from "@roomsync/api-client";
import {
  AUTH_SESSION_STORAGE_KEY,
  clearAuthSession,
  clearAuthSessionIfRefreshTokenMatches,
  createAndroidApiClient,
  getStoreSessionGeneration,
  getStoredAccessToken,
  getStoredAuthSession,
  isAccessTokenExpiringSoon,
  replaceAuthSessionIfRefreshTokenMatches,
  saveAuthSession,
} from "../src/lib/authStorage";

describe("Android SecureStore auth persistence", () => {
  beforeEach(() => {
    backingMap.clear();
    vi.clearAllMocks();
  });

  it("persists and retrieves session tokens strictly via expo-secure-store", async () => {
    await saveAuthSession(
      {
        access_token: "jwt-access-1",
        refresh_token: "rsr_refresh_1",
        expires_in_seconds: 900,
      },
      undefined,
      1_000_000,
    );

    expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(1);
    const loaded = await getStoredAuthSession();
    expect(loaded).toEqual({
      accessToken: "jwt-access-1",
      refreshToken: "rsr_refresh_1",
      expiresAtMs: 1_900_000,
    });
    expect(await getStoredAccessToken()).toBe("jwt-access-1");
    expect(isAccessTokenExpiringSoon(loaded!, 60, 1_850_000)).toBe(true);
    expect(isAccessTokenExpiringSoon(loaded!, 60, 1_500_000)).toBe(false);

    await clearAuthSession();
    expect(await getStoredAuthSession()).toBeNull();
  });

  it("clears corrupt JSON entries safely instead of throwing", async () => {
    backingMap.set(AUTH_SESSION_STORAGE_KEY, "{not-valid-json");
    const loaded = await getStoredAuthSession();
    expect(loaded).toBeNull();
    expect(backingMap.has(AUTH_SESSION_STORAGE_KEY)).toBe(false);
  });

  it("refreshes rotated tokens and wipes SecureStore on refresh reuse detection", async () => {
    await saveAuthSession({
      access_token: "old-jwt",
      refresh_token: "rsr_initial",
      expires_in_seconds: 900,
    });

    const onInvalidated = vi.fn();
    let callIdx = 0;
    const fetchMock = vi.fn<FetchLike>(async (url) => {
      callIdx += 1;
      if (url.toString().endsWith("/api/v1/me") && callIdx === 1) {
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
      if (url.toString().endsWith("/api/v1/auth/refresh")) {
        return new Response(
          JSON.stringify({
            data: {
              user: { id: "u1" },
              platform: "android",
              session_id: "s2",
              expires_in_seconds: 900,
              tokens: {
                access_token: "rotated-jwt",
                refresh_token: "rsr_rotated",
                token_type: "Bearer",
                expires_in_seconds: 900,
              },
            },
            meta: { request_id: "r2" },
          }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify({
          data: { id: "u1" },
          meta: { request_id: "r3" },
        }),
        { status: 200 },
      );
    });

    const client = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: fetchMock,
      onSessionInvalidated: onInvalidated,
    });

    const meRes = await client.getMe();
    expect((meRes.data as { id: string }).id).toBe("u1");
    expect(onInvalidated).not.toHaveBeenCalled();

    const updated = await getStoredAuthSession();
    expect(updated?.accessToken).toBe("rotated-jwt");
    expect(updated?.refreshToken).toBe("rsr_rotated");

    const invalidatedFetch = vi.fn<FetchLike>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_REFRESH_REUSE_DETECTED",
            message: "Reuse detected",
            field_errors: {},
            details: {},
            request_id: "r4",
          },
        }),
        { status: 401 },
      ),
    );
    const deadClient = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: invalidatedFetch,
      onSessionInvalidated: onInvalidated,
    });

    await expect(deadClient.refreshSession({ refresh_token: "rsr_old" })).rejects.toMatchObject({
      code: "AUTH_REFRESH_REUSE_DETECTED",
    });
    expect(onInvalidated).toHaveBeenCalledTimes(1);
    expect(await getStoredAuthSession()).toBeNull();
  });

  it("invokes onSessionInvalidated strictly once on single and concurrent 401 -> failed refresh cycles", async () => {
    await saveAuthSession({
      access_token: "expired-jwt",
      refresh_token: "rsr_revoked",
      expires_in_seconds: 900,
    });

    const onInvalidated = vi.fn();
    let refreshCalls = 0;
    const fetchMock = vi.fn<FetchLike>(async (url) => {
      if (url.toString().endsWith("/api/v1/auth/refresh")) {
        refreshCalls += 1;
        await new Promise((r) => setTimeout(r, 10));
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_INVALID_CREDENTIALS",
              message: "Refresh session revoked.",
              field_errors: {},
              details: {},
              request_id: "r-ref",
            },
          }),
          { status: 401 },
        );
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Access token expired.",
            field_errors: {},
            details: {},
            request_id: "r-me",
          },
        }),
        { status: 401 },
      );
    });

    const client = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: fetchMock,
      onSessionInvalidated: onInvalidated,
    });

    await expect(client.getMe()).rejects.toMatchObject({ status: 401 });
    expect(refreshCalls).toBe(1);
    expect(onInvalidated).toHaveBeenCalledTimes(1);
    expect(await getStoredAuthSession()).toBeNull();

    // Re-seed session and verify concurrent 401s sharing one failed refresh cycle also fire once.
    onInvalidated.mockClear();
    refreshCalls = 0;
    await saveAuthSession({
      access_token: "expired-jwt-2",
      refresh_token: "rsr_revoked_2",
      expires_in_seconds: 900,
    });
    const settled = await Promise.allSettled([client.getMe(), client.getMySessions()]);
    expect(settled.every((item) => item.status === "rejected")).toBe(true);
    expect(refreshCalls).toBe(1);
    expect(onInvalidated).toHaveBeenCalledTimes(1);
    expect(await getStoredAuthSession()).toBeNull();
  });

  it("preserves stored session when refresh fails with 503 or non-refreshable endpoints return 401", async () => {
    await saveAuthSession({
      access_token: "good-jwt",
      refresh_token: "rsr_good",
      expires_in_seconds: 900,
    });
    const onInvalidated = vi.fn();

    const fetchMock = vi.fn<FetchLike>(async (url) => {
      const target = url.toString();
      if (target.endsWith("/api/v1/auth/refresh")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "SERVICE_UNAVAILABLE",
              message: "Temporary Redis outage.",
              field_errors: {},
              details: {},
              request_id: "r-503",
            },
          }),
          { status: 503 },
        );
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Invalid token.",
            field_errors: {},
            details: {},
            request_id: "r-401",
          },
        }),
        { status: 401 },
      );
    });

    const client = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: fetchMock,
      onSessionInvalidated: onInvalidated,
    });

    await expect(
      client.resetPassword({ token: "rsp_invalid", new_password: "ValidPassword#2026" }),
    ).rejects.toMatchObject({ status: 401 });
    await expect(client.getMe()).rejects.toMatchObject({
      status: 503,
      code: "SERVICE_UNAVAILABLE",
    });

    expect(onInvalidated).not.toHaveBeenCalled();
    expect(await getStoredAuthSession()).not.toBeNull();
  });

  it("prevents duplicate invalidation across staggered 401s when SecureStore clears during paused body parsing and recovers after re-login", async () => {
    await saveAuthSession({
      access_token: "expired-jwt-1",
      refresh_token: "rsr_revoked_1",
      expires_in_seconds: 900,
    });

    let notifyBodyParseStarted!: () => void;
    const bodyParseStarted = new Promise<void>((resolve) => {
      notifyBodyParseStarted = resolve;
    });
    let releaseBodyParse!: () => void;
    const bodyParseGate = new Promise<void>((resolve) => {
      releaseBodyParse = resolve;
    });

    const onInvalidated = vi.fn();
    let refreshAttempt = 0;
    const fetchMock = vi.fn<FetchLike>(async (url, init) => {
      const target = url.toString();
      const auth = (init?.headers as Headers).get("Authorization") ?? "";
      if (target.endsWith("/api/v1/auth/refresh")) {
        refreshAttempt += 1;
        if (refreshAttempt === 1) {
          // Simulate refresh endpoint returning 200 without mobile tokens -> refreshAccessToken resolves null.
          return new Response(
            JSON.stringify({
              data: {
                user: { id: "u1" },
                platform: "web",
                session_id: "s1",
                expires_in_seconds: 900,
              },
              meta: { request_id: "r-null-tok" },
            }),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              user: { id: "u1" },
              platform: "android",
              session_id: "s3",
              expires_in_seconds: 900,
              tokens: {
                access_token: "recovered-jwt",
                refresh_token: "rsr_recovered",
                token_type: "Bearer",
                expires_in_seconds: 900,
              },
            },
            meta: { request_id: "r-ref-ok" },
          }),
          { status: 200 },
        );
      }
      if (target.endsWith("/api/v1/me") && auth === "Bearer expired-jwt-1") {
        const pausedResp = new Response(null, { status: 401 });
        Object.defineProperty(pausedResp, "text", {
          value: async () => {
            notifyBodyParseStarted();
            await bodyParseGate;
            return JSON.stringify({
              error: {
                code: "AUTH_INVALID_CREDENTIALS",
                message: "Expired 1",
                field_errors: {},
                details: {},
                request_id: "r-me-paused",
              },
            });
          },
        });
        return pausedResp;
      }
      if (auth === "Bearer recovered-jwt") {
        return new Response(JSON.stringify({ data: { id: "u1" }, meta: { request_id: "r-ok" } }), {
          status: 200,
        });
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Expired",
            field_errors: {},
            details: {},
            request_id: "r-unauth",
          },
        }),
        { status: 401 },
      );
    });

    const client = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: fetchMock,
      onSessionInvalidated: onInvalidated,
    });

    const req1 = client.getMe();
    await bodyParseStarted;

    const req2 = client.getMySessions();
    await expect(req2).rejects.toMatchObject({ status: 401 });

    releaseBodyParse();
    await expect(req1).rejects.toMatchObject({ status: 401 });

    expect(refreshAttempt).toBe(1);
    expect(onInvalidated).toHaveBeenCalledTimes(1);
    expect(await getStoredAuthSession()).toBeNull();

    // New login saves fresh tokens on the same client instance and refreshes cleanly on subsequent 401.
    await saveAuthSession({
      access_token: "expired-jwt-2",
      refresh_token: "rsr_valid_2",
      expires_in_seconds: 900,
    });
    const me = await client.getMe();
    expect((me.data as { id: string }).id).toBe("u1");
    expect(refreshAttempt).toBe(2);
    expect(onInvalidated).toHaveBeenCalledTimes(1);
    expect((await getStoredAuthSession())?.accessToken).toBe("recovered-jwt");
  });

  it("enforces conditional storage CAS and FIFO serialization under concurrent mutations", async () => {
    const delayedBacking = new Map<string, string>();
    let releaseSlowWrite!: () => void;
    const slowWriteGate = new Promise<void>((resolve) => {
      releaseSlowWrite = resolve;
    });
    let notifySlowWriteStarted!: () => void;
    const slowWriteStarted = new Promise<void>((resolve) => {
      notifySlowWriteStarted = resolve;
    });
    let pauseFirstWrite = true;

    const customStore = {
      getItemAsync: async (key: string) => delayedBacking.get(key) ?? null,
      setItemAsync: async (key: string, value: string) => {
        if (pauseFirstWrite && value.includes("rsr_a_rot")) {
          pauseFirstWrite = false;
          notifySlowWriteStarted();
          await slowWriteGate;
        }
        delayedBacking.set(key, value);
      },
      deleteItemAsync: async (key: string) => {
        delayedBacking.delete(key);
      },
    };

    await saveAuthSession(
      {
        access_token: "acc_a",
        refresh_token: "rsr_a",
        expires_in_seconds: 900,
      },
      customStore,
    );
    const genA = getStoreSessionGeneration(customStore);

    // Token mismatch, generation mismatch, unauthorized, and missing checks fail safely without overwriting.
    const mismatchRes = await replaceAuthSessionIfRefreshTokenMatches(
      { access_token: "acc_bad", refresh_token: "rsr_bad", expires_in_seconds: 900 },
      { store: customStore, expectedRefreshToken: "rsr_wrong" },
    );
    expect(mismatchRes).toMatchObject({
      updated: false,
      superseded: true,
      reason: "token_mismatch",
    });

    const genMismatchRes = await replaceAuthSessionIfRefreshTokenMatches(
      { access_token: "acc_bad", refresh_token: "rsr_bad", expires_in_seconds: 900 },
      { store: customStore, expectedStoreGeneration: genA - 1 },
    );
    expect(genMismatchRes).toMatchObject({
      updated: false,
      superseded: true,
      reason: "generation_mismatch",
    });

    const unauthClearRes = await clearAuthSessionIfRefreshTokenMatches({
      store: customStore,
      expectedRefreshToken: "rsr_a",
      isAuthorized: () => false,
    });
    expect(unauthClearRes).toMatchObject({
      cleared: false,
      superseded: true,
      reason: "unauthorized",
    });
    expect((await getStoredAuthSession(customStore))?.refreshToken).toBe("rsr_a");

    // Concurrent slow conditional replace followed immediately by saveAuthSession(B):
    // FIFO mutex + generation check guarantees B always ends in SecureStore.
    const staleReplacePromise = replaceAuthSessionIfRefreshTokenMatches(
      { access_token: "acc_a_rot", refresh_token: "rsr_a_rot", expires_in_seconds: 900 },
      {
        store: customStore,
        expectedRefreshToken: "rsr_a",
        expectedStoreGeneration: genA,
      },
    );
    await slowWriteStarted;

    const saveBPromise = saveAuthSession(
      { access_token: "acc_b", refresh_token: "rsr_b", expires_in_seconds: 900 },
      customStore,
    );
    releaseSlowWrite();

    const [replaceResult] = await Promise.all([staleReplacePromise, saveBPromise]);
    expect(replaceResult.updated).toBe(false);
    expect(replaceResult.superseded).toBe(true);
    expect((await getStoredAuthSession(customStore))?.refreshToken).toBe("rsr_b");

    // Replacing when missing fails cleanly as superseded.
    await clearAuthSession(customStore);
    const missingReplace = await replaceAuthSessionIfRefreshTokenMatches(
      { access_token: "acc_ghost", refresh_token: "rsr_ghost", expires_in_seconds: 900 },
      { store: customStore },
    );
    expect(missingReplace).toMatchObject({
      updated: false,
      superseded: true,
      reason: "missing",
    });
  });

  it("never overwrites or invalidates Session B when Session A refresh resolves 200, 401, or null afterwards", async () => {
    for (const staleMode of ["200_rotated", "401_reuse", "200_null"] as const) {
      backingMap.clear();
      await saveAuthSession({
        access_token: "jwt-session-a-expired",
        refresh_token: "rsr_session_a",
        expires_in_seconds: 900,
      });

      let notifyRefreshStarted!: () => void;
      const refreshStarted = new Promise<void>((resolve) => {
        notifyRefreshStarted = resolve;
      });
      let resolveRefreshA!: (res: Response) => void;
      const refreshGateA = new Promise<Response>((resolve) => {
        resolveRefreshA = resolve;
      });

      const onInvalidated = vi.fn();
      const authHeadersForMe: string[] = [];

      const fetchMock = vi.fn<FetchLike>(async (url, init) => {
        const target = url.toString();
        const auth = (init?.headers as Headers).get("Authorization") ?? "";
        if (target.endsWith("/api/v1/auth/login")) {
          return new Response(
            JSON.stringify({
              data: {
                user: { id: "user-b" },
                platform: "android",
                session_id: "sess-b",
                expires_in_seconds: 900,
                tokens: {
                  access_token: "jwt-session-b",
                  refresh_token: "rsr_session_b",
                  token_type: "Bearer",
                  expires_in_seconds: 900,
                },
              },
              meta: { request_id: "r-login-b" },
            }),
            { status: 200 },
          );
        }
        if (target.endsWith("/api/v1/auth/refresh")) {
          notifyRefreshStarted();
          return refreshGateA;
        }
        if (target.endsWith("/api/v1/me")) {
          authHeadersForMe.push(auth);
          if (auth === "Bearer jwt-session-b") {
            return new Response(
              JSON.stringify({ data: { id: "user-b" }, meta: { request_id: "r-me-b" } }),
              { status: 200 },
            );
          }
          return new Response(
            JSON.stringify({
              error: {
                code: "AUTH_INVALID_CREDENTIALS",
                message: "Session A expired",
                field_errors: {},
                details: {},
                request_id: "r-me-401",
              },
            }),
            { status: 401 },
          );
        }
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      });

      const client = createAndroidApiClient({
        baseOrigin: "http://localhost:8000",
        fetchImpl: fetchMock,
        onSessionInvalidated: onInvalidated,
      });

      const staleReqA = client.getMe();
      await refreshStarted;

      // Session B logs in and persists its fresh tokens while Session A's refresh request is still suspended.
      const loginB = await client.login({
        email: "userb@example.com",
        password: "SessionBStrong#2026",
      });
      await saveAuthSession(loginB.data.tokens!);

      if (staleMode === "200_rotated") {
        resolveRefreshA(
          new Response(
            JSON.stringify({
              data: {
                user: { id: "user-a" },
                platform: "android",
                session_id: "sess-a2",
                expires_in_seconds: 900,
                tokens: {
                  access_token: "jwt-session-a-rotated",
                  refresh_token: "rsr_session_a_rotated",
                  token_type: "Bearer",
                  expires_in_seconds: 900,
                },
              },
              meta: { request_id: "r-ref-a-200" },
            }),
            { status: 200 },
          ),
        );
      } else if (staleMode === "401_reuse") {
        resolveRefreshA(
          new Response(
            JSON.stringify({
              error: {
                code: "AUTH_REFRESH_REUSE_DETECTED",
                message: "Session A reuse detected",
                field_errors: {},
                details: {},
                request_id: "r-ref-a-401",
              },
            }),
            { status: 401 },
          ),
        );
      } else {
        resolveRefreshA(
          new Response(
            JSON.stringify({
              data: {
                user: { id: "user-a" },
                platform: "web",
                session_id: "sess-a-web",
                expires_in_seconds: 900,
              },
              meta: { request_id: "r-ref-a-null" },
            }),
            { status: 200 },
          ),
        );
      }

      await expect(staleReqA).rejects.toMatchObject({ status: 401 });
      expect(onInvalidated).not.toHaveBeenCalled();

      const stored = await getStoredAuthSession();
      expect(stored?.accessToken).toBe("jwt-session-b");
      expect(stored?.refreshToken).toBe("rsr_session_b");

      const meB = await client.getMe();
      expect((meB.data as { id: string }).id).toBe("user-b");
      expect(authHeadersForMe).not.toContain("Bearer jwt-session-a-rotated");
    }
  });

  it("does not refresh Session B or invalidate when an old request returns 401 across logout() -> login()", async () => {
    await saveAuthSession({
      access_token: "jwt-session-a",
      refresh_token: "rsr_session_a",
      expires_in_seconds: 900,
    });

    let notifyOldMeStarted!: () => void;
    const oldMeStarted = new Promise<void>((resolve) => {
      notifyOldMeStarted = resolve;
    });
    let resolveOldMe!: (res: Response) => void;
    const oldMeGate = new Promise<Response>((resolve) => {
      resolveOldMe = resolve;
    });

    let refreshCount = 0;
    const onInvalidated = vi.fn();
    const fetchMock = vi.fn<FetchLike>(async (url, init) => {
      const target = url.toString();
      const auth = (init?.headers as Headers).get("Authorization") ?? "";
      if (target.endsWith("/api/v1/auth/logout")) {
        return new Response(
          JSON.stringify({ data: { logged_out: true }, meta: { request_id: "r-out" } }),
          { status: 200 },
        );
      }
      if (target.endsWith("/api/v1/auth/login")) {
        return new Response(
          JSON.stringify({
            data: {
              user: { id: "user-b" },
              platform: "android",
              session_id: "sess-b",
              expires_in_seconds: 900,
              tokens: {
                access_token: "jwt-session-b",
                refresh_token: "rsr_session_b",
                token_type: "Bearer",
                expires_in_seconds: 900,
              },
            },
            meta: { request_id: "r-in" },
          }),
          { status: 200 },
        );
      }
      if (target.endsWith("/api/v1/auth/refresh")) {
        refreshCount += 1;
        return new Response(JSON.stringify({ error: { code: "UNEXPECTED" } }), { status: 500 });
      }
      if (target.endsWith("/api/v1/me") && auth === "Bearer jwt-session-a") {
        notifyOldMeStarted();
        return oldMeGate;
      }
      return new Response(
        JSON.stringify({ data: { id: "user-b" }, meta: { request_id: "r-me-b" } }),
        { status: 200 },
      );
    });

    const client = createAndroidApiClient({
      baseOrigin: "http://localhost:8000",
      fetchImpl: fetchMock,
      onSessionInvalidated: onInvalidated,
    });

    const oldReq = client.getMe();
    await oldMeStarted;

    await client.logout({ refresh_token: "rsr_session_a" });
    await clearAuthSession();
    const loginRes = await client.login({
      email: "userb@example.com",
      password: "SessionBStrong#2026",
    });
    await saveAuthSession(loginRes.data.tokens!);

    resolveOldMe(
      new Response(
        JSON.stringify({
          error: {
            code: "AUTH_INVALID_CREDENTIALS",
            message: "Old Session A rejected after logout/login",
            field_errors: {},
            details: {},
            request_id: "r-old-401",
          },
        }),
        { status: 401 },
      ),
    );

    await expect(oldReq).rejects.toMatchObject({ status: 401 });
    expect(refreshCount).toBe(0);
    expect(onInvalidated).not.toHaveBeenCalled();

    const stored = await getStoredAuthSession();
    expect(stored?.accessToken).toBe("jwt-session-b");
    expect(stored?.refreshToken).toBe("rsr_session_b");
    expect(((await client.getMe()).data as { id: string }).id).toBe("user-b");
  });

  it("never clears Session B or triggers onSessionInvalidated when direct Session A refreshSession fails afterwards", async () => {
    for (const replaceViaLogin of [true, false]) {
      backingMap.clear();
      await saveAuthSession({
        access_token: "jwt-a",
        refresh_token: "rsr_a",
        expires_in_seconds: 900,
      });

      let notifyDirectRefreshStarted!: () => void;
      const directRefreshStarted = new Promise<void>((resolve) => {
        notifyDirectRefreshStarted = resolve;
      });
      let resolveDirectRefresh!: (res: Response) => void;
      const directRefreshGate = new Promise<Response>((resolve) => {
        resolveDirectRefresh = resolve;
      });

      const onInvalidated = vi.fn();
      const fetchMock = vi.fn<FetchLike>(async (url) => {
        const target = url.toString();
        if (target.endsWith("/api/v1/auth/login")) {
          return new Response(
            JSON.stringify({
              data: {
                user: { id: "user-b" },
                platform: "android",
                session_id: "sess-b",
                expires_in_seconds: 900,
                tokens: {
                  access_token: "jwt-b",
                  refresh_token: "rsr_b",
                  token_type: "Bearer",
                  expires_in_seconds: 900,
                },
              },
              meta: { request_id: "r-login" },
            }),
            { status: 200 },
          );
        }
        if (target.endsWith("/api/v1/auth/refresh")) {
          notifyDirectRefreshStarted();
          return directRefreshGate;
        }
        return new Response(JSON.stringify({ data: { id: "user-b" } }), { status: 200 });
      });

      const client = createAndroidApiClient({
        baseOrigin: "http://localhost:8000",
        fetchImpl: fetchMock,
        onSessionInvalidated: onInvalidated,
      });

      const staleDirectRefresh = client.refreshSession({ refresh_token: "rsr_a" });
      await directRefreshStarted;

      if (replaceViaLogin) {
        const loginRes = await client.login({
          email: "b@example.com",
          password: "SessionBStrong#2026",
        });
        await saveAuthSession(loginRes.data.tokens!);
      } else {
        await saveAuthSession({
          access_token: "jwt-b",
          refresh_token: "rsr_b",
          expires_in_seconds: 900,
        });
      }

      resolveDirectRefresh(
        new Response(
          JSON.stringify({
            error: {
              code: "AUTH_REFRESH_REUSE_DETECTED",
              message: "Old refresh session revoked",
              field_errors: {},
              details: {},
              request_id: "r-stale-direct",
            },
          }),
          { status: 401 },
        ),
      );

      await expect(staleDirectRefresh).rejects.toMatchObject({
        code: "AUTH_REFRESH_REUSE_DETECTED",
        status: 401,
      });
      expect(onInvalidated).not.toHaveBeenCalled();

      const stored = await getStoredAuthSession();
      expect(stored?.accessToken).toBe("jwt-b");
      expect(stored?.refreshToken).toBe("rsr_b");
    }
  });
});

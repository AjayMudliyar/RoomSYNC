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

    const res = await client.request<{ status: string }>("/api/v1/test/", {
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

  it("uses single-flight refresh lock for concurrent Android 401 responses", async () => {
    let token = "stale-token";
    const refreshMock = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 10));
      token = "fresh-token";
      return token;
    });

    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      const headers = init?.headers as Headers;
      if (headers.get("Authorization") === "Bearer stale-token") {
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTH_REQUIRED",
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
      getAccessToken: () => token,
      refreshAccessToken: refreshMock,
    });

    const [r1, r2] = await Promise.all([client.getHealthReady(), client.getHealthReady()]);
    expect(r1).toEqual({ status: "ok" });
    expect(r2).toEqual({ status: "ok" });
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(RoomSyncApiError).toBeDefined();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RoomSyncApiClient } from "@roomsync/api-client";
import { App } from "../src/App";

describe("RoomSync Web M0 Shell", () => {
  it("renders Warm Tech Harmony core promise and live backend status", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: { service: "roomsync-backend", status: "ok", api_version: "v1" },
          meta: { request_id: "web-req-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "web",
      fetchImpl: fetchMock,
    });

    render(<App apiClient={client} />);

    expect(
      screen.getByRole("heading", { name: /Find your people before finding your place\./i }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("roomsync-backend")).toBeInTheDocument();
      expect(screen.getByText("roomsync-rule-v1")).toBeInTheDocument();
    });
  });

  it("renders explicit error state without fake data when backend is unreachable", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockRejectedValue(new Error("ECONNREFUSED"));
    const client = new RoomSyncApiClient({
      baseOrigin: "http://localhost:8000",
      platform: "web",
      fetchImpl: fetchMock,
    });

    render(<App apiClient={client} />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/unreachable/i);
    });
  });
});

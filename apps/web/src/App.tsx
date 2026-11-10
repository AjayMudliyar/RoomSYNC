import { useMemo } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { RoomSyncApiClient, RoomSyncApiError } from "@roomsync/api-client";
import { MATCHING_BASELINE } from "@roomsync/contracts";

function resolveApiOrigin(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (!configured) {
    return "http://localhost:8000";
  }
  return configured.replace(/\/api\/v1\/?$/, "");
}

function FoundationShell({ client }: { client: RoomSyncApiClient }) {
  const statusQuery = useQuery({
    queryKey: ["system-status"],
    queryFn: () => client.getSystemStatus(),
    retry: false,
  });

  const weightEntries = useMemo(
    () =>
      Object.entries(MATCHING_BASELINE.weights).map(([key, weight]) => ({
        key,
        label: key.replaceAll("_", " "),
        weight,
      })),
    [],
  );

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-[#e2e8f0] bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-navy text-lg font-extrabold text-white">
              R
            </span>
            <div>
              <span className="block text-base font-bold text-navy">RoomSync</span>
              <span className="block text-xs font-medium text-muted-ink">
                Warm Tech Harmony — M0 Shell
              </span>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="hidden items-center gap-2 sm:flex">
            {[
              { to: "/", label: "Discover" },
              { to: "/requests", label: "Requests" },
              { to: "/messages", label: "Messages" },
            ].map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "rounded-full px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal",
                    isActive
                      ? "bg-[#e3dfff] text-[#181445]"
                      : "text-secondary-ink hover:bg-surface-low",
                  ].join(" ")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <button
            type="button"
            onClick={() => void statusQuery.refetch()}
            className="min-h-11 rounded-xl bg-teal px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
          >
            Check API Health
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <section className="rounded-2xl border border-[#e2e8f0] bg-card p-8 shadow-[0_4px_14px_0_rgba(30,27,75,0.06)]">
          <p className="inline-flex items-center rounded-full bg-[#ecfdf5] px-3 py-1 text-[11px] font-bold tracking-[0.03em] text-teal uppercase">
            Milestone 0 Foundation Verified
          </p>
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">
            Find your people before finding your place.
          </h1>
          <p className="mt-3 max-w-2xl text-base text-secondary-ink">
            Compatibility-first roommate discovery foundation built on Django + DRF, private
            stateless FastAPI matching, PostgreSQL, Redis, MinIO, and Warm Tech Harmony WCAG 2.1 AA
            tokens.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-[#e2e8f0] bg-surface-low p-5">
              <h2 className="text-sm font-semibold text-navy">Backend Connectivity</h2>
              {statusQuery.isPending ? (
                <p className="mt-2 text-sm font-medium text-muted-ink">
                  Checking Django /api/v1/system/status/...
                </p>
              ) : statusQuery.isError ? (
                <div
                  role="alert"
                  className="mt-2 rounded-lg border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#ba1a1a]"
                >
                  {statusQuery.error instanceof RoomSyncApiError
                    ? `API responded with ${statusQuery.error.code} (${statusQuery.error.status}).`
                    : "Backend service is currently unreachable on local dev origin."}
                </div>
              ) : (
                <div className="mt-2 space-y-1 text-sm text-secondary-ink">
                  <p>
                    Service: <strong className="text-ink">{statusQuery.data.data.service}</strong>
                  </p>
                  <p>
                    Status:{" "}
                    <span className="inline-flex rounded-full bg-[#89f5e7] px-2.5 py-0.5 text-xs font-bold text-[#005049]">
                      {statusQuery.data.data.status}
                    </span>
                  </p>
                  <p className="text-xs text-muted-ink">
                    Request ID: {statusQuery.data.meta.request_id}
                  </p>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-[#e2e8f0] bg-surface-low p-5">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-navy">Matching Engine Baseline</h2>
                <span className="text-xs font-semibold tabular-nums text-teal">
                  {MATCHING_BASELINE.algorithmVersion}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-ink">
                Weights config: {MATCHING_BASELINE.weightsVersion} (Schema v
                {MATCHING_BASELINE.questionSchemaVersion})
              </p>
              <ul className="mt-3 grid grid-cols-2 gap-2 text-xs text-secondary-ink">
                {weightEntries.map((item) => (
                  <li
                    key={item.key}
                    className="flex items-center justify-between rounded-lg bg-card px-2.5 py-1.5"
                  >
                    <span className="capitalize">{item.label}</span>
                    <strong className="tabular-nums text-navy">{item.weight}%</strong>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export function App({ apiClient }: { apiClient?: RoomSyncApiClient }) {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false } },
      }),
    [],
  );

  const resolvedClient = useMemo(
    () =>
      apiClient ??
      new RoomSyncApiClient({
        baseOrigin: resolveApiOrigin(),
        platform: "web",
      }),
    [apiClient],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<FoundationShell client={resolvedClient} />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

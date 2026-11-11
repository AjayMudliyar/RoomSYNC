import * as SecureStore from "expo-secure-store";
import { RoomSyncApiClient, RoomSyncApiError, type FetchLike } from "@roomsync/api-client";
import type { AuthTokens } from "@roomsync/contracts";

export const AUTH_SESSION_STORAGE_KEY = "roomsync.android.auth.session.v1";

export interface StoredAndroidAuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAtMs: number;
}

export interface SecureStoreBackend {
  getItemAsync: (key: string) => Promise<string | null>;
  setItemAsync: (key: string, value: string) => Promise<void>;
  deleteItemAsync: (key: string) => Promise<void>;
}

export interface SessionGuardSnapshot {
  storeGeneration: number;
  expectedRefreshToken: string | null | undefined;
  clientGeneration: number;
}

export interface ConditionalSessionMutationOptions {
  store?: SecureStoreBackend;
  expectedRefreshToken?: string | null;
  expectedStoreGeneration?: number;
  isAuthorized?: () => boolean;
}

export interface ReplaceAuthSessionResult {
  updated: boolean;
  superseded: boolean;
  session: StoredAndroidAuthSession | null;
  reason: "updated" | "missing" | "token_mismatch" | "generation_mismatch" | "unauthorized";
}

export interface ClearAuthSessionIfMatchesResult {
  cleared: boolean;
  superseded: boolean;
  reason: "cleared" | "already_empty" | "token_mismatch" | "generation_mismatch" | "unauthorized";
}

interface ClientRefHolder {
  deref(): RoomSyncApiClient | undefined;
}

interface StoreRuntimeState {
  generation: number;
  hasKnownRefreshToken: boolean;
  latestRefreshToken: string | null;
  queue: Promise<void>;
  externalChangeListeners: Set<ClientRefHolder>;
}

const defaultSecureStore: SecureStoreBackend = {
  getItemAsync: (key) => SecureStore.getItemAsync(key),
  setItemAsync: (key, value) => SecureStore.setItemAsync(key, value),
  deleteItemAsync: (key) => SecureStore.deleteItemAsync(key),
};

const storeRuntimeStates = new WeakMap<SecureStoreBackend, StoreRuntimeState>();

function getStoreRuntimeState(store: SecureStoreBackend): StoreRuntimeState {
  let state = storeRuntimeStates.get(store);
  if (!state) {
    state = {
      generation: 0,
      hasKnownRefreshToken: false,
      latestRefreshToken: null,
      queue: Promise.resolve(),
      externalChangeListeners: new Set(),
    };
    storeRuntimeStates.set(store, state);
  }
  return state;
}

function makeClientRef(client: RoomSyncApiClient): ClientRefHolder {
  if (typeof WeakRef === "function") {
    return new WeakRef(client);
  }
  return { deref: () => client };
}

function registerStoreChangeListener(store: SecureStoreBackend, client: RoomSyncApiClient): void {
  const state = getStoreRuntimeState(store);
  state.externalChangeListeners.add(makeClientRef(client));
}

function notifyExternalStoreChange(state: StoreRuntimeState): void {
  for (const holder of state.externalChangeListeners) {
    const client = holder.deref();
    if (!client) {
      state.externalChangeListeners.delete(holder);
      continue;
    }
    client.resetSessionCycle();
  }
}

function enqueueStoreOp<T>(
  store: SecureStoreBackend,
  task: (state: StoreRuntimeState) => Promise<T>,
): Promise<T> {
  const state = getStoreRuntimeState(store);
  const run = state.queue.then(() => task(state));
  state.queue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

function isValidStoredSession(value: unknown): value is StoredAndroidAuthSession {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.accessToken === "string" &&
    obj.accessToken.length > 0 &&
    typeof obj.refreshToken === "string" &&
    obj.refreshToken.length > 0 &&
    typeof obj.expiresAtMs === "number" &&
    Number.isFinite(obj.expiresAtMs)
  );
}

function buildStoredSession(
  tokens: Pick<AuthTokens, "access_token" | "refresh_token" | "expires_in_seconds">,
  nowMs: number,
): StoredAndroidAuthSession {
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    expiresAtMs: nowMs + Math.max(0, tokens.expires_in_seconds) * 1000,
  };
}

async function readValidSessionUnlocked(
  store: SecureStoreBackend,
  state: StoreRuntimeState,
): Promise<StoredAndroidAuthSession | null> {
  const genAtReadStart = state.generation;
  const raw = await store.getItemAsync(AUTH_SESSION_STORAGE_KEY);
  if (!raw) {
    if (state.generation === genAtReadStart) {
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = null;
    }
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isValidStoredSession(parsed)) {
      await store.deleteItemAsync(AUTH_SESSION_STORAGE_KEY);
      if (state.generation === genAtReadStart) {
        state.hasKnownRefreshToken = true;
        state.latestRefreshToken = null;
      }
      return null;
    }
    if (state.generation === genAtReadStart) {
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = parsed.refreshToken;
    }
    return parsed;
  } catch {
    await store.deleteItemAsync(AUTH_SESSION_STORAGE_KEY);
    if (state.generation === genAtReadStart) {
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = null;
    }
    return null;
  }
}

export function getStoreSessionGeneration(store: SecureStoreBackend = defaultSecureStore): number {
  return getStoreRuntimeState(store).generation;
}

export async function saveAuthSession(
  tokens: Pick<AuthTokens, "access_token" | "refresh_token" | "expires_in_seconds">,
  store: SecureStoreBackend = defaultSecureStore,
  nowMs: number = Date.now(),
): Promise<StoredAndroidAuthSession> {
  const state = getStoreRuntimeState(store);
  // Advance generation synchronously before async SecureStore I/O so in-flight refreshes
  // from an older session see the new session immediately and abort conditional writes.
  state.generation += 1;
  const writeGeneration = state.generation;
  state.hasKnownRefreshToken = true;
  state.latestRefreshToken = tokens.refresh_token;
  notifyExternalStoreChange(state);

  const session = buildStoredSession(tokens, nowMs);
  await enqueueStoreOp(store, async () => {
    await store.setItemAsync(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
    if (state.generation === writeGeneration) {
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = session.refreshToken;
    }
  });
  return session;
}

export async function clearAuthSession(
  store: SecureStoreBackend = defaultSecureStore,
): Promise<void> {
  const state = getStoreRuntimeState(store);
  state.generation += 1;
  const clearGeneration = state.generation;
  state.hasKnownRefreshToken = true;
  state.latestRefreshToken = null;
  notifyExternalStoreChange(state);

  await enqueueStoreOp(store, async () => {
    await store.deleteItemAsync(AUTH_SESSION_STORAGE_KEY);
    if (state.generation === clearGeneration) {
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = null;
    }
  });
}

export async function replaceAuthSessionIfRefreshTokenMatches(
  tokens: Pick<AuthTokens, "access_token" | "refresh_token" | "expires_in_seconds">,
  options: ConditionalSessionMutationOptions = {},
  nowMs: number = Date.now(),
): Promise<ReplaceAuthSessionResult> {
  const store = options.store ?? defaultSecureStore;
  return enqueueStoreOp(store, async (state) => {
    if (options.isAuthorized && !options.isAuthorized()) {
      return {
        updated: false,
        superseded: true,
        session: null,
        reason: "unauthorized",
      };
    }
    if (
      options.expectedStoreGeneration !== undefined &&
      state.generation !== options.expectedStoreGeneration
    ) {
      return {
        updated: false,
        superseded: true,
        session: null,
        reason: "generation_mismatch",
      };
    }

    const current = await readValidSessionUnlocked(store, state);
    if (!current) {
      return {
        updated: false,
        superseded: true,
        session: null,
        reason: "missing",
      };
    }
    if (
      options.expectedRefreshToken !== undefined &&
      current.refreshToken !== options.expectedRefreshToken
    ) {
      return {
        updated: false,
        superseded: true,
        session: null,
        reason: "token_mismatch",
      };
    }

    const baselineGen = state.generation;
    const nextSession = buildStoredSession(tokens, nowMs);
    await store.setItemAsync(AUTH_SESSION_STORAGE_KEY, JSON.stringify(nextSession));

    // If an explicit saveAuthSession/clearAuthSession arrived during `setItemAsync`,
    // that write is already queued right behind us and has bumped `state.generation`.
    if (
      (options.expectedStoreGeneration !== undefined &&
        state.generation !== options.expectedStoreGeneration) ||
      state.generation !== baselineGen
    ) {
      return {
        updated: false,
        superseded: true,
        session: null,
        reason: "generation_mismatch",
      };
    }

    state.generation += 1;
    state.hasKnownRefreshToken = true;
    state.latestRefreshToken = nextSession.refreshToken;
    return {
      updated: true,
      superseded: false,
      session: nextSession,
      reason: "updated",
    };
  });
}

export async function clearAuthSessionIfRefreshTokenMatches(
  options: ConditionalSessionMutationOptions = {},
): Promise<ClearAuthSessionIfMatchesResult> {
  const store = options.store ?? defaultSecureStore;
  return enqueueStoreOp(store, async (state) => {
    if (options.isAuthorized && !options.isAuthorized()) {
      return {
        cleared: false,
        superseded: true,
        reason: "unauthorized",
      };
    }
    if (
      options.expectedStoreGeneration !== undefined &&
      state.generation !== options.expectedStoreGeneration
    ) {
      return {
        cleared: false,
        superseded: true,
        reason: "generation_mismatch",
      };
    }

    const current = await readValidSessionUnlocked(store, state);
    if (!current) {
      // Because expectedStoreGeneration and isAuthorized both passed, this store was
      // already emptied within this exact session cycle (e.g. refreshAccessToken null path).
      state.hasKnownRefreshToken = true;
      state.latestRefreshToken = null;
      return {
        cleared: false,
        superseded: false,
        reason: "already_empty",
      };
    }

    if (
      options.expectedRefreshToken !== undefined &&
      current.refreshToken !== options.expectedRefreshToken
    ) {
      return {
        cleared: false,
        superseded: true,
        reason: "token_mismatch",
      };
    }

    const baselineGen = state.generation;
    await store.deleteItemAsync(AUTH_SESSION_STORAGE_KEY);
    if (state.generation !== baselineGen) {
      return {
        cleared: false,
        superseded: true,
        reason: "generation_mismatch",
      };
    }

    // Keep state.generation intact when clearing within the active cycle so
    // RoomSyncApiClient's ensuing onSessionInvalidated notification does not treat its own
    // refresh-phase cleanup as an external superseding session.
    state.hasKnownRefreshToken = true;
    state.latestRefreshToken = null;
    return {
      cleared: true,
      superseded: false,
      reason: "cleared",
    };
  });
}

export async function getStoredAuthSession(
  store: SecureStoreBackend = defaultSecureStore,
): Promise<StoredAndroidAuthSession | null> {
  return enqueueStoreOp(store, (state) => readValidSessionUnlocked(store, state));
}

export async function getStoredAccessToken(
  store: SecureStoreBackend = defaultSecureStore,
): Promise<string | null> {
  const session = await getStoredAuthSession(store);
  return session?.accessToken ?? null;
}

export function isAccessTokenExpiringSoon(
  session: StoredAndroidAuthSession,
  skewSeconds = 60,
  nowMs: number = Date.now(),
): boolean {
  return session.expiresAtMs - nowMs <= skewSeconds * 1000;
}

export interface CreateAndroidApiClientOptions {
  baseOrigin: string;
  fetchImpl?: FetchLike;
  store?: SecureStoreBackend;
  onSessionInvalidated?: (error: RoomSyncApiError) => Promise<void> | void;
}

export function createAndroidApiClient(options: CreateAndroidApiClientOptions): RoomSyncApiClient {
  const store = options.store ?? defaultSecureStore;
  const state = getStoreRuntimeState(store);

  let clientRef: RoomSyncApiClient | null = null;
  const isGenerationAuthorized = (expectedClientGeneration: number): boolean =>
    clientRef !== null && clientRef.getSessionGeneration() === expectedClientGeneration;

  const captureGuardSnapshot = (explicitClientGeneration?: number): SessionGuardSnapshot => ({
    storeGeneration: state.generation,
    expectedRefreshToken: state.hasKnownRefreshToken ? state.latestRefreshToken : undefined,
    clientGeneration: explicitClientGeneration ?? clientRef?.getSessionGeneration() ?? 0,
  });

  const client = new RoomSyncApiClient({
    baseOrigin: options.baseOrigin,
    platform: "android",
    fetchImpl: options.fetchImpl,
    getAccessToken: () => getStoredAccessToken(store),
    captureSessionGuard: () => captureGuardSnapshot(),
    refreshAccessToken: async ({ generation }) => {
      const guardAtStart = captureGuardSnapshot(generation);
      const current = await getStoredAuthSession(store);
      if (
        !current ||
        !clientRef ||
        !isGenerationAuthorized(generation) ||
        state.generation !== guardAtStart.storeGeneration
      ) {
        return null;
      }

      try {
        const refreshed = await clientRef.refreshSession({
          refresh_token: current.refreshToken,
        });
        const nextTokens = refreshed.data.tokens;
        if (!nextTokens) {
          const clearRes = await clearAuthSessionIfRefreshTokenMatches({
            store,
            expectedRefreshToken: current.refreshToken,
            expectedStoreGeneration: guardAtStart.storeGeneration,
            isAuthorized: () => isGenerationAuthorized(generation),
          });
          if (clearRes.superseded && isGenerationAuthorized(generation)) {
            clientRef.resetSessionCycle();
          }
          return null;
        }
        const replaceRes = await replaceAuthSessionIfRefreshTokenMatches(nextTokens, {
          store,
          expectedRefreshToken: current.refreshToken,
          expectedStoreGeneration: guardAtStart.storeGeneration,
          isAuthorized: () => isGenerationAuthorized(generation),
        });
        if (!replaceRes.updated || !replaceRes.session) {
          if (replaceRes.superseded && isGenerationAuthorized(generation)) {
            clientRef.resetSessionCycle();
          }
          return null;
        }
        return replaceRes.session.accessToken;
      } catch (err) {
        if (err instanceof RoomSyncApiError && err.status === 401) {
          const clearRes = await clearAuthSessionIfRefreshTokenMatches({
            store,
            expectedRefreshToken: current.refreshToken,
            expectedStoreGeneration: guardAtStart.storeGeneration,
            isAuthorized: () => isGenerationAuthorized(generation),
          });
          if (clearRes.superseded && isGenerationAuthorized(generation)) {
            clientRef.resetSessionCycle();
          }
        }
        throw err;
      }
    },
    onSessionInvalidated: async (error, { generation, guardContext }) => {
      const guard = guardContext as SessionGuardSnapshot | undefined;
      if (
        !isGenerationAuthorized(generation) ||
        (guard && !isGenerationAuthorized(guard.clientGeneration))
      ) {
        return;
      }
      const clearResult = await clearAuthSessionIfRefreshTokenMatches({
        store,
        expectedRefreshToken: guard?.expectedRefreshToken,
        expectedStoreGeneration: guard?.storeGeneration,
        isAuthorized: () =>
          isGenerationAuthorized(generation) &&
          (!guard || isGenerationAuthorized(guard.clientGeneration)),
      });
      if (clearResult.superseded || !isGenerationAuthorized(generation)) {
        return;
      }
      await options.onSessionInvalidated?.(error);
    },
  });
  clientRef = client;
  registerStoreChangeListener(store, client);
  return client;
}

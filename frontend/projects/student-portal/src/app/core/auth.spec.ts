import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth';

const REFRESH_KEY = 'mm_refresh';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Minimal Storage stand-in — the runner's environment has no localStorage global. */
function memoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    key: (index: number) => [...store.keys()][index] ?? null,
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    removeItem: (key: string) => void store.delete(key),
    clear: () => store.clear(),
  };
}

describe('AuthService.tryRefresh', () => {
  let auth: AuthService;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.stubGlobal('localStorage', memoryStorage());
    localStorage.setItem(REFRESH_KEY, 'refresh-token');
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resolves false immediately when no refresh token is stored', async () => {
    localStorage.removeItem(REFRESH_KEY);
    await expect(auth.tryRefresh()).resolves.toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('stores the new access token in memory only and keeps the rotated refresh token', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { access: 'new-access', refresh: 'rotated' }));

    await expect(auth.tryRefresh()).resolves.toBe(true);

    expect(auth.accessToken).toBe('new-access');
    expect(localStorage.getItem(REFRESH_KEY)).toBe('rotated');
    // The access token must never be persisted.
    expect(localStorage.getItem('mm_access')).toBeNull();
    expect(auth.refreshRetryable()).toBe(false);
  });

  it('logs out when the refresh endpoint returns 401', async () => {
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: 'token invalid' }));

    await expect(auth.tryRefresh()).resolves.toBe(false);

    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
    expect(auth.accessToken).toBeNull();
    expect(auth.user()).toBeNull();
  });

  it('logs out when the refresh endpoint returns 403', async () => {
    fetchMock.mockResolvedValue(jsonResponse(403, { detail: 'forbidden' }));

    await expect(auth.tryRefresh()).resolves.toBe(false);

    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
  });

  it('keeps the session and flags a retryable state on 503', async () => {
    fetchMock.mockResolvedValue(jsonResponse(503, { detail: 'maintenance' }));

    await expect(auth.tryRefresh()).resolves.toBe(false);

    // NOT logged out — the refresh token survives a server-side outage.
    expect(localStorage.getItem(REFRESH_KEY)).toBe('refresh-token');
    expect(auth.refreshRetryable()).toBe(true);
  });

  it('keeps the session and flags a retryable state on network errors', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(auth.tryRefresh()).resolves.toBe(false);

    expect(localStorage.getItem(REFRESH_KEY)).toBe('refresh-token');
    expect(auth.refreshRetryable()).toBe(true);
  });

  it('clears the retryable flag after a later successful refresh', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(503, {}));
    await auth.tryRefresh();
    expect(auth.refreshRetryable()).toBe(true);

    fetchMock.mockResolvedValueOnce(jsonResponse(200, { access: 'ok' }));
    await expect(auth.tryRefresh()).resolves.toBe(true);
    expect(auth.refreshRetryable()).toBe(false);
  });

  it('shares a single in-flight refresh across concurrent callers', async () => {
    let resolveFetch!: (res: Response) => void;
    fetchMock.mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      }),
    );

    const first = auth.tryRefresh();
    const second = auth.tryRefresh();
    resolveFetch(jsonResponse(200, { access: 'shared-access' }));

    await expect(Promise.all([first, second])).resolves.toEqual([true, true]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(auth.accessToken).toBe('shared-access');
  });

  it('allows a fresh refresh attempt after the previous one settled', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { access: 'a1' }));
    await auth.tryRefresh();
    await auth.tryRefresh();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

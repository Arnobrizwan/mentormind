import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth';
import { authInterceptor } from './auth-interceptor';

const REFRESH_KEY = 'mm_refresh';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Let the interceptor's refresh promise chain (fetch -> json -> retry) settle. */
function settle(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
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

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: AuthService;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.stubGlobal('localStorage', memoryStorage());
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    vi.unstubAllGlobals();
  });

  it('passes non-API requests through untouched', async () => {
    const promise = firstValueFrom(http.get('/assets/data.json'));
    const req = httpMock.expectOne('/assets/data.json');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({ ok: true });
    await expect(promise).resolves.toEqual({ ok: true });
  });

  it('attaches the in-memory access token to API requests', async () => {
    localStorage.setItem(REFRESH_KEY, 'refresh-token');
    fetchMock.mockResolvedValue(jsonResponse(200, { access: 'access-1' }));
    await auth.tryRefresh(); // mints the in-memory access token

    const promise = firstValueFrom(http.get('/api/v1/courses/'));
    const req = httpMock.expectOne('/api/v1/courses/');
    expect(req.request.headers.get('Authorization')).toBe('Bearer access-1');
    req.flush({ results: [] });
    await promise;
  });

  it('refreshes once on 401 and retries the request with the fresh token', async () => {
    localStorage.setItem(REFRESH_KEY, 'refresh-token');
    fetchMock.mockResolvedValue(jsonResponse(200, { access: 'fresh-access' }));

    const promise = firstValueFrom(http.get('/api/v1/courses/'));
    httpMock
      .expectOne('/api/v1/courses/')
      .flush({ detail: 'expired' }, { status: 401, statusText: 'Unauthorized' });

    await settle();

    const retried = httpMock.expectOne('/api/v1/courses/');
    expect(retried.request.headers.get('Authorization')).toBe('Bearer fresh-access');
    retried.flush({ results: ['ok'] });

    await expect(promise).resolves.toEqual({ results: ['ok'] });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('deduplicates concurrent 401s into a single refresh, retrying both requests', async () => {
    localStorage.setItem(REFRESH_KEY, 'refresh-token');
    fetchMock.mockResolvedValue(jsonResponse(200, { access: 'fresh-access' }));

    const first = firstValueFrom(http.get('/api/v1/courses/'));
    const second = firstValueFrom(http.get('/api/v1/enrollments/'));

    httpMock
      .expectOne('/api/v1/courses/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    httpMock
      .expectOne('/api/v1/enrollments/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });

    await settle();

    // One shared refresh call for both 401s.
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const retriedCourses = httpMock.expectOne('/api/v1/courses/');
    const retriedEnrollments = httpMock.expectOne('/api/v1/enrollments/');
    expect(retriedCourses.request.headers.get('Authorization')).toBe('Bearer fresh-access');
    expect(retriedEnrollments.request.headers.get('Authorization')).toBe('Bearer fresh-access');
    retriedCourses.flush({ results: [] });
    retriedEnrollments.flush({ results: [] });

    await expect(first).resolves.toEqual({ results: [] });
    await expect(second).resolves.toEqual({ results: [] });
  });

  it('propagates the original 401 (no retry) when the refresh is rejected', async () => {
    localStorage.setItem(REFRESH_KEY, 'refresh-token');
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: 'refresh invalid' }));

    const promise = firstValueFrom(http.get('/api/v1/courses/'));
    httpMock
      .expectOne('/api/v1/courses/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });

    await expect(promise).rejects.toMatchObject({ status: 401 });
    // The rejected refresh logged the session out — no retried request.
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
  });

  it('does not attempt a refresh when no refresh token exists', async () => {
    const promise = firstValueFrom(http.get('/api/v1/courses/'));
    httpMock
      .expectOne('/api/v1/courses/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });

    await expect(promise).rejects.toBeInstanceOf(HttpErrorResponse);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('does not try to refresh on 401 from the token endpoints themselves', async () => {
    localStorage.setItem(REFRESH_KEY, 'refresh-token');

    const promise = firstValueFrom(http.post('/api/v1/auth/token/', {}));
    httpMock
      .expectOne('/api/v1/auth/token/')
      .flush({}, { status: 401, statusText: 'Unauthorized' });

    await expect(promise).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

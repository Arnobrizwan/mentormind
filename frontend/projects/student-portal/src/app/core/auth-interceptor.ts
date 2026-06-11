import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, switchMap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { API_BASE_URL } from './api-base-url';
import { AuthService } from './auth';

const TOKEN_URLS = ['/api/v1/auth/token/', '/api/v1/auth/register/'];

function withBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * Attaches the JWT to API calls and transparently retries once after a
 * refresh on 401. Also prepends API_BASE_URL to relative /api requests so
 * the same code works from native (Capacitor) origins — on the web the base
 * is '' and requests stay same-origin relative.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const baseUrl = inject(API_BASE_URL);

  const isApi = req.url.startsWith('/api/');
  const isTokenEndpoint = TOKEN_URLS.some((url) => req.url.startsWith(url));

  const target = isApi && baseUrl ? req.clone({ url: `${baseUrl}${req.url}` }) : req;
  const token = auth.accessToken;
  const outgoing = isApi && !isTokenEndpoint && token ? withBearer(target, token) : target;

  return next(outgoing).pipe(
    catchError((err: unknown) => {
      const is401 =
        err instanceof HttpErrorResponse && err.status === 401 && isApi && !isTokenEndpoint;
      if (!is401 || !auth.refreshToken) {
        return throwError(() => err);
      }
      return from(auth.tryRefresh()).pipe(
        switchMap((refreshed) => {
          const fresh = auth.accessToken;
          if (!refreshed || !fresh) {
            return throwError(() => err);
          }
          return next(withBearer(target, fresh));
        }),
      );
    }),
  );
};

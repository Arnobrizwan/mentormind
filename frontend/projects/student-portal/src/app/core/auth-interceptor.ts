import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, switchMap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthService } from './auth';

const TOKEN_URLS = ['/api/v1/auth/token/', '/api/v1/auth/register/'];

function withBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/** Attaches the JWT to API calls and transparently retries once after a refresh on 401. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  const isApi = req.url.startsWith('/api/');
  const isTokenEndpoint = TOKEN_URLS.some((url) => req.url.startsWith(url));
  const token = auth.accessToken;

  const outgoing = isApi && !isTokenEndpoint && token ? withBearer(req, token) : req;

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
          return next(withBearer(req, fresh));
        }),
      );
    }),
  );
};

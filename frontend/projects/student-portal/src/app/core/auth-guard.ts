import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth';

/**
 * Requires a signed-in user. Waits for the boot-time session restore to
 * finish (restore() runs without blocking public routes) before deciding.
 */
export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.whenReady();
  return auth.isLoggedIn()
    ? true
    : router.createUrlTree(['/auth'], { queryParams: { next: state.url } });
};

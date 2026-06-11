import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth';

/**
 * Requires a staff account — not just any signed-in user. Waits for the
 * boot-time session restore to finish before deciding. Signed-in users
 * without staff rights land on /auth with an access-denied notice instead
 * of the console.
 */
export const staffGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.whenReady();
  if (auth.isStaff()) return true;
  return router.createUrlTree(['/auth'], {
    queryParams: auth.isLoggedIn() ? { denied: '1' } : { next: state.url },
  });
};

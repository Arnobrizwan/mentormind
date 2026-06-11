import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth';

/**
 * Requires an instructor (or staff) account — not just any signed-in user.
 * Waits for the boot-time session restore to finish before deciding.
 * Signed-in users without the instructor role land on /auth with an
 * access-denied notice instead of the protected page.
 */
export const instructorGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.whenReady();
  if (auth.isInstructor()) return true;
  return router.createUrlTree(['/auth'], {
    queryParams: auth.isLoggedIn() ? { denied: '1' } : { next: state.url },
  });
};

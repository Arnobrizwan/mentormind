import { HttpInterceptorFn } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { finalize } from 'rxjs/operators';

/** How long an API call may run before we assume the free-tier server is
 * cold-starting and tell the visitor to hang on. */
const SLOW_AFTER_MS = 4000;

/**
 * Tracks in-flight API requests and flips `waking` when any of them runs
 * long — the demo API sleeps on the free tier and takes ~a minute to wake,
 * which otherwise looks like a broken site.
 */
@Injectable({ providedIn: 'root' })
export class SlowApiService {
  readonly waking = signal(false);

  private pending = 0;
  private slow = 0;
  private timers = new Set<ReturnType<typeof setTimeout>>();

  started(): () => void {
    this.pending += 1;
    let counted = false;
    const timer = setTimeout(() => {
      counted = true;
      this.slow += 1;
      this.waking.set(true);
    }, SLOW_AFTER_MS);
    this.timers.add(timer);

    return () => {
      clearTimeout(timer);
      this.timers.delete(timer);
      this.pending -= 1;
      if (counted) {
        this.slow -= 1;
      }
      if (this.slow <= 0) {
        this.slow = 0;
        this.waking.set(false);
      }
    };
  }
}

/** Flags long-running API calls so the shell can show the wake-up notice. */
export const slowApiInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.includes('/api/')) {
    return next(req);
  }
  const done = inject(SlowApiService).started();
  return next(req).pipe(finalize(done));
};

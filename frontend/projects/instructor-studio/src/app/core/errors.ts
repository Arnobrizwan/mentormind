import { HttpErrorResponse } from '@angular/common/http';

/** Pull the most useful human-readable message out of a DRF error payload. */
export function apiErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpErrorResponse) {
    const payload = err.error as Record<string, unknown> | string | null;
    if (payload && typeof payload === 'object') {
      if (typeof payload['detail'] === 'string') return payload['detail'];
      if (typeof payload['error'] === 'string') return payload['error'];
      const first = Object.values(payload)[0];
      if (Array.isArray(first) && first.length > 0) return String(first[0]);
      if (typeof first === 'string') return first;
    }
  }
  return fallback;
}

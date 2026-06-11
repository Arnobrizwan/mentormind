import { InjectionToken } from '@angular/core';

/**
 * Base URL prepended to relative `/api/...` requests by the auth interceptor
 * (and by AuthService's direct fetch to the token-refresh endpoint).
 *
 * Defaults to '' so web builds keep using same-origin relative URLs and the
 * dev-server proxy. Native (Capacitor) builds load from the
 * capacitor://localhost origin, where relative /api calls cannot reach the
 * backend — those apps pass `apiBaseUrlWindowKey` to provideMmCore() (see
 * config.ts), which overrides this token from a window-level property set
 * before the Angular app boots.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => '',
});

/**
 * Reads the window property named by `key` (e.g. 'MM_API_BASE_URL'),
 * falling back to '' (same-origin web) when unset or not a string.
 */
export function apiBaseUrlFromWindow(key: string): string {
  if (typeof window === 'undefined') return '';
  const value = (window as unknown as Record<string, unknown>)[key];
  return typeof value === 'string' ? value : '';
}

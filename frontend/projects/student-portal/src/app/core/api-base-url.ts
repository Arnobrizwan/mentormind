import { InjectionToken } from '@angular/core';

declare global {
  interface Window {
    /** Optional runtime override of the API origin (used by native builds). */
    MM_API_BASE_URL?: string;
  }
}

/**
 * Base URL prepended to relative `/api/...` requests by the auth interceptor
 * (and by AuthService's direct fetch to the token-refresh endpoint).
 *
 * Defaults to '' so the web build keeps using same-origin relative URLs and
 * the dev-server proxy. Native (Capacitor) builds load from the
 * capacitor://localhost origin, where relative /api calls cannot reach the
 * backend — override by setting `window.MM_API_BASE_URL = 'https://api.host'`
 * in a small script tag in index.html (or injected by the native shell)
 * before the Angular app boots. See also capacitor.config.ts.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: apiBaseUrlFromWindow,
});

/** Reads the window-level override, falling back to '' (same-origin web). */
export function apiBaseUrlFromWindow(): string {
  return (typeof window !== 'undefined' && window.MM_API_BASE_URL) || '';
}

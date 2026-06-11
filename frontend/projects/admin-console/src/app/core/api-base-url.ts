import { InjectionToken } from '@angular/core';

/**
 * Base URL prepended to relative `/api/...` requests by the auth interceptor
 * (and by AuthService's direct fetch to the token-refresh endpoint).
 *
 * Defaults to '' so the web build keeps using same-origin relative URLs and
 * the dev-server proxy. Override the provider in app.config.ts to point at
 * a real API host when serving from a non-web origin.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => '',
});

import { EnvironmentProviders, InjectionToken, makeEnvironmentProviders } from '@angular/core';

import { API_BASE_URL, apiBaseUrlFromWindow } from './api-base-url';

/**
 * Per-app knobs for the shared core. Everything else (token handling,
 * refresh dedup, retry semantics, guards, interceptor) is identical across
 * the three MentorMinds apps and lives in this library exactly once.
 */
export interface MmCoreConfig {
  /** localStorage key the refresh token persists under (e.g. 'mm_refresh'). */
  refreshTokenKey: string;
  /**
   * The access token used to be persisted under this key — it is removed on
   * boot/logout as cleanup (e.g. 'mm_access').
   */
  legacyAccessTokenKey: string;
  /** App name appended to document.title after SiteConfig.load() (e.g. 'Student Portal'). */
  appTitle: string;
  /**
   * Optional window property checked at injection time for a runtime API
   * origin override (e.g. 'MM_API_BASE_URL'). Used by native (Capacitor)
   * builds where relative /api calls cannot reach the backend. When omitted,
   * API_BASE_URL stays '' and requests remain same-origin relative.
   */
  apiBaseUrlWindowKey?: string;
}

export const MM_CORE_CONFIG = new InjectionToken<MmCoreConfig>('MM_CORE_CONFIG');

/**
 * Registers the shared-core configuration and the API_BASE_URL provider for
 * an app. Add to the root providers of app.config.ts (and to TestBed
 * providers in specs that exercise AuthService / SiteConfig).
 */
export function provideMmCore(config: MmCoreConfig): EnvironmentProviders {
  return makeEnvironmentProviders([
    { provide: MM_CORE_CONFIG, useValue: config },
    {
      provide: API_BASE_URL,
      useFactory: () =>
        config.apiBaseUrlWindowKey ? apiBaseUrlFromWindow(config.apiBaseUrlWindowKey) : '',
    },
  ]);
}

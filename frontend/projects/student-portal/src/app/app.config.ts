import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';
import { API_BASE_URL, apiBaseUrlFromWindow } from './core/api-base-url';
import { AuthService } from './core/auth';
import { authInterceptor } from './core/auth-interceptor';
import { slowApiInterceptor } from './core/slow-api';
import { SiteConfig } from './core/site-config';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withInMemoryScrolling({ scrollPositionRestoration: 'top' })),
    provideHttpClient(withInterceptors([authInterceptor, slowApiInterceptor])),
    // API origin for native (Capacitor) builds. '' on the web keeps requests
    // same-origin relative; a native shell sets window.MM_API_BASE_URL (e.g.
    // via a script tag in index.html) before boot to point at the real host.
    { provide: API_BASE_URL, useFactory: apiBaseUrlFromWindow },
    // Kick off the JWT session restore WITHOUT blocking the first render —
    // public routes (catalog) paint immediately; auth guards await
    // AuthService.whenReady() before deciding.
    provideAppInitializer(() => {
      void inject(AuthService).restore();
    }),
    // Bootstrap branding + flags from the settings engine (dynamic-first).
    provideAppInitializer(() => inject(SiteConfig).load()),
  ],
};

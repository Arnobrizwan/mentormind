import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { API_BASE_URL } from './core/api-base-url';
import { AuthService } from './core/auth';
import { authInterceptor } from './core/auth-interceptor';
import { SiteConfig } from './core/site-config';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    // API origin override point — '' keeps requests same-origin relative.
    { provide: API_BASE_URL, useValue: '' },
    // Kick off the JWT session restore WITHOUT blocking the first render —
    // auth guards await AuthService.whenReady() before deciding.
    provideAppInitializer(() => {
      void inject(AuthService).restore();
    }),
    provideAppInitializer(() => inject(SiteConfig).load()),
  ],
};

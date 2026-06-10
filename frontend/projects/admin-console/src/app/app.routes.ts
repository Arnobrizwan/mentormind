import { Routes } from '@angular/router';

import { staffGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    canActivate: [staffGuard],
    loadComponent: () => import('./pages/console').then((m) => m.ConsolePage),
  },
  {
    path: 'auth',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  { path: '**', redirectTo: '' },
];

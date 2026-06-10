import { Routes } from '@angular/router';

import { instructorGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    canActivate: [instructorGuard],
    loadComponent: () => import('./pages/dashboard').then((m) => m.DashboardPage),
  },
  {
    path: 'auth',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  {
    path: 'courses/:slug',
    canActivate: [instructorGuard],
    loadComponent: () => import('./pages/workbench').then((m) => m.WorkbenchPage),
  },
  { path: '**', redirectTo: '' },
];

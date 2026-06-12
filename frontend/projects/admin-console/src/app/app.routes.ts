import { Routes } from '@angular/router';

import { staffGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Console · MentorMinds Admin',
    canActivate: [staffGuard],
    loadComponent: () => import('./pages/console').then((m) => m.ConsolePage),
  },
  {
    path: 'system',
    title: 'System Status · MentorMinds Admin',
    canActivate: [staffGuard],
    loadComponent: () => import('./pages/system').then((m) => m.SystemPage),
  },
  {
    path: 'auth',
    title: 'Operator Login · MentorMinds Admin',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  { path: '**', redirectTo: '' },
];

import { Routes } from '@angular/router';

import { instructorGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Dashboard · MentorMinds Studio',
    canActivate: [instructorGuard],
    loadComponent: () => import('./pages/dashboard').then((m) => m.DashboardPage),
  },
  {
    path: 'auth',
    title: 'Sign In · MentorMinds Studio',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  {
    path: 'courses/:slug',
    title: 'Course Workbench · MentorMinds Studio',
    canActivate: [instructorGuard],
    loadComponent: () => import('./pages/workbench').then((m) => m.WorkbenchPage),
  },
  { path: '**', redirectTo: '' },
];

import { Routes } from '@angular/router';

import { authGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/catalog').then((m) => m.CatalogPage),
  },
  {
    path: 'auth',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/dashboard').then((m) => m.DashboardPage),
  },
  {
    path: 'courses/:slug',
    loadComponent: () => import('./pages/course-detail').then((m) => m.CourseDetailPage),
  },
  {
    path: 'courses/:slug/lessons/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/lesson').then((m) => m.LessonPage),
  },
  {
    path: 'courses/:slug/quiz/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/quiz').then((m) => m.QuizPage),
  },
  { path: '**', redirectTo: '' },
];

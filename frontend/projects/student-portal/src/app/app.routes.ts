import { Routes } from '@angular/router';

import { authGuard } from './core/auth-guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Course Catalog · MentorMinds',
    loadComponent: () => import('./pages/catalog').then((m) => m.CatalogPage),
  },
  {
    path: 'auth',
    title: 'Sign In · MentorMinds',
    loadComponent: () => import('./pages/auth-page').then((m) => m.AuthPage),
  },
  {
    path: 'dashboard',
    title: 'Dashboard · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/dashboard').then((m) => m.DashboardPage),
  },
  {
    path: 'tutor',
    title: 'AI Tutor · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/tutor').then((m) => m.TutorPage),
  },
  {
    path: 'revision',
    title: 'Revision · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/revision').then((m) => m.RevisionPage),
  },
  {
    path: 'planner',
    title: 'Study Plan · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/planner').then((m) => m.PlannerPage),
  },
  {
    path: 'profile',
    title: 'Profile · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/profile').then((m) => m.ProfilePage),
  },
  {
    path: 'notifications',
    title: 'Notifications · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/notifications').then((m) => m.NotificationsPage),
  },
  {
    path: 'courses/:slug',
    title: 'Course · MentorMinds',
    loadComponent: () => import('./pages/course-detail').then((m) => m.CourseDetailPage),
  },
  {
    path: 'courses/:slug/lessons/:id',
    title: 'Lesson · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/lesson').then((m) => m.LessonPage),
  },
  {
    path: 'courses/:slug/quiz/:id',
    title: 'Quiz · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/quiz').then((m) => m.QuizPage),
  },
  {
    path: 'courses/:slug/practice',
    title: 'Practice · MentorMinds',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/short-answers').then((m) => m.ShortAnswersPage),
  },
  { path: '**', redirectTo: '' },
];

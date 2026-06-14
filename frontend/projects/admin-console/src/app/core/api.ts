import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface FeatureFlag {
  id: number;
  key: string;
  enabled: boolean;
  description: string;
  updated_at: string;
}

export interface SiteSetting {
  id: number;
  key: string;
  value: unknown;
  is_public: boolean;
  description: string;
  updated_at: string;
}

export interface Badge {
  id: number;
  key: string;
  name: string;
  description: string;
  icon: string;
  rule: string;
  threshold: number;
  order: number;
  rule_choices: { value: string; label: string }[];
}

export interface LeaderboardRow {
  rank: number;
  student: string;
  points: number;
}

/** Mirror of Badge.Rule on the backend — the counting rules are code,
 * only their thresholds/labels are data. */
export const BADGE_RULES: { value: string; label: string }[] = [
  { value: 'points_total', label: 'Total points' },
  { value: 'quizzes_taken', label: 'Quizzes taken' },
  { value: 'perfect_quizzes', label: 'Perfect quiz scores' },
  { value: 'lessons_completed', label: 'Lessons completed' },
  { value: 'streak_days', label: 'Day streak' },
  { value: 'enrollments', label: 'Courses enrolled' },
  { value: 'chat_messages', label: 'Chat messages sent' },
  { value: 'tutor_questions', label: 'AI tutor questions asked' },
];

export interface ComponentStatus {
  status: string;
  detail?: string;
  latency_ms?: number;
}

export interface SystemStatus {
  instance: string;
  healthy: boolean;
  components: Record<string, ComponentStatus>;
}

export interface AdminStats {
  users_total: number;
  premium_users: number;
  courses_total: number;
  courses_published: number;
  enrollments_total: number;
  quiz_attempts_today: number;
  tutor_sessions_today: number;
  points_awarded_today: number;
}

@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);

  system(): Promise<SystemStatus> {
    return firstValueFrom(this.http.get<SystemStatus>('/api/v1/system/'));
  }

  flags(): Promise<FeatureFlag[]> {
    return firstValueFrom(this.http.get<FeatureFlag[]>('/api/v1/flags/manage/'));
  }

  createFlag(data: Partial<FeatureFlag>): Promise<FeatureFlag> {
    return firstValueFrom(this.http.post<FeatureFlag>('/api/v1/flags/manage/', data));
  }

  updateFlag(id: number, data: Partial<FeatureFlag>): Promise<FeatureFlag> {
    return firstValueFrom(this.http.patch<FeatureFlag>(`/api/v1/flags/manage/${id}/`, data));
  }

  deleteFlag(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/flags/manage/${id}/`));
  }

  settings(): Promise<SiteSetting[]> {
    return firstValueFrom(this.http.get<SiteSetting[]>('/api/v1/settings/manage/'));
  }

  createSetting(data: Partial<SiteSetting>): Promise<SiteSetting> {
    return firstValueFrom(this.http.post<SiteSetting>('/api/v1/settings/manage/', data));
  }

  updateSetting(id: number, data: Partial<SiteSetting>): Promise<SiteSetting> {
    return firstValueFrom(
      this.http.patch<SiteSetting>(`/api/v1/settings/manage/${id}/`, data),
    );
  }

  deleteSetting(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/settings/manage/${id}/`));
  }

  badges(): Promise<Badge[]> {
    // Tolerate either a bare array or a DRF-paginated {results} body — a
    // non-array here would throw inside the page's @for and blank the console.
    return firstValueFrom(
      this.http.get<Badge[] | { results: Badge[] }>('/api/v1/engagement/badges/manage/'),
    ).then((b) => (Array.isArray(b) ? b : (b?.results ?? [])));
  }

  createBadge(data: Partial<Badge>): Promise<Badge> {
    return firstValueFrom(this.http.post<Badge>('/api/v1/engagement/badges/manage/', data));
  }

  updateBadge(id: number, data: Partial<Badge>): Promise<Badge> {
    return firstValueFrom(
      this.http.patch<Badge>(`/api/v1/engagement/badges/manage/${id}/`, data),
    );
  }

  deleteBadge(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/engagement/badges/manage/${id}/`));
  }

  leaderboard(): Promise<LeaderboardRow[]> {
    return firstValueFrom(this.http.get<LeaderboardRow[]>('/api/v1/engagement/leaderboard/'));
  }

  stats(): Promise<AdminStats> {
    return firstValueFrom(this.http.get<AdminStats>('/api/v1/admin/stats/'));
  }
}

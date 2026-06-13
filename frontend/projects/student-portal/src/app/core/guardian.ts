import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { WeakTopic } from './practice-insights';

export interface GuardianLink {
  token: string;
  created_at: string;
  /** Frontend route for the public page, e.g. /guardian/<token>. */
  path: string;
}

export interface GuardianCourse {
  course_title: string;
  readiness: number;
  predicted_grade: string;
  components: {
    progress_pct: number;
    quiz_avg: number;
    practice_volume: number;
    accuracy: number;
  };
}

export interface GuardianRecentQuiz {
  quiz: string;
  course: string;
  score: number;
  completed_at: string;
}

export interface GuardianSummary {
  student_name: string;
  generated_at: string;
  points_week: number;
  streak: number;
  weak_topics: WeakTopic[];
  courses: GuardianCourse[];
  recent_quizzes: GuardianRecentQuiz[];
}

@Injectable({ providedIn: 'root' })
export class GuardianApi {
  private readonly http = inject(HttpClient);

  link(): Promise<{ link: GuardianLink | null }> {
    return firstValueFrom(
      this.http.get<{ link: GuardianLink | null }>('/api/v1/engagement/guardian/link/'),
    );
  }

  create(): Promise<{ link: GuardianLink }> {
    return firstValueFrom(
      this.http.post<{ link: GuardianLink }>('/api/v1/engagement/guardian/link/', {}),
    );
  }

  revoke(): Promise<void> {
    return firstValueFrom(this.http.delete<void>('/api/v1/engagement/guardian/link/'));
  }

  /** Public — readable with only the token, no auth header needed. */
  summary(token: string): Promise<GuardianSummary> {
    return firstValueFrom(
      this.http.get<GuardianSummary>(
        `/api/v1/engagement/guardian/summary/${encodeURIComponent(token)}/`,
      ),
    );
  }
}

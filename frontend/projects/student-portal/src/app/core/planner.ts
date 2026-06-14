import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom, retry, timer } from 'rxjs';

/** Same idempotent-GET retry policy as the other read-mostly services. */
const GET_RETRY = {
  count: 2,
  delay: (error: unknown) => {
    const status = error instanceof HttpErrorResponse ? error.status : 0;
    if (status >= 400 && status < 500) throw error;
    return timer(400);
  },
};

export type PlanItemKind = 'revision' | 'practice' | 'lesson' | 'quiz';

export interface PlanItem {
  id: number;
  kind: PlanItemKind;
  title: string;
  detail: string;
  link: string;
  done: boolean;
}

export interface WeekPlan {
  id: number;
  week_start: string;
  items: PlanItem[];
  completion_pct: number;
  generated_at: string;
}

export interface StudyInsight {
  insight: string;
  weak_topics: { topic: string; accuracy: number; samples: number }[];
  due_cards: number;
  source: 'model' | 'fallback';
}

@Injectable({ providedIn: 'root' })
export class PlannerApi {
  private readonly http = inject(HttpClient);

  week(): Promise<WeekPlan> {
    return firstValueFrom(
      this.http.get<WeekPlan>('/api/v1/planner/week/').pipe(retry(GET_RETRY)),
    );
  }

  rebuild(): Promise<WeekPlan> {
    return firstValueFrom(this.http.post<WeekPlan>('/api/v1/planner/week/', {}));
  }

  /** One-paragraph "what to focus on this week" suggestion. */
  insight(): Promise<StudyInsight> {
    return firstValueFrom(
      this.http.get<StudyInsight>('/api/v1/planner/insight/').pipe(retry(GET_RETRY)),
    );
  }

  toggle(itemId: number): Promise<WeekPlan> {
    return firstValueFrom(this.http.post<WeekPlan>(`/api/v1/planner/items/${itemId}/toggle/`, {}));
  }

  /** This week's plan as an iCalendar blob (import into Google/Apple/Outlook). */
  exportIcs(): Promise<Blob> {
    return firstValueFrom(
      this.http.get('/api/v1/planner/week.ics', { responseType: 'blob' }),
    );
  }
}

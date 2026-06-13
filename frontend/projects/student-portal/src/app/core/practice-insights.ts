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

export interface WeakTopic {
  topic: string;
  accuracy: number;
  samples: number;
}

export interface RecommendedItem {
  type: 'quiz' | 'short_answer';
  id: number;
  quiz_id?: number;
  course_slug: string;
  title: string;
  preview: string;
  topic: string;
}

export interface PracticeRecommendations {
  topics: WeakTopic[];
  recommended: RecommendedItem[];
}

export interface ReadinessComponents {
  progress_pct: number;
  quiz_avg: number;
  practice_volume: number;
  accuracy: number;
}

export interface CourseReadiness {
  course: number;
  course_slug: string;
  course_title: string;
  readiness: number;
  /** Cambridge band (A*–U) projected from the readiness blend. */
  predicted_grade: string;
  components: ReadinessComponents;
}

@Injectable({ providedIn: 'root' })
export class PracticeInsightsApi {
  private readonly http = inject(HttpClient);

  recommendations(): Promise<PracticeRecommendations> {
    return firstValueFrom(
      this.http
        .get<PracticeRecommendations>('/api/v1/practice/recommendations/')
        .pipe(retry(GET_RETRY)),
    );
  }

  readiness(): Promise<CourseReadiness[]> {
    return firstValueFrom(
      this.http.get<CourseReadiness[]>('/api/v1/practice/readiness/').pipe(retry(GET_RETRY)),
    );
  }
}

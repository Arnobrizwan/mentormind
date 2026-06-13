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

export interface RevisionCard {
  id: number;
  front: string;
  back: string;
  topic: string;
  course_title: string;
  interval_days: number;
  repetitions: number;
  due_at: string;
}

export interface RevisionQueue {
  due_count: number;
  cards: RevisionCard[];
}

export interface ReviewResult {
  id: number;
  due_at: string;
  interval_days: number;
  repetitions: number;
  ease_factor: number;
}

@Injectable({ providedIn: 'root' })
export class RevisionApi {
  private readonly http = inject(HttpClient);

  queue(): Promise<RevisionQueue> {
    return firstValueFrom(
      this.http.get<RevisionQueue>('/api/v1/revision/queue/').pipe(retry(GET_RETRY)),
    );
  }

  review(cardId: number, grade: number): Promise<ReviewResult> {
    return firstValueFrom(
      this.http.post<ReviewResult>('/api/v1/revision/review/', { card: cardId, grade }),
    );
  }

  /** The student's whole deck as an Anki-importable CSV blob. */
  exportCsv(): Promise<Blob> {
    return firstValueFrom(
      this.http.get('/api/v1/revision/export.csv', { responseType: 'blob' }),
    );
  }
}

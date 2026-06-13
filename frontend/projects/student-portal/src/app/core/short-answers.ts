import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom, retry, timer } from 'rxjs';

import { Paginated } from './models';

/**
 * Retry policy for idempotent GETs — absorbs transient network blips and
 * 5xx hiccups, but never retries 4xx client errors (401 is already handled
 * by the auth interceptor's refresh-and-retry).
 */
const GET_RETRY = {
  count: 2,
  delay: (error: unknown) => {
    const status = error instanceof HttpErrorResponse ? error.status : 0;
    if (status >= 400 && status < 500) throw error;
    return timer(400);
  },
};

export interface ShortAnswerQuestion {
  id: number;
  course: number;
  lesson: number | null;
  prompt: string;
  max_score: number;
  is_published: boolean;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ShortAnswerSubmission {
  id: number;
  question: number;
  enrollment: number;
  student_email: string;
  student_name: string;
  answer_text: string;
  score: number;
  max_score: number;
  criteria_met: string[];
  criteria_missing: string[];
  feedback: string;
  engine: 'llm' | 'heuristic';
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ShortAnswerApi {
  private readonly http = inject(HttpClient);

  list(courseId: number): Promise<ShortAnswerQuestion[]> {
    // page_size lifts the default page of 20 (backend caps it at 200) so
    // courses with many questions aren't silently truncated.
    return firstValueFrom(
      this.http
        .get<Paginated<ShortAnswerQuestion>>(
          `/api/v1/short-answers/?course=${courseId}&page_size=100`,
        )
        .pipe(retry(GET_RETRY)),
    ).then((page) => page.results);
  }

  submit(questionId: number, answer: string): Promise<ShortAnswerSubmission> {
    return firstValueFrom(
      this.http.post<ShortAnswerSubmission>(`/api/v1/short-answers/${questionId}/submit/`, {
        answer,
      }),
    );
  }

  submissions(questionId: number): Promise<ShortAnswerSubmission[]> {
    return firstValueFrom(
      this.http
        .get<ShortAnswerSubmission[]>(`/api/v1/short-answers/${questionId}/submissions/`)
        .pipe(retry(GET_RETRY)),
    );
  }

  /** OCR a photographed handwritten answer — returns the extracted text
   * for the student to review and correct before submitting. */
  ocr(image: File): Promise<{ text: string }> {
    const form = new FormData();
    form.append('image', image, image.name || 'answer.jpg');
    return firstValueFrom(this.http.post<{ text: string }>('/api/v1/practice/ocr/', form));
  }
}

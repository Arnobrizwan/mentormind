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

export interface TutorMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  feedback: number | null;
  created_at: string;
}

export interface TutorSession {
  id: number;
  subject: string;
  level: string;
  title: string;
  last_message?: string;
  messages?: TutorMessage[];
  updated_at: string;
}

export interface TutorQuota {
  limit: number | null;
  used: number;
  remaining: number | null;
  is_premium: boolean;
}

@Injectable({ providedIn: 'root' })
export class TutorApi {
  private readonly http = inject(HttpClient);

  listSessions(): Promise<TutorSession[]> {
    return firstValueFrom(
      this.http.get<Paginated<TutorSession>>('/api/v1/tutor/sessions/').pipe(retry(GET_RETRY)),
    ).then((page) => page.results);
  }

  getSession(id: number): Promise<TutorSession> {
    return firstValueFrom(
      this.http.get<TutorSession>(`/api/v1/tutor/sessions/${id}/`).pipe(retry(GET_RETRY)),
    );
  }

  createSession(subject: string, level: string): Promise<TutorSession> {
    return firstValueFrom(
      this.http.post<TutorSession>('/api/v1/tutor/sessions/', { subject, level }),
    );
  }

  quota(): Promise<TutorQuota> {
    return firstValueFrom(
      this.http.get<TutorQuota>('/api/v1/tutor/sessions/quota/').pipe(retry(GET_RETRY)),
    );
  }

  send(
    sessionId: number,
    content: string,
    image?: File,
  ): Promise<{ user_message: TutorMessage; assistant_message: TutorMessage; remaining: number | null }> {
    // With an attachment we post multipart FormData; the browser sets the
    // Content-Type (with boundary) itself — never set it manually.
    let body: FormData | { content: string };
    if (image) {
      const form = new FormData();
      form.append('content', content);
      form.append('image', image, image.name);
      body = form;
    } else {
      body = { content };
    }
    return firstValueFrom(
      this.http.post<{
        user_message: TutorMessage;
        assistant_message: TutorMessage;
        remaining: number | null;
      }>(`/api/v1/tutor/sessions/${sessionId}/messages/`, body),
    );
  }

  feedback(sessionId: number, messageId: number, value: 1 | -1): Promise<TutorMessage> {
    return firstValueFrom(
      this.http.post<TutorMessage>(
        `/api/v1/tutor/sessions/${sessionId}/messages/${messageId}/feedback/`,
        { value },
      ),
    );
  }

  subscribe(plan: 'monthly' | 'yearly'): Promise<unknown> {
    return firstValueFrom(this.http.post('/api/v1/auth/subscribe/', { plan }));
  }
}

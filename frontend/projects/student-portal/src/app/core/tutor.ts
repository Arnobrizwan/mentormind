import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Paginated } from './models';

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
      this.http.get<Paginated<TutorSession>>('/api/v1/tutor/sessions/'),
    ).then((page) => page.results);
  }

  getSession(id: number): Promise<TutorSession> {
    return firstValueFrom(this.http.get<TutorSession>(`/api/v1/tutor/sessions/${id}/`));
  }

  createSession(subject: string, level: string): Promise<TutorSession> {
    return firstValueFrom(
      this.http.post<TutorSession>('/api/v1/tutor/sessions/', { subject, level }),
    );
  }

  quota(): Promise<TutorQuota> {
    return firstValueFrom(this.http.get<TutorQuota>('/api/v1/tutor/sessions/quota/'));
  }

  send(
    sessionId: number,
    content: string,
  ): Promise<{ user_message: TutorMessage; assistant_message: TutorMessage; remaining: number | null }> {
    return firstValueFrom(
      this.http.post<{
        user_message: TutorMessage;
        assistant_message: TutorMessage;
        remaining: number | null;
      }>(`/api/v1/tutor/sessions/${sessionId}/messages/`, { content }),
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

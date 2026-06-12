import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { API_BASE_URL } from './api-base-url';
import { AuthService } from './auth';

export interface ChatMessage {
  id: number;
  body: string;
  created_at: string;
  sender_name?: string;
  sender?: string;
}

export interface ChatSocketMessage {
  id?: number;
  body?: string;
  created_at?: string;
  sender?: string;
  error?: string;
  detail?: string;
}

/** Build the websocket origin from the HTTP API base (or same-origin on web). */
export function websocketOrigin(apiBaseUrl: string): string {
  if (apiBaseUrl) {
    const url = new URL(apiBaseUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.origin;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }
  return '';
}

@Injectable({ providedIn: 'root' })
export class CourseChatApi {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly apiBaseUrl = inject(API_BASE_URL);

  history(slug: string): Promise<ChatMessage[]> {
    return firstValueFrom(
      this.http.get<ChatMessage[]>(`/api/v1/chat/courses/${slug}/messages/`),
    );
  }

  /** Live room socket — caller must close on destroy. */
  connect(slug: string): WebSocket | null {
    const token = this.auth.accessToken;
    if (!token) return null;
    const origin = websocketOrigin(this.apiBaseUrl);
    const url = `${origin}/ws/courses/${encodeURIComponent(slug)}/chat/`;
    return new WebSocket(url, ['jwt', token]);
  }

  displayName(message: ChatMessage): string {
    return message.sender_name || message.sender || 'Student';
  }
}

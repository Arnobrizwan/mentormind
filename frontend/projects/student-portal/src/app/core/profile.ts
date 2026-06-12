import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Paginated, User } from './models';

/** /auth/me/ returns the base user plus subscription fields. */
export interface ProfileUser extends User {
  is_premium?: boolean;
  premium_until?: string | null;
}

export interface PointsEvent {
  action: string;
  points: number;
  at: string;
}

/** Max avatar upload size enforced client-side before hitting the server. */
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024;

/** Human label for a raw engagement action key (e.g. 'lesson:12'). */
export function humanizeAction(action: string): string {
  const key = action.split(':')[0];
  switch (key) {
    case 'lesson':
      return 'Lesson completed';
    case 'revision_review':
      return 'Flashcard review';
    case 'tutor_question':
      return 'Asked the AI tutor';
    case 'daily_login':
      return 'Daily login bonus';
    case 'quiz':
    case 'quiz_attempt':
      return 'Quiz attempt';
    default: {
      const text = key.replace(/_/g, ' ').trim();
      return text ? text.charAt(0).toUpperCase() + text.slice(1) : action;
    }
  }
}

/** Compact relative timestamp — "just now", "5m ago", "3h ago", "2d ago", then a date. */
export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

@Injectable({ providedIn: 'root' })
export class ProfileApi {
  private readonly http = inject(HttpClient);

  me(): Promise<ProfileUser> {
    return firstValueFrom(this.http.get<ProfileUser>('/api/v1/auth/me/'));
  }

  updateDisplayName(displayName: string): Promise<ProfileUser> {
    return firstValueFrom(
      this.http.patch<ProfileUser>('/api/v1/auth/me/', { display_name: displayName }),
    );
  }

  /**
   * Uploads a new avatar as multipart FormData — the browser sets the
   * Content-Type (with boundary) itself. The server validates type/size.
   */
  uploadAvatar(file: File): Promise<ProfileUser> {
    const form = new FormData();
    form.append('avatar', file, file.name);
    return firstValueFrom(this.http.post<ProfileUser>('/api/v1/auth/me/avatar/', form));
  }

  history(page = 1): Promise<Paginated<PointsEvent>> {
    return firstValueFrom(
      this.http.get<Paginated<PointsEvent>>('/api/v1/engagement/history/', {
        params: { page },
      }),
    );
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Paginated } from './models';

export interface AppNotification {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

/** How many items the header dropdown keeps around. */
const LATEST_LIMIT = 8;

/**
 * Header notifications: unread badge count + the latest few items for the
 * bell dropdown. Every call is non-blocking — failures keep the last known
 * state (or empty) and never throw to the caller.
 */
@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly http = inject(HttpClient);

  /** Unread badge count — 0 hides the badge. */
  readonly unread = signal(0);

  /** Newest-first slice for the dropdown. */
  readonly latest = signal<AppNotification[]>([]);

  async refreshUnread(): Promise<void> {
    try {
      const res = await firstValueFrom(
        this.http.get<{ unread: number }>('/api/v1/notifications/unread-count/'),
      );
      this.unread.set(res.unread);
    } catch {
      // Non-blocking: keep the previous count.
    }
  }

  async refreshLatest(): Promise<void> {
    try {
      const page = await firstValueFrom(
        this.http.get<Paginated<AppNotification>>('/api/v1/notifications/'),
      );
      this.latest.set(page.results.slice(0, LATEST_LIMIT));
    } catch {
      // Non-blocking: keep the previous list.
    }
  }

  async markRead(id: number): Promise<void> {
    try {
      const updated = await firstValueFrom(
        this.http.post<AppNotification>(`/api/v1/notifications/${id}/read/`, {}),
      );
      this.latest.update((items) => items.map((n) => (n.id === updated.id ? updated : n)));
      this.unread.update((n) => Math.max(0, n - 1));
    } catch {
      // Non-blocking: the item simply stays unread.
    }
  }

  async markAllRead(): Promise<void> {
    try {
      await firstValueFrom(
        this.http.post<{ marked_read: number }>('/api/v1/notifications/read-all/', {}),
      );
      this.latest.update((items) => items.map((n) => ({ ...n, is_read: true })));
      this.unread.set(0);
    } catch {
      // Non-blocking.
    }
  }

  /** Clear state on sign-out so the next account starts fresh. */
  reset(): void {
    this.unread.set(0);
    this.latest.set([]);
  }
}

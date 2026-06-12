import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { apiErrorMessage } from '../core/errors';
import { Paginated } from '../core/models';
import { AppNotification, NotificationsService } from '../core/notifications';
import { relativeTime } from '../core/profile';

const KIND_ICONS: Record<string, string> = {
  enrollment: '🎓',
  quiz_result: '📝',
  proctoring: '🚨',
  risk: '🌱',
  system: '📣',
};

@Component({
  selector: 'mm-notifications',
  template: `
    <section class="head rise">
      <div class="head__row">
        <div>
          <p class="mono-label">Inbox</p>
          <h1>Notifications</h1>
        </div>
        @if (hasUnread()) {
          <button
            type="button"
            class="btn btn--ghost btn--small"
            (click)="markAllRead()"
            [disabled]="markingAll()"
          >
            {{ markingAll() ? 'Marking…' : 'Mark all as read' }}
          </button>
        }
      </div>
    </section>

    @if (loading() && items().length === 0) {
      <div class="skeletons" role="status" aria-label="Loading notifications">
        <div class="skeleton skeleton--row"></div>
        <div class="skeleton skeleton--row"></div>
        <div class="skeleton skeleton--row"></div>
      </div>
    } @else if (error(); as msg) {
      <p class="error-note rise" role="alert">{{ msg }}</p>
    } @else if (items().length === 0) {
      <div class="empty rise">
        <span class="empty__icon" aria-hidden="true">🔔</span>
        <h2>You're all caught up.</h2>
        <p>Course updates, quiz results, and announcements will land here.</p>
      </div>
    } @else {
      <ul class="list rise" style="animation-delay: 60ms">
        @for (item of items(); track item.id) {
          <li>
            <button
              type="button"
              class="note"
              [class.note--unread]="!item.is_read"
              (click)="open(item)"
            >
              <span class="note__icon" aria-hidden="true">{{ icon(item.kind) }}</span>
              <span class="note__body">
                <span class="note__title">
                  {{ item.title }}
                  @if (!item.is_read) {
                    <span class="note__dot" aria-hidden="true"></span>
                    <span class="visually-hidden">(unread)</span>
                  }
                </span>
                @if (item.body) {
                  <span class="note__text">{{ item.body }}</span>
                }
              </span>
              <span class="mono-label note__when">{{ when(item) }}</span>
            </button>
          </li>
        }
      </ul>

      @if (nextPage() !== null) {
        <button
          type="button"
          class="btn btn--ghost btn--small more"
          (click)="loadMore()"
          [disabled]="loading()"
        >
          {{ loading() ? 'Loading…' : 'Load more' }}
        </button>
      }
    }
  `,
  styles: `
    .head { margin-bottom: 1.8rem; }

    .head__row {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;

      h1 {
        font-size: clamp(2rem, 4.5vw, 3rem);
        margin-top: 0.7rem;
      }
    }

    .btn--small {
      padding: 0.45rem 1.05rem;
      font-size: 0.82rem;
    }

    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
      border: 0;
    }

    .list {
      list-style: none;
      margin: 0 0 1.2rem;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .note {
      display: flex;
      align-items: flex-start;
      gap: 0.9rem;
      width: 100%;
      padding: 0.9rem 1.1rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 12px;
      color: var(--ink);
      font-family: var(--font-body);
      font-size: 0.95rem;
      text-align: left;
      cursor: pointer;

      &:hover { border-color: var(--accent); }
      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    }

    .note--unread {
      border-color: color-mix(in srgb, var(--accent) 55%, var(--line));
      background: color-mix(in srgb, var(--accent) 6%, var(--card));

      .note__title { font-weight: 800; }
    }

    .note__icon {
      font-size: 1.25rem;
      line-height: 1.4;
      flex-shrink: 0;
    }

    .note__body {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }

    .note__title {
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
    }

    .note__dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      flex-shrink: 0;
    }

    .note__text {
      color: var(--ink-soft);
      font-size: 0.88rem;
    }

    .note__when {
      color: var(--ink-soft);
      white-space: nowrap;
      padding-top: 0.2rem;
    }

    .more { margin-bottom: 2rem; }

    .empty {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      align-items: flex-start;
      padding: 1.5rem 0;

      p { color: var(--ink-soft); }
    }

    .empty__icon { font-size: 2rem; }

    .skeletons {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      padding: 0.5rem 0 1.5rem;
    }

    .skeleton--row { height: 72px; }
  `,
})
export class NotificationsPage {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly service = inject(NotificationsService);

  protected readonly items = signal<AppNotification[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly markingAll = signal(false);
  protected readonly nextPage = signal<number | null>(null);

  protected readonly hasUnread = computed(
    () => this.service.unread() > 0 || this.items().some((n) => !n.is_read),
  );

  constructor() {
    void this.load(1);
    void this.service.refreshUnread();
  }

  /**
   * The shared NotificationsService only keeps a small dropdown slice, so the
   * full page reads the same paginated endpoint directly (mark-read calls
   * still go through the service to keep the header badge in sync).
   */
  private async load(page: number): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const result = await firstValueFrom(
        this.http.get<Paginated<AppNotification>>('/api/v1/notifications/', {
          params: { page },
        }),
      );
      this.items.update((all) => (page === 1 ? result.results : [...all, ...result.results]));
      this.nextPage.set(result.next ? page + 1 : null);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load your notifications.'));
    } finally {
      this.loading.set(false);
    }
  }

  protected loadMore(): void {
    const page = this.nextPage();
    if (page !== null && !this.loading()) void this.load(page);
  }

  protected icon(kind: string): string {
    return KIND_ICONS[kind] ?? '🔔';
  }

  protected when(item: AppNotification): string {
    return relativeTime(item.created_at);
  }

  protected async open(item: AppNotification): Promise<void> {
    if (!item.is_read) {
      // Optimistic local flip; the service updates the header badge.
      this.items.update((all) =>
        all.map((n) => (n.id === item.id ? { ...n, is_read: true } : n)),
      );
      await this.service.markRead(item.id);
    }
    if (item.link) {
      if (/^https?:\/\//i.test(item.link)) {
        window.open(item.link, '_blank', 'noopener');
      } else {
        void this.router.navigateByUrl(item.link);
      }
    }
  }

  protected async markAllRead(): Promise<void> {
    if (this.markingAll()) return;
    this.markingAll.set(true);
    try {
      await this.service.markAllRead();
      // The service swallows failures — only mirror locally when it stuck.
      if (this.service.unread() === 0) {
        this.items.update((all) => all.map((n) => ({ ...n, is_read: true })));
      }
    } finally {
      this.markingAll.set(false);
    }
  }
}

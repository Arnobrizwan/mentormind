import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../core/auth';
import { AppNotification, NotificationsService } from '../core/notifications';

const POLL_INTERVAL_MS = 60_000;

@Component({
  selector: 'mm-notifications-bell',
  imports: [RouterLink],
  host: {
    '(document:click)': 'onDocumentClick($event)',
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    <button
      #trigger
      type="button"
      class="bell"
      (click)="toggle()"
      [attr.aria-expanded]="open()"
      aria-haspopup="true"
      aria-controls="bell-panel"
      [attr.aria-label]="ariaLabel()"
    >
      <span class="bell__icon" aria-hidden="true">🔔</span>
      @if (notifications.unread() > 0) {
        <span class="bell__badge" aria-hidden="true">{{ badge() }}</span>
      }
    </button>

    @if (open()) {
      <div class="panel" id="bell-panel" role="region" aria-label="Notifications">
        <header class="panel__head">
          <span class="mono-label">Notifications</span>
          @if (notifications.unread() > 0) {
            <button type="button" class="panel__mark-all" (click)="markAllRead()">
              Mark all read
            </button>
          }
        </header>

        @if (notifications.latest().length === 0) {
          <p class="panel__empty">You're all caught up <span aria-hidden="true">✨</span></p>
        } @else {
          <ul class="panel__list">
            @for (item of notifications.latest(); track item.id) {
              <li>
                <button
                  type="button"
                  class="item"
                  [class.item--unread]="!item.is_read"
                  (click)="openItem(item)"
                >
                  <span class="item__row">
                    <span class="item__title">{{ item.title }}</span>
                    @if (!item.is_read) {
                      <span class="item__dot"><span class="visually-hidden">unread</span></span>
                    }
                  </span>
                  @if (item.body) {
                    <span class="item__body">{{ item.body }}</span>
                  }
                  <span class="item__time">{{ when(item.created_at) }}</span>
                </button>
              </li>
            }
          </ul>
        }

        <footer class="panel__foot">
          <a routerLink="/notifications" class="panel__all" (click)="close()">View all →</a>
        </footer>
      </div>
    }
  `,
  styles: `
    :host {
      position: relative;
      display: inline-flex;
    }

    .bell {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      border: 1.5px solid var(--line-strong);
      border-radius: 50%;
      background: var(--card);
      font-size: 1.02rem;
      cursor: pointer;

      &:hover {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 8%, var(--card));
      }
    }

    .bell__badge {
      position: absolute;
      top: -5px;
      right: -5px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 4px;
      border: 2px solid var(--paper);
      border-radius: 999px;
      background: var(--danger);
      color: #fff;
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 700;
      line-height: 1;
    }

    .panel {
      position: absolute;
      top: calc(100% + 10px);
      right: 0;
      z-index: 70;
      width: min(340px, calc(100vw - 2rem));
      overflow: hidden;
      border: 1.5px solid var(--line-strong);
      border-radius: 16px;
      background: var(--card);
      box-shadow: var(--shadow-lift);
      animation: panel-in 160ms var(--ease) both;
    }

    @keyframes panel-in {
      from {
        opacity: 0;
        transform: translateY(-6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .panel__head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.8rem 1rem 0.55rem;
      border-bottom: 1px solid var(--line);
    }

    .panel__mark-all {
      border: 0;
      padding: 0.15rem 0.2rem;
      background: none;
      color: var(--accent-deep);
      font-family: var(--font-body);
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }

    .panel__empty {
      padding: 1.4rem 1rem;
      text-align: center;
      color: var(--ink-soft);
      font-size: 0.9rem;
    }

    .panel__list {
      margin: 0;
      padding: 0;
      list-style: none;
      max-height: min(56dvh, 380px);
      overflow-y: auto;
    }

    .item {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      width: 100%;
      padding: 0.65rem 1rem;
      border: 0;
      border-bottom: 1px solid var(--line);
      background: none;
      color: var(--ink);
      font-family: var(--font-body);
      text-align: left;
      cursor: pointer;

      &:hover {
        background: color-mix(in srgb, var(--accent) 6%, transparent);
      }
    }

    .item--unread {
      background: color-mix(in srgb, var(--accent) 7%, var(--card));

      .item__title {
        font-weight: 800;
      }
    }

    .item__row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }

    .item__title {
      font-size: 0.88rem;
      font-weight: 600;
    }

    .item__dot {
      flex: 0 0 auto;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
    }

    .item__body {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      color: var(--ink-soft);
      font-size: 0.8rem;
      line-height: 1.4;
    }

    .item__time {
      font-family: var(--font-mono);
      font-size: 0.62rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-soft);
    }

    .panel__foot {
      padding: 0.6rem 1rem;
    }

    .panel__all {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--accent-deep);
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }

    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }

    @media (prefers-reduced-motion: reduce) {
      .panel {
        animation: none;
      }
    }
  `,
})
export class NotificationsBell {
  protected readonly notifications = inject(NotificationsService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  private readonly trigger = viewChild.required<ElementRef<HTMLButtonElement>>('trigger');

  protected readonly open = signal(false);

  protected readonly badge = computed(() =>
    this.notifications.unread() > 99 ? '99+' : String(this.notifications.unread()),
  );

  protected readonly ariaLabel = computed(() => {
    const unread = this.notifications.unread();
    return unread > 0 ? `Notifications, ${unread} unread` : 'Notifications';
  });

  private pollTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    const destroyRef = inject(DestroyRef);
    // Poll the unread count every minute while logged in; stop + reset on
    // sign-out. Non-blocking — the service swallows errors.
    effect(() => {
      if (this.auth.isLoggedIn()) {
        void this.notifications.refreshUnread();
        this.startPolling();
      } else {
        this.stopPolling();
        this.notifications.reset();
        this.open.set(false);
      }
    });
    destroyRef.onDestroy(() => this.stopPolling());
  }

  protected toggle(): void {
    if (this.open()) {
      this.close();
      return;
    }
    this.open.set(true);
    // Refresh both the list and the count whenever the dropdown opens.
    void this.notifications.refreshLatest();
    void this.notifications.refreshUnread();
  }

  protected close(): void {
    this.open.set(false);
  }

  protected onEscape(): void {
    if (!this.open()) return;
    this.close();
    this.trigger().nativeElement.focus();
  }

  protected onDocumentClick(event: Event): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.close();
    }
  }

  protected openItem(item: AppNotification): void {
    if (!item.is_read) {
      void this.notifications.markRead(item.id);
    }
    this.close();
    if (item.link) {
      void this.router.navigateByUrl(item.link);
    }
  }

  protected markAllRead(): void {
    void this.notifications.markAllRead();
  }

  protected when(iso: string): string {
    const then = new Date(iso).getTime();
    if (!Number.isFinite(then)) return '';
    const mins = Math.round((Date.now() - then) / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(then).toLocaleDateString();
  }

  private startPolling(): void {
    if (this.pollTimer !== null) return;
    this.pollTimer = setInterval(() => void this.notifications.refreshUnread(), POLL_INTERVAL_MS);
  }

  private stopPolling(): void {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }
}

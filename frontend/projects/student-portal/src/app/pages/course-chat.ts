import { Component, DestroyRef, ElementRef, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { ChatMessage, ChatSocketMessage, CourseChatApi } from '../core/chat';
import { EngagementApi } from '../core/engagement';
import { SiteConfig } from '../core/site-config';
import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';

@Component({
  selector: 'mm-course-chat',
  imports: [RouterLink],
  template: `
    @if (loading()) {
      <p class="mono-label">Opening the study hall…</p>
    } @else if (blocked(); as reason) {
      <div class="blocked rise">
        <h1>Chat unavailable</h1>
        <p>{{ reason }}</p>
        <a [routerLink]="['/courses', slug()]" class="btn btn--ghost">← Back to course</a>
      </div>
    } @else {
      <article class="room rise">
        <header class="head">
          <a [routerLink]="['/courses', slug()]" class="mono-label head__crumb">← {{ courseTitle() }}</a>
          <h1>Course chat</h1>
          <p class="head__sub mono-label">
            @if (connected()) {
              <span class="live">● live</span>
            } @else {
              <span class="quiet">reconnecting…</span>
            }
            · study together with classmates
          </p>
        </header>

        @if (error(); as message) {
          <p class="error-note" role="alert">{{ message }}</p>
        }

        <div class="thread" #thread role="log" aria-live="polite" aria-relevant="additions">
          @for (msg of messages(); track msg.id) {
            <div class="bubble" [class.bubble--mine]="isMine(msg)">
              <span class="bubble__who mono-label">{{ chat.displayName(msg) }}</span>
              <p class="bubble__body">{{ msg.body }}</p>
              <time class="bubble__time mono-label">{{ formatTime(msg.created_at) }}</time>
            </div>
          } @empty {
            <p class="quiet thread__empty">No messages yet — say hello to break the ice.</p>
          }
        </div>

        <form class="composer" (submit)="send($event)">
          <input
            type="text"
            placeholder="Message the room…"
            aria-label="Chat message"
            [value]="draft()"
            (input)="draft.set($any($event.target).value)"
            [disabled]="!connected() || sending()"
            maxlength="2000"
          />
          <button class="btn btn--accent" type="submit" [disabled]="!connected() || sending() || !draft().trim()">
            Send
          </button>
        </form>
      </article>
    }
  `,
  styles: `
    .blocked {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
      padding: 2rem 0;
    }

    .head__crumb {
      text-decoration: none;
      &:hover { color: var(--accent); }
    }

    .head h1 {
      font-size: clamp(1.8rem, 4vw, 2.6rem);
      margin: 0.6rem 0 0.3rem;
    }

    .head__sub {
      color: var(--ink-soft);
    }

    .live { color: var(--sage-deep); }
    .quiet { color: var(--ink-soft); }

    .thread {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      min-height: 320px;
      max-height: min(58vh, 520px);
      overflow-y: auto;
      padding: 1rem;
      margin: 1.2rem 0;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 12px;
    }

    .thread__empty {
      margin: auto;
      text-align: center;
    }

    .bubble {
      max-width: 85%;
      align-self: flex-start;
      padding: 0.65rem 0.9rem;
      background: color-mix(in srgb, var(--chip-pink) 35%, var(--card));
      border: 1px solid var(--line);
      border-radius: 12px 12px 12px 4px;
    }

    .bubble--mine {
      align-self: flex-end;
      background: color-mix(in srgb, var(--accent) 12%, var(--card));
      border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
      border-radius: 12px 12px 4px 12px;
    }

    .bubble__who {
      display: block;
      margin-bottom: 0.25rem;
      color: var(--accent-deep);
    }

    .bubble__body {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .bubble__time {
      display: block;
      margin-top: 0.35rem;
      color: var(--ink-soft);
      font-size: 0.68rem;
    }

    .composer {
      display: flex;
      gap: 0.6rem;

      input {
        flex: 1;
        padding: 0.7rem 0.9rem;
        border: 1.5px solid var(--line-strong);
        border-radius: 10px;
        background: var(--card);
        font-family: var(--font-body);
      }
    }
  `,
})
export class CourseChatPage {
  private readonly route = inject(ActivatedRoute);
  private readonly learningApi = inject(LearningApi);
  private readonly auth = inject(AuthService);
  protected readonly chat = inject(CourseChatApi);
  private readonly engagement = inject(EngagementApi);
  protected readonly config = inject(SiteConfig);
  private readonly destroyRef = inject(DestroyRef);

  private readonly threadEl = viewChild<ElementRef<HTMLElement>>('thread');

  protected readonly slug = signal('');
  protected readonly courseTitle = signal('Course');
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly draft = signal('');
  protected readonly loading = signal(true);
  protected readonly connected = signal(false);
  protected readonly sending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly blocked = signal<string | null>(null);

  private socket: WebSocket | null = null;

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      if (slug) void this.boot(slug);
    });

    this.destroyRef.onDestroy(() => this.closeSocket());
  }

  private async boot(slug: string): Promise<void> {
    this.closeSocket();
    this.slug.set(slug);
    this.loading.set(true);
    this.blocked.set(null);
    this.error.set(null);
    this.messages.set([]);

    if (!this.config.flagEnabled('chat')) {
      this.blocked.set('Course chat is turned off for this deployment.');
      this.loading.set(false);
      return;
    }
    if (!this.auth.isLoggedIn()) {
      this.blocked.set('Sign in and enroll to join the course chat.');
      this.loading.set(false);
      return;
    }

    try {
      const [history, course] = await Promise.all([
        this.chat.history(slug),
        this.learningApi.getCourse(slug).catch(() => null),
      ]);
      if (course) this.courseTitle.set(course.title);
      this.messages.set(history);
      this.openSocket(slug);
    } catch (err) {
      this.blocked.set(apiErrorMessage(err, 'You need to enroll in this course to chat.'));
    } finally {
      this.loading.set(false);
      this.scrollToEnd();
    }
  }

  private openSocket(slug: string): void {
    const socket = this.chat.connect(slug);
    if (!socket) {
      this.error.set('Session expired — refresh and sign in again.');
      return;
    }
    this.socket = socket;

    socket.onopen = () => this.connected.set(true);
    socket.onclose = () => this.connected.set(false);
    socket.onerror = () => this.error.set('Connection lost — messages may not send.');
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as ChatSocketMessage;
      if (payload.error) {
        this.error.set(payload.detail || 'Could not send message.');
        return;
      }
      if (payload.id && payload.body && payload.created_at) {
        const incoming: ChatMessage = {
          id: payload.id,
          body: payload.body,
          created_at: payload.created_at,
          sender: payload.sender,
        };
        this.messages.update((all) =>
          all.some((m) => m.id === incoming.id) ? all : [...all, incoming],
        );
        void this.engagement.refresh();
        this.scrollToEnd();
      }
    };
  }

  private closeSocket(): void {
    this.socket?.close();
    this.socket = null;
    this.connected.set(false);
  }

  protected isMine(msg: ChatMessage): boolean {
    const me = this.auth.user();
    if (!me) return false;
    const name = this.chat.displayName(msg);
    return name === (me.display_name || me.email);
  }

  protected formatTime(iso: string): string {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  protected send(event: Event): void {
    event.preventDefault();
    const body = this.draft().trim();
    if (!body || !this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.sending.set(true);
    this.error.set(null);
    this.socket.send(JSON.stringify({ message: body }));
    this.draft.set('');
    this.sending.set(false);
  }

  private scrollToEnd(): void {
    queueMicrotask(() => {
      const el = this.threadEl()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}

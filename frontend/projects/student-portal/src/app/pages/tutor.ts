import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';

import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { TutorApi, TutorMessage, TutorQuota, TutorSession } from '../core/tutor';

const SUBJECTS = ['Math', 'Physics', 'Chemistry', 'Biology', 'Computer Science', 'General'];
const LEVELS = ['O-Level', 'A-Level'];
const STARTERS = [
  'Explain photosynthesis simply',
  'How do I integrate x·sin(x)?',
  "What is Newton's second law?",
  'Walk me through balancing redox equations',
];

@Component({
  selector: 'mm-tutor',
  template: `
    <div class="layout rise">
      <!-- sessions sidebar -->
      <aside class="sidebar">
        <button class="btn btn--accent sidebar__new" (click)="newChat()">+ New chat</button>
        <p class="mono-label">Previous sessions</p>
        @for (s of sessions(); track s.id) {
          <button
            type="button"
            class="sidebar__item"
            [class.is-active]="session()?.id === s.id"
            (click)="openSession(s.id)"
          >
            <strong>{{ s.title || s.subject || 'Untitled' }}</strong>
            <span class="mono-label">{{ s.subject }} · {{ s.level }}</span>
          </button>
        } @empty {
          <p class="sidebar__empty">No sessions yet.</p>
        }
      </aside>

      <!-- chat column -->
      <section class="chat">
        <header class="chat__head">
          <h1>AI Tutor</h1>
          <div class="chat__pickers">
            <select [value]="subject()" (change)="subject.set($any($event.target).value)" [disabled]="!!session()" aria-label="Subject">
              @for (s of subjects; track s) { <option [value]="s">{{ s }}</option> }
            </select>
            <select [value]="level()" (change)="level.set($any($event.target).value)" [disabled]="!!session()" aria-label="Level">
              @for (l of levels; track l) { <option [value]="l">{{ l }}</option> }
            </select>
          </div>
        </header>

        @if (quota(); as q) {
          @if (q.limit !== null && q.remaining !== null && q.remaining <= 2 && q.remaining > 0) {
            <p class="banner banner--warn mono-label">
              {{ q.used }}/{{ q.limit }} messages used today — {{ q.remaining }} left on the free plan.
            </p>
          }
          @if (q.limit !== null && q.remaining === 0) {
            <div class="banner banner--limit">
              <p><strong>Daily limit reached.</strong> Upgrade for unlimited tutoring.</p>
              <button class="btn btn--accent" (click)="upgrade()" [disabled]="busy()">
                {{ busy() ? 'Upgrading…' : 'Go Premium (simulated)' }}
              </button>
            </div>
          }
        }

        @if (loadError(); as message) {
          <p class="error-note" role="alert">
            {{ message }}
            <button type="button" class="retry" (click)="reload()">retry</button>
          </p>
        }

        <div class="thread" aria-live="polite">
          @for (message of messages(); track message.id) {
            <div class="bubble" [class.bubble--mine]="message.role === 'user'">
              <div class="bubble__content">{{ message.content }}</div>
              @if (message.role === 'assistant') {
                <div class="bubble__tools">
                  <button type="button" (click)="copy(message)" title="Copy" aria-label="Copy message">⧉</button>
                  <button
                    type="button"
                    [class.is-picked]="message.feedback === 1"
                    (click)="rate(message, 1)"
                    title="Helpful"
                    aria-label="Rate answer as helpful"
                  >👍</button>
                  <button
                    type="button"
                    [class.is-picked]="message.feedback === -1"
                    (click)="rate(message, -1)"
                    title="Not helpful"
                    aria-label="Rate answer as not helpful"
                  >👎</button>
                </div>
              }
            </div>
          } @empty {
            <div class="starters">
              <p class="mono-label">Ask anything — or try one of these:</p>
              @for (starter of starters; track starter) {
                <button type="button" class="starters__chip" (click)="draft.set(starter)">
                  {{ starter }}
                </button>
              }
            </div>
          }
          @if (thinking()) {
            <div class="bubble">
              <div class="bubble__content dots"><span>●</span><span>●</span><span>●</span></div>
            </div>
          }
        </div>

        @if (error(); as message) {
          <p class="error-note" role="alert">
            {{ message }}
            <button type="button" class="retry" (click)="send()">retry</button>
          </p>
        }

        <form class="composer" (submit)="onSubmit($event)">
          <input
            type="text"
            placeholder="Ask your tutor…"
            aria-label="Ask your tutor"
            [value]="draft()"
            (input)="draft.set($any($event.target).value)"
            [disabled]="thinking()"
          />
          <button class="btn btn--accent" type="submit" [disabled]="thinking() || !draft().trim()">
            Send
          </button>
        </form>
      </section>
    </div>
  `,
  styles: `
    .layout {
      display: grid;
      grid-template-columns: 250px 1fr;
      gap: 1.6rem;
      align-items: start;
    }

    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .sidebar__new {
      justify-content: center;
      margin-bottom: 0.5rem;
    }

    .sidebar__item {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.1rem;
      padding: 0.6rem 0.8rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 8px;
      cursor: pointer;
      text-align: left;
      font-family: var(--font-body);
      color: var(--ink);

      strong {
        font-size: 0.85rem;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      &.is-active { border-color: var(--accent); }
      &:hover { border-color: var(--line-strong); }
    }

    .sidebar__empty {
      color: var(--ink-soft);
      font-size: 0.85rem;
    }

    .chat__head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 1rem;
      flex-wrap: wrap;
      margin-bottom: 1rem;

      h1 { font-size: 2rem; }
    }

    .chat__pickers {
      display: flex;
      gap: 0.5rem;

      select {
        padding: 0.45rem 0.7rem;
        border: 1.5px solid var(--line-strong);
        border-radius: 8px;
        background: var(--card);
        font-family: var(--font-body);
        font-size: 0.85rem;
      }
    }

    .banner {
      padding: 0.6rem 0.9rem;
      border-radius: 8px;
      margin-bottom: 0.9rem;
    }

    .banner--warn {
      background: rgba(242, 194, 73, 0.25);
      border: 1px solid var(--marker);
    }

    .banner--limit {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      background: rgba(200, 69, 31, 0.08);
      border: 1.5px solid var(--accent);
    }

    .thread {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      min-height: 320px;
      padding: 1.2rem;
      background: var(--card);
      border: 1.5px solid var(--ink);
      border-radius: 12px;
      margin-bottom: 0.9rem;
    }

    .bubble {
      max-width: 85%;
      align-self: flex-start;
    }

    .bubble--mine {
      align-self: flex-end;

      .bubble__content {
        background: var(--ink);
        color: var(--paper);
      }
    }

    .bubble__content {
      padding: 0.75rem 1rem;
      background: var(--paper-deep);
      border-radius: 12px;
      font-size: 0.95rem;
      white-space: pre-wrap;
    }

    .bubble__tools {
      display: flex;
      gap: 0.3rem;
      margin-top: 0.25rem;

      button {
        border: 1px solid var(--line);
        background: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.78rem;
        padding: 0.15rem 0.45rem;

        &.is-picked { border-color: var(--accent); background: rgba(200, 69, 31, 0.1); }
      }
    }

    .dots span {
      animation: blink-dot 1.2s infinite;
      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }

    @keyframes blink-dot {
      0%, 100% { opacity: 0.2; }
      50% { opacity: 1; }
    }

    .starters {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      align-items: flex-start;
    }

    .starters__chip {
      padding: 0.5rem 0.95rem;
      border: 1.5px dashed var(--line-strong);
      border-radius: 999px;
      background: none;
      font-family: var(--font-body);
      font-size: 0.88rem;
      cursor: pointer;

      &:hover { border-color: var(--accent); color: var(--accent); }
    }

    .composer {
      display: flex;
      gap: 0.7rem;

      input {
        flex: 1;
        padding: 0.75rem 1rem;
        border: 1.5px solid var(--line-strong);
        border-radius: 999px;
        background: var(--card);
        font-family: var(--font-body);
        font-size: 0.95rem;

        &:focus {
          outline: none;
          border-color: var(--accent);
        }
      }
    }

    .retry {
      border: none;
      background: none;
      color: var(--danger);
      text-decoration: underline;
      cursor: pointer;
      font-size: 0.85rem;
    }

    @media (max-width: 860px) {
      .layout { grid-template-columns: 1fr; }
    }
  `,
})
export class TutorPage {
  private readonly api = inject(TutorApi);
  private readonly auth = inject(AuthService);

  protected readonly subjects = SUBJECTS;
  protected readonly levels = LEVELS;
  protected readonly starters = STARTERS;

  protected readonly sessions = signal<TutorSession[]>([]);
  protected readonly session = signal<TutorSession | null>(null);
  protected readonly messages = signal<TutorMessage[]>([]);
  protected readonly quota = signal<TutorQuota | null>(null);
  protected readonly subject = signal(SUBJECTS[0]);
  protected readonly level = signal(LEVELS[1]);
  protected readonly draft = signal('');
  protected readonly thinking = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly loadError = signal<string | null>(null);

  private lastFailed = '';

  constructor() {
    void this.bootstrap();
  }

  /** Re-runs the initial sessions/quota load after a visible failure. */
  protected reload(): void {
    void this.bootstrap();
  }

  private async bootstrap(): Promise<void> {
    this.loadError.set(null);
    try {
      const [sessions, quota] = await Promise.all([this.api.listSessions(), this.api.quota()]);
      this.sessions.set(sessions);
      this.quota.set(quota);
    } catch (err) {
      this.loadError.set(apiErrorMessage(err, 'Could not load your tutor sessions.'));
    }
  }

  protected newChat(): void {
    this.session.set(null);
    this.messages.set([]);
    this.error.set(null);
  }

  protected async openSession(id: number): Promise<void> {
    try {
      const full = await this.api.getSession(id);
      this.session.set(full);
      this.subject.set(full.subject || SUBJECTS[0]);
      this.level.set(full.level || LEVELS[1]);
      this.messages.set(full.messages ?? []);
      this.error.set(null);
      this.loadError.set(null);
    } catch (err) {
      this.loadError.set(apiErrorMessage(err, 'Could not open that session.'));
    }
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    void this.send();
  }

  protected async send(): Promise<void> {
    const content = (this.draft().trim() || this.lastFailed).trim();
    if (!content || this.thinking()) return;
    this.thinking.set(true);
    this.error.set(null);
    try {
      let active = this.session();
      if (!active) {
        active = await this.api.createSession(this.subject(), this.level());
        this.session.set(active);
      }
      const result = await this.api.send(active.id, content);
      this.messages.update((all) => [...all, result.user_message, result.assistant_message]);
      this.draft.set('');
      this.lastFailed = '';
      // Ancillary refreshes after a successful send: deliberately keep the
      // last-known values on failure instead of erroring a successful chat
      // turn (the GETs already retry transient failures at the service layer).
      this.quota.set(await this.api.quota().catch(() => this.quota()));
      this.sessions.set(await this.api.listSessions().catch(() => this.sessions()));
    } catch (err) {
      this.lastFailed = content;
      if (err instanceof HttpErrorResponse && err.status === 429) {
        this.quota.set(await this.api.quota().catch(() => this.quota()));
        this.error.set('Daily limit reached — upgrade to keep going.');
      } else {
        this.error.set(apiErrorMessage(err, 'The tutor had trouble answering.'));
      }
    } finally {
      this.thinking.set(false);
    }
  }

  protected async rate(message: TutorMessage, value: 1 | -1): Promise<void> {
    const active = this.session();
    if (!active) return;
    try {
      const updated = await this.api.feedback(active.id, message.id, value);
      this.messages.update((all) => all.map((m) => (m.id === updated.id ? updated : m)));
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not record your feedback — try again.'));
    }
  }

  protected copy(message: TutorMessage): void {
    void navigator.clipboard?.writeText(message.content);
  }

  protected async upgrade(): Promise<void> {
    this.busy.set(true);
    try {
      await this.api.subscribe('monthly');
      await this.auth.loadMe();
      this.quota.set(await this.api.quota());
      this.error.set(null);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Upgrade failed — try again.'));
    } finally {
      this.busy.set(false);
    }
  }
}

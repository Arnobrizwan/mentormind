import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, NgZone, inject, signal } from '@angular/core';

import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { TutorApi, TutorMessage, TutorQuota, TutorSession } from '../core/tutor';

/**
 * Minimal typings for the (still prefixed in some browsers) Web Speech
 * recognition API — TypeScript's DOM lib doesn't ship them.
 */
interface DictationAlternative {
  transcript: string;
}
interface DictationResultEvent {
  results: ArrayLike<ArrayLike<DictationAlternative>>;
}
interface DictationErrorEvent {
  error: string;
}
interface Dictation {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: DictationResultEvent) => void) | null;
  onerror: ((event: DictationErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}
type DictationCtor = new () => Dictation;

function dictationCtor(): DictationCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  return (w['SpeechRecognition'] as DictationCtor | undefined) ??
    (w['webkitSpeechRecognition'] as DictationCtor | undefined) ??
    null;
}

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
                  @if (ttsSupported) {
                    <button
                      type="button"
                      [class.is-picked]="speakingId() === message.id"
                      (click)="toggleSpeak(message)"
                      [title]="speakingId() === message.id ? 'Stop reading' : 'Read aloud'"
                      [attr.aria-label]="speakingId() === message.id ? 'Stop reading aloud' : 'Read message aloud'"
                      [attr.aria-pressed]="speakingId() === message.id"
                    >{{ speakingId() === message.id ? '⏹' : '🔊' }}</button>
                  }
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

        @if (attachment(); as file) {
          <div class="attach-chip">
            @if (previewUrl(); as url) {
              <img class="attach-chip__thumb" [src]="url" alt="Attached image preview" />
            }
            <span class="attach-chip__name">{{ file.name }}</span>
            <button
              type="button"
              class="attach-chip__remove"
              (click)="clearAttachment()"
              aria-label="Remove attached image"
            >×</button>
          </div>
        }

        <form class="composer" (submit)="onSubmit($event)">
          <input
            #fileInput
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            (change)="onFileSelected($event)"
          />
          <button
            type="button"
            class="composer__attach"
            (click)="fileInput.click()"
            [disabled]="thinking()"
            title="Attach a photo"
            aria-label="Attach a photo"
          >📎</button>
          @if (speechSupported) {
            <button
              type="button"
              class="composer__mic"
              [class.is-listening]="listening()"
              (click)="toggleMic()"
              [disabled]="thinking()"
              [title]="listening() ? 'Stop dictation' : 'Dictate your question'"
              [attr.aria-label]="listening() ? 'Stop dictation' : 'Dictate your question'"
              [attr.aria-pressed]="listening()"
            >
              🎤
              @if (listening()) {
                <span class="composer__mic-dot" aria-hidden="true"></span>
              }
            </button>
          }
          <input
            type="text"
            placeholder="Ask your tutor…"
            aria-label="Ask your tutor"
            [value]="draft()"
            (input)="draft.set($any($event.target).value)"
            [disabled]="thinking()"
          />
          <button
            class="btn btn--accent"
            type="submit"
            [disabled]="thinking() || (!draft().trim() && !attachment())"
          >
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

    .attach-chip {
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
      max-width: 100%;
      padding: 0.35rem 0.55rem;
      margin-bottom: 0.6rem;
      background: var(--card);
      border: 1.5px dashed var(--line-strong);
      border-radius: 10px;
    }

    .attach-chip__thumb {
      width: 38px;
      height: 38px;
      object-fit: cover;
      border-radius: 6px;
      border: 1px solid var(--line);
    }

    .attach-chip__name {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--ink-soft);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 26ch;
    }

    .attach-chip__remove {
      border: 1px solid var(--line);
      background: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.95rem;
      line-height: 1;
      padding: 0.15rem 0.45rem;
      color: var(--ink);

      &:hover,
      &:focus-visible { border-color: var(--danger); color: var(--danger); }
    }

    .composer__attach {
      width: 46px;
      height: 46px;
      flex-shrink: 0;
      border: 1.5px solid var(--line-strong);
      border-radius: 999px;
      background: var(--card);
      cursor: pointer;
      font-size: 1.05rem;

      &:hover:not(:disabled),
      &:focus-visible { border-color: var(--accent); }

      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

      &:disabled { opacity: 0.5; cursor: default; }
    }

    .composer__mic {
      position: relative;
      width: 46px;
      height: 46px;
      flex-shrink: 0;
      border: 1.5px solid var(--line-strong);
      border-radius: 999px;
      background: var(--card);
      cursor: pointer;
      font-size: 1.05rem;

      &:hover:not(:disabled),
      &:focus-visible { border-color: var(--accent); }

      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

      &:disabled { opacity: 0.5; cursor: default; }

      &.is-listening { border-color: var(--danger); }
    }

    .composer__mic-dot {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--danger);
      animation: mic-pulse 1.1s ease-in-out infinite;
    }

    @keyframes mic-pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.7); }
    }

    .composer {
      display: flex;
      align-items: center;
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
  protected readonly attachment = signal<File | null>(null);
  protected readonly previewUrl = signal<string | null>(null);

  // Voice in (dictation) and voice out (read-aloud) — both feature-detected.
  protected readonly speechSupported = dictationCtor() !== null;
  protected readonly ttsSupported =
    typeof window !== 'undefined' && 'speechSynthesis' in window;
  protected readonly listening = signal(false);
  protected readonly speakingId = signal<number | null>(null);

  private readonly zone = inject(NgZone);
  private recognition: Dictation | null = null;
  /** Draft text captured when dictation starts; transcripts append to it. */
  private dictationBase = '';

  private lastFailed = '';

  private static readonly MAX_IMAGE_BYTES = 8 * 1024 * 1024;

  constructor() {
    void this.bootstrap();
    // Make sure the preview object URL, mic and speech never outlive the page.
    inject(DestroyRef).onDestroy(() => {
      this.clearAttachment();
      this.stopMic();
      this.stopSpeech();
    });
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
    this.clearAttachment();
    this.stopMic();
    this.stopSpeech();
  }

  /** Press to dictate, press again (or pause long enough) to stop. */
  protected toggleMic(): void {
    if (this.listening()) {
      this.stopMic();
      return;
    }
    const Ctor = dictationCtor();
    if (!Ctor) return;
    const recognition = new Ctor();
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = true;
    recognition.continuous = true;
    const existing = this.draft().trimEnd();
    this.dictationBase = existing ? `${existing} ` : '';
    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0]?.transcript ?? '';
      }
      this.zone.run(() => this.draft.set(this.dictationBase + transcript));
    };
    recognition.onerror = (event) => {
      this.zone.run(() => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          this.error.set(
            'Microphone access was blocked — allow it in your browser settings to dictate.',
          );
        } else if (event.error !== 'aborted' && event.error !== 'no-speech') {
          this.error.set('Dictation hit a snag — try again.');
        }
        this.listening.set(false);
      });
    };
    recognition.onend = () => {
      this.zone.run(() => {
        this.listening.set(false);
        this.recognition = null;
      });
    };
    this.recognition = recognition;
    try {
      recognition.start();
      this.error.set(null);
      this.listening.set(true);
    } catch {
      this.recognition = null;
      this.error.set('Could not start the microphone — try again.');
    }
  }

  private stopMic(): void {
    try {
      this.recognition?.stop();
    } catch {
      // Already stopped — nothing to do.
    }
    this.recognition = null;
    this.listening.set(false);
  }

  /** Read an assistant message aloud; clicking again stops it. */
  protected toggleSpeak(message: TutorMessage): void {
    if (!this.ttsSupported) return;
    if (this.speakingId() === message.id) {
      this.stopSpeech();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(this.speechText(message.content));
    utterance.onend = () => this.zone.run(() => this.speakingId.set(null));
    utterance.onerror = () => this.zone.run(() => this.speakingId.set(null));
    this.speakingId.set(message.id);
    window.speechSynthesis.speak(utterance);
  }

  private stopSpeech(): void {
    if (this.ttsSupported) window.speechSynthesis.cancel();
    this.speakingId.set(null);
  }

  /** Strip markdown punctuation so the voice doesn't read "asterisk asterisk". */
  private speechText(markdown: string): string {
    return markdown
      .replace(/```[\s\S]*?```/g, ' code snippet ')
      .replace(/`([^`]*)`/g, '$1')
      .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^\s*[-*+]\s+/gm, '')
      .replace(/^\s*>\s+/gm, '')
      .replace(/[*_~|]/g, '')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    // Reset so re-picking the same file fires (change) again.
    input.value = '';
    if (!file) return;
    if (file.size > TutorPage.MAX_IMAGE_BYTES) {
      this.error.set('That image is too large — the limit is 8 MB.');
      return;
    }
    this.error.set(null);
    this.setAttachment(file);
  }

  protected clearAttachment(): void {
    this.setAttachment(null);
  }

  private setAttachment(file: File | null): void {
    const previous = this.previewUrl();
    if (previous) URL.revokeObjectURL(previous);
    this.attachment.set(file);
    this.previewUrl.set(file ? URL.createObjectURL(file) : null);
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
      this.clearAttachment();
      this.stopMic();
      this.stopSpeech();
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
    const image = this.attachment();
    if ((!content && !image) || this.thinking()) return;
    this.thinking.set(true);
    this.error.set(null);
    try {
      let active = this.session();
      if (!active) {
        active = await this.api.createSession(this.subject(), this.level());
        this.session.set(active);
      }
      const result = await this.api.send(active.id, content, image ?? undefined);
      this.messages.update((all) => [...all, result.user_message, result.assistant_message]);
      this.draft.set('');
      this.lastFailed = '';
      this.clearAttachment();
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

import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { ConfettiBurst as ConfettiComponent } from '../core/confetti';
import { renderMarkdown } from '../core/markdown';
import {
  PaperQuestion,
  PastPapersApi,
  SUBJECT_NAMES,
  subjectName,
} from '../core/pastpapers';

const SECONDS_PER_QUESTION = 90;

@Component({
  selector: 'mm-mock-exam',
  imports: [ConfettiComponent],
  template: `
    <section class="page-head rise">
      <p class="mono-label">Timed · real past-paper questions · self-marked</p>
      <h1>Mock exam</h1>
    </section>

    @if (error(); as message) {
      <p class="error-note" role="alert">{{ message }}</p>
    }

    @if (phase() === 'setup') {
      <div class="card setup rise">
        <label>Subject
          <select [value]="subjectCode()" (change)="subjectCode.set($any($event.target).value)">
            @for (entry of subjectOptions; track entry[0]) {
              <option [value]="entry[0]">{{ entry[1] }} ({{ entry[0] }})</option>
            }
          </select>
        </label>
        <label>Length
          <select [value]="length()" (change)="length.set(+$any($event.target).value)">
            <option [value]="5">5 questions · 7½ min</option>
            <option [value]="10">10 questions · 15 min</option>
            <option [value]="15">15 questions · 22½ min</option>
          </select>
        </label>
        <button type="button" class="btn btn--accent" [disabled]="loading()" (click)="start()">
          {{ loading() ? 'Preparing paper…' : 'Start mock exam' }}
        </button>
      </div>
    } @else if (phase() === 'running') {
      <div class="bar">
        <span class="mono-label">Q{{ index() + 1 }} / {{ questions().length }}</span>
        <span class="timer mono-label" role="timer" [class.timer--low]="secondsLeft() <= 60">
          {{ clock() }}
        </span>
      </div>
      @if (current(); as q) {
        <article class="card paper rise">
          <p class="mono-label">Cambridge {{ q.subject_code }} · {{ q.year }} {{ q.session }} · Paper {{ q.variant }} · Q{{ q.question_number }}</p>
          <div class="paper__body" [innerHTML]="rendered(q.question_markdown)"></div>
          <label class="working">Your working (for self-marking later)
            <textarea rows="4" [value]="working()[index()] ?? ''" (input)="note($any($event.target).value)"></textarea>
          </label>
          <div class="paper__nav">
            <button type="button" class="btn btn--ghost" [disabled]="index() === 0" (click)="index.set(index() - 1)">Prev</button>
            @if (index() < questions().length - 1) {
              <button type="button" class="btn btn--accent" (click)="index.set(index() + 1)">Next</button>
            } @else {
              <button type="button" class="btn btn--accent" (click)="finish()">Finish exam</button>
            }
          </div>
        </article>
      }
    } @else {
      <div class="bar">
        <h2 style="margin:0">Self-marking</h2>
        <span class="mono-label">{{ marked() }} / {{ questions().length }} correct
          ({{ scorePct() }}%)</span>
      </div>
      @if (scorePct() >= 50) { <mm-confetti /> }
      @for (q of questions(); track q.id; let i = $index) {
        <article class="card paper rise" style="margin-bottom: 1rem;">
          <p class="mono-label">Q{{ i + 1 }} · Cambridge {{ q.subject_code }} {{ q.year }}{{ q.session }} P{{ q.variant }}</p>
          <div class="paper__body" [innerHTML]="rendered(q.question_markdown)"></div>
          @if (working()[i]) {
            <p class="mono-label">Your working</p>
            <pre class="mywork">{{ working()[i] }}</pre>
          }
          <div class="scheme">
            <p class="mono-label">Official mark scheme</p>
            <div [innerHTML]="rendered(q.mark_scheme_markdown ?? '')"></div>
          </div>
          <label class="selfmark">
            <input type="checkbox" [checked]="selfMarks()[i]" (change)="mark(i, $any($event.target).checked)" />
            I got this one right
          </label>
        </article>
      }
      <button type="button" class="btn btn--accent" (click)="reset()">New mock exam</button>
    }
  `,
  styles: `
    .page-head h1 { font-size: clamp(2rem, 4.5vw, 3rem); margin: 0.4rem 0 1.2rem; }
    .setup { display: flex; flex-direction: column; gap: 1rem; max-width: 420px;
      padding: 1.4rem; border: 1.5px solid var(--line-strong); border-radius: 12px; background: var(--card); }
    .setup label { display: flex; flex-direction: column; gap: 0.35rem; font-weight: 600; }
    .setup select { font: inherit; padding: 0.55rem; border-radius: 8px; border: 1.5px solid var(--line-strong); }
    .bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.6rem; }
    .timer { font-size: 1.1rem; font-weight: 700; }
    .timer--low { color: var(--danger); animation: mock-pulse 1s ease-in-out infinite; }
    @keyframes mock-pulse { 50% { opacity: 0.55; } }
    @media (prefers-reduced-motion: reduce) { .timer--low { animation: none; } }
    .paper { padding: 1.4rem; border: 1.5px solid var(--line-strong); border-radius: 12px; background: var(--card); }
    .paper__body { margin: 0.8rem 0 1rem; line-height: 1.65; }
    .paper__nav { display: flex; justify-content: space-between; margin-top: 1rem; }
    .working { display: flex; flex-direction: column; gap: 0.35rem; font-weight: 600; }
    .working textarea { font: inherit; padding: 0.6rem; border-radius: 8px; border: 1.5px solid var(--line-strong); resize: vertical; }
    .mywork { background: color-mix(in srgb, var(--accent) 7%, transparent); padding: 0.7rem; border-radius: 8px; white-space: pre-wrap; font-family: var(--font-mono); font-size: 0.85rem; }
    .scheme { border-top: 2px dashed var(--line-strong); margin-top: 1rem; padding-top: 1rem; }
    .selfmark { display: flex; gap: 0.5rem; align-items: center; margin-top: 1rem; font-weight: 700; }
  `,
})
export class MockExamPage {
  private readonly api = inject(PastPapersApi);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly subjectOptions = Object.entries(SUBJECT_NAMES);
  protected readonly subjectCode = signal('0625');
  protected readonly length = signal(10);
  protected readonly phase = signal<'setup' | 'running' | 'review'>('setup');
  protected readonly questions = signal<PaperQuestion[]>([]);
  protected readonly index = signal(0);
  protected readonly working = signal<Record<number, string>>({});
  protected readonly selfMarks = signal<Record<number, boolean>>({});
  protected readonly secondsLeft = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly current = computed(() => this.questions()[this.index()] ?? null);
  protected readonly clock = computed(() => {
    const s = this.secondsLeft();
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  });
  protected readonly marked = computed(
    () => Object.values(this.selfMarks()).filter(Boolean).length,
  );
  protected readonly scorePct = computed(() =>
    this.questions().length
      ? Math.round((100 * this.marked()) / this.questions().length)
      : 0,
  );

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.destroyRef.onDestroy(() => this.stopTimer());
  }

  protected name = subjectName;

  protected async start(): Promise<void> {
    this.loading.set(true);
    try {
      const body = await this.api.sample(this.subjectCode(), this.length());
      if (!body.questions.length) {
        this.error.set('No questions available for that subject yet.');
        return;
      }
      this.questions.set(body.questions);
      this.index.set(0);
      this.working.set({});
      this.selfMarks.set({});
      this.secondsLeft.set(body.questions.length * SECONDS_PER_QUESTION);
      this.error.set(null);
      this.phase.set('running');
      this.timer = setInterval(() => {
        this.secondsLeft.update((s) => s - 1);
        if (this.secondsLeft() <= 0) this.finish();
      }, 1000);
    } catch {
      this.error.set('The past-paper service is waking up — try again in a minute.');
    } finally {
      this.loading.set(false);
    }
  }

  protected note(text: string): void {
    this.working.update((w) => ({ ...w, [this.index()]: text }));
  }

  protected mark(i: number, checked: boolean): void {
    this.selfMarks.update((m) => ({ ...m, [i]: checked }));
  }

  protected finish(): void {
    this.stopTimer();
    this.phase.set('review');
  }

  protected reset(): void {
    this.stopTimer();
    this.phase.set('setup');
    this.questions.set([]);
  }

  private stopTimer(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  protected rendered(text: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(renderMarkdown(text));
  }
}

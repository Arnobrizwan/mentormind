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

/** Matches an option line like "A coil of wire" / "B) split-ring" / "C. poles". */
const OPTION_LINE = /^\(?([A-D])[).]?\s+(\S.*)$/;

interface McqOption {
  letter: string;
  text: string;
}

interface ParsedMcq {
  stem: string;
  options: McqOption[];
  answer: string; // the correct letter, A–D
}

interface Prepared {
  q: PaperQuestion;
  /** A clean, selectable MCQ — or null for a free-text/theory question. */
  mcq: ParsedMcq | null;
}

function tidy(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

/** Pull the correct option letter out of a multiple-choice mark scheme.
 * MCQ schemes look like "30 B 1" (question · answer · marks). */
function parseAnswer(markScheme?: string): string | null {
  if (!markScheme) return null;
  const match = markScheme.match(/(?:^|\s)([A-D])(?:\s|$)/);
  return match ? match[1] : null;
}

/** Parse a past-paper question into a structured MCQ, or null if it isn't one.
 * Options must appear in order A, B, C, D — each on its own line. Anything
 * after option D (page numbers, copyright footer) is ignored. */
function parseMcq(question: PaperQuestion): ParsedMcq | null {
  const lines = (question.question_markdown || '')
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim());

  const stemParts: string[] = [];
  const options: McqOption[] = [];
  let expecting = 'A';

  for (const line of lines) {
    if (!line) continue;
    const match = line.match(OPTION_LINE);
    if (match && match[1] === expecting) {
      options.push({ letter: match[1], text: tidy(match[2]) });
      expecting = String.fromCharCode(expecting.charCodeAt(0) + 1);
      if (options.length === 4) break;
      continue;
    }
    // Stem is whatever sits before the first option; skip stray page numbers.
    if (options.length === 0 && !/^\d+$/.test(line)) stemParts.push(line);
  }

  if (options.length < 4) return null;
  const answer = parseAnswer(question.mark_scheme_markdown);
  if (!answer) return null;

  // Drop the leading question number ("33 ...") from the stem.
  const stem = tidy(stemParts.join(' ')).replace(/^\d+\s*/, '');
  return { stem, options, answer };
}

/** A parsed MCQ is only worth showing if it doesn't depend on a figure we
 * lost in OCR, and its options are real, distinct text. */
function isRenderable(mcq: ParsedMcq): boolean {
  if (mcq.stem.length < 8) return false;
  // "Which graph/diagram shows…" hinges on an image the corpus doesn't have.
  if (/\b(graph|diagram)\b/i.test(mcq.stem)) return false;
  const texts = mcq.options.map((o) => o.text.toLowerCase());
  // Every option needs at least a couple of real letters.
  if (texts.some((t) => t.replace(/[^a-z]/g, '').length < 2)) return false;
  // Duplicate option text is a tell-tale sign of garbled axis labels.
  if (new Set(texts).size < texts.length) return false;
  return true;
}

@Component({
  selector: 'mm-mock-exam',
  imports: [ConfettiComponent],
  template: `
    <section class="page-head rise hero-panel">
      <span class="hero-panel__sticker" aria-hidden="true">⏱️</span>
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
        <span class="mono-label">Q{{ index() + 1 }} / {{ prepared().length }}</span>
        <span class="timer mono-label" role="timer" [class.timer--low]="secondsLeft() <= 60">
          {{ clock() }}
        </span>
      </div>
      @if (currentPrep(); as p) {
        <article class="card paper rise">
          <p class="mono-label">Cambridge {{ p.q.subject_code }} · {{ p.q.year }} {{ p.q.session }} · Paper {{ p.q.variant }} · Q{{ p.q.question_number }}</p>
          @if (p.mcq; as mcq) {
            <p class="paper__stem">{{ mcq.stem }}</p>
            <div class="choices" role="radiogroup" [attr.aria-label]="'Question ' + (index() + 1)">
              @for (opt of mcq.options; track opt.letter) {
                <label class="choice" [class.choice--picked]="answers()[index()] === opt.letter">
                  <input
                    type="radio"
                    [name]="'q' + index()"
                    [checked]="answers()[index()] === opt.letter"
                    (change)="pick(opt.letter)"
                  />
                  <span class="choice__letter">{{ opt.letter }}</span>
                  <span class="choice__text">{{ opt.text }}</span>
                </label>
              }
            </div>
          } @else {
            <div class="paper__body" [innerHTML]="rendered(p.q.question_markdown)"></div>
            <label class="working">Your working (for self-marking later)
              <textarea rows="4" [value]="working()[index()] ?? ''" (input)="note($any($event.target).value)"></textarea>
            </label>
          }
          <div class="paper__nav">
            <button type="button" class="btn btn--ghost" [disabled]="index() === 0" (click)="index.set(index() - 1)">Prev</button>
            @if (index() < prepared().length - 1) {
              <button type="button" class="btn btn--accent" (click)="index.set(index() + 1)">Next</button>
            } @else {
              <button type="button" class="btn btn--accent" (click)="finish()">Finish exam</button>
            }
          </div>
        </article>
      }
    } @else {
      <div class="bar">
        <h2 style="margin:0">Results</h2>
        <span class="mono-label">{{ marked() }} / {{ prepared().length }} correct
          ({{ scorePct() }}%)</span>
      </div>
      @if (scorePct() >= 50) { <mm-confetti /> }
      @for (p of prepared(); track p.q.id; let i = $index) {
        <article class="card paper rise" style="margin-bottom: 1rem;">
          <p class="mono-label">Q{{ i + 1 }} · Cambridge {{ p.q.subject_code }} {{ p.q.year }}{{ p.q.session }} P{{ p.q.variant }}</p>
          @if (p.mcq; as mcq) {
            <p class="paper__stem">{{ mcq.stem }}</p>
            <div class="choices choices--review">
              @for (opt of mcq.options; track opt.letter) {
                <div
                  class="choice"
                  [class.choice--correct]="opt.letter === mcq.answer"
                  [class.choice--wrong]="answers()[i] === opt.letter && opt.letter !== mcq.answer"
                >
                  <span class="choice__letter">{{ opt.letter }}</span>
                  <span class="choice__text">{{ opt.text }}</span>
                  @if (opt.letter === mcq.answer) { <span class="choice__tag">correct</span> }
                  @else if (answers()[i] === opt.letter) { <span class="choice__tag choice__tag--bad">your answer</span> }
                </div>
              }
            </div>
            <p class="verdict mono-label" [class.verdict--good]="answers()[i] === mcq.answer">
              {{ answers()[i] === mcq.answer ? '✓ Correct' : (answers()[i] ? '✗ Not quite' : '— Skipped') }}
            </p>
          } @else {
            <div class="paper__body" [innerHTML]="rendered(p.q.question_markdown)"></div>
            @if (working()[i]) {
              <p class="mono-label">Your working</p>
              <pre class="mywork">{{ working()[i] }}</pre>
            }
            <div class="scheme">
              <p class="mono-label">Official mark scheme</p>
              <div [innerHTML]="rendered(p.q.mark_scheme_markdown ?? '')"></div>
            </div>
            <label class="selfmark">
              <input type="checkbox" [checked]="selfMarks()[i]" (change)="mark(i, $any($event.target).checked)" />
              I got this one right
            </label>
          }
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
    .paper__stem { margin: 0.8rem 0 1.1rem; font-size: 1.1rem; font-weight: 600; line-height: 1.5; }
    .paper__nav { display: flex; justify-content: space-between; margin-top: 1.2rem; }

    /* MCQ options ---------------------------------------------------------- */
    .choices { display: flex; flex-direction: column; gap: 0.6rem; }
    .choice {
      display: flex; align-items: flex-start; gap: 0.7rem;
      padding: 0.8rem 1rem;
      border: 1.5px solid var(--line-strong); border-radius: 12px;
      cursor: pointer; background: var(--card);
      transition: border-color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
    }
    .choice:hover { border-color: var(--accent); transform: translateY(-1px); }
    .choice input { margin-top: 0.2rem; accent-color: var(--accent); }
    .choice__letter {
      font-family: var(--font-display, inherit); font-weight: 700;
      min-width: 1.3rem; color: var(--accent);
    }
    .choice__text { flex: 1; line-height: 1.45; }
    .choice--picked { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); }

    .choices--review .choice { cursor: default; }
    .choices--review .choice:hover { transform: none; border-color: var(--line-strong); }
    .choice__tag {
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
      padding: 0.15rem 0.5rem; border-radius: 999px; align-self: center;
      background: color-mix(in srgb, var(--success, #16a34a) 16%, transparent); color: var(--success, #16a34a);
    }
    .choice__tag--bad { background: color-mix(in srgb, var(--danger, #dc2626) 16%, transparent); color: var(--danger, #dc2626); }
    .choice--correct { border-color: var(--success, #16a34a); background: color-mix(in srgb, var(--success, #16a34a) 8%, transparent); }
    .choice--wrong { border-color: var(--danger, #dc2626); background: color-mix(in srgb, var(--danger, #dc2626) 7%, transparent); }
    .verdict { margin-top: 0.9rem; font-weight: 700; }
    .verdict--good { color: var(--success, #16a34a); }

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
  protected readonly prepared = signal<Prepared[]>([]);
  protected readonly index = signal(0);
  protected readonly working = signal<Record<number, string>>({});
  protected readonly answers = signal<Record<number, string>>({});
  protected readonly selfMarks = signal<Record<number, boolean>>({});
  protected readonly secondsLeft = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly currentPrep = computed(() => this.prepared()[this.index()] ?? null);
  protected readonly clock = computed(() => {
    const s = this.secondsLeft();
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  });
  // MCQs auto-mark from the answer key; theory questions use the self-mark box.
  protected readonly marked = computed(() => {
    let n = 0;
    this.prepared().forEach((p, i) => {
      if (p.mcq) {
        if (this.answers()[i] && this.answers()[i] === p.mcq.answer) n++;
      } else if (this.selfMarks()[i]) {
        n++;
      }
    });
    return n;
  });
  protected readonly scorePct = computed(() =>
    this.prepared().length
      ? Math.round((100 * this.marked()) / this.prepared().length)
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
      const target = this.length();
      // Over-fetch so dropping broken diagram MCQs still leaves a full paper.
      const ask = Math.min(target * 2, 20);
      const body = await this.api.sample(this.subjectCode(), ask);
      const prepared = this.prepare(body.questions).slice(0, target);
      if (!prepared.length) {
        this.error.set('No clear questions available for that subject yet.');
        return;
      }
      this.prepared.set(prepared);
      this.index.set(0);
      this.working.set({});
      this.answers.set({});
      this.selfMarks.set({});
      this.secondsLeft.set(prepared.length * SECONDS_PER_QUESTION);
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

  /** Parse clean MCQs into radios, drop broken/figure MCQs, keep theory Qs. */
  private prepare(questions: PaperQuestion[]): Prepared[] {
    const out: Prepared[] = [];
    for (const q of questions) {
      const mcq = parseMcq(q);
      if (mcq) {
        if (isRenderable(mcq)) out.push({ q, mcq }); // good MCQ
        // else: un-renderable diagram/garbled MCQ — drop it
      } else {
        out.push({ q, mcq: null }); // readable theory question
      }
    }
    return out;
  }

  protected pick(letter: string): void {
    this.answers.update((a) => ({ ...a, [this.index()]: letter }));
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
    this.prepared.set([]);
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

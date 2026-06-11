import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course } from '../core/models';
import { ShortAnswerApi, ShortAnswerQuestion, ShortAnswerSubmission } from '../core/short-answers';

const MAX_ATTEMPTS = 3;

@Component({
  selector: 'mm-short-answers',
  imports: [RouterLink],
  template: `
    @if (loading()) {
      <p class="mono-label">Opening the practice book…</p>
    } @else if (!course()) {
      <div class="missing rise">
        <h1>Course not found.</h1>
        <a routerLink="/" class="btn btn--ghost">← Back to catalog</a>
      </div>
    } @else if (course(); as c) {
      <article class="practice rise">
        <header class="practice__head">
          <a [routerLink]="['/courses', c.slug]" class="mono-label practice__crumb">
            ← {{ c.title }}
          </a>
          <p class="mono-label">Short-answer practice</p>
          <h1>Practice in your own words</h1>
          <p class="practice__desc">
            Answer in full sentences — an AI grader scores your response against the mark scheme
            and tells you what you nailed and what's missing.
          </p>
        </header>

        @if (loadError(); as message) {
          <p class="error-note" role="alert">{{ message }}</p>
        }

        <div class="layout">
          <aside class="qlist">
            <p class="mono-label">Questions</p>
            @for (question of questions(); track question.id; let i = $index) {
              <button
                type="button"
                class="qlist__item"
                [class.is-active]="selected()?.id === question.id"
                (click)="select(question)"
              >
                <span class="qlist__no mono-label">{{ pad(i + 1) }}</span>
                <span class="qlist__prompt">{{ question.prompt }}</span>
              </button>
            } @empty {
              <p class="quiet">No practice questions published for this course yet.</p>
            }
          </aside>

          @if (selected(); as q) {
            <section class="work">
              <h2 class="work__prompt">{{ q.prompt }}</h2>
              <p class="mono-label">
                worth {{ q.max_score }} {{ q.max_score === 1 ? 'mark' : 'marks' }} ·
                {{ attemptsUsed() }} / {{ maxAttempts }} attempts used
              </p>

              @if (result(); as graded) {
                <div class="grade">
                  <div class="grade__head">
                    <span class="grade__score" [class.grade__score--pass]="graded.score >= graded.max_score / 2">
                      {{ graded.score }} / {{ graded.max_score }}
                    </span>
                    <span class="grade__engine mono-label">
                      {{ graded.engine === 'llm' ? 'Graded by AI' : 'Auto-graded' }}
                    </span>
                  </div>
                  @if (graded.criteria_met.length > 0) {
                    <ul class="criteria">
                      @for (item of graded.criteria_met; track item) {
                        <li class="criteria__item criteria__item--met">
                          <span aria-hidden="true">✓</span> {{ item }}
                        </li>
                      }
                    </ul>
                  }
                  @if (graded.criteria_missing.length > 0) {
                    <ul class="criteria">
                      @for (item of graded.criteria_missing; track item) {
                        <li class="criteria__item criteria__item--missing">
                          <span aria-hidden="true">✗</span> {{ item }}
                        </li>
                      }
                    </ul>
                  }
                  @if (graded.feedback) {
                    <p class="grade__feedback">{{ graded.feedback }}</p>
                  }
                  @if (canAttempt()) {
                    <button type="button" class="btn btn--ghost" (click)="tryAgain()">
                      Try again
                    </button>
                  }
                </div>
              } @else {
                <form (submit)="onSubmit($event)">
                  <textarea
                    rows="6"
                    placeholder="Write your answer here…"
                    aria-label="Your answer"
                    [value]="answer()"
                    (input)="answer.set($any($event.target).value)"
                    [disabled]="busy() || !canAttempt()"
                  ></textarea>
                  @if (error(); as message) {
                    <p class="error-note" role="alert">{{ message }}</p>
                  }
                  <div class="work__actions">
                    @if (!canAttempt()) {
                      <span class="quiet">
                        All {{ maxAttempts }} attempts used — review your feedback below.
                      </span>
                    }
                    <button
                      class="btn btn--accent"
                      type="submit"
                      [disabled]="busy() || !answer().trim() || !canAttempt()"
                    >
                      {{ busy() ? 'Grading…' : 'Submit for grading' }}
                    </button>
                  </div>
                </form>
              }

              @if (history().length > 0) {
                <section class="history">
                  <p class="mono-label">Past attempts</p>
                  @for (attempt of history(); track attempt.id) {
                    <div class="history__item">
                      <div class="history__meta">
                        <span class="history__score">{{ attempt.score }} / {{ attempt.max_score }}</span>
                        <span class="grade__engine mono-label">
                          {{ attempt.engine === 'llm' ? 'Graded by AI' : 'Auto-graded' }}
                        </span>
                        <span class="mono-label">{{ shortDate(attempt.created_at) }}</span>
                      </div>
                      <p class="history__answer">{{ attempt.answer_text }}</p>
                      @if (attempt.feedback) {
                        <p class="history__feedback">{{ attempt.feedback }}</p>
                      }
                    </div>
                  }
                </section>
              }
            </section>
          } @else if (questions().length > 0) {
            <section class="work work--empty">
              <p class="quiet">Pick a question on the left to start practising.</p>
            </section>
          }
        </div>
      </article>
    }
  `,
  styles: `
    .missing {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
      padding: 2rem 0;
    }

    .practice__crumb {
      text-decoration: none;
      display: inline-block;
      margin-bottom: 1.2rem;
      &:hover { color: var(--accent); }
    }

    .practice__head h1 {
      font-size: clamp(2rem, 4.5vw, 3rem);
      margin: 0.4rem 0 0.8rem;
    }

    .practice__desc {
      max-width: 60ch;
      color: var(--ink-soft);
      padding-bottom: 1.4rem;
      border-bottom: 2px solid var(--ink);
      margin-bottom: 1.4rem;
    }

    .layout {
      display: grid;
      grid-template-columns: 290px 1fr;
      gap: 1.6rem;
      align-items: start;
    }

    .qlist {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .qlist__item {
      display: flex;
      gap: 0.7rem;
      align-items: baseline;
      padding: 0.65rem 0.8rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 8px;
      cursor: pointer;
      text-align: left;
      font-family: var(--font-body);
      font-size: 0.88rem;
      color: var(--ink);

      &.is-active { border-color: var(--accent); }
      &:hover { border-color: var(--line-strong); }
      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    }

    .qlist__no {
      color: var(--accent);
      font-weight: 600;
    }

    .qlist__prompt {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .quiet { color: var(--ink-soft); }

    .work__prompt {
      font-size: 1.35rem;
      margin-bottom: 0.4rem;
    }

    .work textarea {
      width: 100%;
      margin-top: 0.9rem;
      padding: 0.85rem 1rem;
      border: 1.5px solid var(--line-strong);
      border-radius: 10px;
      background: var(--card);
      font-family: var(--font-body);
      font-size: 0.95rem;
      resize: vertical;

      &:focus {
        outline: none;
        border-color: var(--accent);
      }
    }

    .work__actions {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      margin-top: 0.8rem;
    }

    .grade {
      margin-top: 1rem;
      padding: 1.2rem;
      background: var(--card);
      border: 1.5px solid var(--ink);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      align-items: flex-start;
    }

    .grade__head {
      display: flex;
      align-items: baseline;
      gap: 0.8rem;
    }

    .grade__score {
      font-family: var(--font-display);
      font-size: 2rem;
      font-weight: 640;
      color: var(--accent-deep);

      &--pass { color: var(--sage-deep); }
    }

    .grade__engine {
      padding: 0.15rem 0.55rem;
      border: 1px solid var(--line-strong);
      border-radius: 999px;
      color: var(--ink-soft);
    }

    .criteria {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .criteria__item {
      display: flex;
      gap: 0.5rem;
      font-size: 0.92rem;

      span { font-weight: 700; }
    }

    .criteria__item--met span { color: var(--sage); }
    .criteria__item--missing span { color: var(--danger); }

    .grade__feedback {
      font-size: 0.95rem;
      color: var(--ink-soft);
      border-left: 3px solid var(--line-strong);
      padding-left: 0.8rem;
    }

    .history {
      margin-top: 1.8rem;
      padding-top: 1.2rem;
      border-top: 1px dashed var(--line-strong);
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }

    .history__item {
      padding: 0.85rem 1rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 10px;
    }

    .history__meta {
      display: flex;
      align-items: baseline;
      gap: 0.7rem;
      flex-wrap: wrap;
      margin-bottom: 0.4rem;
    }

    .history__score {
      font-weight: 700;
      font-size: 0.95rem;
    }

    .history__answer {
      font-size: 0.9rem;
      white-space: pre-wrap;
    }

    .history__feedback {
      margin-top: 0.4rem;
      font-size: 0.88rem;
      color: var(--ink-soft);
    }

    @media (max-width: 860px) {
      .layout { grid-template-columns: 1fr; }
    }
  `,
})
export class ShortAnswersPage {
  private readonly api = inject(LearningApi);
  private readonly shortAnswers = inject(ShortAnswerApi);
  private readonly route = inject(ActivatedRoute);

  protected readonly maxAttempts = MAX_ATTEMPTS;

  protected readonly course = signal<Course | null>(null);
  protected readonly questions = signal<ShortAnswerQuestion[]>([]);
  protected readonly selected = signal<ShortAnswerQuestion | null>(null);
  protected readonly answer = signal('');
  protected readonly result = signal<ShortAnswerSubmission | null>(null);
  protected readonly history = signal<ShortAnswerSubmission[]>([]);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly loadError = signal<string | null>(null);

  /** Set when the backend reports the attempt cap, even if history is stale. */
  private readonly capReported = signal(false);

  protected readonly attemptsUsed = computed(() => this.history().length);
  protected readonly canAttempt = computed(
    () => !this.capReported() && this.attemptsUsed() < MAX_ATTEMPTS,
  );

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      if (slug && this.course()?.slug !== slug) {
        void this.load(slug);
      }
    });
  }

  private async load(slug: string): Promise<void> {
    this.loading.set(true);
    this.loadError.set(null);
    try {
      const course = await this.api.getCourse(slug);
      this.course.set(course);
      const questions = await this.shortAnswers.list(course.id);
      this.questions.set(questions.filter((q) => q.is_published));
    } catch (err) {
      if (this.course()) {
        this.loadError.set(apiErrorMessage(err, 'Could not load the practice questions.'));
      } else {
        this.course.set(null);
      }
    } finally {
      this.loading.set(false);
    }
  }

  protected select(question: ShortAnswerQuestion): void {
    if (this.selected()?.id === question.id) return;
    this.selected.set(question);
    this.answer.set('');
    this.result.set(null);
    this.error.set(null);
    this.capReported.set(false);
    this.history.set([]);
    void this.loadHistory(question.id);
  }

  private async loadHistory(questionId: number): Promise<void> {
    try {
      const past = await this.shortAnswers.submissions(questionId);
      if (this.selected()?.id !== questionId) return;
      // Newest first so the latest feedback sits at the top.
      this.history.set(
        [...past].sort((a, b) => b.created_at.localeCompare(a.created_at)),
      );
    } catch {
      // Past attempts are a nice-to-have — never block answering on them.
    }
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    void this.submit();
  }

  private async submit(): Promise<void> {
    const question = this.selected();
    const answer = this.answer().trim();
    if (!question || !answer || this.busy() || !this.canAttempt()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      const graded = await this.shortAnswers.submit(question.id, answer);
      this.result.set(graded);
      this.history.update((all) => [graded, ...all]);
    } catch (err) {
      const message = apiErrorMessage(err, 'Grading failed — please try again.');
      if (
        err instanceof HttpErrorResponse &&
        err.status === 400 &&
        message.toLowerCase().includes('attempt')
      ) {
        this.capReported.set(true);
        this.error.set('You have used all your attempts for this question.');
      } else {
        this.error.set(message);
      }
    } finally {
      this.busy.set(false);
    }
  }

  protected tryAgain(): void {
    this.result.set(null);
    this.answer.set('');
    this.error.set(null);
  }

  protected pad(n: number): string {
    return String(n).padStart(2, '0');
  }

  protected shortDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

import { Component, effect, inject, input, signal } from '@angular/core';

import { staggerDelay } from '../core/animations';
import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course, ShortAnswerQuestion, ShortAnswerSubmission } from '../core/models';

/**
 * Short-answer authoring + AI-marked submission review for one course.
 * Rendered as a tab inside the course workbench.
 */
@Component({
  selector: 'st-short-answers-tab',
  template: `
    @if (error(); as message) {
      <p class="error-note" role="alert" style="margin-bottom: 1rem">{{ message }}</p>
    }

    @if (loading()) {
      <p class="tag" style="padding: 1.2rem 0">Pulling short-answer sheets…</p>
    } @else {
      <div class="rows">
        @if (questions().length === 0) {
          <p class="tag" style="padding: 0.6rem 0">
            No short-answer questions yet — draft the first one below.
          </p>
        }

        @for (question of questions(); track question.id; let i = $index) {
          <div class="panel sa sheet-in" [style.animation-delay.ms]="stagger(i)">
            @if (editingId() === question.id) {
              <form (submit)="saveEdit($event, question)">
                <p class="tag">Editing question</p>
                <label class="field">
                  <span class="tag">Prompt</span>
                  <textarea required [value]="prompt()" (input)="prompt.set($any($event.target).value)"></textarea>
                </label>
                <label class="field">
                  <span class="tag">Topic (optional)</span>
                  <input type="text" maxlength="100" placeholder="Kinematics" [value]="topic()" (input)="topic.set($any($event.target).value)" />
                </label>
                <label class="field">
                  <span class="tag">Mark scheme — one criterion per line</span>
                  <textarea required [value]="markScheme()" (input)="markScheme.set($any($event.target).value)"></textarea>
                </label>
                <div class="sa__inline">
                  <label class="field">
                    <span class="tag">Max score</span>
                    <input type="number" min="1" required [value]="maxScore()" (input)="maxScore.set(+$any($event.target).value)" />
                  </label>
                  <label class="check">
                    <input type="checkbox" [checked]="isPublished()" (change)="isPublished.set($any($event.target).checked)" />
                    <span class="tag">Published</span>
                  </label>
                </div>
                <div class="sa__actions">
                  <button class="btn btn--sm" type="submit" [disabled]="busy()">Save changes</button>
                  <button class="btn btn--line btn--sm" type="button" (click)="cancelEdit()" [disabled]="busy()">
                    Cancel
                  </button>
                </div>
              </form>
            } @else {
              <div class="sa__head">
                <span class="tag sa__no">{{ question.order }}</span>
                <div class="sa__body">
                  <strong>{{ question.prompt }}</strong>
                  <span class="tag">
                    {{ question.max_score }} pts · {{ question.is_published ? 'published' : 'draft' }}
                    @if (question.topic) {
                      <span class="topic-tag">{{ question.topic }}</span>
                    }
                  </span>
                </div>
                <div class="sa__actions">
                  <button class="btn btn--line btn--sm" (click)="startEdit(question)" [disabled]="busy()">Edit</button>
                  <button class="btn btn--line btn--sm" (click)="togglePublish(question)" [disabled]="busy()">
                    {{ question.is_published ? 'Unpublish' : 'Publish' }}
                  </button>
                  <button class="btn btn--danger btn--sm" (click)="remove(question)" [disabled]="busy()">Delete</button>
                </div>
              </div>

              <details class="scheme">
                <summary class="tag">Mark scheme</summary>
                <ul>
                  @for (criterion of criteria(question); track $index) {
                    <li>{{ criterion }}</li>
                  }
                </ul>
              </details>

              <div class="subs">
                <button
                  type="button"
                  class="btn btn--line btn--sm"
                  (click)="toggleSubmissions(question)"
                  [attr.aria-expanded]="openSubmissions() === question.id"
                >
                  {{ openSubmissions() === question.id ? 'Hide submissions' : 'View submissions' }}
                </button>

                @if (openSubmissions() === question.id) {
                  @if (subsLoading()) {
                    <p class="tag" style="margin-top: 0.8rem">Collecting answer sheets…</p>
                  } @else if (submissions().length === 0) {
                    <p class="tag" style="margin-top: 0.8rem">No submissions yet for this question.</p>
                  } @else {
                    <div class="subs__list">
                      @for (sub of submissions(); track sub.id; let si = $index) {
                        <article class="panel sub sheet-in" [style.animation-delay.ms]="stagger(si)">
                          <header class="sub__head">
                            <strong>{{ sub.student_name || sub.student_email }}</strong>
                            <span class="tag">{{ sub.created_at.slice(0, 10) }}</span>
                            <span class="tag sub__engine">{{ sub.engine }}</span>
                            <span class="sub__score">{{ sub.score }} / {{ sub.max_score }}</span>
                          </header>
                          <p class="sub__answer">{{ sub.answer_text }}</p>
                          <ul class="sub__criteria">
                            @for (met of sub.criteria_met; track $index) {
                              <li class="is-met"><span aria-hidden="true">✓</span> {{ met }}</li>
                            }
                            @for (missing of sub.criteria_missing; track $index) {
                              <li class="is-missing"><span aria-hidden="true">✗</span> {{ missing }}</li>
                            }
                          </ul>
                          @if (sub.feedback) {
                            <p class="sub__feedback"><span class="tag">AI feedback</span> {{ sub.feedback }}</p>
                          }
                        </article>
                      }
                    </div>
                  }
                }
              </div>
            }
          </div>
        }

        <div class="panel composer">
          <p class="tag">New short-answer question</p>
          <form (submit)="add($event)">
            <label class="field">
              <span class="tag">Prompt</span>
              <textarea required [value]="newPrompt()" (input)="newPrompt.set($any($event.target).value)"></textarea>
            </label>
            <label class="field">
              <span class="tag">Topic (optional)</span>
              <input type="text" maxlength="100" placeholder="Kinematics" [value]="newTopic()" (input)="newTopic.set($any($event.target).value)" />
            </label>
            <label class="field">
              <span class="tag">Mark scheme — one criterion per line</span>
              <textarea
                required
                placeholder="Mentions gradient descent&#10;Explains the learning rate&#10;Gives a concrete example"
                [value]="newMarkScheme()"
                (input)="newMarkScheme.set($any($event.target).value)"
              ></textarea>
            </label>
            <div class="sa__inline">
              <label class="field">
                <span class="tag">Max score</span>
                <input type="number" min="1" required [value]="newMaxScore()" (input)="newMaxScore.set(+$any($event.target).value)" />
              </label>
              <label class="check">
                <input type="checkbox" [checked]="newPublished()" (change)="newPublished.set($any($event.target).checked)" />
                <span class="tag">Publish immediately</span>
              </label>
            </div>
            <button class="btn" type="submit" [disabled]="busy()">Add question</button>
          </form>
        </div>
      </div>
    }
  `,
  styles: `
    .rows {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }

    .sa form,
    .composer form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-top: 0.5rem;

      .btn { align-self: flex-start; }
    }

    .sa__head {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .sa__no {
      color: var(--amber);
      width: 1.6rem;
      padding-top: 0.2rem;
    }

    .sa__body {
      flex: 1;
      min-width: 220px;
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }

    .sa__actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .topic-tag {
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      padding: 0.05rem 0.5rem;
      margin-left: 0.5rem;
    }

    .sa__inline {
      display: flex;
      align-items: flex-end;
      gap: 1.4rem;
      flex-wrap: wrap;

      .field input { width: 110px; }
    }

    .check {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding-bottom: 0.7rem;
      cursor: pointer;

      input { accent-color: var(--amber); }
    }

    .scheme {
      margin-top: 0.9rem;
      border-top: 1px dashed var(--line);
      padding-top: 0.7rem;

      summary { cursor: pointer; }

      ul {
        margin: 0.6rem 0 0;
        padding-left: 1.2rem;
        color: var(--ink-dim);
        font-size: 0.88rem;

        li { margin-bottom: 0.2rem; }
      }
    }

    .subs {
      margin-top: 0.9rem;
      border-top: 1px solid var(--line);
      padding-top: 0.9rem;
    }

    .subs__list {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      margin-top: 0.9rem;
    }

    .sub {
      background: var(--panel-raised);
      padding: 1rem 1.1rem;
    }

    .sub__head {
      display: flex;
      align-items: baseline;
      gap: 0.8rem;
      flex-wrap: wrap;
    }

    .sub__engine {
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      padding: 0.05rem 0.5rem;
    }

    .sub__score {
      margin-left: auto;
      font-family: var(--font-mono);
      font-weight: 700;
      color: var(--amber);
    }

    .sub__answer {
      margin: 0.6rem 0;
      font-size: 0.92rem;
      white-space: pre-wrap;
    }

    .sub__criteria {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      font-size: 0.86rem;

      .is-met { color: var(--teal); }
      .is-missing { color: var(--red); }

      span { font-family: var(--font-mono); margin-right: 0.3rem; }
    }

    .sub__feedback {
      margin-top: 0.7rem;
      padding-top: 0.6rem;
      border-top: 1px dashed var(--line);
      font-size: 0.88rem;
      color: var(--ink-dim);

      .tag { margin-right: 0.5rem; }
    }
  `,
})
export class ShortAnswersTab {
  private readonly api = inject(StudioApi);

  readonly course = input.required<Course>();

  protected readonly questions = signal<ShortAnswerQuestion[]>([]);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Question id whose submissions panel is open, or null. */
  protected readonly openSubmissions = signal<number | null>(null);
  protected readonly submissions = signal<ShortAnswerSubmission[]>([]);
  protected readonly subsLoading = signal(false);

  // Edit-in-place form state.
  protected readonly editingId = signal<number | null>(null);
  protected readonly prompt = signal('');
  protected readonly topic = signal('');
  protected readonly markScheme = signal('');
  protected readonly maxScore = signal(10);
  protected readonly isPublished = signal(false);

  // Composer form state.
  protected readonly newPrompt = signal('');
  protected readonly newTopic = signal('');
  protected readonly newMarkScheme = signal('');
  protected readonly newMaxScore = signal(10);
  protected readonly newPublished = signal(true);

  constructor() {
    effect(() => {
      const courseId = this.course().id;
      void this.load(courseId);
    });
  }

  private async load(courseId: number): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      this.questions.set(await this.api.shortAnswers(courseId));
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load short-answer questions.'));
    } finally {
      this.loading.set(false);
    }
  }

  private async run(action: () => Promise<unknown>, failure: string): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
      this.questions.set(await this.api.shortAnswers(this.course().id));
    } catch (err) {
      this.error.set(apiErrorMessage(err, failure));
    } finally {
      this.busy.set(false);
    }
  }

  /** Entrance-stagger delay (ms) for the nth row, capped at ~10. */
  protected stagger(index: number): number {
    return staggerDelay(index);
  }

  protected criteria(question: ShortAnswerQuestion): string[] {
    return question.mark_scheme
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
  }

  protected add(event: Event): void {
    event.preventDefault();
    const prompt = this.newPrompt().trim();
    const scheme = this.newMarkScheme().trim();
    if (!prompt || !scheme) {
      this.error.set('A question needs both a prompt and a mark scheme.');
      return;
    }
    const nextOrder = Math.max(0, ...this.questions().map((q) => q.order)) + 1;
    void this.run(async () => {
      await this.api.createShortAnswer({
        course: this.course().id,
        prompt,
        topic: this.newTopic().trim(),
        mark_scheme: scheme,
        max_score: this.newMaxScore(),
        is_published: this.newPublished(),
        order: nextOrder,
      });
      this.newPrompt.set('');
      this.newTopic.set('');
      this.newMarkScheme.set('');
      this.newMaxScore.set(10);
      this.newPublished.set(true);
    }, 'Could not add the question.');
  }

  protected startEdit(question: ShortAnswerQuestion): void {
    this.editingId.set(question.id);
    this.prompt.set(question.prompt);
    this.topic.set(question.topic ?? '');
    this.markScheme.set(question.mark_scheme);
    this.maxScore.set(question.max_score);
    this.isPublished.set(question.is_published);
  }

  protected cancelEdit(): void {
    this.editingId.set(null);
  }

  protected saveEdit(event: Event, question: ShortAnswerQuestion): void {
    event.preventDefault();
    void this.run(async () => {
      await this.api.updateShortAnswer(question.id, {
        prompt: this.prompt().trim(),
        topic: this.topic().trim(),
        mark_scheme: this.markScheme().trim(),
        max_score: this.maxScore(),
        is_published: this.isPublished(),
      });
      this.editingId.set(null);
    }, 'Could not save the question.');
  }

  protected togglePublish(question: ShortAnswerQuestion): void {
    void this.run(
      () => this.api.updateShortAnswer(question.id, { is_published: !question.is_published }),
      'Could not change the publish state.',
    );
  }

  protected remove(question: ShortAnswerQuestion): void {
    if (!confirm('Delete this short-answer question and its submissions?')) return;
    void this.run(() => this.api.deleteShortAnswer(question.id), 'Could not delete the question.');
  }

  protected toggleSubmissions(question: ShortAnswerQuestion): void {
    if (this.openSubmissions() === question.id) {
      this.openSubmissions.set(null);
      return;
    }
    this.openSubmissions.set(question.id);
    this.submissions.set([]);
    this.subsLoading.set(true);
    this.api
      .shortAnswerSubmissions(question.id)
      .then((subs) => {
        if (this.openSubmissions() === question.id) this.submissions.set(subs);
      })
      .catch((err) => {
        if (this.openSubmissions() === question.id) {
          this.error.set(apiErrorMessage(err, 'Could not load submissions.'));
        }
      })
      // Same guard as above: a stale request settling must not clear the
      // spinner (or set errors) for the panel that is currently open.
      .finally(() => {
        if (this.openSubmissions() === question.id) this.subsLoading.set(false);
      });
  }
}

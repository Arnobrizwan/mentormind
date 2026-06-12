import { Component, effect, inject, input, output, signal, untracked } from '@angular/core';

import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course } from '../core/models';

interface DraftQuestionForm {
  text: string;
  options: string[];
  correct: number;
  topic: string;
}

interface DraftForm {
  title: string;
  lesson: number;
  engine: 'llm' | 'heuristic';
  questions: DraftQuestionForm[];
}

/**
 * "Draft with AI" flow for the quizzes tab: pick a lesson, generate a draft
 * synchronously (can take ~90s), review/edit every question, then persist the
 * quiz + questions via the standard endpoints. Nothing is saved until confirm.
 */
@Component({
  selector: 'st-quiz-ai-draft',
  template: `
    <div class="panel ai">
      <p class="tag">✨ Draft with AI</p>

      @if (error(); as message) {
        <p class="error-note" role="alert" style="margin: 0.8rem 0 0">{{ message }}</p>
      }

      @if (!draft()) {
        @if (course().lessons.length === 0) {
          <p class="tag" style="margin-top: 0.6rem">Add a lesson first — the AI drafts questions from lesson content.</p>
        } @else {
          <div class="ai__row">
            <label class="field">
              <span class="tag">Lesson</span>
              <select
                [value]="lessonId() ?? ''"
                (change)="lessonId.set(+$any($event.target).value)"
                [disabled]="generating()"
              >
                @for (lesson of course().lessons; track lesson.id) {
                  <option [value]="lesson.id">{{ lesson.order }}. {{ lesson.title }}</option>
                }
              </select>
            </label>
            <button class="btn btn--sm" type="button" (click)="generate()" [disabled]="generating()">
              {{ generating() ? 'Drafting…' : '✨ Draft with AI' }}
            </button>
          </div>
          @if (generating()) {
            <div class="ai__wait" role="status">
              <p class="tag">Drafting questions… this can take a minute.</p>
              <div class="ai__bar" aria-hidden="true">
                <div class="ai__bar-sweep"></div>
              </div>
            </div>
          }
        }
      } @else if (draft(); as d) {
        <p class="tag ai__note" role="status">
          Drafted by AI ({{ d.engine === 'llm' ? 'language model' : 'heuristic' }}) — review before publishing.
        </p>

        <form (submit)="confirm($event)">
          <label class="field">
            <span class="tag">Quiz title</span>
            <input type="text" required [value]="d.title" (input)="setTitle($any($event.target).value)" />
          </label>

          @for (question of d.questions; track $index; let qi = $index) {
            <fieldset class="q">
              <legend class="tag">Question {{ qi + 1 }}</legend>
              <div class="q__head">
                <label class="field q__text">
                  <span class="tag">Text</span>
                  <input type="text" required [value]="question.text" (input)="setText(qi, $any($event.target).value)" />
                </label>
                <button
                  class="btn btn--danger btn--sm"
                  type="button"
                  (click)="removeQuestion(qi)"
                  [attr.aria-label]="'Remove question ' + (qi + 1)"
                >
                  Remove
                </button>
              </div>
              <label class="field q__topic">
                <span class="tag">Topic (optional)</span>
                <input
                  type="text"
                  maxlength="100"
                  placeholder="Kinematics"
                  [value]="question.topic"
                  (input)="setTopic(qi, $any($event.target).value)"
                />
              </label>
              <div class="q__options" role="radiogroup" [attr.aria-label]="'Correct answer for question ' + (qi + 1)">
                @for (option of question.options; track $index; let oi = $index) {
                  <div class="q__option">
                    <input
                      type="radio"
                      [name]="'correct-' + qi"
                      [checked]="question.correct === oi"
                      (change)="setCorrect(qi, oi)"
                      [attr.aria-label]="'Option ' + (oi + 1) + ' is correct'"
                    />
                    <input
                      class="q__option-text"
                      type="text"
                      required
                      [value]="option"
                      (input)="setOption(qi, oi, $any($event.target).value)"
                      [attr.aria-label]="'Option ' + (oi + 1) + ' text'"
                    />
                  </div>
                }
              </div>
            </fieldset>
          }

          <div class="ai__actions">
            <button class="btn" type="submit" [disabled]="busy() || d.questions.length === 0">
              {{ busy() ? 'Saving…' : 'Create quiz (' + d.questions.length + ' questions)' }}
            </button>
            <button class="btn btn--line" type="button" (click)="discard()" [disabled]="busy()">
              Discard draft
            </button>
          </div>
        </form>
      }
    </div>
  `,
  styles: `
    .ai__row {
      display: flex;
      align-items: flex-end;
      gap: 1rem;
      flex-wrap: wrap;
      margin-top: 0.6rem;

      .field { min-width: 240px; }
    }

    .ai__wait {
      margin-top: 0.9rem;

      .tag { color: var(--amber); }
    }

    /* Indeterminate processing bar while the AI drafts. */
    .ai__bar {
      height: 4px;
      margin-top: 0.55rem;
      max-width: 420px;
      border-radius: 99px;
      background: rgba(154, 100, 2, 0.15);
      overflow: hidden;
    }

    .ai__bar-sweep {
      height: 100%;
      width: 35%;
      border-radius: 99px;
      background: linear-gradient(90deg, rgba(154, 100, 2, 0.25), var(--amber), rgba(154, 100, 2, 0.25));
      animation: ai-sweep 1.3s ease-in-out infinite;
    }

    @keyframes ai-sweep {
      from { transform: translateX(-120%); }
      to { transform: translateX(420%); }
    }

    .ai__note {
      margin-top: 0.6rem;
      color: var(--teal);
    }

    .ai form {
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
      margin-top: 0.9rem;
    }

    .q {
      border: 1px dashed var(--line-strong);
      border-radius: 6px;
      padding: 0.9rem 1rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.8rem;

      legend { padding: 0 0.4rem; color: var(--amber); }
    }

    .q__head {
      display: flex;
      align-items: flex-end;
      gap: 0.8rem;
    }

    .q__text { flex: 1; }

    .q__topic input { max-width: 280px; }

    .q__options {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .q__option {
      display: flex;
      align-items: center;
      gap: 0.6rem;

      input[type='radio'] { accent-color: var(--teal); flex-shrink: 0; }
    }

    .q__option-text {
      flex: 1;
      background: var(--desk);
      border: 1px solid var(--line-strong);
      border-radius: 4px;
      color: inherit;
      font: inherit;
      font-size: 0.92rem;
      padding: 0.45rem 0.6rem;

      &:focus { outline: none; border-color: var(--amber); }
    }

    .ai__actions {
      display: flex;
      gap: 0.7rem;
      flex-wrap: wrap;
    }
  `,
})
export class QuizAiDraft {
  private readonly api = inject(StudioApi);

  readonly course = input.required<Course>();
  /** Fires after the drafted quiz and its questions are persisted. */
  readonly saved = output<void>();

  protected readonly lessonId = signal<number | null>(null);
  protected readonly generating = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly draft = signal<DraftForm | null>(null);

  constructor() {
    effect(() => {
      const course = this.course();
      if (untracked(this.lessonId) === null && course.lessons.length > 0) {
        this.lessonId.set(course.lessons[0].id);
      }
    });
  }

  protected generate(): void {
    const lessonId = this.lessonId();
    if (lessonId === null || this.generating()) return;
    this.generating.set(true);
    this.error.set(null);
    this.api
      .generateQuizDraft(lessonId)
      .then((d) => {
        this.draft.set({
          title: d.suggested_title,
          lesson: d.lesson,
          engine: d.engine,
          questions: d.questions.map((q) => ({
            text: q.text,
            // Pad to four editable option slots.
            options: [...q.options, '', '', '', ''].slice(0, Math.max(4, q.options.length)),
            correct: q.correct_option_index,
            topic: '',
          })),
        });
      })
      .catch((err) => this.error.set(apiErrorMessage(err, 'Could not draft the quiz.')))
      .finally(() => this.generating.set(false));
  }

  private patchQuestion(index: number, patch: Partial<DraftQuestionForm>): void {
    this.draft.update((d) =>
      d
        ? { ...d, questions: d.questions.map((q, i) => (i === index ? { ...q, ...patch } : q)) }
        : d,
    );
  }

  protected setTitle(value: string): void {
    this.draft.update((d) => (d ? { ...d, title: value } : d));
  }

  protected setText(index: number, value: string): void {
    this.patchQuestion(index, { text: value });
  }

  protected setTopic(index: number, value: string): void {
    this.patchQuestion(index, { topic: value });
  }

  protected setCorrect(index: number, optionIndex: number): void {
    this.patchQuestion(index, { correct: optionIndex });
  }

  protected setOption(index: number, optionIndex: number, value: string): void {
    const question = this.draft()?.questions[index];
    if (!question) return;
    this.patchQuestion(index, {
      options: question.options.map((o, i) => (i === optionIndex ? value : o)),
    });
  }

  protected removeQuestion(index: number): void {
    this.draft.update((d) =>
      d ? { ...d, questions: d.questions.filter((_, i) => i !== index) } : d,
    );
  }

  protected discard(): void {
    this.draft.set(null);
    this.error.set(null);
  }

  protected confirm(event: Event): void {
    event.preventDefault();
    const d = this.draft();
    if (!d || this.busy()) return;

    const title = d.title.trim();
    if (!title) {
      this.error.set('The quiz needs a title.');
      return;
    }
    // Drop empty option slots while keeping track of where the correct answer lands.
    const questions = d.questions.map((q) => {
      const kept = q.options
        .map((option, index) => ({ option: option.trim(), index }))
        .filter((entry) => entry.option.length > 0);
      return {
        text: q.text.trim(),
        options: kept.map((entry) => entry.option),
        correct: kept.findIndex((entry) => entry.index === q.correct),
        topic: q.topic.trim(),
      };
    });
    for (const [i, q] of questions.entries()) {
      if (!q.text || q.options.length < 2 || q.correct === -1) {
        this.error.set(
          `Question ${i + 1} needs text, at least two non-empty options, and a non-empty correct answer.`,
        );
        return;
      }
    }

    this.busy.set(true);
    this.error.set(null);
    void (async () => {
      try {
        const quiz = await this.api.createQuiz({
          course: this.course().id,
          lesson: d.lesson,
          title,
          description: '',
        });
        for (const [i, q] of questions.entries()) {
          await this.api.createQuestion({
            quiz: quiz.id,
            text: q.text,
            options: q.options,
            correct_option_index: q.correct,
            topic: q.topic,
            order: i + 1,
          });
        }
        this.draft.set(null);
        this.saved.emit();
      } catch (err) {
        this.error.set(apiErrorMessage(err, 'Could not save the drafted quiz.'));
      } finally {
        this.busy.set(false);
      }
    })();
  }
}

import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course, Enrollment, Lesson, Quiz, ReadinessRow } from '../core/models';
import { FlashcardsTab } from './flashcards-tab';
import { ProctoringTab } from './proctoring-tab';
import { QuizAiDraft } from './quiz-ai-draft';
import { ShortAnswersTab } from './short-answers-tab';

type Tab = 'lessons' | 'quizzes' | 'short answers' | 'flashcards' | 'exam sessions' | 'roster';

@Component({
  selector: 'st-workbench',
  imports: [RouterLink, ShortAnswersTab, ProctoringTab, FlashcardsTab, QuizAiDraft],
  template: `
    @if (loading()) {
      <p class="tag">Unrolling the blueprint…</p>
    } @else if (!course()) {
      <div class="panel sheet-in">
        <h1>Course not found.</h1>
        <a routerLink="/" class="btn btn--line" style="margin-top: 1rem">← Back to the drawer</a>
      </div>
    } @else if (course(); as c) {
      <a routerLink="/" class="tag crumb">← Course drawer</a>

      <header class="head sheet-in">
        <div class="head__main">
          <h1>{{ c.title }}</h1>
          <span class="tag">/{{ c.slug }} · {{ c.is_published ? 'LIVE' : 'DRAFT' }}</span>
        </div>
        <button
          class="btn"
          [class.btn--line]="c.is_published"
          (click)="togglePublish()"
          [disabled]="busy()"
        >
          {{ c.is_published ? 'Unpublish' : 'Publish course' }}
        </button>
      </header>

      <section class="panel meta sheet-in" style="animation-delay: 60ms">
        <p class="tag">Course sheet</p>
        <form (submit)="saveMeta($event)">
          <label class="field">
            <span class="tag">Title</span>
            <input type="text" [value]="title()" (input)="title.set($any($event.target).value)" />
          </label>
          <label class="field">
            <span class="tag">Description</span>
            <textarea [value]="description()" (input)="description.set($any($event.target).value)"></textarea>
          </label>
          <button class="btn btn--line btn--sm" type="submit" [disabled]="busy()">Save sheet</button>
        </form>
      </section>

      @if (error(); as message) {
        <p class="error-note" role="alert" style="margin-top: 1rem">{{ message }}</p>
      }

      <nav class="tabs" role="tablist">
        @for (t of tabs; track t) {
          <button
            type="button"
            role="tab"
            [attr.aria-selected]="tab() === t"
            [class.is-active]="tab() === t"
            (click)="tab.set(t)"
          >
            {{ t }}
            @if (t === 'lessons') { ({{ c.lessons.length }}) }
            @if (t === 'quizzes') { ({{ c.quizzes.length }}) }
            @if (t === 'roster') { ({{ roster().length }}) }
          </button>
        }
      </nav>

      @switch (tab()) {
        @case ('lessons') {
          <div class="rows">
            @for (lesson of c.lessons; track lesson.id) {
              <div class="panel row">
                <span class="tag row__no">{{ lesson.order }}</span>
                <div class="row__body">
                  <strong>{{ lesson.title }}</strong>
                  <span class="tag">{{ lesson.is_published ? 'published' : 'draft' }}</span>
                </div>
                <div class="row__actions">
                  <button class="btn btn--line btn--sm" (click)="toggleLesson(lesson)" [disabled]="busy()">
                    {{ lesson.is_published ? 'Unpublish' : 'Publish' }}
                  </button>
                  <button class="btn btn--danger btn--sm" (click)="removeLesson(lesson)" [disabled]="busy()">
                    Delete
                  </button>
                </div>
              </div>
            }

            <div class="panel composer">
              <p class="tag">Add lesson</p>
              <form (submit)="addLesson($event)">
                <label class="field">
                  <span class="tag">Title</span>
                  <input type="text" required [value]="lessonTitle()" (input)="lessonTitle.set($any($event.target).value)" />
                </label>
                <label class="field">
                  <span class="tag">Content (markdown or text)</span>
                  <textarea required [value]="lessonContent()" (input)="lessonContent.set($any($event.target).value)"></textarea>
                </label>
                <label class="field">
                  <span class="tag">Video URL (optional)</span>
                  <input type="url" [value]="lessonVideo()" (input)="lessonVideo.set($any($event.target).value)" />
                </label>
                <button class="btn" type="submit" [disabled]="busy()">Add to syllabus</button>
              </form>
            </div>
          </div>
        }

        @case ('quizzes') {
          <div class="rows">
            @for (quiz of c.quizzes; track quiz.id) {
              <div class="panel quiz">
                <div class="quiz__head">
                  <strong>{{ quiz.title }}</strong>
                  <button class="btn btn--danger btn--sm" (click)="removeQuiz(quiz)" [disabled]="busy()">
                    Delete quiz
                  </button>
                </div>

                <ol class="questions">
                  @for (question of quiz.questions; track question.id) {
                    <li>
                      <span>{{ question.text }}</span>
                      @if (question.topic) {
                        <span class="tag topic-tag">{{ question.topic }}</span>
                      }
                      <span class="tag">
                        ✓ {{ question.options[question.correct_option_index ?? 0] }}
                      </span>
                      <button class="btn btn--danger btn--sm" (click)="removeQuestion(question.id)" [disabled]="busy()">×</button>
                    </li>
                  }
                </ol>

                <form class="q-form" (submit)="addQuestion($event, quiz)">
                  <label class="field">
                    <span class="tag">New question</span>
                    <input type="text" required [value]="questionText()[quiz.id] || ''" (input)="setQuestionText(quiz.id, $any($event.target).value)" />
                  </label>
                  <label class="field">
                    <span class="tag">Topic (optional)</span>
                    <input
                      type="text"
                      maxlength="100"
                      placeholder="Kinematics"
                      [value]="questionTopic()[quiz.id] || ''"
                      (input)="setQuestionTopic(quiz.id, $any($event.target).value)"
                    />
                  </label>
                  <label class="field">
                    <span class="tag">Options — one per line, prefix the correct one with *</span>
                    <textarea
                      required
                      placeholder="*Machine Learning&#10;Max Likelihood&#10;My Life"
                      [value]="questionOptions()[quiz.id] || ''"
                      (input)="setQuestionOptions(quiz.id, $any($event.target).value)"
                    ></textarea>
                  </label>
                  <button class="btn btn--line btn--sm" type="submit" [disabled]="busy()">Add question</button>
                </form>
              </div>
            }

            <st-quiz-ai-draft [course]="c" (saved)="refresh()" />

            <div class="panel composer">
              <p class="tag">New quiz</p>
              <form (submit)="addQuiz($event)">
                <label class="field">
                  <span class="tag">Title</span>
                  <input type="text" required [value]="quizTitle()" (input)="quizTitle.set($any($event.target).value)" />
                </label>
                <button class="btn" type="submit" [disabled]="busy()">Create quiz</button>
              </form>
            </div>
          </div>
        }

        @case ('short answers') {
          <st-short-answers-tab [course]="c" />
        }

        @case ('flashcards') {
          <st-flashcards-tab [course]="c" />
        }

        @case ('exam sessions') {
          <st-proctoring-tab [course]="c" />
        }

        @case ('roster') {
          @if (roster().length === 0) {
            <p class="tag" style="padding: 1.2rem 0">No students enrolled yet.</p>
          } @else {
            <table class="roster">
              <thead>
                <tr>
                  <th class="tag">Student</th>
                  <th class="tag">Enrolled</th>
                  <th class="tag">Progress</th>
                  <th class="tag">Quiz attempts</th>
                  <th class="tag">Exam readiness</th>
                </tr>
              </thead>
              <tbody>
                @for (enrollment of roster(); track enrollment.id) {
                  <tr>
                    <td>{{ enrollment.student_name || enrollment.student_email }}</td>
                    <td class="tag">{{ enrollment.enrolled_at.slice(0, 10) }}</td>
                    <td>
                      <div class="bar"><div class="bar__fill" [style.width.%]="enrollment.progress_percentage"></div></div>
                      <span class="tag">{{ enrollment.progress_percentage }}%</span>
                    </td>
                    <td class="tag">{{ enrollment.quiz_attempts.length }}</td>
                    <td>
                      @if (readinessFor(enrollment.id); as r) {
                        <div class="bar" [title]="readinessTitle(r)">
                          <div
                            class="bar__fill"
                            [class.bar__fill--mid]="r.readiness >= 40 && r.readiness < 70"
                            [class.bar__fill--low]="r.readiness < 40"
                            [style.width.%]="r.readiness"
                          ></div>
                        </div>
                        <span
                          class="tag ready"
                          [class.ready--ok]="r.readiness >= 70"
                          [class.ready--mid]="r.readiness >= 40 && r.readiness < 70"
                          [class.ready--low]="r.readiness < 40"
                          [title]="readinessTitle(r)"
                        >
                          {{ r.readiness }}
                        </span>
                      } @else {
                        <span class="tag">—</span>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
        }
      }
    }
  `,
  styles: `
    .crumb {
      text-decoration: none;
      display: inline-block;
      margin-bottom: 1rem;
      transition: color 160ms ease, transform 160ms ease;
      &:hover { color: var(--amber); transform: translateX(-2px); }
    }

    .head {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1.4rem;
      flex-wrap: wrap;
      margin-bottom: 1.2rem;

      h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); margin-bottom: 0.3rem; }
    }

    .meta form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-top: 0.7rem;

      .btn { align-self: flex-start; }
    }

    .tabs {
      display: flex;
      gap: 0.3rem;
      margin: 1.6rem 0 1.1rem;
      border-bottom: 1px solid var(--line);

      button {
        padding: 0.55rem 1.1rem;
        background: none;
        border: 0;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
        color: var(--ink-dim);
        font-family: var(--font-mono);
        font-size: 0.78rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        cursor: pointer;
        transition: color 160ms ease, border-bottom-color 160ms ease, background 160ms ease;

        &:hover {
          color: var(--ink);
          background: rgba(31, 28, 22, 0.04);
        }

        &.is-active {
          color: var(--amber);
          border-bottom-color: var(--amber);
        }
      }
    }

    .rows {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }

    .row {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.9rem 1.2rem;
    }

    .row__no {
      color: var(--amber);
      width: 1.6rem;
    }

    .row__body {
      flex: 1;
      display: flex;
      align-items: baseline;
      gap: 0.8rem;
      flex-wrap: wrap;
    }

    .row__actions {
      display: flex;
      gap: 0.5rem;
    }

    .composer form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-top: 0.7rem;

      .btn { align-self: flex-start; }
    }

    .quiz__head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }

    .questions {
      list-style: none;
      margin: 0.9rem 0;
      padding: 0;
      display: flex;
      flex-direction: column;

      li {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        padding: 0.55rem 0;
        border-bottom: 1px dashed var(--line);

        span:first-child { flex: 1; }
      }
    }

    .q-form {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      padding-top: 0.8rem;
      border-top: 1px solid var(--line);

      .btn { align-self: flex-start; }
    }

    .roster {
      width: 100%;
      border-collapse: collapse;

      th { text-align: left; padding: 0.55rem 0.6rem; border-bottom: 1px solid var(--line-strong); }
      td { padding: 0.7rem 0.6rem; border-bottom: 1px dashed var(--line); font-size: 0.92rem; }
    }

    .bar {
      width: 130px;
      height: 7px;
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      overflow: hidden;
      display: inline-block;
      margin-right: 0.6rem;
      vertical-align: middle;
      background: var(--desk);
    }

    .bar__fill {
      height: 100%;
      background: var(--teal);
      transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1), background 160ms ease;
      animation: bar-grow 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes bar-grow {
      from { transform: scaleX(0); transform-origin: left center; }
      to { transform: scaleX(1); transform-origin: left center; }
    }

    .bar__fill--mid { background: var(--amber); }
    .bar__fill--low { background: var(--red); }

    .ready {
      font-weight: 700;
    }

    .ready--ok { color: var(--teal); }
    .ready--mid { color: var(--amber); }
    .ready--low { color: var(--red); }

    .topic-tag {
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      padding: 0.05rem 0.5rem;
    }
  `,
})
export class WorkbenchPage {
  private readonly api = inject(StudioApi);
  private readonly route = inject(ActivatedRoute);

  protected readonly tabs: Tab[] = ['lessons', 'quizzes', 'short answers', 'flashcards', 'exam sessions', 'roster'];
  protected readonly tab = signal<Tab>('lessons');

  protected readonly course = signal<Course | null>(null);
  protected readonly roster = signal<Enrollment[]>([]);
  protected readonly readinessRows = signal<ReadinessRow[]>([]);
  private readonly readinessByEnrollment = computed(
    () => new Map(this.readinessRows().map((row) => [row.enrollment, row])),
  );
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly title = signal('');
  protected readonly description = signal('');
  protected readonly lessonTitle = signal('');
  protected readonly lessonContent = signal('');
  protected readonly lessonVideo = signal('');
  protected readonly quizTitle = signal('');
  protected readonly questionText = signal<Record<number, string>>({});
  protected readonly questionTopic = signal<Record<number, string>>({});
  protected readonly questionOptions = signal<Record<number, string>>({});

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      if (slug) void this.load(slug);
    });
  }

  private async load(slug: string): Promise<void> {
    this.loading.set(true);
    try {
      const course = await this.api.getCourse(slug);
      this.course.set(course);
      this.title.set(course.title);
      this.description.set(course.description);
      this.roster.set(await this.api.students(slug).catch(() => []));
      this.readinessRows.set(await this.api.readiness(slug).catch(() => []));
    } catch {
      this.course.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  private async reload(): Promise<void> {
    const c = this.course();
    if (c) await this.load(c.slug);
  }

  /** Reload the course after a child tab persists something (e.g. AI quiz draft). */
  protected refresh(): void {
    void this.reload();
  }

  protected readinessFor(enrollmentId: number): ReadinessRow | undefined {
    return this.readinessByEnrollment().get(enrollmentId);
  }

  protected readinessTitle(row: ReadinessRow): string {
    const c = row.components;
    return (
      `Progress ${c.progress_pct}% · Quiz avg ${c.quiz_avg} · ` +
      `Practice volume ${c.practice_volume} · Accuracy ${c.accuracy}`
    );
  }

  private async run(action: () => Promise<unknown>, failure: string): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
      await this.reload();
    } catch (err) {
      this.error.set(apiErrorMessage(err, failure));
    } finally {
      this.busy.set(false);
    }
  }

  protected togglePublish(): void {
    const c = this.course();
    if (!c) return;
    void this.run(
      () => this.api.updateCourse(c.slug, { is_published: !c.is_published }),
      'Could not change the publish state.',
    );
  }

  protected saveMeta(event: Event): void {
    event.preventDefault();
    const c = this.course();
    if (!c) return;
    void this.run(
      () => this.api.updateCourse(c.slug, { title: this.title(), description: this.description() }),
      'Could not save the course sheet.',
    );
  }

  protected addLesson(event: Event): void {
    event.preventDefault();
    const c = this.course();
    if (!c) return;
    const nextOrder = Math.max(0, ...c.lessons.map((l) => l.order)) + 1;
    void this.run(async () => {
      await this.api.createLesson({
        course: c.id,
        title: this.lessonTitle(),
        content: this.lessonContent(),
        video_url: this.lessonVideo() || null,
        order: nextOrder,
        is_published: true,
      });
      this.lessonTitle.set('');
      this.lessonContent.set('');
      this.lessonVideo.set('');
    }, 'Could not add the lesson.');
  }

  protected toggleLesson(lesson: Lesson): void {
    void this.run(
      () => this.api.updateLesson(lesson.id, { is_published: !lesson.is_published }),
      'Could not update the lesson.',
    );
  }

  protected removeLesson(lesson: Lesson): void {
    void this.run(() => this.api.deleteLesson(lesson.id), 'Could not delete the lesson.');
  }

  protected addQuiz(event: Event): void {
    event.preventDefault();
    const c = this.course();
    if (!c) return;
    void this.run(async () => {
      await this.api.createQuiz({ course: c.id, title: this.quizTitle(), description: '' });
      this.quizTitle.set('');
    }, 'Could not create the quiz.');
  }

  protected removeQuiz(quiz: Quiz): void {
    void this.run(() => this.api.deleteQuiz(quiz.id), 'Could not delete the quiz.');
  }

  protected setQuestionText(quizId: number, value: string): void {
    this.questionText.update((m) => ({ ...m, [quizId]: value }));
  }

  protected setQuestionTopic(quizId: number, value: string): void {
    this.questionTopic.update((m) => ({ ...m, [quizId]: value }));
  }

  protected setQuestionOptions(quizId: number, value: string): void {
    this.questionOptions.update((m) => ({ ...m, [quizId]: value }));
  }

  protected addQuestion(event: Event, quiz: Quiz): void {
    event.preventDefault();
    const text = (this.questionText()[quiz.id] || '').trim();
    const lines = (this.questionOptions()[quiz.id] || '')
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    const correct = lines.findIndex((l) => l.startsWith('*'));
    if (!text || lines.length < 2 || correct === -1) {
      this.error.set(
        'A question needs text plus at least two options, with the correct one marked by a leading *.',
      );
      return;
    }
    const options = lines.map((l) => l.replace(/^\*/, '').trim());
    const nextOrder = Math.max(0, ...quiz.questions.map((q) => q.order)) + 1;
    void this.run(async () => {
      await this.api.createQuestion({
        quiz: quiz.id,
        text,
        options,
        correct_option_index: correct,
        topic: (this.questionTopic()[quiz.id] || '').trim(),
        order: nextOrder,
      });
      this.setQuestionText(quiz.id, '');
      this.setQuestionTopic(quiz.id, '');
      this.setQuestionOptions(quiz.id, '');
    }, 'Could not add the question.');
  }

  protected removeQuestion(id: number): void {
    void this.run(() => this.api.deleteQuestion(id), 'Could not delete the question.');
  }
}

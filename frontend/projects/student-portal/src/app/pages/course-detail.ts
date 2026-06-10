import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { Course, Quiz } from '../core/models';

@Component({
  selector: 'mm-course-detail',
  imports: [RouterLink],
  template: `
    @if (loading()) {
      <p class="mono-label">Opening the course file…</p>
    } @else if (!course()) {
      <div class="missing rise">
        <h1>Course not found.</h1>
        <p>This entry isn't in the catalog — it may be unpublished.</p>
        <a routerLink="/" class="btn btn--ghost">← Back to catalog</a>
      </div>
    } @else if (course(); as c) {
      <article>
        <header class="head rise">
          <a routerLink="/" class="mono-label head__crumb">← Catalog</a>
          <div class="head__row">
            <div>
              <h1>{{ c.title }}</h1>
              <p class="head__byline">
                taught by <strong>{{ c.instructor_name || 'a mentor' }}</strong>
              </p>
            </div>
            <div class="head__cta">
              @if (enrollment(); as e) {
                <span class="stamp">Enrolled</span>
                <div class="progress" role="progressbar" [attr.aria-valuenow]="e.progress_percentage">
                  <div class="progress__bar" [style.width.%]="e.progress_percentage"></div>
                </div>
                <span class="mono-label">{{ e.progress_percentage }}% complete</span>
              } @else {
                <button class="btn btn--accent" (click)="enroll()" [disabled]="busy()">
                  {{ busy() ? 'Enrolling…' : 'Enroll — it’s free' }}
                </button>
              }
            </div>
          </div>
          <p class="head__desc">{{ c.description }}</p>
          @if (error(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          }
        </header>

        <section class="syllabus rise" style="animation-delay: 120ms">
          <div class="section-head">
            <h2>Syllabus</h2>
            <span class="mono-label">{{ c.lessons.length }} lessons</span>
          </div>
          @if (c.lessons.length === 0) {
            <p class="quiet">No lessons published yet.</p>
          }
          <ol class="lesson-list">
            @for (lesson of c.lessons; track lesson.id; let i = $index) {
              <li class="lesson" [class.lesson--done]="isComplete(lesson.id)">
                <span class="lesson__index mono-label">{{ pad(i + 1) }}</span>
                <div class="lesson__body">
                  <span class="lesson__title">{{ lesson.title }}</span>
                  @if (isComplete(lesson.id)) {
                    <span class="lesson__check" aria-label="completed">✓ done</span>
                  }
                </div>
                @if (enrollment()) {
                  <a class="btn btn--ghost lesson__open" [routerLink]="['/courses', c.slug, 'lessons', lesson.id]">
                    Open
                  </a>
                } @else {
                  <span class="lesson__lock mono-label">enroll to unlock</span>
                }
              </li>
            }
          </ol>
        </section>

        @if (c.quizzes.length > 0) {
          <section class="syllabus rise" style="animation-delay: 200ms">
            <div class="section-head">
              <h2>Quizzes</h2>
              <span class="mono-label">{{ c.quizzes.length }} assessments</span>
            </div>
            <ol class="lesson-list">
              @for (quiz of c.quizzes; track quiz.id) {
                <li class="lesson">
                  <span class="lesson__index mono-label">QZ</span>
                  <div class="lesson__body">
                    <span class="lesson__title">{{ quiz.title }}</span>
                    @if (bestScore(quiz); as best) {
                      <span class="lesson__check">best score: {{ best }}%</span>
                    }
                  </div>
                  @if (enrollment()) {
                    <a class="btn btn--ghost lesson__open" [routerLink]="['/courses', c.slug, 'quiz', quiz.id]">
                      {{ bestScore(quiz) !== null ? 'Retake' : 'Take quiz' }}
                    </a>
                  } @else {
                    <span class="lesson__lock mono-label">enroll to unlock</span>
                  }
                </li>
              }
            </ol>
          </section>
        }
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

    .head__crumb {
      text-decoration: none;
      &:hover { color: var(--accent); }
    }

    .head__row {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 2rem;
      margin: 1rem 0 1.2rem;
      flex-wrap: wrap;
    }

    .head h1 {
      font-size: clamp(2.2rem, 5vw, 3.6rem);
      max-width: 18ch;
    }

    .head__byline {
      margin-top: 0.6rem;
      color: var(--ink-soft);
      strong { color: var(--ink); }
    }

    .head__cta {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      align-items: flex-end;
      min-width: 200px;
    }

    .head__desc {
      max-width: 65ch;
      color: var(--ink-soft);
      font-size: 1.05rem;
      padding-bottom: 1.4rem;
      border-bottom: 2px solid var(--ink);
      margin-bottom: 0.6rem;
    }

    .progress {
      width: 200px;
      height: 8px;
      border: 1px solid var(--ink);
      border-radius: 99px;
      overflow: hidden;
      background: var(--card);
    }

    .progress__bar {
      height: 100%;
      background: var(--sage);
      transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .syllabus {
      padding-top: 2.2rem;
    }

    .section-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 1rem;

      h2 { font-size: 1.7rem; }
    }

    .quiet { color: var(--ink-soft); }

    .lesson-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
    }

    .lesson {
      display: flex;
      align-items: center;
      gap: 1.2rem;
      padding: 0.95rem 0.4rem;
      border-bottom: 1px dashed var(--line-strong);

      &:first-child { border-top: 1px dashed var(--line-strong); }
    }

    .lesson--done .lesson__title {
      color: var(--ink-soft);
    }

    .lesson__index {
      width: 2.2rem;
      color: var(--accent);
      font-weight: 600;
    }

    .lesson__body {
      flex: 1;
      display: flex;
      align-items: baseline;
      gap: 0.8rem;
      flex-wrap: wrap;
    }

    .lesson__title {
      font-weight: 600;
      font-size: 1.02rem;
    }

    .lesson__check {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--sage-deep);
      letter-spacing: 0.08em;
    }

    .lesson__lock {
      letter-spacing: 0.12em;
    }

    .lesson__open {
      padding: 0.4rem 1rem;
      font-size: 0.82rem;
    }
  `,
})
export class CourseDetailPage {
  private readonly api = inject(LearningApi);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly course = signal<Course | null>(null);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly enrollment = computed(() => {
    const c = this.course();
    return c ? this.api.enrollments().find((e) => e.course === c.id) : undefined;
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      if (slug) void this.load(slug);
    });
  }

  private async load(slug: string): Promise<void> {
    this.loading.set(true);
    try {
      this.course.set(await this.api.getCourse(slug));
    } catch {
      this.course.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  protected pad(n: number): string {
    return String(n).padStart(2, '0');
  }

  protected isComplete(lessonId: number): boolean {
    return this.enrollment()?.completed_lessons.includes(lessonId) ?? false;
  }

  protected bestScore(quiz: Quiz): number | null {
    const attempts = this.enrollment()?.quiz_attempts.filter((a) => a.quiz === quiz.id) ?? [];
    if (attempts.length === 0) return null;
    return Math.max(...attempts.map((a) => a.score));
  }

  protected async enroll(): Promise<void> {
    const c = this.course();
    if (!c) return;
    if (!this.auth.isLoggedIn()) {
      void this.router.navigate(['/auth'], { queryParams: { next: `/courses/${c.slug}` } });
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.api.enroll(c.slug);
      // Reload so the now-unlocked lesson content replaces the teaser copy.
      await this.load(c.slug);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Enrollment failed — please try again.'));
    } finally {
      this.busy.set(false);
    }
  }
}

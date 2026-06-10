import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { QuizAttempt } from '../core/models';

interface CourseRef {
  course: number;
  slug: string;
}

@Component({
  selector: 'mm-dashboard',
  imports: [RouterLink],
  template: `
    <section class="desk rise">
      <p class="mono-label">My Desk</p>
      <h1>
        Welcome back,
        <em>{{ firstName() }}.</em>
      </h1>
    </section>

    <div class="stats rise" style="animation-delay: 90ms">
      <div class="stat">
        <span class="stat__number">{{ api.enrollments().length }}</span>
        <span class="mono-label">courses enrolled</span>
      </div>
      <div class="stat">
        <span class="stat__number">{{ averageProgress() }}<small>%</small></span>
        <span class="mono-label">average progress</span>
      </div>
      <div class="stat">
        <span class="stat__number">{{ attempts().length }}</span>
        <span class="mono-label">quiz attempts</span>
      </div>
    </div>

    @if (loading()) {
      <p class="mono-label state-note">Tidying the desk…</p>
    } @else if (api.enrollments().length === 0) {
      <div class="empty rise">
        <h2>Your desk is clear.</h2>
        <p>Enroll in a course from the catalog and it will appear here.</p>
        <a routerLink="/" class="btn btn--accent">Browse the catalog</a>
      </div>
    } @else {
      <section class="block rise" style="animation-delay: 160ms">
        <h2>In progress</h2>
        <div class="enrollments">
          @for (enrollment of api.enrollments(); track enrollment.id) {
            <div class="enrollment">
              <div class="enrollment__info">
                <h3>{{ enrollment.course_title }}</h3>
                <span class="mono-label">
                  enrolled {{ enrollment.enrolled_at.slice(0, 10) }} ·
                  {{ enrollment.completed_lessons.length }} lesson(s) done
                </span>
              </div>
              <div class="enrollment__progress">
                <div class="progress" role="progressbar" [attr.aria-valuenow]="enrollment.progress_percentage">
                  <div class="progress__bar" [style.width.%]="enrollment.progress_percentage"></div>
                </div>
                <span class="mono-label">{{ enrollment.progress_percentage }}%</span>
              </div>
              @if (slugFor(enrollment.course); as slug) {
                <a class="btn btn--ghost enrollment__btn" [routerLink]="['/courses', slug]">
                  {{ enrollment.progress_percentage >= 100 ? 'Review' : 'Continue' }} →
                </a>
              }
            </div>
          }
        </div>
      </section>

      @if (attempts().length > 0) {
        <section class="block rise" style="animation-delay: 230ms">
          <h2>Quiz record</h2>
          <table class="record">
            <thead>
              <tr>
                <th class="mono-label">Quiz</th>
                <th class="mono-label">Score</th>
                <th class="mono-label">Correct</th>
                <th class="mono-label">Date</th>
              </tr>
            </thead>
            <tbody>
              @for (attempt of attempts(); track attempt.id) {
                <tr>
                  <td>{{ attempt.quiz_title }}</td>
                  <td>
                    <span class="score" [class.score--pass]="attempt.score >= 50">
                      {{ attempt.score }}%
                    </span>
                  </td>
                  <td>{{ attempt.correct_answers }} / {{ attempt.total_questions }}</td>
                  <td class="mono-label">{{ attempt.completed_at.slice(0, 10) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      }
    }
  `,
  styles: `
    .desk h1 {
      font-size: clamp(2.2rem, 5vw, 3.6rem);
      margin-top: 0.7rem;

      em {
        font-style: italic;
        color: var(--accent);
      }
    }

    .stats {
      display: flex;
      gap: 0;
      margin: 2rem 0 2.4rem;
      border-top: 2px solid var(--ink);
      border-bottom: 2px solid var(--ink);
    }

    .stat {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      padding: 1.2rem 1.4rem;

      & + .stat {
        border-left: 1px solid var(--line);
      }
    }

    .stat__number {
      font-family: var(--font-display);
      font-size: 2.6rem;
      font-weight: 640;
      line-height: 1;

      small { font-size: 1.2rem; }
    }

    .state-note { padding: 1.5rem 0; }

    .empty {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      align-items: flex-start;
      padding: 1.5rem 0;

      p { color: var(--ink-soft); }
      .btn { margin-top: 0.5rem; }
    }

    .block {
      margin-bottom: 2.6rem;

      h2 {
        font-size: 1.7rem;
        margin-bottom: 1.1rem;
      }
    }

    .enrollments {
      display: flex;
      flex-direction: column;
    }

    .enrollment {
      display: flex;
      align-items: center;
      gap: 1.6rem;
      padding: 1.1rem 0.4rem;
      border-bottom: 1px dashed var(--line-strong);
      flex-wrap: wrap;

      &:first-child { border-top: 1px dashed var(--line-strong); }
    }

    .enrollment__info {
      flex: 1;
      min-width: 220px;

      h3 {
        font-size: 1.25rem;
        margin-bottom: 0.25rem;
      }
    }

    .enrollment__progress {
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }

    .progress {
      width: 160px;
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

    .enrollment__btn {
      font-size: 0.82rem;
      padding: 0.45rem 1rem;
    }

    .record {
      width: 100%;
      border-collapse: collapse;

      th {
        text-align: left;
        padding: 0.6rem 0.4rem;
        border-bottom: 2px solid var(--ink);
      }

      td {
        padding: 0.75rem 0.4rem;
        border-bottom: 1px dashed var(--line-strong);
        font-size: 0.95rem;
      }
    }

    .score {
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--accent-deep);

      &--pass { color: var(--sage-deep); }
    }
  `,
})
export class DashboardPage {
  protected readonly api = inject(LearningApi);
  private readonly auth = inject(AuthService);

  protected readonly loading = signal(true);
  private readonly courseRefs = signal<CourseRef[]>([]);

  protected readonly attempts = computed<QuizAttempt[]>(() =>
    this.api
      .enrollments()
      .flatMap((e) => e.quiz_attempts)
      .sort((a, b) => b.completed_at.localeCompare(a.completed_at)),
  );

  protected readonly averageProgress = computed(() => {
    const all = this.api.enrollments();
    if (all.length === 0) return 0;
    const total = all.reduce((sum, e) => sum + e.progress_percentage, 0);
    return Math.round(total / all.length);
  });

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [, courses] = await Promise.all([
        this.api.refreshEnrollments(),
        this.api.listCourses(),
      ]);
      this.courseRefs.set(courses.map((c) => ({ course: c.id, slug: c.slug })));
    } finally {
      this.loading.set(false);
    }
  }

  protected firstName(): string {
    const user = this.auth.user();
    const name = user?.display_name || user?.email || 'scholar';
    return name.split(/[\s@]/)[0];
  }

  protected slugFor(courseId: number): string | null {
    return this.courseRefs().find((r) => r.course === courseId)?.slug ?? null;
  }
}

import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { CourseLeaderboardRow, LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { SiteConfig } from '../core/site-config';
import { apiErrorMessage } from '../core/errors';
import { Course, Quiz } from '../core/models';
import { PracticeInsightsApi, RecommendedItem } from '../core/practice-insights';
import { ShortAnswerApi } from '../core/short-answers';

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

        @if (leaderboard().length > 0) {
          <section class="syllabus rise" style="animation-delay: 240ms">
            <div class="section-head">
              <h2>Quiz leaderboard</h2>
              <span class="mono-label">top scorers</span>
            </div>
            <ol class="leaderboard">
              @for (row of leaderboard(); track row.rank) {
                <li class="leaderboard__row" [class.leaderboard__row--top]="row.rank === 1">
                  <span class="leaderboard__rank mono-label">#{{ row.rank }}</span>
                  <span class="leaderboard__name">{{ row.student }}</span>
                  <span class="leaderboard__score">{{ row.best_score }}%</span>
                </li>
              }
            </ol>
          </section>
        }

        @if (enrollment() && config.flagEnabled('chat')) {
          <section class="syllabus rise" style="animation-delay: 250ms">
            <div class="section-head">
              <h2>Study hall</h2>
              <span class="mono-label">live chat</span>
            </div>
            <ol class="lesson-list">
              <li class="lesson">
                <span class="lesson__index mono-label">💬</span>
                <div class="lesson__body">
                  <span class="lesson__title">Course chat</span>
                  <span class="lesson__check">ask classmates, share tips, earn Chatterbox points</span>
                </div>
                <a class="btn btn--ghost lesson__open" [routerLink]="['/courses', c.slug, 'chat']">
                  Join chat
                </a>
              </li>
            </ol>
          </section>
        }

        @if (courseDrill().length > 0) {
          <section class="syllabus rise" style="animation-delay: 255ms">
            <div class="section-head">
              <h2>Weak-topic drill</h2>
              <span class="mono-label">adaptive practice</span>
            </div>
            <ol class="lesson-list">
              @for (item of courseDrill(); track item.type + '-' + item.id) {
                <li class="lesson">
                  <span class="lesson__index mono-label">{{ item.type === 'quiz' ? 'QZ' : 'SA' }}</span>
                  <div class="lesson__body">
                    <span class="lesson__title">{{ item.title }}</span>
                    <span class="lesson__check">{{ item.topic }} · {{ item.preview }}</span>
                  </div>
                  <a class="btn btn--ghost lesson__open" [routerLink]="drillLink(item)">
                    Practise
                  </a>
                </li>
              }
            </ol>
          </section>
        }

        @if (practiceCount() > 0 && config.flagEnabled('short_answer_grading')) {
          <section class="syllabus rise" style="animation-delay: 260ms">
            <div class="section-head">
              <h2>Practice</h2>
              <span class="mono-label">
                {{ practiceCount() }} short-answer {{ practiceCount() === 1 ? 'question' : 'questions' }}
              </span>
            </div>
            <ol class="lesson-list">
              <li class="lesson">
                <span class="lesson__index mono-label">SA</span>
                <div class="lesson__body">
                  <span class="lesson__title">Short-answer practice</span>
                  <span class="lesson__check">graded by AI with instant feedback</span>
                </div>
                @if (enrollment()) {
                  <a class="btn btn--ghost lesson__open" [routerLink]="['/courses', c.slug, 'practice']">
                    Practise
                  </a>
                } @else {
                  <span class="lesson__lock mono-label">enroll to unlock</span>
                }
              </li>
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
      border-bottom: 2px solid var(--line-strong);
      margin-bottom: 0.6rem;
    }

    .progress {
      width: 200px;
      height: 8px;
      border: 1px solid var(--line-strong);
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

    .leaderboard {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .leaderboard__row {
      display: grid;
      grid-template-columns: 3rem 1fr auto;
      align-items: center;
      gap: 0.75rem;
      padding: 0.65rem 0.9rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 10px;
    }

    .leaderboard__row--top {
      border-color: var(--accent);
      background: color-mix(in srgb, var(--chip-pink) 40%, var(--card));
    }

    .leaderboard__score {
      font-family: var(--font-mono);
      font-weight: 700;
      color: var(--accent-deep);
    }
  `,
})
export class CourseDetailPage {
  private readonly api = inject(LearningApi);
  private readonly shortAnswers = inject(ShortAnswerApi);
  private readonly practiceInsights = inject(PracticeInsightsApi);
  private readonly auth = inject(AuthService);
  protected readonly config = inject(SiteConfig);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly course = signal<Course | null>(null);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly practiceCount = signal(0);
  protected readonly leaderboard = signal<CourseLeaderboardRow[]>([]);
  protected readonly courseDrill = signal<RecommendedItem[]>([]);

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
      void this.loadPracticeCount();
      void this.loadLeaderboard(slug);
      void this.loadCourseDrill(slug);
    } catch {
      this.course.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  private async loadLeaderboard(slug: string): Promise<void> {
    try {
      this.leaderboard.set(await this.api.courseLeaderboard(slug));
    } catch {
      this.leaderboard.set([]);
    }
  }

  /** Practice is a quiet extra — if the lookup fails we simply hide the section. */
  private async loadCourseDrill(slug: string): Promise<void> {
    if (!this.auth.isLoggedIn() || !this.enrollment()) {
      this.courseDrill.set([]);
      return;
    }
    try {
      const feed = await this.practiceInsights.recommendations();
      this.courseDrill.set(
        feed.recommended.filter((item) => item.course_slug === slug).slice(0, 5),
      );
    } catch {
      this.courseDrill.set([]);
    }
  }

  protected drillLink(item: RecommendedItem): string[] {
    if (item.type === 'quiz' && item.quiz_id) {
      return ['/courses', item.course_slug, 'quiz', String(item.quiz_id)];
    }
    return ['/courses', item.course_slug, 'practice'];
  }

  private async loadPracticeCount(): Promise<void> {
    const c = this.course();
    if (!c || !this.auth.isLoggedIn()) {
      this.practiceCount.set(0);
      return;
    }
    try {
      const questions = await this.shortAnswers.list(c.id);
      this.practiceCount.set(questions.filter((q) => q.is_published).length);
    } catch {
      this.practiceCount.set(0);
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

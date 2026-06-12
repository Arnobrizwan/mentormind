import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { LocaleService } from '../core/locale';
import { ConfettiBurst } from '../core/confetti';
import { CountUpDirective } from '../core/count-up';
import { EngagementApi } from '../core/engagement';
import { Course, Enrollment, QuizAttempt } from '../core/models';
import { PlannerApi } from '../core/planner';
import {
  CourseReadiness,
  PracticeInsightsApi,
  PracticeRecommendations,
  RecommendedItem,
} from '../core/practice-insights';
import { RevisionApi } from '../core/revision';

interface CourseRef {
  course: number;
  slug: string;
}

interface ContinueHero {
  enrollment: Enrollment;
  slug: string | null;
  lessonLine: string;
}

@Component({
  selector: 'mm-dashboard',
  imports: [RouterLink, ConfettiBurst, CountUpDirective],
  template: `
    <section class="desk rise">
      <p class="mono-label">{{ locale.t('nav.desk') }}</p>
      <h1>{{ locale.id() === 'ms' ? 'Selamat kembali' : 'Welcome back' }}, {{ auth.user()?.display_name || 'student' }}</h1>

      @if (engagement.me(); as eng) {
        <div class="spark-row">
          <span class="mono-label">🔥 <span [mmCountUp]="eng.streak"></span>-{{ locale.t('dash.streak') }}</span>
          <span class="mono-label">★ <span [mmCountUp]="eng.points_total"></span> {{ locale.t('dash.pts') }}</span>
          @if (!eng.daily_login_claimed) {
            <button class="btn btn--accent claim-btn" (click)="claimDaily()" [disabled]="claiming()">
              {{ locale.t('dash.claim') }} +{{ eng.daily_login_points }} {{ locale.t('dash.pts') }}
            </button>
          } @else {
            <span class="stamp">{{ locale.t('dash.claimed') }}</span>
          }
          @if (claimBurst(); as burst) {
            <span class="claim-burst" aria-live="polite">+{{ burst }} {{ locale.t('dash.pts') }}!<mm-confetti /></span>
          }
        </div>
      }
    </section>

    @if (hero(); as h) {
      <section class="hero rise" style="animation-delay: 60ms" aria-label="Continue learning">
        <p class="mono-label hero__label">{{ locale.t('dash.continue') }}</p>
        <h2 class="hero__title">{{ h.enrollment.course_title }}</h2>
        <p class="hero__lesson">{{ h.lessonLine }}</p>
        <div class="hero__progress">
          <div
            class="progress hero__bar"
            role="progressbar"
            [attr.aria-valuenow]="h.enrollment.progress_percentage"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label="Course progress"
          >
            <div class="progress__bar" [style.width.%]="h.enrollment.progress_percentage"></div>
          </div>
          <span class="mono-label">{{ h.enrollment.progress_percentage }}%</span>
        </div>
        @if (h.slug) {
          <a class="btn btn--accent hero__btn" [routerLink]="['/courses', h.slug]">{{ locale.id() === 'ms' ? 'Teruskan' : 'Continue' }} →</a>
        }
      </section>
    }

    <div class="stats">
      <div class="stat">
        <span class="stat__number">{{ api.enrollments().length }}</span>
        <span class="mono-label">{{ locale.t('dash.enrolled') }}</span>
      </div>
      <div class="stat">
        <span class="stat__number">{{ averageProgress() }}<small>%</small></span>
        <span class="mono-label">{{ locale.t('dash.avgProgress') }}</span>
      </div>
      <div class="stat">
        <span class="stat__number">{{ attempts().length }}</span>
        <span class="mono-label">{{ locale.t('dash.attempts') }}</span>
      </div>
    </div>

    <section class="quick rise" style="animation-delay: 105ms" aria-label="Study shortcuts">
      <a routerLink="/revision" class="quick__tile">
        <span class="quick__icon" aria-hidden="true">🃏</span>
        <span class="quick__label">{{ locale.t('nav.revision') }}</span>
        @if (dueCards() > 0) {
          <span class="quick__badge">{{ dueCards() }} {{ locale.t('dash.due') }}</span>
        }
      </a>
      <a routerLink="/planner" class="quick__tile">
        <span class="quick__icon" aria-hidden="true">🗓️</span>
        <span class="quick__label">{{ locale.t('nav.planner') }}</span>
        @if (planPct() !== null) {
          <span class="mono-label quick__note">{{ planPct() }}% {{ locale.t('dash.done') }}</span>
        }
      </a>
    </section>

    @if (focus(); as f) {
      @if (f.topics.length > 0) {
        <section class="block focus rise" style="animation-delay: 130ms">
          <h2>{{ locale.t('dash.focus') }}</h2>
          <div class="focus__topics">
            @for (topic of f.topics; track topic.topic) {
              <div class="focus__row">
                <span class="focus__name">{{ topic.topic }}</span>
                <span
                  class="focus__meter"
                  role="meter"
                  [attr.aria-valuenow]="topic.accuracy"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  [attr.aria-label]="topic.topic + ' accuracy'"
                >
                  <span
                    class="focus__meter-fill"
                    [class.focus__meter-fill--low]="topic.accuracy < 50"
                    [style.width.%]="topic.accuracy"
                  ></span>
                </span>
                <span class="focus__pct mono-label">{{ topic.accuracy }}%</span>
                <span class="mono-label focus__samples">
                  {{ topic.samples }} {{ topic.samples === 1 ? locale.t('dash.answer') : locale.t('dash.answers') }}
                </span>
              </div>
            }
          </div>
          @if (recommended().length > 0) {
            <p class="mono-label focus__label">{{ locale.t('dash.recommended') }}</p>
            <ul class="focus__recs">
              @for (item of recommended(); track item.type + '-' + item.id) {
                <li>
                  <a class="focus__rec" [routerLink]="recLink(item)">
                    <span class="focus__rec-icon" aria-hidden="true">
                      {{ item.type === 'quiz' ? '📝' : '🎯' }}
                    </span>
                    <span class="focus__rec-body">
                      <strong>{{ item.title }}</strong>
                      <span class="focus__rec-preview">{{ item.preview }}</span>
                    </span>
                    <span class="mono-label focus__rec-topic">{{ item.topic }}</span>
                  </a>
                </li>
              }
            </ul>
          }
        </section>
      }
    }

    @if (engagement.me(); as eng) {
      <section class="badges rise" style="animation-delay: 120ms">
        <h2>{{ locale.t('dash.badges') }}</h2>
        <div class="badges__row">
          @for (badge of eng.badges; track badge.key) {
            <div class="badge" [class.badge--locked]="!badge.earned" [title]="badge.description">
              <span class="badge__icon">{{ badge.earned ? badge.icon : '🔒' }}</span>
              <span class="badge__name">{{ badge.name }}</span>
              <span class="mono-label">
                {{ badge.earned ? (locale.id() === 'ms' ? 'didapat' : 'earned') : badge.progress + '/' + badge.threshold }}
              </span>
              @if (!badge.earned) {
                <span class="badge__meter">
                  <span
                    class="badge__meter-fill"
                    [style.width.%]="meterWidth(badge.progress, badge.threshold)"
                  ></span>
                </span>
              }
            </div>
          }
        </div>
      </section>
    }

    <section class="leaderboard rise" style="animation-delay: 150ms">
      <h2>{{ locale.t('dash.leaderboard') }}</h2>
      @if (engagement.leaderboard().length > 0) {
        <ol class="leaderboard__list">
          @for (row of engagement.leaderboard(); track row.rank) {
            <li class="leaderboard__row" [class.leaderboard__row--top]="row.rank === 1">
              <span class="leaderboard__rank">{{ medal(row.rank) }}</span>
              <span class="leaderboard__name">{{ row.student }}</span>
              <span class="mono-label">★ {{ row.points }} {{ locale.t('dash.pts') }}</span>
            </li>
          }
        </ol>
      } @else {
        <p class="leaderboard__empty mono-label">
          {{ locale.id() === 'ms' ? 'Tiada mata dicatatkan lagi minggu ini — ambil kuiz untuk menuntut tempat teratas.' : 'No points logged yet this week — take a quiz to claim the top spot.' }}
        </p>
      }
    </section>

    @if (loading()) {
      <div class="skeletons" role="status" aria-label="Loading your desk">
        <div class="skeleton skeleton--row"></div>
        <div class="skeleton skeleton--row"></div>
        <div class="skeleton skeleton--row"></div>
      </div>
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
              @if (readinessFor(enrollment.course); as ready) {
                <div class="ready" [title]="readinessTitle(ready)">
                  <span class="ready__ring" [style.background]="ringBg(ready.readiness)" aria-hidden="true">
                    <span class="ready__hole"></span>
                  </span>
                  <span class="mono-label">
                    Exam readiness:
                    <strong class="ready__num"><span [mmCountUp]="ready.readiness"></span>%</strong>
                  </span>
                </div>
              }
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
    .hero {
      margin-top: 1.8rem;
      padding: 1.7rem 1.9rem;
      border-radius: 18px;
      /* accent gradient border over a soft pink card */
      border: 2px solid transparent;
      background:
        linear-gradient(
            135deg,
            color-mix(in srgb, var(--accent) 7%, var(--card)) 0%,
            var(--card) 65%
          )
          padding-box,
        var(--grad-hero) border-box;
      box-shadow: var(--shadow-card);
    }

    .hero__label { color: var(--accent-deep); }

    .hero__title {
      font-size: clamp(1.6rem, 3.4vw, 2.3rem);
      margin: 0.55rem 0 0.35rem;
    }

    .hero__lesson {
      font-size: 1.02rem;
      color: var(--ink-soft);
      margin-bottom: 1rem;
    }

    .hero__progress {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      margin-bottom: 1.2rem;
    }

    .hero__bar {
      width: min(320px, 100%);
      height: 10px;

      .progress__bar { background: var(--grad-btn); }
    }

    .spark-row {
      display: flex;
      align-items: center;
      gap: 1.2rem;
      margin-top: 1rem;
      flex-wrap: wrap;
    }

    .claim-btn {
      padding: 0.45rem 1.05rem;
      font-size: 0.82rem;
    }

    .badges {
      margin-bottom: 2.2rem;

      h2 {
        font-size: 1.5rem;
        margin-bottom: 0.9rem;
      }
    }

    .badges__row {
      display: flex;
      gap: 0.9rem;
      flex-wrap: wrap;
    }

    .badge {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.15rem;
      width: 108px;
      padding: 0.8rem 0.5rem;
      background: var(--card);
      border: 1.5px solid var(--sage);
      border-radius: 10px;
      text-align: center;
    }

    .badge--locked {
      border-color: var(--line);
      filter: grayscale(1);
      opacity: 0.65;
    }

    .badge__icon { font-size: 1.5rem; }

    .badge__name {
      font-size: 0.74rem;
      font-weight: 700;
    }

    .badge__meter {
      width: 100%;
      height: 5px;
      margin-top: 0.35rem;
      border-radius: 3px;
      background: var(--line);
      overflow: hidden;
    }

    .badge__meter-fill {
      display: block;
      height: 100%;
      border-radius: 3px;
      background: var(--accent);
      transition: width 600ms ease;
    }

    .claim-burst {
      position: relative;
      font-weight: 800;
      color: var(--accent);
      animation: burst-pop 1.8s ease forwards;
    }

    @keyframes burst-pop {
      0% { opacity: 0; transform: translateY(6px) scale(0.8); }
      18% { opacity: 1; transform: translateY(0) scale(1.15); }
      30% { transform: scale(1); }
      80% { opacity: 1; }
      100% { opacity: 0; transform: translateY(-8px); }
    }

    .leaderboard {
      margin-bottom: 2.2rem;

      h2 {
        font-size: 1.5rem;
        margin-bottom: 0.9rem;
      }
    }

    .leaderboard__empty {
      color: var(--ink-soft);
      margin: 0.25rem 0 0;
      max-width: 42ch;
    }

    .leaderboard__list {
      list-style: none;
      padding: 0;
      margin: 0;
      max-width: 460px;
    }

    .leaderboard__row {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      padding: 0.55rem 0.8rem;
      border-bottom: 1px dashed var(--line);
    }

    .leaderboard__row--top {
      background: var(--card);
      border: 1.5px solid var(--accent);
      border-radius: 10px;
    }

    .leaderboard__rank {
      width: 2.2rem;
      text-align: center;
      font-weight: 800;
    }

    .leaderboard__name {
      flex: 1;
      font-weight: 600;
      font-size: 0.92rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .quick {
      display: flex;
      gap: 0.9rem;
      flex-wrap: wrap;
      margin-bottom: 2.2rem;
    }

    .quick__tile {
      display: inline-flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.7rem 1.1rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 10px;
      text-decoration: none;
      color: var(--ink);

      &:hover { border-color: var(--accent); }
      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    }

    .quick__icon { font-size: 1.15rem; }

    .quick__label { font-weight: 700; }

    .quick__badge {
      padding: 0.1rem 0.55rem;
      border-radius: 999px;
      background: var(--accent);
      color: var(--paper);
      font-family: var(--font-mono);
      font-size: 0.74rem;
      font-weight: 700;
    }

    .quick__note { color: var(--ink-soft); }

    .focus__topics {
      display: flex;
      flex-direction: column;
      margin-bottom: 1.1rem;
    }

    .focus__row {
      display: flex;
      align-items: center;
      gap: 0.9rem;
      padding: 0.6rem 0.4rem;
      border-bottom: 1px dashed var(--line);
      flex-wrap: wrap;
    }

    .focus__name {
      flex: 1;
      min-width: 140px;
      font-weight: 600;
    }

    .focus__meter {
      width: 160px;
      height: 8px;
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      overflow: hidden;
      background: var(--card);
    }

    .focus__meter-fill {
      display: block;
      height: 100%;
      background: var(--marker);
      transition: width 600ms ease;

      &--low { background: var(--danger); }
    }

    .focus__pct {
      width: 3.2ch;
      text-align: right;
    }

    .focus__samples { color: var(--ink-soft); }

    .focus__label { margin-bottom: 0.6rem; }

    .focus__recs {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    }

    .focus__rec {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      padding: 0.6rem 0.8rem;
      background: var(--card);
      border: 1.5px solid var(--line);
      border-radius: 10px;
      text-decoration: none;
      color: var(--ink);

      &:hover { border-color: var(--accent); }
      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    }

    .focus__rec-body {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 0.1rem;

      strong { font-size: 0.92rem; }
    }

    .focus__rec-preview {
      font-size: 0.85rem;
      color: var(--ink-soft);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .focus__rec-topic { color: var(--sage-deep); }

    .ready {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .ready__ring {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .ready__hole {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--paper);
    }

    .ready__num { font-weight: 700; }

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
      border-top: 2px solid var(--line-strong);
      border-bottom: 2px solid var(--line-strong);
    }

    .stat {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      padding: 1.2rem 1.4rem;
      /* staggered entrance, once per load (rise-in lives in styles.scss) */
      animation: rise-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
      animation-delay: 90ms;

      &:nth-child(2) { animation-delay: 145ms; }
      &:nth-child(3) { animation-delay: 200ms; }

      & + .stat {
        border-left: 1px solid var(--line);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .stat { animation: none; }
    }

    .stat__number {
      font-family: var(--font-display);
      font-size: 2.6rem;
      font-weight: 640;
      line-height: 1;

      small { font-size: 1.2rem; }
    }

    .state-note { padding: 1.5rem 0; }

    .skeletons {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      padding: 0.5rem 0 1.5rem;
    }

    .skeleton--row { height: 76px; }

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
        border-bottom: 2px solid var(--line-strong);
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
  protected readonly engagement = inject(EngagementApi);
  private readonly auth = inject(AuthService);
  private readonly insights = inject(PracticeInsightsApi);
  private readonly revision = inject(RevisionApi);
  private readonly planner = inject(PlannerApi);
  protected readonly locale = inject(LocaleService);

  protected readonly loading = signal(true);
  private readonly courseRefs = signal<CourseRef[]>([]);
  private readonly courses = signal<Course[]>([]);

  protected readonly focus = signal<PracticeRecommendations | null>(null);
  private readonly readiness = signal<CourseReadiness[]>([]);
  protected readonly dueCards = signal(0);
  protected readonly planPct = signal<number | null>(null);

  protected readonly recommended = computed<RecommendedItem[]>(
    () => this.focus()?.recommended.slice(0, 5) ?? [],
  );

  protected readonly attempts = computed<QuizAttempt[]>(() =>
    this.api
      .enrollments()
      .flatMap((e) => e.quiz_attempts)
      .sort((a, b) => b.completed_at.localeCompare(a.completed_at)),
  );

  /**
   * "Continue learning" focal card: the in-progress enrollment closest to
   * the finish line (most recent breaks ties). Hidden when everything is
   * complete or nothing is enrolled.
   */
  protected readonly hero = computed<ContinueHero | null>(() => {
    const candidates = this.api.enrollments().filter((e) => e.progress_percentage < 100);
    if (candidates.length === 0) return null;
    const enrollment = [...candidates].sort(
      (a, b) =>
        b.progress_percentage - a.progress_percentage ||
        b.enrolled_at.localeCompare(a.enrolled_at),
    )[0];
    const course = this.courses().find((c) => c.id === enrollment.course) ?? null;
    return {
      enrollment,
      slug: course?.slug ?? null,
      lessonLine: this.heroLessonLine(enrollment, course),
    };
  });

  /** "Lesson n of total: title" when lesson data is on hand, else a progress summary. */
  private heroLessonLine(enrollment: Enrollment, course: Course | null): string {
    const done = new Set(enrollment.completed_lessons);
    if (course && course.lessons.length > 0) {
      const ordered = [...course.lessons].sort((a, b) => a.order - b.order);
      const index = ordered.findIndex((lesson) => !done.has(lesson.id));
      if (index >= 0) {
        return `Lesson ${index + 1} of ${ordered.length}: ${ordered[index].title}`;
      }
      return `${ordered.length}/${ordered.length} lessons · ${enrollment.progress_percentage}%`;
    }
    return (
      `${done.size} lesson${done.size === 1 ? '' : 's'} done · ` +
      `${enrollment.progress_percentage}%`
    );
  }

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
        this.engagement.refresh(),
        this.engagement.refreshLeaderboard(),
        // Study aids are nice-to-haves — never block (or break) the desk.
        this.insights
          .recommendations()
          .then((recs) => this.focus.set(recs))
          .catch(() => undefined),
        this.insights
          .readiness()
          .then((rows) => this.readiness.set(rows))
          .catch(() => undefined),
        this.revision
          .queue()
          .then((queue) => this.dueCards.set(queue.due_count))
          .catch(() => undefined),
        this.planner
          .week()
          .then((plan) => this.planPct.set(plan.completion_pct))
          .catch(() => undefined),
      ]);
      this.courses.set(courses);
      this.courseRefs.set(courses.map((c) => ({ course: c.id, slug: c.slug })));
    } finally {
      this.loading.set(false);
    }
  }

  protected recLink(item: RecommendedItem): string[] {
    return item.type === 'short_answer'
      ? ['/courses', item.course_slug, 'practice']
      : ['/courses', item.course_slug];
  }

  protected readinessFor(courseId: number): CourseReadiness | null {
    return this.readiness().find((r) => r.course === courseId) ?? null;
  }

  protected readinessTitle(entry: CourseReadiness): string {
    const c = entry.components;
    return (
      `Course progress ${c.progress_pct}% · Quiz average ${c.quiz_avg}% · ` +
      `Practice volume ${c.practice_volume}% · Accuracy ${c.accuracy}%`
    );
  }

  protected ringBg(readiness: number): string {
    const color =
      readiness >= 70 ? 'var(--sage)' : readiness >= 40 ? 'var(--marker)' : 'var(--danger)';
    const pct = Math.max(0, Math.min(100, readiness));
    return `conic-gradient(${color} ${pct}%, var(--line) ${pct}% 100%)`;
  }

  protected greeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  protected readonly claiming = signal(false);
  protected readonly claimBurst = signal<number | null>(null);

  protected async claimDaily(): Promise<void> {
    if (this.claiming()) return;
    this.claiming.set(true);
    try {
      const result = await this.engagement.claimDailyLogin();
      if (result.claimed) {
        this.claimBurst.set(result.points);
        setTimeout(() => this.claimBurst.set(null), 1800);
        void this.engagement.refreshLeaderboard();
      }
    } finally {
      this.claiming.set(false);
    }
  }

  protected meterWidth(progress: number, threshold: number): number {
    if (threshold <= 0) return 0;
    return Math.min(100, Math.round((progress / threshold) * 100));
  }

  protected medal(rank: number): string {
    return rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
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

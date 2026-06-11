import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { EngagementApi } from '../core/engagement';
import { QuizAttempt } from '../core/models';
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

@Component({
  selector: 'mm-dashboard',
  imports: [RouterLink],
  template: `
    <section class="desk rise">
      <p class="mono-label">My Desk</p>
      <h1>
        {{ greeting() }},
        <em>{{ firstName() }}.</em>
      </h1>
      @if (engagement.me(); as eng) {
        <div class="spark-row">
          <span class="mono-label">🔥 {{ eng.streak }}-day streak</span>
          <span class="mono-label">★ {{ eng.points_total }} pts</span>
          @if (!eng.daily_login_claimed) {
            <button class="btn btn--accent claim-btn" (click)="claimDaily()" [disabled]="claiming()">
              Claim today's +{{ eng.daily_login_points }} pts
            </button>
          } @else {
            <span class="stamp">Daily reward claimed</span>
          }
          @if (claimBurst(); as burst) {
            <span class="claim-burst" aria-live="polite">+{{ burst }} pts!</span>
          }
        </div>
      }
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

    <section class="quick rise" style="animation-delay: 105ms" aria-label="Study shortcuts">
      <a routerLink="/revision" class="quick__tile">
        <span class="quick__icon" aria-hidden="true">🃏</span>
        <span class="quick__label">Revision</span>
        @if (dueCards() > 0) {
          <span class="quick__badge">{{ dueCards() }} due</span>
        }
      </a>
      <a routerLink="/planner" class="quick__tile">
        <span class="quick__icon" aria-hidden="true">🗓️</span>
        <span class="quick__label">This week's plan</span>
        @if (planPct() !== null) {
          <span class="mono-label quick__note">{{ planPct() }}% done</span>
        }
      </a>
    </section>

    @if (focus(); as f) {
      @if (f.topics.length > 0) {
        <section class="block focus rise" style="animation-delay: 130ms">
          <h2>Focus areas</h2>
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
                  {{ topic.samples }} {{ topic.samples === 1 ? 'answer' : 'answers' }}
                </span>
              </div>
            }
          </div>
          @if (recommended().length > 0) {
            <p class="mono-label focus__label">Recommended next</p>
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
        <h2>Badges</h2>
        <div class="badges__row">
          @for (badge of eng.badges; track badge.key) {
            <div class="badge" [class.badge--locked]="!badge.earned" [title]="badge.description">
              <span class="badge__icon">{{ badge.earned ? badge.icon : '🔒' }}</span>
              <span class="badge__name">{{ badge.name }}</span>
              <span class="mono-label">
                {{ badge.earned ? 'earned' : badge.progress + '/' + badge.threshold }}
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

    @if (engagement.leaderboard().length > 0) {
      <section class="leaderboard rise" style="animation-delay: 150ms">
        <h2>This week's leaderboard</h2>
        <ol class="leaderboard__list">
          @for (row of engagement.leaderboard(); track row.rank) {
            <li class="leaderboard__row" [class.leaderboard__row--top]="row.rank === 1">
              <span class="leaderboard__rank">{{ medal(row.rank) }}</span>
              <span class="leaderboard__name">{{ row.student }}</span>
              <span class="mono-label">★ {{ row.points }} pts</span>
            </li>
          }
        </ol>
      </section>
    }

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
              @if (readinessFor(enrollment.course); as ready) {
                <div class="ready" [title]="readinessTitle(ready)">
                  <span class="ready__ring" [style.background]="ringBg(ready.readiness)" aria-hidden="true">
                    <span class="ready__hole"></span>
                  </span>
                  <span class="mono-label">
                    Exam readiness:
                    <strong class="ready__num">{{ ready.readiness }}%</strong>
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
      border: 1px solid var(--ink);
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
  protected readonly engagement = inject(EngagementApi);
  private readonly auth = inject(AuthService);
  private readonly insights = inject(PracticeInsightsApi);
  private readonly revision = inject(RevisionApi);
  private readonly planner = inject(PlannerApi);

  protected readonly loading = signal(true);
  private readonly courseRefs = signal<CourseRef[]>([]);

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

import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { Course } from '../core/models';
import { LocaleService } from '../core/locale';
import { SiteConfig } from '../core/site-config';

@Component({
  selector: 'mm-catalog',
  imports: [RouterLink],
  template: `
    <section class="hero rise">
      <p class="mono-label">{{ locale.t('catalog.hero.label') }}</p>
      <h1>
        {{ locale.t('catalog.hero.line1') }}<br />
        <em>{{ locale.t('catalog.hero.line2') }}</em>
      </h1>
      <p class="hero__sub">{{ locale.t('catalog.hero.sub') }}</p>
    </section>

    @if (loading()) {
      <div class="grid" role="status" aria-label="Loading the catalog">
        @for (s of skeletonSlots; track s) {
          <div class="skeleton skeleton--card"></div>
        }
      </div>
    } @else if (courses().length === 0) {
      <div class="empty rise">
        <h2>{{ locale.t('catalog.empty.title') }}</h2>
        <p>{{ locale.t('catalog.empty.sub') }}</p>
      </div>
    } @else {
      @if (recommended().length > 0) {
        <section class="recs rise">
          <div class="ledger-row">
            <span class="mono-label">{{ locale.t('catalog.recs.title') }}</span>
            <hr class="hairline" style="flex:1" />
          </div>
          <div class="grid grid--recs">
            @for (course of recommended(); track course.id; let i = $index) {
              <a
                class="card card--rec rise"
                [routerLink]="['/courses', course.slug]"
                [style.animation-delay.ms]="stagger(i)"
              >
                <span class="mono-label">{{ locale.t('catalog.recs.badge') }}</span>
                <h2 class="card__title">{{ course.title }}</h2>
                <p class="card__desc">{{ course.description }}</p>
                <span class="card__arrow" aria-hidden="true">→</span>
              </a>
            }
          </div>
        </section>
      }

      <div class="ledger-row">
        <span class="mono-label">{{ courses().length }} {{ locale.t('catalog.record') }}</span>
        <hr class="hairline" style="flex:1" />
      </div>
      <div class="grid">
        @for (course of courses(); track course.id; let i = $index) {
          <a
            class="card rise"
            [routerLink]="['/courses', course.slug]"
            [style.animation-delay.ms]="stagger(i)"
          >
            <div class="card__top">
              <span class="mono-label">No. {{ serial(i) }}</span>
              @if (enrolledIn(course)) {
                <span class="stamp">{{ locale.t('catalog.enrolled') }}</span>
              }
            </div>
            <h2 class="card__title">{{ course.title }}</h2>
            <p class="card__byline">
              {{ locale.t('catalog.taughtBy') }} <strong>{{ course.instructor_name || locale.t('catalog.aMentor') }}</strong>
            </p>
            <p class="card__desc">{{ course.description }}</p>
            <div class="card__meta">
              <span class="mono-label">{{ course.lessons.length }} {{ locale.t('catalog.lessonsCount') }}</span>
              <span class="mono-label">{{ course.quizzes.length }} {{ locale.t('catalog.quizzesCount') }}</span>
              <span class="card__arrow" aria-hidden="true">→</span>
            </div>
          </a>
        }
      </div>
    }
  `,
  styles: `
    .hero {
      padding: clamp(0.5rem, 3vw, 2rem) 0 2.5rem;
      max-width: 720px;
    }

    .hero h1 {
      font-size: clamp(2.6rem, 6.5vw, 4.6rem);
      margin: 0.9rem 0 1.2rem;

      em {
        font-style: italic;
        color: var(--accent);
        background: linear-gradient(transparent 64%, var(--marker) 64%, var(--marker) 94%, transparent 94%);
      }
    }

    .hero__sub {
      color: var(--ink-soft);
      font-size: 1.08rem;
      max-width: 52ch;
    }

    .state-note {
      padding: 2rem 0;
    }

    .skeleton--card { height: 230px; }

    .empty {
      padding: 3rem 0;
      h2 { margin-bottom: 0.6rem; }
      p { color: var(--ink-soft); }
    }

    .ledger-row {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.6rem;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1.4rem;
    }

    .card {
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      padding: 1.4rem 1.4rem 1.2rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 12px;
      box-shadow: var(--shadow-card);
      text-decoration: none;
      transition: transform 0.2s ease, box-shadow 0.2s ease;

      &:hover {
        transform: translateY(-4px) rotate(-0.4deg);
        box-shadow: var(--shadow-lift);

        .card__arrow {
          transform: translateX(5px);
        }
      }
    }

    .card__top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      min-height: 1.6rem;
    }

    .card__title {
      font-size: 1.45rem;
    }

    .card__byline {
      font-size: 0.85rem;
      color: var(--ink-soft);

      strong { color: var(--ink); }
    }

    .card__desc {
      font-size: 0.92rem;
      color: var(--ink-soft);
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
      flex: 1;
    }

    .card__meta {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding-top: 0.8rem;
      border-top: 1px dashed var(--line-strong);
    }

    .card__arrow {
      margin-left: auto;
      font-size: 1.2rem;
      color: var(--accent);
      transition: transform 0.2s ease;
    }

    .recs { margin-bottom: 2rem; }

    .grid--recs {
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    }

    .card--rec {
      border-color: color-mix(in srgb, var(--accent) 35%, var(--line-strong));
      background: color-mix(in srgb, var(--chip-pink) 35%, var(--card));
    }
  `,
})
export class CatalogPage {
  private readonly learningApi = inject(LearningApi);
  protected readonly auth = inject(AuthService);
  protected readonly locale = inject(LocaleService);
  private readonly config = inject(SiteConfig);

  protected readonly courses = signal<Course[]>([]);
  protected readonly recommended = signal<Course[]>([]);
  protected readonly loading = signal(true);
  protected readonly skeletonSlots = [0, 1, 2, 3, 4, 5];

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      if (this.auth.isLoggedIn()) {
        await this.learningApi.refreshEnrollments();
      }
      const courses = await this.learningApi.listCourses();
      this.courses.set(courses);
      if (this.auth.isLoggedIn() && this.config.flagEnabled('recommendations')) {
        try {
          const recs = await this.learningApi.listRecommended();
          const enrolled = new Set(
            this.learningApi.enrollments().map((e) => e.course),
          );
          this.recommended.set(recs.filter((c) => !enrolled.has(c.id)).slice(0, 3));
        } catch {
          this.recommended.set([]);
        }
      } else {
        this.recommended.set([]);
      }
    } finally {
      this.loading.set(false);
    }
  }

  protected serial(index: number): string {
    return String(index + 1).padStart(3, '0');
  }

  /** Per-card entrance delay — 55ms steps, capped after 8 items. */
  protected stagger(index: number): number {
    return 80 + Math.min(index, 8) * 55;
  }

  protected enrolledIn(course: Course): boolean {
    return this.learningApi.enrollmentFor(course.id) !== undefined;
  }
}

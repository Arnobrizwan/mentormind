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
      <span class="hero__sticker hero__sticker--1" aria-hidden="true">✦</span>
      <span class="hero__sticker hero__sticker--2" aria-hidden="true">✏️</span>
      <p class="mono-label">{{ locale.t('catalog.hero.label') }}</p>
      <h1>
        {{ locale.t('catalog.hero.line1') }}<br />
        <em>{{ locale.t('catalog.hero.line2') }}</em>
      </h1>
      <p class="hero__sub">{{ locale.t('catalog.hero.sub') }}</p>
    </section>

    <section class="features rise">
      <div class="features__head">
        <p class="mono-label">Why MentorMind</p>
        <h2>Built to <em>teach</em>, not just test</h2>
      </div>
      <div class="features__grid">
        <a class="feature feature--a" routerLink="/tutor">
          <span class="feature__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 13l.9 2.1 2.1.9-2.1.9L19 19l-.9-2.1-2.1-.9 2.1-.9z"/></svg>
          </span>
          <div class="feature__tags">
            <span class="ftag">Mark schemes</span>
            <span class="ftag">Grounded</span>
            <span class="ftag">24/7</span>
          </div>
          <div class="feature__bottom">
            <h3 class="feature__title">AI tutor that never sleeps</h3>
            <span class="feature__cta">Start learning <span aria-hidden="true">↘</span></span>
          </div>
        </a>
        <a class="feature feature--b" routerLink="/revision">
          <span class="feature__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
          </span>
          <div class="feature__tags">
            <span class="ftag">Quizzes</span>
            <span class="ftag">Flashcards</span>
            <span class="ftag">Spaced repetition</span>
          </div>
          <div class="feature__bottom">
            <h3 class="feature__title">Practice that adapts to you</h3>
            <span class="feature__cta">Start practising <span aria-hidden="true">↘</span></span>
          </div>
        </a>
        <a class="feature feature--c" routerLink="/dashboard">
          <span class="feature__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/></svg>
          </span>
          <div class="feature__tags">
            <span class="ftag">Web</span>
            <span class="ftag">Android</span>
            <span class="ftag">Offline PWA</span>
          </div>
          <div class="feature__bottom">
            <h3 class="feature__title">Learn anytime, anywhere</h3>
            <span class="feature__cta">Open your desk <span aria-hidden="true">↘</span></span>
          </div>
        </a>
      </div>
    </section>

    <section class="vision section-dark rise">
      <div class="vision__text">
        <p class="mono-label">Our vision</p>
        <h2>Learn the basics in a <em>modern</em> way</h2>
        <p class="vision__sub">
          MentorMind puts an AI tutor, real past papers and spaced repetition in one
          place — grounded in official mark schemes, running on your own server.
        </p>
      </div>
      <div class="vision__art" aria-hidden="true">
        <svg viewBox="0 0 200 200">
          <polygon class="hexa hexa--1" points="180,100 140,169.3 60,169.3 20,100 60,30.7 140,30.7" />
          <polygon class="hexa hexa--2" points="155,100 127.5,147.6 72.5,147.6 45,100 72.5,52.4 127.5,52.4" />
          <polygon class="hexa hexa--3" points="130,100 115,126 85,126 70,100 85,74 115,74" />
          <circle class="spark spark--1" cx="168" cy="48" r="4" />
          <circle class="spark spark--2" cx="36" cy="150" r="3" />
          <circle class="spark spark--3" cx="150" cy="160" r="2.5" />
        </svg>
      </div>
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

      <section class="path">
        <div class="path__head">
          <p class="mono-label">Catalog</p>
          <h2>Choose your <em>path</em></h2>
          <p class="path__note">
            {{ courses().length }} {{ locale.t('catalog.record') }} — each course bundles
            video lessons, quizzes and a mentor.
          </p>
        </div>
        <div class="path__list">
          @for (course of courses(); track course.id; let i = $index) {
            <a
              class="path-row rise"
              [routerLink]="['/courses', course.slug]"
              [style.animation-delay.ms]="stagger(i)"
            >
              <span class="path-row__cat">{{ subjectLabel(course) }}</span>
              <div class="path-row__main">
                <h3 class="path-row__title">
                  {{ course.title }}
                  @if (enrolledIn(course)) {
                    <span class="stamp">{{ locale.t('catalog.enrolled') }}</span>
                  }
                </h3>
                <p class="path-row__desc">{{ course.description }}</p>
              </div>
              <span class="path-row__meta">
                {{ course.lessons.length }} {{ locale.t('catalog.lessonsCount') }}
                <span class="path-row__arrow" aria-hidden="true">↘</span>
              </span>
            </a>
          }
        </div>
      </section>
    }
  `,
  styles: `
    .hero {
      position: relative;
      overflow: visible;
      margin-bottom: 2.5rem;
      padding: clamp(1rem, 3vw, 2rem) 0;
      background: transparent;
      color: var(--ink);
    }

    .hero .mono-label {
      color: var(--ink);
      opacity: 1;
      display: inline-flex;
      align-items: center;
    }

    .hero .mono-label::after {
      content: ' ↘';
      color: var(--accent);
      font-weight: 700;
    }

    .hero h1 {
      font-size: clamp(3rem, 8vw, 6.5rem);
      line-height: 0.88;
      margin: 0.9rem 0 1.2rem;
      color: var(--ink);

      em {
        font-style: normal;
        color: var(--accent);
        background: none;
      }
    }

    .hero__sub {
      color: var(--ink-soft);
      font-size: 1.08rem;
      max-width: 52ch;
    }

    .hero__sticker { display: none; }

    .hero__sticker--1 {
      display: none;
    }

    .hero__sticker--2 {
      bottom: 1rem;
      right: clamp(1.5rem, 6vw, 4rem);
      font-size: 3.2rem;
      transform: rotate(12deg);
      filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.18));
      animation: float-soft 3.4s var(--ease) infinite;
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

    /* ---- feature cards (EduNova dark pill-tag cards) ---- */
    .features { margin: 0 0 2.6rem; }

    .features__head { margin-bottom: 1.4rem; }

    .features__head .mono-label::after {
      content: ' ↘';
      color: var(--accent);
    }

    .features__head h2 {
      font-size: clamp(1.9rem, 4.5vw, 3.2rem);
      margin-top: 0.5rem;

      em { font-style: normal; color: var(--accent); }
    }

    .features__grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.2rem;
    }

    .feature {
      position: relative;
      min-height: 250px;
      padding: 1.5rem;
      border-radius: var(--r-lg);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1.5rem;
      text-decoration: none;
      color: #fff;
      overflow: hidden;
      background: linear-gradient(160deg, #232228, var(--dark));
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .feature:hover {
      transform: translateY(-5px);
      box-shadow: var(--shadow-lift);
    }

    .feature--a { background: linear-gradient(160deg, color-mix(in srgb, var(--accent) 42%, #1a1018), var(--dark)); }
    .feature--b { background: linear-gradient(160deg, color-mix(in srgb, var(--accent-2) 42%, #15131f), var(--dark)); }
    .feature--c { background: linear-gradient(160deg, #2a2930, var(--dark)); }

    .feature__icon {
      position: absolute;
      top: 1.3rem;
      right: 1.3rem;
      width: 2.5rem;
      height: 2.5rem;
      color: #fff;
      opacity: 0.85;
      animation: float-soft 3.6s var(--ease) infinite;
    }

    .feature__icon svg { width: 100%; height: 100%; }

    .feature:hover .feature__icon { opacity: 1; }

    .feature__tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      padding-right: 3rem;
    }

    .ftag {
      background: rgba(255, 255, 255, 0.94);
      color: #141418;
      font-weight: 700;
      font-size: 0.7rem;
      padding: 0.3rem 0.72rem;
      border-radius: var(--r-pill);
    }

    .feature__title {
      font-family: var(--font-display);
      text-transform: uppercase;
      font-size: 1.5rem;
      line-height: 1;
      color: #fff;
      margin: 0 0 0.7rem;
    }

    .feature__cta {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #fff;
      transition: color 0.18s ease;
    }

    .feature:hover .feature__cta { color: #fff; opacity: 0.85; }

    /* ---- dark vision section (EduNova) ---- */
    .vision {
      margin: 0 0 2.6rem;
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 2rem;
      align-items: center;
    }

    .vision .mono-label::after {
      content: ' ↘';
      color: var(--accent);
    }

    .vision h2 {
      font-size: clamp(1.9rem, 4.5vw, 3.4rem);
      line-height: 0.94;
      margin: 0.7rem 0 0.9rem;
      max-width: 22ch;

      em { font-style: normal; color: var(--accent); }
    }

    .vision__sub {
      max-width: 56ch;
      font-size: 1.02rem;
    }

    .vision__art {
      display: flex;
      justify-content: center;
    }

    .vision__art svg {
      width: 100%;
      max-width: 240px;
      overflow: visible;
    }

    .hexa { fill: none; transform-origin: center; }
    .hexa--1 { stroke: rgba(255, 255, 255, 0.16); stroke-width: 1.5; animation: hexa-spin 34s linear infinite; }
    .hexa--2 { stroke: var(--accent); stroke-width: 2; animation: hexa-spin 24s linear infinite reverse; }
    .hexa--3 { fill: color-mix(in srgb, var(--accent) 34%, transparent); stroke: none; animation: float-soft 4.2s var(--ease) infinite; transform-origin: center; }
    .spark { fill: #fff; animation: spark-pulse 2.8s ease-in-out infinite; }
    .spark--2 { fill: var(--accent); animation-delay: 0.6s; }
    .spark--3 { animation-delay: 1.2s; }

    @keyframes hexa-spin { to { transform: rotate(360deg); } }
    @keyframes spark-pulse { 0%, 100% { opacity: 0.25; } 50% { opacity: 1; } }

    @media (max-width: 720px) {
      .vision { grid-template-columns: 1fr; }
      .vision__art { display: none; }
    }

    /* ---- "Choose your path" list (EduNova) ---- */
    .path__head {
      margin-bottom: 1.4rem;
    }

    .path__head .mono-label::after {
      content: ' ↘';
      color: var(--accent);
    }

    .path__head h2 {
      font-size: clamp(2.2rem, 5.5vw, 4rem);
      margin: 0.5rem 0 0.6rem;

      em { font-style: normal; color: var(--accent); }
    }

    .path__note {
      color: var(--ink-soft);
      max-width: 60ch;
    }

    .path__list {
      border-top: 2px solid var(--ink);
    }

    .path-row {
      display: grid;
      grid-template-columns: 180px 1fr auto;
      gap: 1.5rem;
      align-items: start;
      padding: 1.6rem 0.5rem;
      border-bottom: 1px solid var(--line-strong);
      text-decoration: none;
      color: var(--ink);
      transition: background 0.15s ease, padding 0.15s ease;

      &:hover {
        background: color-mix(in srgb, var(--accent) 6%, transparent);
        padding-left: 1.1rem;
        padding-right: 1.1rem;

        .path-row__arrow { transform: translate(3px, 3px); color: var(--accent); }
        .path-row__title { color: var(--accent-deep); }
      }
    }

    .path-row__cat {
      font-family: var(--font-display);
      text-transform: uppercase;
      font-size: 1.05rem;
      letter-spacing: 0.01em;
      color: var(--ink);
      padding-top: 0.1rem;
    }

    .path-row__title {
      font-family: var(--font-display);
      text-transform: uppercase;
      font-size: 1.5rem;
      line-height: 1;
      margin: 0 0 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.7rem;
      transition: color 0.15s ease;
    }

    .path-row__desc {
      color: var(--ink-soft);
      font-size: 0.95rem;
      max-width: 64ch;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .path-row__meta {
      white-space: nowrap;
      font-family: var(--font-mono);
      font-size: 0.74rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-soft);
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding-top: 0.35rem;
    }

    .path-row__arrow {
      font-size: 1.1rem;
      color: var(--ink);
      transition: transform 0.18s ease, color 0.18s ease;
    }

    @media (max-width: 640px) {
      .path-row {
        grid-template-columns: 1fr;
        gap: 0.5rem;
      }
      .path-row__meta { padding-top: 0; }
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

  /** EduNova-style category label — the subject, e.g. "Physics" from
   * "IGCSE Physics (0625)"; falls back to the first word of the title. */
  protected subjectLabel(course: Course): string {
    const m = course.title.match(/IGCSE\s+([A-Za-z][A-Za-z ]*?)(?:\s*\(|$)/);
    return (m ? m[1] : course.title.split(' ')[0] || 'Course').trim();
  }

  /** Per-card entrance delay — 55ms steps, capped after 8 items. */
  protected stagger(index: number): number {
    return 80 + Math.min(index, 8) * 55;
  }

  protected enrolledIn(course: Course): boolean {
    return this.learningApi.enrollmentFor(course.id) !== undefined;
  }
}

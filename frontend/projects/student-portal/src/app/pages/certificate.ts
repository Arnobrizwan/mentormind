import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { ConfettiBurst } from '../core/confetti';
import { LocaleService } from '../core/locale';
import { Course } from '../core/models';

/**
 * Course-completion certificate — derived entirely from data the app already
 * has (enrollment.progress_percentage === 100). Print-ready: `styles.scss`
 * carries a `@media print` block that isolates `.cert-sheet` on the page.
 */
@Component({
  selector: 'mm-certificate',
  imports: [RouterLink, ConfettiBurst],
  template: `
    @if (loading()) {
      <p class="mono-label">{{ locale.t('cert.loading') }}</p>
    } @else if (!course()) {
      <div class="missing rise">
        <h1>{{ locale.t('cert.notFound') }}</h1>
        <a routerLink="/" class="btn btn--ghost">← {{ locale.t('nav.catalog') }}</a>
      </div>
    } @else if (course(); as c) {
      <a class="mono-label crumb no-print" [routerLink]="['/courses', c.slug]">
        {{ locale.t('cert.crumb') }}
      </a>

      @if (!completed()) {
        <div class="locked rise">
          <span class="locked__icon" aria-hidden="true">🎓</span>
          <h1>{{ locale.t('cert.locked.title') }}</h1>
          <p class="locked__sub">{{ locale.t('cert.locked.sub') }}</p>
          <div class="locked__progress">
            <div
              class="progress"
              role="progressbar"
              [attr.aria-valuenow]="progress()"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="progress__bar" [style.width.%]="progress()"></div>
            </div>
            <span class="mono-label">{{ progress() }}%</span>
          </div>
          <a class="btn btn--accent" [routerLink]="['/courses', c.slug]">
            {{ locale.t('cert.locked.back') }} →
          </a>
        </div>
      } @else {
        <div class="stage rise">
          <article class="cert-sheet" [attr.aria-label]="locale.t('cert.title')">
            <div class="cert-sheet__inner">
              <mm-confetti />
              <p class="cert-wordmark">MentorMinds</p>
              <p class="cert-kicker mono-label">{{ locale.t('cert.title') }}</p>
              <p class="cert-presented">{{ locale.t('cert.presented') }}</p>
              <h1 class="cert-name">{{ studentName() }}</h1>
              <p class="cert-presented">{{ locale.t('cert.completed') }}</p>
              <h2 class="cert-course">{{ c.title }}</h2>
              <p class="cert-date mono-label">
                {{ locale.t('cert.completedOn') }} {{ completionDate() }}
              </p>
              <div class="cert-rule" aria-hidden="true">
                <span class="cert-rule__seal">🎓</span>
              </div>
              <p class="cert-footer">
                {{ locale.t('cert.verified') }}
              </p>
            </div>
          </article>

          <div class="actions no-print">
            <button class="btn btn--accent" type="button" (click)="print()">
              🖨 {{ locale.t('cert.print') }}
            </button>
            <button class="btn btn--ghost" type="button" (click)="share()">
              @if (copied()) {
                {{ locale.t('cert.copied') }}
              } @else {
                ↗ {{ locale.t('cert.share') }}
              }
            </button>
          </div>
        </div>
      }
    }
  `,
  styles: `
    .crumb {
      display: inline-block;
      margin-bottom: 1.4rem;
      text-decoration: none;
      &:hover { color: var(--accent); }
    }

    .missing,
    .locked {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
      padding: 2rem 0;
    }

    .locked__icon { font-size: 2.6rem; }

    .locked h1 { font-size: clamp(1.9rem, 4vw, 2.8rem); }

    .locked__sub {
      color: var(--ink-soft);
      max-width: 48ch;
      font-size: 1.05rem;
    }

    .locked__progress {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      margin: 0.4rem 0 0.6rem;
    }

    .progress {
      width: 240px;
      height: 10px;
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

    .stage {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1.4rem;
      padding-bottom: 2rem;
    }

    /* A4-landscape feel: 297 × 210 proportions, centered. */
    .cert-sheet {
      position: relative;
      width: min(100%, 980px);
      aspect-ratio: 297 / 210;
      background: var(--card);
      border: 3px solid var(--accent);
      border-radius: 6px;
      box-shadow: var(--shadow-lift);
      padding: clamp(0.6rem, 2vw, 1.1rem);
    }

    .cert-sheet__inner {
      position: relative;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      gap: clamp(0.3rem, 1.2vw, 0.7rem);
      border: 1.5px solid var(--marker);
      outline: 1px dashed var(--line-strong);
      outline-offset: -10px;
      padding: clamp(1rem, 3.5vw, 2.4rem);
      background:
        radial-gradient(circle at 0% 0%, color-mix(in srgb, var(--marker) 16%, transparent) 0%, transparent 26%),
        radial-gradient(circle at 100% 100%, color-mix(in srgb, var(--accent) 10%, transparent) 0%, transparent 26%);
    }

    .cert-wordmark {
      font-family: var(--font-display);
      font-weight: 700;
      font-size: clamp(0.85rem, 1.6vw, 1.05rem);
      letter-spacing: 0.04em;
      color: var(--ink);
    }

    .cert-kicker {
      color: var(--accent-deep);
      letter-spacing: 0.28em;
      text-transform: uppercase;
      font-size: clamp(0.62rem, 1.3vw, 0.8rem);
    }

    .cert-presented {
      color: var(--ink-soft);
      font-size: clamp(0.78rem, 1.5vw, 0.98rem);
    }

    .cert-name {
      font-family: var(--font-display);
      font-size: clamp(1.6rem, 5vw, 3.2rem);
      line-height: 1.1;
      color: var(--ink);
      max-width: 22ch;
    }

    .cert-course {
      font-size: clamp(1.05rem, 2.6vw, 1.7rem);
      color: var(--accent-deep);
      max-width: 34ch;
    }

    .cert-date {
      color: var(--ink-soft);
      margin-top: 0.2rem;
    }

    .cert-rule {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      width: min(60%, 360px);
      margin-top: clamp(0.3rem, 1.4vw, 0.9rem);

      &::before,
      &::after {
        content: '';
        flex: 1;
        height: 2px;
        background: var(--sage);
      }
    }

    .cert-rule__seal { font-size: clamp(1.2rem, 2.6vw, 1.8rem); }

    .cert-footer {
      font-family: var(--font-mono);
      font-size: clamp(0.56rem, 1.1vw, 0.72rem);
      letter-spacing: 0.08em;
      color: var(--ink-soft);
    }

    .actions {
      display: flex;
      gap: 0.8rem;
      flex-wrap: wrap;
      justify-content: center;
    }
  `,
})
export class CertificatePage {
  protected readonly locale = inject(LocaleService);
  private readonly api = inject(LearningApi);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  protected readonly course = signal<Course | null>(null);
  protected readonly loading = signal(true);
  protected readonly copied = signal(false);
  private copiedTimer: ReturnType<typeof setTimeout> | null = null;

  protected readonly enrollment = computed(() => {
    const c = this.course();
    return c ? this.api.enrollments().find((e) => e.course === c.id) : undefined;
  });

  protected readonly progress = computed(() => this.enrollment()?.progress_percentage ?? 0);

  protected readonly completed = computed(() => this.progress() >= 100);

  protected readonly studentName = computed(
    () =>
      this.auth.user()?.display_name ||
      this.enrollment()?.student_name ||
      this.auth.user()?.email ||
      'Student',
  );

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      if (slug) void this.load(slug);
    });
  }

  private async load(slug: string): Promise<void> {
    this.loading.set(true);
    try {
      const [course] = await Promise.all([
        this.api.getCourse(slug),
        // Make sure enrollments are on hand even on a cold navigation.
        this.api.refreshEnrollments(),
      ]);
      this.course.set(course);
    } catch {
      this.course.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  /** Completion date — today, formatted for the active locale. */
  protected completionDate(): string {
    return new Date().toLocaleDateString(this.locale.id() === 'ms' ? 'ms-MY' : 'en-MY', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }

  protected print(): void {
    window.print();
  }

  protected async share(): Promise<void> {
    const c = this.course();
    const url = window.location.href;
    const title = `${this.locale.t('cert.title')} — ${c?.title ?? 'MentorMinds'}`;
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({ title, url });
        return;
      } catch {
        // Cancelled or unsupported payload — fall through to copy.
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      this.copied.set(true);
      if (this.copiedTimer) clearTimeout(this.copiedTimer);
      this.copiedTimer = setTimeout(() => this.copied.set(false), 2000);
    } catch {
      // Clipboard blocked — nothing else to do.
    }
  }
}

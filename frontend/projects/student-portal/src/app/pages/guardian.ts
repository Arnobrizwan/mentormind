import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';

import { GuardianApi, GuardianSummary } from '../core/guardian';
import { LocaleService } from '../core/locale';

/**
 * The parent/guardian progress report — a public, read-only page reachable
 * only with the share token a student generates from their profile. No
 * account or login: revoking the link from the profile kills this URL.
 */
@Component({
  selector: 'mm-guardian',
  template: `
    @if (loading()) {
      <p class="mono-label">{{ locale.t('guardian.page.loading') }}</p>
    } @else if (summary(); as s) {
      <article class="report rise">
        <header class="report__head">
          <p class="mono-label">{{ locale.t('guardian.page.label') }} · MentorMinds</p>
          <h1>{{ s.student_name }}</h1>
          <p class="mono-label">
            {{ locale.t('guardian.page.generated') }} {{ shortDate(s.generated_at) }}
          </p>
        </header>

        <div class="stats">
          <div class="stat">
            <span class="stat__num">{{ s.points_week }}</span>
            <span class="mono-label">{{ locale.t('guardian.page.points') }}</span>
          </div>
          <div class="stat">
            <span class="stat__num">🔥 {{ s.streak }}</span>
            <span class="mono-label">{{ locale.t('dash.streak') }}</span>
          </div>
        </div>

        <section class="block">
          <h2>{{ locale.t('guardian.page.courses') }}</h2>
          @for (course of s.courses; track course.course_title) {
            <div class="course">
              <div class="course__head">
                <strong>{{ course.course_title }}</strong>
                <span class="grade mono-label">{{ locale.t('dash.predicted') }} {{ course.predicted_grade }}</span>
              </div>
              <div class="bar" role="img" [attr.aria-label]="course.readiness + '%'">
                <div class="bar__fill" [style.width.%]="course.readiness"></div>
              </div>
              <span class="mono-label">
                {{ course.readiness }}% {{ locale.t('guardian.page.readiness') }} ·
                {{ course.components.progress_pct }}% {{ locale.t('dash.avgProgress') }}
              </span>
            </div>
          } @empty {
            <p class="quiet">{{ locale.t('guardian.page.empty') }}</p>
          }
        </section>

        @if (s.weak_topics.length > 0) {
          <section class="block">
            <h2>{{ locale.t('guardian.page.focus') }}</h2>
            <ul class="topics">
              @for (topic of s.weak_topics; track topic.topic) {
                <li>
                  {{ topic.topic }}
                  <span class="mono-label">{{ topic.accuracy }}% {{ locale.t('dash.accuracy') }}</span>
                </li>
              }
            </ul>
          </section>
        }

        @if (s.recent_quizzes.length > 0) {
          <section class="block">
            <h2>{{ locale.t('guardian.page.recent') }}</h2>
            <table class="record">
              <tbody>
                @for (attempt of s.recent_quizzes; track attempt.completed_at) {
                  <tr>
                    <td>{{ attempt.quiz }}</td>
                    <td class="mono-label">{{ attempt.course }}</td>
                    <td class="score" [class.score--pass]="attempt.score >= 50">
                      {{ attempt.score }}%
                    </td>
                    <td class="mono-label">{{ shortDate(attempt.completed_at) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </section>
        }
      </article>
    } @else {
      <div class="missing rise">
        <h1>{{ locale.t('guardian.page.expired.title') }}</h1>
        <p class="quiet">{{ locale.t('guardian.page.expired.sub') }}</p>
      </div>
    }
  `,
  styles: `
    .report {
      max-width: 660px;
      margin: 0 auto;
    }

    .report__head {
      padding-bottom: 1.2rem;
      border-bottom: 2px solid var(--line-strong);
      margin-bottom: 1.4rem;

      h1 {
        font-size: clamp(2rem, 4.5vw, 2.8rem);
        margin: 0.4rem 0;
      }
    }

    .stats {
      display: flex;
      gap: 1.2rem;
      margin-bottom: 1.6rem;
    }

    .stat {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
      padding: 1rem 1.2rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 12px;
    }

    .stat__num {
      font-family: var(--font-display);
      font-size: 1.9rem;
      font-weight: 640;
    }

    .block {
      margin-bottom: 1.6rem;

      h2 { font-size: 1.25rem; margin-bottom: 0.7rem; }
    }

    .course {
      padding: 0.85rem 0;
      border-bottom: 1px dashed var(--line);
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .course__head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.8rem;
    }

    .grade {
      padding: 0.1rem 0.55rem;
      border: 1.5px solid var(--marker);
      border-radius: 999px;
      font-weight: 700;
      white-space: nowrap;
    }

    .bar {
      height: 10px;
      border-radius: 99px;
      background: color-mix(in srgb, var(--ink) 8%, transparent);
      border: 1px solid var(--line);
      overflow: hidden;
    }

    .bar__fill {
      height: 100%;
      border-radius: inherit;
      background: var(--sage);
    }

    .topics {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      li {
        display: flex;
        justify-content: space-between;
        gap: 0.8rem;
        padding: 0.5rem 0;
        border-bottom: 1px dashed var(--line);
      }
    }

    .record {
      width: 100%;
      border-collapse: collapse;

      td {
        padding: 0.6rem 0.5rem;
        border-bottom: 1px dashed var(--line);
        font-size: 0.92rem;
      }
    }

    .score { font-weight: 700; color: var(--danger); }
    .score--pass { color: var(--sage-deep, var(--sage)); }

    .quiet { color: var(--ink-soft); }

    .missing {
      max-width: 560px;
      margin: 3rem auto;
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
    }
  `,
})
export class GuardianPage {
  private readonly api = inject(GuardianApi);
  private readonly route = inject(ActivatedRoute);
  protected readonly locale = inject(LocaleService);

  protected readonly summary = signal<GuardianSummary | null>(null);
  protected readonly loading = signal(true);

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const token = params.get('token');
      if (token) void this.load(token);
    });
  }

  private async load(token: string): Promise<void> {
    this.loading.set(true);
    try {
      this.summary.set(await this.api.summary(token));
    } catch {
      this.summary.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  protected shortDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  }
}

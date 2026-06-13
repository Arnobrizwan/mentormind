import { Component, OnInit, computed, inject, input, signal } from '@angular/core';

import { CourseInsights, StudioApi } from '../core/api';
import { staggerDelay } from '../core/animations';
import { apiErrorMessage } from '../core/errors';
import { Course, ItemAnalysis } from '../core/models';

/**
 * Class-wide topic insights: quiz accuracy and short-answer scores per topic,
 * weakest-first, so the instructor can see what to reteach at a glance.
 */
@Component({
  selector: 'st-insights-tab',
  template: `
    @if (loading()) {
      <p class="tag" style="padding: 1.2rem 0">Reading the class signals…</p>
    } @else if (error(); as message) {
      <p class="error-note" role="alert">{{ message }}</p>
    } @else if (insights(); as data) {
      @if (teachNext(); as topic) {
        <div class="panel callout sheet-in" role="status">
          📌 Teach next: <strong>{{ topic }}</strong>
        </div>
      }

      <section class="panel block sheet-in" style="animation-delay: 60ms">
        <p class="tag">Quiz accuracy by topic · weakest first</p>
        @if (data.quiz_topics.length === 0) {
          <p class="tag empty">No quiz attempts yet — insights appear once students answer quizzes.</p>
        } @else {
          <ul class="topics">
            @for (t of data.quiz_topics; track t.topic; let i = $index) {
              <li class="topic sheet-in" [style.animation-delay.ms]="stagger(i)">
                <div class="topic__head">
                  <span class="topic__name">{{ t.topic }}</span>
                  <span class="tag" [class]="bandTag(t.accuracy)">{{ t.accuracy }}%</span>
                </div>
                <div class="ibar" role="img" [attr.aria-label]="t.topic + ': ' + t.accuracy + '% accuracy'">
                  <div
                    class="ibar__fill"
                    [class.ibar__fill--low]="t.accuracy < 50"
                    [class.ibar__fill--mid]="t.accuracy >= 50 && t.accuracy < 80"
                    [style.width.%]="t.accuracy"
                  ></div>
                </div>
                <span class="tag topic__count">{{ t.answers }} {{ t.answers === 1 ? 'answer' : 'answers' }}</span>
              </li>
            }
          </ul>
        }
      </section>

      <section class="panel block sheet-in" style="animation-delay: 90ms">
        <p class="tag">Item analysis · per-question difficulty &amp; discrimination</p>
        @if (course().quizzes.length === 0) {
          <p class="tag empty">No quizzes yet — create one to analyse its questions.</p>
        } @else {
          <div class="quiz-pick">
            @for (quiz of course().quizzes; track quiz.id) {
              <button
                type="button"
                class="btn btn--line btn--sm"
                [class.is-active]="analysis()?.quiz === quiz.id"
                (click)="analyse(quiz.id)"
                [disabled]="analysing()"
              >
                {{ quiz.title }}
              </button>
            }
          </div>

          @if (analysisError(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          } @else if (analysing()) {
            <p class="tag empty">Crunching the responses…</p>
          } @else if (analysis(); as items) {
            @if (items.attempts === 0) {
              <p class="tag empty">No attempts on this quiz yet — analysis appears once students answer.</p>
            } @else {
              <p class="tag">
                {{ items.attempts }} attempt(s).
                @if (items.attempts < items.min_attempts_for_discrimination) {
                  Discrimination needs at least {{ items.min_attempts_for_discrimination }} attempts.
                }
              </p>
              <ul class="items">
                @for (item of items.questions; track item.id) {
                  <li class="item">
                    <div class="item__head">
                      <span class="item__text">{{ item.text }}</span>
                      @for (flag of item.flags; track flag) {
                        <span class="tag flag" [class.flag--warn]="flag === 'review'">
                          {{ flagLabel(flag) }}
                        </span>
                      }
                    </div>
                    <div class="item__stats">
                      <span class="tag">
                        difficulty
                        <strong>{{ item.difficulty === null ? '—' : pct(item.difficulty) }}</strong>
                      </span>
                      <span class="tag" [title]="'Upper-lower 27% index — negative means strong students miss it more than weak ones'">
                        discrimination
                        <strong [class.neg]="(item.discrimination ?? 0) < 0">
                          {{ item.discrimination === null ? '—' : item.discrimination }}
                        </strong>
                      </span>
                      <span class="tag">{{ item.responses }} response(s)</span>
                    </div>
                    <ul class="distractors">
                      @for (d of item.distractors; track $index) {
                        <li class="tag" [class.distractor--correct]="d.is_correct">
                          {{ d.is_correct ? '✓' : '·' }} {{ d.option }} — {{ d.picks }}
                        </li>
                      }
                    </ul>
                  </li>
                }
              </ul>
            }
          }
        }
      </section>

      <section class="panel block sheet-in" style="animation-delay: 120ms">
        <p class="tag">Short-answer scores by topic · weakest first</p>
        @if (data.short_answer_topics.length === 0) {
          <p class="tag empty">No short-answer submissions yet — insights appear once students submit.</p>
        } @else {
          <ul class="topics">
            @for (t of data.short_answer_topics; track t.topic; let i = $index) {
              <li class="topic sheet-in" [style.animation-delay.ms]="stagger(i)">
                <div class="topic__head">
                  <span class="topic__name">{{ t.topic }}</span>
                  <span class="tag" [class]="bandTag(t.avg_pct)">avg {{ t.avg_pct }}%</span>
                </div>
                <div class="ibar" role="img" [attr.aria-label]="t.topic + ': average ' + t.avg_pct + '%'">
                  <div
                    class="ibar__fill"
                    [class.ibar__fill--low]="t.avg_pct < 50"
                    [class.ibar__fill--mid]="t.avg_pct >= 50 && t.avg_pct < 80"
                    [style.width.%]="t.avg_pct"
                  ></div>
                </div>
                <span class="tag topic__count">
                  {{ t.submissions }} {{ t.submissions === 1 ? 'submission' : 'submissions' }}
                </span>
              </li>
            }
          </ul>
        }
      </section>
    }
  `,
  styles: `
    .callout {
      padding: 0.9rem 1.2rem;
      margin-bottom: 1.1rem;
      border-left: 4px solid var(--amber);
      font-size: 1.05rem;
    }

    .block {
      padding: 1.2rem;
      margin-bottom: 1.1rem;
    }

    .empty {
      padding: 0.9rem 0 0.3rem;
    }

    .topics {
      list-style: none;
      margin: 0.8rem 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .topic__head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.8rem;
      margin-bottom: 0.35rem;
    }

    .topic__name {
      font-weight: 600;
    }

    .band--low { color: var(--red, #b23a2c); }
    .band--mid { color: var(--amber); }
    .band--ok { color: var(--teal); }

    .ibar {
      height: 10px;
      border-radius: 99px;
      background: color-mix(in srgb, var(--ink) 8%, transparent);
      border: 1px solid var(--line, color-mix(in srgb, var(--ink) 14%, transparent));
      overflow: hidden;
    }

    .ibar__fill {
      height: 100%;
      border-radius: inherit;
      background: var(--teal);
      transform-origin: left center;
      animation: ibar-grow 600ms ease both;
    }

    .ibar__fill--mid { background: var(--amber); }
    .ibar__fill--low { background: var(--red, #b23a2c); }

    .topic__count {
      display: inline-block;
      margin-top: 0.3rem;
    }

    @keyframes ibar-grow {
      from { transform: scaleX(0); }
      to { transform: scaleX(1); }
    }

    .quiz-pick {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
      margin: 0.8rem 0;

      .is-active { border-color: var(--amber); color: var(--amber); }
    }

    .items {
      list-style: none;
      margin: 0.8rem 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
    }

    .item__head {
      display: flex;
      align-items: baseline;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .item__text { font-weight: 600; }

    .flag {
      padding: 0.1rem 0.5rem;
      border: 1px solid var(--line-strong);
      border-radius: 999px;
    }

    .flag--warn { border-color: var(--red, #b23a2c); color: var(--red, #b23a2c); }

    .item__stats {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      margin: 0.35rem 0;

      .neg { color: var(--red, #b23a2c); }
    }

    .distractors {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      gap: 0.8rem;
      flex-wrap: wrap;
    }

    .distractor--correct { color: var(--teal); font-weight: 600; }

    @media (prefers-reduced-motion: reduce) {
      .ibar__fill { animation: none; }
    }
  `,
})
export class InsightsTab implements OnInit {
  private readonly api = inject(StudioApi);

  readonly course = input.required<Course>();

  protected readonly insights = signal<CourseInsights | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  /** Weakest quiz topic (list is weakest-first) when anything sits below 80%. */
  protected readonly teachNext = computed(() => {
    const first = this.insights()?.quiz_topics[0];
    return first && first.accuracy < 80 ? first.topic : null;
  });

  async ngOnInit(): Promise<void> {
    try {
      this.insights.set(await this.api.courseInsights(this.course().slug));
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load class insights.'));
    } finally {
      this.loading.set(false);
    }
  }

  protected bandTag(pct: number): string {
    return pct < 50 ? 'tag band--low' : pct < 80 ? 'tag band--mid' : 'tag band--ok';
  }

  protected stagger(index: number): number {
    return staggerDelay(index);
  }

  protected readonly analysis = signal<ItemAnalysis | null>(null);
  protected readonly analysing = signal(false);
  protected readonly analysisError = signal<string | null>(null);

  protected async analyse(quizId: number): Promise<void> {
    if (this.analysing()) return;
    this.analysing.set(true);
    this.analysisError.set(null);
    try {
      this.analysis.set(await this.api.itemAnalysis(quizId));
    } catch (err) {
      this.analysis.set(null);
      this.analysisError.set(apiErrorMessage(err, 'Could not analyse that quiz.'));
    } finally {
      this.analysing.set(false);
    }
  }

  protected pct(p: number): string {
    return `${Math.round(p * 100)}%`;
  }

  protected flagLabel(flag: string): string {
    return flag === 'too_easy'
      ? 'too easy'
      : flag === 'too_hard'
        ? 'too hard'
        : 'review — possible miskey';
  }
}

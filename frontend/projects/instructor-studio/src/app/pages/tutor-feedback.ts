import { Component, inject, signal } from '@angular/core';

import { StudioApi, TutorFeedbackItem } from '../core/api';
import { apiErrorMessage } from '../core/errors';

/**
 * The human-in-the-loop end of the tutor's model-improvement flywheel:
 * every thumbs-down (and any flag note a student left) surfaces here, paired
 * with the question that prompted it — raw material for the next fine-tune.
 */
@Component({
  selector: 'st-tutor-feedback',
  template: `
    <header class="head sheet-in">
      <div>
        <p class="tag">AI tutor</p>
        <h1>Flagged answers</h1>
      </div>
      <div class="head__actions">
        <button class="btn btn--line" (click)="refresh()" [disabled]="loading()">Refresh</button>
      </div>
    </header>

    @if (review(); as r) {
      <div class="stats">
        <div class="panel stat">
          <span class="stat__num">👍 {{ r.summary.up }}</span>
          <span class="tag">helpful</span>
        </div>
        <div class="panel stat">
          <span class="stat__num">👎 {{ r.summary.down }}</span>
          <span class="tag">not helpful</span>
        </div>
        <div class="panel stat">
          <span class="stat__num">🚩 {{ r.summary.flagged }}</span>
          <span class="tag">with a note</span>
        </div>
      </div>
    }

    @if (error(); as message) {
      <p class="error-note" role="alert" style="margin-bottom: 1rem">{{ message }}</p>
    }

    @if (loading()) {
      <p class="tag" style="padding: 1.2rem 0" role="status">Reading the feedback ledger…</p>
    } @else if (review()?.items?.length) {
      <div class="list">
        @for (item of review()!.items; track item.id) {
          <article class="panel fb">
            <div class="fb__meta">
              <span class="tag">{{ item.subject || 'general' }}{{ item.level ? ' · ' + item.level : '' }}</span>
              <span class="tag">{{ item.student }}</span>
              <span class="tag">{{ item.created_at.slice(0, 10) }}</span>
            </div>
            <p class="fb__q"><strong>Q:</strong> {{ item.question || '—' }}</p>
            <p class="fb__a">{{ item.content }}</p>
            @if (item.feedback_note) {
              <p class="fb__note">🚩 {{ item.feedback_note }}</p>
            }
          </article>
        }
      </div>
    } @else {
      <p class="tag" style="padding: 1.2rem 0" role="status">
        No flagged answers — students are happy with the tutor. 🎉
      </p>
    }
  `,
  styles: `
    .stats {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      margin-bottom: 1.4rem;
    }
    .stat {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
      padding: 0.9rem 1.2rem;
    }
    .stat__num {
      font-size: 1.4rem;
      font-weight: 600;
    }
    .list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .fb {
      padding: 1.1rem 1.3rem;
    }
    .fb__meta {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
      margin-bottom: 0.6rem;
    }
    .fb__q {
      margin: 0 0 0.5rem;
    }
    .fb__a {
      margin: 0;
      opacity: 0.85;
      white-space: pre-wrap;
    }
    .fb__note {
      margin: 0.7rem 0 0;
      padding: 0.6rem 0.8rem;
      border-left: 3px solid var(--danger, #e5484d);
      background: color-mix(in srgb, var(--danger, #e5484d) 8%, transparent);
      border-radius: 0 6px 6px 0;
    }
  `,
})
export class TutorFeedbackPage {
  private readonly api = inject(StudioApi);

  protected readonly review = signal<{
    summary: { up: number; down: number; flagged: number };
    items: TutorFeedbackItem[];
  } | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  constructor() {
    void this.refresh();
  }

  protected async refresh(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      this.review.set(await this.api.tutorFeedback());
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load tutor feedback.'));
    } finally {
      this.loading.set(false);
    }
  }
}

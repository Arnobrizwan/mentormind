import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../core/errors';
import { RevisionApi, RevisionCard } from '../core/revision';

/** Button order on screen ↔ keyboard keys 1-4. */
const GRADES = [
  { key: 1, grade: 1, label: 'Again', kind: 'again' },
  { key: 2, grade: 3, label: 'Hard', kind: 'hard' },
  { key: 3, grade: 4, label: 'Good', kind: 'good' },
  { key: 4, grade: 5, label: 'Easy', kind: 'easy' },
] as const;

@Component({
  selector: 'mm-revision',
  imports: [RouterLink],
  host: { '(window:keydown)': 'onKey($event)' },
  template: `
    <section class="rev rise">
      <header class="rev__head">
        <p class="mono-label">Spaced repetition</p>
        <h1>Revision</h1>
        @if (!loading()) {
          <p class="mono-label rev__due" aria-live="polite">
            {{ dueCount() }} {{ dueCount() === 1 ? 'card' : 'cards' }} due ·
            {{ queue().length }} in this session
          </p>
        }
      </header>

      @if (loadError(); as message) {
        <p class="error-note" role="alert">
          {{ message }}
          <button type="button" class="retry" (click)="reload()">retry</button>
        </p>
      }

      @if (loading()) {
        <p class="mono-label">Shuffling your cards…</p>
      } @else if (current(); as card) {
        <div class="card" [class.card--flipped]="revealed()">
          <div class="card__labels">
            @if (card.topic) {
              <span class="card__topic mono-label">{{ card.topic }}</span>
            }
            <span class="mono-label card__course">{{ card.course_title }}</span>
          </div>
          <p class="card__face">{{ card.front }}</p>
          @if (revealed()) {
            <hr class="card__rule" />
            <p class="card__face card__face--back">{{ card.back }}</p>
          }
        </div>

        @if (error(); as message) {
          <p class="error-note" role="alert">{{ message }}</p>
        }

        @if (!revealed()) {
          <div class="rev__actions">
            <button type="button" class="btn btn--accent rev__flip" (click)="flip()">
              Show answer <kbd>space</kbd>
            </button>
          </div>
        } @else {
          <div class="grades" role="group" aria-label="Grade this card">
            @for (option of grades; track option.key) {
              <button
                type="button"
                class="grade-btn"
                [class.grade-btn--again]="option.kind === 'again'"
                [class.grade-btn--easy]="option.kind === 'easy'"
                [disabled]="busy()"
                (click)="grade(option.grade)"
                [attr.aria-label]="option.label + ' — comes back in ' + intervalHint(card, option.grade)"
              >
                <span class="grade-btn__label">{{ option.label }}</span>
                <span class="grade-btn__hint mono-label">
                  {{ intervalHint(card, option.grade) }} · {{ option.key }}
                </span>
              </button>
            }
          </div>
        }
      } @else {
        <div class="done rise">
          <h2>All caught up 🎉</h2>
          <p>No cards are due right now — come back tomorrow.</p>
          <a routerLink="/dashboard" class="btn btn--ghost">← Back to my desk</a>
        </div>
      }
    </section>
  `,
  styles: `
    .rev {
      max-width: 640px;
      margin: 0 auto;
    }

    .rev__head {
      margin-bottom: 1.4rem;

      h1 {
        font-size: clamp(2rem, 4.5vw, 3rem);
        margin: 0.4rem 0 0.5rem;
      }
    }

    .rev__due { color: var(--ink-soft); }

    .card {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      min-height: 240px;
      padding: 1.6rem;
      background: var(--card);
      border: 2px solid var(--ink);
      border-radius: 14px;
      margin-bottom: 1.1rem;
    }

    .card__labels {
      display: flex;
      align-items: baseline;
      gap: 0.7rem;
      flex-wrap: wrap;
    }

    .card__topic {
      padding: 0.15rem 0.6rem;
      border: 1.5px solid var(--sage);
      border-radius: 999px;
      color: var(--sage-deep);
    }

    .card__course { color: var(--ink-soft); }

    .card__face {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-family: var(--font-display);
      font-size: 1.4rem;
      line-height: 1.4;
      white-space: pre-wrap;
    }

    .card__face--back {
      font-family: var(--font-body);
      font-size: 1.05rem;
      color: var(--ink);
    }

    .card__rule {
      border: none;
      border-top: 1.5px dashed var(--line-strong);
      width: 100%;
      margin: 0;
    }

    .rev__actions {
      display: flex;
      justify-content: center;
    }

    .rev__flip kbd {
      margin-left: 0.45rem;
      padding: 0.05rem 0.4rem;
      border: 1px solid currentColor;
      border-radius: 5px;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      opacity: 0.8;
    }

    .grades {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.7rem;
    }

    .grade-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.2rem;
      padding: 0.7rem 0.5rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 10px;
      cursor: pointer;
      font-family: var(--font-body);
      color: var(--ink);

      &:hover:not(:disabled) { border-color: var(--accent); }
      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
      &:disabled { opacity: 0.5; cursor: default; }
    }

    .grade-btn__label { font-weight: 700; }

    .grade-btn__hint { color: var(--ink-soft); }

    .grade-btn--again {
      border-color: var(--danger);
      .grade-btn__label { color: var(--danger); }
    }

    .grade-btn--easy {
      border-color: var(--sage);
      .grade-btn__label { color: var(--sage-deep); }
    }

    .done {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      align-items: flex-start;
      padding: 1.5rem 0;

      p { color: var(--ink-soft); }
      .btn { margin-top: 0.5rem; }
    }

    @media (max-width: 560px) {
      .grades { grid-template-columns: repeat(2, 1fr); }
    }
  `,
})
export class RevisionPage {
  private readonly api = inject(RevisionApi);

  protected readonly grades = GRADES;

  protected readonly queue = signal<RevisionCard[]>([]);
  protected readonly dueCount = signal(0);
  protected readonly revealed = signal(false);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly loadError = signal<string | null>(null);

  protected readonly current = computed<RevisionCard | null>(() => this.queue()[0] ?? null);

  /** One confirmation refetch when the local queue empties, to be sure. */
  private confirmedEmpty = false;

  constructor() {
    void this.load();
  }

  protected reload(): void {
    this.confirmedEmpty = false;
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.loadError.set(null);
    try {
      const queue = await this.api.queue();
      this.queue.set(queue.cards);
      this.dueCount.set(queue.due_count);
      this.revealed.set(false);
    } catch (err) {
      this.loadError.set(apiErrorMessage(err, 'Could not load your revision queue.'));
    } finally {
      this.loading.set(false);
    }
  }

  protected flip(): void {
    if (!this.current()) return;
    this.revealed.update((open) => !open);
  }

  protected async grade(grade: number): Promise<void> {
    const card = this.current();
    if (!card || this.busy() || !this.revealed()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.api.review(card.id, grade);
      this.queue.update((cards) => cards.filter((c) => c.id !== card.id));
      this.dueCount.update((count) => Math.max(0, count - 1));
      this.revealed.set(false);
      if (this.queue().length === 0 && !this.confirmedEmpty) {
        // Refetch once to confirm nothing else came due mid-session.
        this.confirmedEmpty = true;
        void this.load();
      }
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not record that review — try again.'));
    } finally {
      this.busy.set(false);
    }
  }

  protected onKey(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    if (target && /^(input|textarea|select)$/i.test(target.tagName)) return;
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.code === 'Space') {
      event.preventDefault();
      this.flip();
      return;
    }
    if (this.revealed() && event.key >= '1' && event.key <= '4') {
      const option = GRADES[Number(event.key) - 1];
      event.preventDefault();
      void this.grade(option.grade);
    }
  }

  /** Mirror of the backend SM-2 schedule, for the button hints. */
  protected intervalHint(card: RevisionCard, grade: number): string {
    if (grade < 3) return '10 min';
    if (card.repetitions === 0) return '1 d';
    if (card.repetitions === 1) return '6 d';
    // Ease isn't exposed to the client; ~2.5 is the SM-2 starting point.
    return `~${Math.max(1, Math.round(card.interval_days * 2.5))} d`;
  }
}

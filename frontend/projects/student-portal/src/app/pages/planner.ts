import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../core/errors';
import { PlanItem, PlanItemKind, PlannerApi, WeekPlan } from '../core/planner';

const KIND_ICONS: Record<PlanItemKind, string> = {
  revision: '🃏',
  practice: '🎯',
  lesson: '📖',
  quiz: '📝',
};

@Component({
  selector: 'mm-planner',
  imports: [RouterLink],
  template: `
    <section class="plan rise">
      <header class="plan__head">
        <p class="mono-label">Study planner</p>
        @if (plan(); as p) {
          <h1>Week of {{ weekLabel(p.week_start) }}</h1>
          <div class="plan__meter">
            <div
              class="progress"
              role="progressbar"
              aria-label="Plan completion"
              [attr.aria-valuenow]="p.completion_pct"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="progress__bar" [style.width.%]="p.completion_pct"></div>
            </div>
            <span class="mono-label">{{ p.completion_pct }}% done</span>
            <button
              type="button"
              class="btn btn--ghost plan__refresh"
              (click)="refresh()"
              [disabled]="busy()"
            >
              {{ busy() ? 'Rebuilding…' : '↻ Refresh plan' }}
            </button>
          </div>
        } @else if (loading()) {
          <h1>This week</h1>
        }
      </header>

      @if (error(); as message) {
        <p class="error-note" role="alert">
          {{ message }}
          <button type="button" class="retry" (click)="reload()">retry</button>
        </p>
      }

      @if (loading()) {
        <p class="mono-label">Sketching out your week…</p>
      } @else if (plan(); as p) {
        <ul class="items">
          @for (item of p.items; track item.id) {
            <li class="item" [class.item--done]="item.done">
              <input
                type="checkbox"
                class="item__check"
                [checked]="item.done"
                [disabled]="togglingId() !== null"
                (change)="toggle(item, $event)"
                [attr.aria-label]="(item.done ? 'Mark not done: ' : 'Mark done: ') + item.title"
              />
              <span class="item__icon" aria-hidden="true">{{ icon(item.kind) }}</span>
              <div class="item__body">
                @if (item.link) {
                  <a class="item__title" [routerLink]="item.link">{{ item.title }}</a>
                } @else {
                  <span class="item__title">{{ item.title }}</span>
                }
                @if (item.detail) {
                  <p class="item__detail">{{ item.detail }}</p>
                }
              </div>
            </li>
          } @empty {
            <li class="items__empty">
              <p>Nothing on the plan yet — enroll in a course and check back.</p>
              <a routerLink="/" class="btn btn--ghost">Browse the catalog</a>
            </li>
          }
        </ul>
      }
    </section>
  `,
  styles: `
    .plan {
      max-width: 720px;
    }

    .plan__head {
      margin-bottom: 1.4rem;

      h1 {
        font-size: clamp(2rem, 4.5vw, 3rem);
        margin: 0.4rem 0 0.8rem;
      }
    }

    .plan__meter {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      flex-wrap: wrap;
    }

    .plan__refresh {
      font-size: 0.82rem;
      padding: 0.45rem 1rem;
      margin-left: auto;
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

    .items {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
    }

    .item {
      display: flex;
      align-items: flex-start;
      gap: 0.8rem;
      padding: 0.9rem 0.4rem;
      border-bottom: 1px dashed var(--line-strong);

      &:first-child { border-top: 1px dashed var(--line-strong); }
    }

    .item--done {
      .item__title { text-decoration: line-through; }
      .item__title,
      .item__detail { color: var(--ink-soft); }
    }

    .item__check {
      width: 1.15rem;
      height: 1.15rem;
      margin-top: 0.15rem;
      accent-color: var(--accent);
      cursor: pointer;

      &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
      &:disabled { cursor: default; }
    }

    .item__icon {
      font-size: 1.05rem;
      line-height: 1.5;
    }

    .item__body { flex: 1; }

    .item__title {
      font-weight: 600;
      color: var(--ink);
      text-decoration: none;
    }

    a.item__title:hover { color: var(--accent); }

    .item__detail {
      margin-top: 0.2rem;
      font-size: 0.88rem;
      color: var(--ink-soft);
    }

    .items__empty {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      align-items: flex-start;
      padding: 1.5rem 0;

      p { color: var(--ink-soft); }
    }
  `,
})
export class PlannerPage {
  private readonly api = inject(PlannerApi);

  protected readonly plan = signal<WeekPlan | null>(null);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly togglingId = signal<number | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    void this.load();
  }

  protected reload(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      this.plan.set(await this.api.week());
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load this week’s plan.'));
    } finally {
      this.loading.set(false);
    }
  }

  protected async refresh(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      this.plan.set(await this.api.rebuild());
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not rebuild the plan — try again.'));
    } finally {
      this.busy.set(false);
    }
  }

  protected async toggle(item: PlanItem, event: Event): Promise<void> {
    const checkbox = event.target as HTMLInputElement;
    if (this.togglingId() !== null) {
      // Another toggle is in flight — undo the native flip so the box keeps
      // matching the model ([checked] won't rewrite an unchanged binding).
      checkbox.checked = item.done;
      return;
    }
    this.togglingId.set(item.id);
    this.error.set(null);
    try {
      this.plan.set(await this.api.toggle(item.id));
    } catch (err) {
      checkbox.checked = item.done;
      this.error.set(apiErrorMessage(err, 'Could not update that item — try again.'));
    } finally {
      this.togglingId.set(null);
    }
  }

  protected icon(kind: PlanItemKind): string {
    return KIND_ICONS[kind] ?? '•';
  }

  protected weekLabel(weekStart: string): string {
    const date = new Date(`${weekStart}T00:00:00`);
    if (Number.isNaN(date.getTime())) return weekStart;
    return date.toLocaleDateString(undefined, { day: 'numeric', month: 'long' });
  }
}

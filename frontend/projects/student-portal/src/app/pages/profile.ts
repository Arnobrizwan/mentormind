import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { User } from '../core/models';
import {
  AVATAR_MAX_BYTES,
  ActivityCalendar,
  PointsEvent,
  ProfileApi,
  ProfileUser,
  humanizeAction,
  relativeTime,
} from '../core/profile';

const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

/** Heatmap shape: 17 week-columns × 7 weekday-rows (Mon–Sun) = 119 cells. */
const HEATMAP_WEEKS = 17;

interface HeatCell {
  date: string;
  title: string;
  active: boolean;
  today: boolean;
  future: boolean;
}

/** Local-timezone YYYY-MM-DD (the API sends calendar dates, not instants). */
function isoLocal(date: Date): string {
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${m}-${d}`;
}

@Component({
  selector: 'mm-profile',
  imports: [RouterLink],
  template: `
    <section class="head rise">
      <p class="mono-label">My Profile</p>
      <h1>Your details</h1>
    </section>

    @if (loading()) {
      <div class="skeletons" role="status" aria-label="Loading your profile">
        <div class="skeleton skeleton--row"></div>
        <div class="skeleton skeleton--row"></div>
      </div>
    } @else if (loadError(); as msg) {
      <p class="error-note rise" role="alert">{{ msg }}</p>
    } @else if (user(); as u) {
      <section class="card-block rise" style="animation-delay: 60ms" aria-label="Avatar">
        <div class="avatar-row">
          @if (u.avatar_url) {
            <img class="avatar" [src]="u.avatar_url" [alt]="(u.display_name || u.email) + ' avatar'" />
          } @else {
            <span class="avatar avatar--initial" aria-hidden="true">{{ initial() }}</span>
          }
          <div class="avatar-meta">
            <strong>{{ u.display_name || u.email }}</strong>
            <span class="mono-label">{{ u.email }}</span>
            <div class="avatar-actions">
              <input
                #avatarInput
                class="visually-hidden"
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                (change)="onAvatarPicked($event)"
                aria-label="Choose a new profile photo"
              />
              <button
                type="button"
                class="btn btn--ghost btn--small"
                (click)="avatarInput.click()"
                [disabled]="avatarSaving()"
              >
                {{ avatarSaving() ? 'Uploading…' : 'Change photo' }}
              </button>
              @if (avatarSaved()) {
                <span class="tick" aria-live="polite">✓ Updated</span>
              }
            </div>
            @if (avatarError(); as msg) {
              <p class="error-note" role="alert">{{ msg }}</p>
            }
          </div>
        </div>
      </section>

      <section class="card-block rise" style="animation-delay: 110ms" aria-label="Display name">
        <h2>Display name</h2>
        <form class="name-row" (submit)="saveName($event)">
          <label class="field name-field">
            <span class="visually-hidden">Display name</span>
            <input
              type="text"
              name="display_name"
              [value]="nameDraft()"
              (input)="nameDraft.set(nameInput.value)"
              #nameInput
              maxlength="120"
              [disabled]="nameSaving()"
            />
          </label>
          <button
            type="submit"
            class="btn btn--accent btn--small"
            [disabled]="nameSaving() || !nameDirty()"
          >
            {{ nameSaving() ? 'Saving…' : 'Save' }}
          </button>
          @if (nameSaved()) {
            <span class="tick" aria-live="polite">✓ Saved</span>
          }
        </form>
        @if (nameError(); as msg) {
          <p class="error-note" role="alert">{{ msg }}</p>
        }
      </section>

      <section
        class="card-block rise"
        [class.card-block--premium]="u.is_premium"
        style="animation-delay: 160ms"
        aria-label="Subscription"
      >
        <h2>Plan</h2>
        @if (u.is_premium) {
          <p class="plan plan--premium">
            ✨ Premium{{ premiumUntil() ? ' until ' + premiumUntil() : '' }}
          </p>
          <p class="plan-note">Unlimited AI tutor questions and all premium features.</p>
        } @else {
          <p class="plan">Free plan</p>
          <p class="plan-note">
            Want unlimited AI tutor questions?
            <a routerLink="/tutor">Upgrade from the AI Tutor page</a>.
          </p>
        }
      </section>
    }

    <section class="card-block rise" style="animation-delay: 185ms" aria-label="Activity">
      <h2>Activity</h2>
      @if (activity(); as cal) {
        <div class="heatmap" role="img" [attr.aria-label]="heatmapLabel()">
          @for (cell of heatmapCells(); track cell.date; let i = $index) {
            <span
              class="cell"
              [class.cell--active]="cell.active"
              [class.cell--today]="cell.today"
              [class.cell--future]="cell.future"
              [style.animation-delay.ms]="cellDelay(i)"
              [title]="cell.title"
            ></span>
          }
        </div>
        <p class="streak">🔥 {{ cal.streak }}-day streak</p>
      } @else if (activityError(); as msg) {
        <p class="plan-note">{{ msg }}</p>
      } @else {
        <p class="plan-note" role="status">Loading activity…</p>
      }
    </section>

    <section class="card-block rise" style="animation-delay: 210ms" aria-label="Points history">
      <h2>Points history</h2>
      @if (events().length === 0 && !historyLoading()) {
        <p class="plan-note">No points yet — complete a lesson or review some flashcards.</p>
      } @else {
        <ul class="feed">
          @for (event of events(); track event.at + event.action; let i = $index) {
            <li class="feed__row">
              <span class="feed__action">{{ label(event) }}</span>
              <span class="feed__pts">+{{ event.points }} pts</span>
              <span class="mono-label feed__when">{{ when(event) }}</span>
            </li>
          }
        </ul>
      }
      @if (historyError(); as msg) {
        <p class="error-note" role="alert">{{ msg }}</p>
      }
      @if (hasMore()) {
        <button
          type="button"
          class="btn btn--ghost btn--small"
          (click)="loadMore()"
          [disabled]="historyLoading()"
        >
          {{ historyLoading() ? 'Loading…' : 'Load more' }}
        </button>
      }
    </section>
  `,
  styles: `
    .head {
      margin-bottom: 1.8rem;

      h1 {
        font-size: clamp(2rem, 4.5vw, 3rem);
        margin-top: 0.7rem;
      }
    }

    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
      border: 0;
    }

    .card-block {
      margin-bottom: 1.6rem;
      padding: 1.4rem 1.6rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 14px;

      h2 {
        font-size: 1.25rem;
        margin-bottom: 0.9rem;
      }
    }

    .card-block--premium {
      border-color: var(--accent);
      background: linear-gradient(
        135deg,
        color-mix(in srgb, var(--accent) 8%, var(--card)) 0%,
        var(--card) 70%
      );
    }

    .avatar-row {
      display: flex;
      align-items: center;
      gap: 1.2rem;
      flex-wrap: wrap;
    }

    .avatar {
      width: 84px;
      height: 84px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid var(--line-strong);
      flex-shrink: 0;
    }

    .avatar--initial {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--grad-btn);
      color: #fff;
      font-family: var(--font-display);
      font-size: 2rem;
      border-color: transparent;
    }

    .avatar-meta {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      min-width: 0;

      strong { font-size: 1.1rem; }
    }

    .avatar-actions {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      margin-top: 0.3rem;
    }

    .btn--small {
      padding: 0.45rem 1.05rem;
      font-size: 0.82rem;
    }

    .tick {
      color: var(--sage);
      font-weight: 700;
      font-size: 0.88rem;
      animation: tick-in 0.3s var(--ease) both;
    }

    @keyframes tick-in {
      from { opacity: 0; transform: scale(0.7); }
      to { opacity: 1; transform: scale(1); }
    }

    @media (prefers-reduced-motion: reduce) {
      .tick { animation: none; }
    }

    .name-row {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      flex-wrap: wrap;
    }

    .name-field {
      flex: 1;
      min-width: 200px;
      max-width: 360px;
    }

    .error-note { margin-top: 0.7rem; }

    .plan {
      font-size: 1.05rem;
      font-weight: 700;
    }

    .plan--premium { color: var(--accent-deep); }

    .plan-note {
      margin-top: 0.35rem;
      color: var(--ink-soft);
      font-size: 0.92rem;

      a { color: var(--accent-deep); }
    }

    .heatmap {
      display: grid;
      grid-template-rows: repeat(7, 12px);
      grid-auto-flow: column;
      grid-auto-columns: 12px;
      gap: 3px;
      margin-bottom: 0.9rem;
      overflow-x: auto;
      padding: 2px;
      width: fit-content;
      max-width: 100%;
    }

    .cell {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      background: var(--line);
      animation: cell-in 0.35s var(--ease) both;
    }

    .cell--active { background: var(--accent); }

    .cell--today {
      outline: 2px solid var(--accent-deep);
      outline-offset: 1px;
    }

    .cell--future { visibility: hidden; }

    @keyframes cell-in {
      from { opacity: 0; transform: scale(0.6); }
      to { opacity: 1; transform: scale(1); }
    }

    @media (prefers-reduced-motion: reduce) {
      .cell { animation: none; }
    }

    .streak {
      font-weight: 700;
      font-size: 0.95rem;
    }

    .feed {
      list-style: none;
      margin: 0 0 0.9rem;
      padding: 0;
    }

    .feed__row {
      display: flex;
      align-items: baseline;
      gap: 0.9rem;
      padding: 0.55rem 0.2rem;
      border-bottom: 1px dashed var(--line);
      flex-wrap: wrap;
    }

    .feed__action {
      flex: 1;
      min-width: 160px;
      font-weight: 600;
      font-size: 0.95rem;
    }

    .feed__pts {
      font-family: var(--font-mono);
      font-weight: 700;
      color: var(--sage-deep);
      font-size: 0.88rem;
    }

    .feed__when { color: var(--ink-soft); }

    .skeletons {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      padding: 0.5rem 0 1.5rem;
    }

    .skeleton--row { height: 96px; }
  `,
})
export class ProfilePage {
  private readonly api = inject(ProfileApi);
  private readonly auth = inject(AuthService);

  protected readonly loading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  protected readonly user = signal<ProfileUser | null>(null);

  protected readonly nameDraft = signal('');
  protected readonly nameSaving = signal(false);
  protected readonly nameSaved = signal(false);
  protected readonly nameError = signal<string | null>(null);

  protected readonly avatarSaving = signal(false);
  protected readonly avatarSaved = signal(false);
  protected readonly avatarError = signal<string | null>(null);

  protected readonly activity = signal<ActivityCalendar | null>(null);
  protected readonly activityError = signal<string | null>(null);

  /**
   * 17 columns × 7 rows, column-major so `grid-auto-flow: column` lays weeks
   * out left-to-right with Mon–Sun rows. The last column is the current week;
   * its not-yet-reached days render as invisible placeholders.
   */
  protected readonly heatmapCells = computed<HeatCell[]>(() => {
    const cal = this.activity();
    if (!cal) return [];
    const active = new Set(cal.days);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayIso = isoLocal(today);
    const monday = new Date(today);
    monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
    const start = new Date(monday);
    start.setDate(start.getDate() - (HEATMAP_WEEKS - 1) * 7);
    const cells: HeatCell[] = [];
    for (let i = 0; i < HEATMAP_WEEKS * 7; i++) {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      const iso = isoLocal(date);
      const isActive = active.has(iso);
      const label = date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
      cells.push({
        date: iso,
        title: `${label} — ${isActive ? 'active' : 'no activity'}`,
        active: isActive,
        today: iso === todayIso,
        future: date.getTime() > today.getTime(),
      });
    }
    return cells;
  });

  protected readonly heatmapLabel = computed(() => {
    const cal = this.activity();
    if (!cal) return '';
    return `Activity heatmap: ${cal.days.length} active days in the last ${HEATMAP_WEEKS} weeks, ${cal.streak}-day streak`;
  });

  protected readonly events = signal<PointsEvent[]>([]);
  protected readonly historyLoading = signal(false);
  protected readonly historyError = signal<string | null>(null);
  private readonly nextPage = signal<number | null>(1);
  protected readonly hasMore = computed(() => this.nextPage() !== null);

  protected readonly initial = computed(() => {
    const u = this.user();
    const name = u?.display_name || u?.email || '?';
    return name.charAt(0).toUpperCase();
  });

  protected readonly nameDirty = computed(
    () => this.nameDraft().trim() !== (this.user()?.display_name ?? '').trim(),
  );

  protected readonly premiumUntil = computed(() => {
    const until = this.user()?.premium_until;
    if (!until) return null;
    const date = new Date(until);
    return Number.isNaN(date.getTime())
      ? until
      : date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  });

  constructor() {
    void this.load();
    void this.loadActivity();
    void this.loadMore();
  }

  /** Capped stagger so late cells don't drag the entrance out. */
  protected cellDelay(index: number): number {
    return Math.min(index * 4, 320);
  }

  private async loadActivity(): Promise<void> {
    try {
      this.activity.set(await this.api.activity());
    } catch (err) {
      this.activityError.set(apiErrorMessage(err, 'Could not load your activity calendar.'));
    }
  }

  private async load(): Promise<void> {
    try {
      const me = await this.api.me();
      this.user.set(me);
      this.nameDraft.set(me.display_name ?? '');
    } catch (err) {
      this.loadError.set(apiErrorMessage(err, 'Could not load your profile. Try again shortly.'));
    } finally {
      this.loading.set(false);
    }
  }

  protected label(event: PointsEvent): string {
    return humanizeAction(event.action);
  }

  protected when(event: PointsEvent): string {
    return relativeTime(event.at);
  }

  protected async saveName(submit: Event): Promise<void> {
    submit.preventDefault();
    const name = this.nameDraft().trim();
    if (this.nameSaving() || !name || !this.nameDirty()) return;
    this.nameSaving.set(true);
    this.nameError.set(null);
    this.nameSaved.set(false);
    try {
      const updated = await this.api.updateDisplayName(name);
      this.applyUser(updated);
      this.nameDraft.set(updated.display_name ?? name);
      this.nameSaved.set(true);
      setTimeout(() => this.nameSaved.set(false), 2500);
    } catch (err) {
      this.nameError.set(apiErrorMessage(err, 'Could not save your display name.'));
    } finally {
      this.nameSaving.set(false);
    }
  }

  protected async onAvatarPicked(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || this.avatarSaving()) return;
    this.avatarError.set(null);
    this.avatarSaved.set(false);

    if (!AVATAR_TYPES.includes(file.type)) {
      this.avatarError.set('Please choose a JPEG, PNG, WebP, or GIF image.');
      input.value = '';
      return;
    }
    if (file.size > AVATAR_MAX_BYTES) {
      this.avatarError.set('That image is over 2 MB — please pick a smaller one.');
      input.value = '';
      return;
    }

    this.avatarSaving.set(true);
    try {
      const updated = await this.api.uploadAvatar(file);
      this.applyUser(updated);
      this.avatarSaved.set(true);
      setTimeout(() => this.avatarSaved.set(false), 2500);
    } catch (err) {
      this.avatarError.set(apiErrorMessage(err, 'Could not upload that photo.'));
    } finally {
      this.avatarSaving.set(false);
      input.value = '';
    }
  }

  /** Keep both the page and the app-wide auth user (header) in sync. */
  private applyUser(updated: ProfileUser): void {
    this.user.set(updated);
    this.auth.user.set(updated as User);
  }

  protected async loadMore(): Promise<void> {
    const page = this.nextPage();
    if (page === null || this.historyLoading()) return;
    this.historyLoading.set(true);
    this.historyError.set(null);
    try {
      const result = await this.api.history(page);
      this.events.update((all) => [...all, ...result.results]);
      this.nextPage.set(result.next ? page + 1 : null);
    } catch (err) {
      this.historyError.set(apiErrorMessage(err, 'Could not load your points history.'));
    } finally {
      this.historyLoading.set(false);
    }
  }
}

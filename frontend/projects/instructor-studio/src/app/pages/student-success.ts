import { Component, inject, signal } from '@angular/core';

import { staggerDelay } from '../core/animations';
import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { RiskTicket, RiskTicketStatus } from '../core/models';

type StatusFilter = RiskTicketStatus | 'all';

/**
 * Dropout-risk remediation queue: triage at-risk students, log outreach
 * notes, and trigger fresh engagement scans.
 */
@Component({
  selector: 'st-student-success',
  template: `
    <header class="head hero-panel sheet-in">
      <span class="hero-panel__sticker" aria-hidden="true">🎯</span>
      <div>
        <p class="tag">Student success</p>
        <h1>Dropout-risk queue</h1>
      </div>
      <div class="head__actions">
        <button class="btn btn--line" (click)="refresh()" [disabled]="loading()">Refresh</button>
        <button class="btn" (click)="runScan()" [disabled]="scanning()">
          {{ scanning() ? 'Queueing…' : 'Run scan now' }}
        </button>
      </div>
    </header>

    @if (scanNotice()) {
      <p class="notice" role="status">
        Scan queued — refresh in a minute to pick up new tickets.
      </p>
    }

    @if (error(); as message) {
      <p class="error-note" role="alert" style="margin-bottom: 1rem">{{ message }}</p>
    }

    <nav class="tabs" role="tablist" aria-label="Filter tickets by status">
      @for (f of filters; track f) {
        <button
          type="button"
          role="tab"
          [attr.aria-selected]="filter() === f"
          [class.is-active]="filter() === f"
          (click)="setFilter(f)"
        >
          {{ f }}
        </button>
      }
    </nav>

    @if (loading()) {
      <p class="tag" style="padding: 1.2rem 0 0" role="status">Checking the attendance ledgers…</p>
      <div class="list" style="margin-top: 1.2rem" aria-hidden="true">
        @for (s of [0, 1, 2]; track s) {
          <div class="panel ticket">
            <div class="skeleton skeleton--title"></div>
            <div class="skeleton skeleton--line"></div>
            <div class="skeleton skeleton--line skeleton--short"></div>
          </div>
        }
      </div>
    } @else if (tickets().length === 0) {
      <div class="panel empty sheet-in">
        <h2>All clear on this shelf.</h2>
        <p>
          {{
            filter() === 'open'
              ? 'No open at-risk tickets — your students are keeping pace. Run a scan to double-check.'
              : 'No tickets match this filter.'
          }}
        </p>
      </div>
    } @else {
      <div class="list">
        @for (ticket of tickets(); track ticket.id; let i = $index) {
          <article
            class="panel ticket sheet-in"
            [class.is-high]="ticket.risk === 'high'"
            [class.just-saved]="savedId() === ticket.id"
            [style.animation-delay.ms]="stagger(i)"
          >
            <header class="ticket__head">
              <div class="ticket__who">
                <strong>{{ ticket.student_name || ticket.student_email }}</strong>
                <span class="tag">{{ ticket.student_email }}</span>
              </div>
              <span class="risk" [class.risk--high]="ticket.risk === 'high'">
                {{ ticket.risk }} risk · {{ probabilityPct(ticket) }}%
              </span>
            </header>

            <p class="ticket__features tag">{{ featureSnapshot(ticket) }}</p>

            <div class="ticket__controls">
              <label class="field">
                <span class="tag">Status</span>
                <select
                  [value]="ticket.status"
                  (change)="setStatus(ticket, $any($event.target).value)"
                  [disabled]="savingId() === ticket.id"
                >
                  <option value="open">open</option>
                  <option value="contacted">contacted</option>
                  <option value="resolved">resolved</option>
                </select>
              </label>
              <label class="field ticket__note">
                <span class="tag">Outreach note — saved on blur</span>
                <textarea
                  [value]="noteDraft(ticket)"
                  (input)="setNoteDraft(ticket.id, $any($event.target).value)"
                  (blur)="saveNote(ticket)"
                  [disabled]="savingId() === ticket.id"
                  placeholder="e.g. Emailed on Tuesday, offered a catch-up session…"
                ></textarea>
              </label>
            </div>

            <footer class="ticket__foot tag">
              <span>Opened {{ ticket.created_at.slice(0, 10) }}</span>
              @if (savingId() === ticket.id) {
                <span>Saving…</span>
              } @else if (savedId() === ticket.id) {
                <span class="ticket__saved" role="status"><span class="ticket__tick" aria-hidden="true">✓</span> Saved</span>
              }
            </footer>
          </article>
        }
      </div>
    }
  `,
  styles: `
    .head {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1.4rem;
      flex-wrap: wrap;

      h1 { font-size: clamp(1.9rem, 4vw, 2.8rem); margin-top: 0.5rem; }
    }

    .head__actions {
      display: flex;
      gap: 0.7rem;
    }

    .notice {
      margin-top: 1rem;
      padding: 0.6rem 0.85rem;
      border-left: 3px solid var(--teal);
      background: rgba(14, 125, 104, 0.08);
      color: var(--teal);
      font-size: 0.86rem;
      border-radius: 0 5px 5px 0;
    }

    .tabs {
      display: flex;
      gap: 0.3rem;
      margin: 1.6rem 0 1.1rem;
      border-bottom: 1px solid var(--line);

      button {
        padding: 0.55rem 1.1rem;
        background: none;
        border: 0;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
        color: var(--ink-dim);
        font-family: var(--font-mono);
        font-size: 0.78rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        cursor: pointer;
        transition: color 160ms ease, border-bottom-color 160ms ease, background 160ms ease;

        &:hover {
          color: var(--ink);
          background: rgba(31, 28, 22, 0.04);
        }

        &.is-active {
          color: var(--amber);
          border-bottom-color: var(--amber);
        }
      }
    }

    .empty {
      h2 { font-size: 1.3rem; margin-bottom: 0.4rem; }
      p { color: var(--ink-dim); }
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .ticket {
      border-left: 3px solid var(--amber);

      &.is-high { border-left-color: var(--red); }
    }

    .ticket__head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .ticket__who {
      display: flex;
      align-items: baseline;
      gap: 0.7rem;
      flex-wrap: wrap;

      strong { font-size: 1.05rem; }
    }

    .risk {
      font-family: var(--font-mono);
      font-size: 0.7rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--amber);
      border: 1px solid var(--amber);
      border-radius: 99px;
      padding: 0.15rem 0.7rem;

      &.risk--high {
        color: var(--red);
        border-color: var(--red);
        background: rgba(178, 58, 44, 0.07);
      }
    }

    .ticket__features {
      margin: 0.7rem 0 1rem;
      letter-spacing: 0.08em;
    }

    .ticket__controls {
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 1rem;
      align-items: start;
    }

    .ticket__note textarea { min-height: 64px; }

    .ticket__foot {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-top: 0.8rem;
      padding-top: 0.7rem;
      border-top: 1px dashed var(--line);
    }

    .ticket__saved {
      color: var(--teal);
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }

    .ticket__tick {
      display: inline-block;
      animation: tick-pop 300ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    /* Success pulse when a PATCH lands; sheet-in is kept in the list so it
       does not replay when the class is later removed. */
    .ticket.just-saved {
      animation:
        sheet-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both,
        saved-pulse 600ms ease;
    }

    @keyframes saved-pulse {
      0% { box-shadow: 0 0 0 0 rgba(14, 125, 104, 0.35); }
      100% { box-shadow: 0 0 0 14px rgba(14, 125, 104, 0); }
    }

    @keyframes tick-pop {
      from { opacity: 0; transform: scale(0.4); }
      60% { transform: scale(1.25); }
      to { opacity: 1; transform: scale(1); }
    }

    @media (max-width: 700px) {
      .ticket__controls { grid-template-columns: 1fr; }
    }
  `,
})
export class StudentSuccessPage {
  private readonly api = inject(StudioApi);

  protected readonly filters: StatusFilter[] = ['open', 'contacted', 'resolved', 'all'];
  protected readonly filter = signal<StatusFilter>('open');

  protected readonly tickets = signal<RiskTicket[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly scanning = signal(false);
  protected readonly scanNotice = signal(false);

  protected readonly savingId = signal<number | null>(null);
  protected readonly savedId = signal<number | null>(null);
  private readonly noteDrafts = signal<Record<number, string>>({});

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const filter = this.filter();
      const page = await this.api.riskTickets(filter === 'all' ? undefined : filter);
      this.tickets.set(page.results);
      this.noteDrafts.set({});
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load the risk queue.'));
    } finally {
      this.loading.set(false);
    }
  }

  /** Entrance-stagger delay (ms) for the nth ticket, capped at ~10. */
  protected stagger(index: number): number {
    return staggerDelay(index, 40);
  }

  protected setFilter(filter: StatusFilter): void {
    if (this.filter() === filter) return;
    this.filter.set(filter);
    void this.load();
  }

  protected refresh(): void {
    this.scanNotice.set(false);
    void this.load();
  }

  protected async runScan(): Promise<void> {
    if (this.scanning()) return;
    this.scanning.set(true);
    this.error.set(null);
    try {
      await this.api.triggerRiskScan();
      this.scanNotice.set(true);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not queue the scan.'));
    } finally {
      this.scanning.set(false);
    }
  }

  /** Probability rendered as a percentage whether the API sends 0–1 or 0–100. */
  protected probabilityPct(ticket: RiskTicket): number {
    const p = ticket.probability;
    return Math.round(p <= 1 ? p * 100 : p);
  }

  protected featureSnapshot(ticket: RiskTicket): string {
    const f = ticket.features;
    return [
      `Last login ${f.days_since_last_login}d ago`,
      `${Math.round(f.progress_pct)}% progress`,
      `quiz avg ${Math.round(f.quiz_avg)}%`,
      `${f.lessons_per_week} lessons/wk`,
      `${f.chat_messages} chat msgs`,
    ].join(' · ');
  }

  protected noteDraft(ticket: RiskTicket): string {
    return this.noteDrafts()[ticket.id] ?? ticket.note ?? '';
  }

  protected setNoteDraft(ticketId: number, value: string): void {
    this.noteDrafts.update((drafts) => ({ ...drafts, [ticketId]: value }));
  }

  protected saveNote(ticket: RiskTicket): void {
    const draft = this.noteDrafts()[ticket.id];
    if (draft === undefined || draft === (ticket.note ?? '')) return;
    void this.patch(ticket, { note: draft });
  }

  protected setStatus(ticket: RiskTicket, status: string): void {
    if (status === ticket.status) return;
    void this.patch(ticket, { status: status as RiskTicketStatus });
  }

  private async patch(
    ticket: RiskTicket,
    data: Partial<Pick<RiskTicket, 'status' | 'note'>>,
  ): Promise<void> {
    this.savingId.set(ticket.id);
    this.savedId.set(null);
    this.error.set(null);
    try {
      const updated = await this.api.updateRiskTicket(ticket.id, data);
      this.tickets.update((all) => all.map((t) => (t.id === updated.id ? updated : t)));
      if (data.note !== undefined) {
        this.noteDrafts.update((drafts) => {
          const { [ticket.id]: _, ...rest } = drafts;
          return rest;
        });
      }
      this.savedId.set(ticket.id);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not update the ticket.'));
    } finally {
      this.savingId.set(null);
    }
  }
}

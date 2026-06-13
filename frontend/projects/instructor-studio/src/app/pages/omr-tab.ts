import { Component, computed, inject, signal } from '@angular/core';

import { StudioApi, OmrGradeResult } from '../core/api';
import { saveBlob } from '../core/download';
import { apiErrorMessage } from '../core/errors';
import { SiteConfig } from '../core/site-config';

/** One uploaded bubble sheet moving through the grading queue. */
interface SheetEntry {
  id: number;
  file: File;
  label: string;
  preview: string;
  status: 'pending' | 'grading' | 'done' | 'error';
  error?: string;
  result?: OmrGradeResult;
  /** Instructor corrections: question index -> answer index (or null = blank). */
  overrides: Record<number, number | null>;
}

/** Top-two fill ratios closer than this = flag the row for review. */
const AMBIGUOUS_GAP = 0.04;

/**
 * OMR grading workbench. Build the answer key by tapping letters, drop in a
 * batch of sheet photos, and review each sheet's detected bubbles against
 * the actual fill ratios — overriding any misread before exporting marks.
 * Layout must be a uniform grid: one question per row, N bubbles per row.
 */
@Component({
  selector: 'st-omr-tab',
  template: `
    @if (!config.flagEnabled('omr_grading')) {
      <p class="tag" style="padding: 1.2rem 0">OMR grading is turned off for this deployment.</p>
    } @else {
      <p class="tag omr__intro">
        Photograph grid-layout answer sheets — one row per question, bubbles left to right.
        Tap out the answer key, add the photos, then review anything flagged before exporting.
      </p>

      <div class="omr__layout">
        <!-- ① Answer key ------------------------------------------------ -->
        <section class="panel omr__panel">
          <p class="tag">① Answer key</p>
          <div class="omr__dims">
            <label class="field field--inline">
              <span class="tag">Questions</span>
              <input
                type="number"
                min="1"
                max="100"
                [value]="key().length"
                (change)="resizeKey(+$any($event.target).value)"
              />
            </label>
            <label class="field field--inline">
              <span class="tag">Options</span>
              <input
                type="number"
                min="2"
                max="8"
                [value]="numOptions()"
                (change)="setNumOptions(+$any($event.target).value)"
              />
            </label>
          </div>

          <div class="key-grid">
            @for (answer of key(); track $index; let q = $index) {
              <div class="key-grid__row">
                <span class="key-grid__q tag">{{ q + 1 }}</span>
                @for (letter of letters(); track $index; let opt = $index) {
                  <button
                    type="button"
                    class="bubble"
                    [class.is-key]="answer === opt"
                    (click)="setKey(q, opt)"
                    [attr.aria-label]="'Question ' + (q + 1) + ' answer ' + letter"
                    [attr.aria-pressed]="answer === opt"
                  >
                    {{ letter }}
                  </button>
                }
              </div>
            }
          </div>
          @if (!keyComplete()) {
            <p class="tag omr__hint">Pick an answer for every question to enable grading.</p>
          }
        </section>

        <!-- ② Sheets ----------------------------------------------------- -->
        <section class="panel omr__panel">
          <p class="tag">② Sheets</p>
          <label class="field">
            <span class="tag">Add sheet photos (one per student)</span>
            <input type="file" accept="image/*" multiple (change)="onFiles($event)" />
          </label>

          @if (sheets().length > 0) {
            <ul class="sheet-list">
              @for (sheet of sheets(); track sheet.id) {
                <li
                  class="sheet-list__row"
                  [class.is-selected]="selectedId() === sheet.id"
                  (click)="selectedId.set(sheet.id)"
                  (keydown.enter)="selectedId.set(sheet.id)"
                  tabindex="0"
                >
                  <img class="sheet-list__thumb" [src]="sheet.preview" alt="" />
                  <input
                    class="sheet-list__label"
                    [value]="sheet.label"
                    (input)="relabel(sheet.id, $any($event.target).value)"
                    (click)="$event.stopPropagation()"
                    aria-label="Student or sheet label"
                  />
                  <span class="sheet-list__status tag" [class.is-error]="sheet.status === 'error'">
                    @switch (sheet.status) {
                      @case ('pending') { queued }
                      @case ('grading') { grading… }
                      @case ('error') { failed }
                      @case ('done') { {{ scoreOf(sheet).correct }}/{{ key().length }} }
                    }
                  </span>
                  <button
                    type="button"
                    class="sheet-list__remove"
                    (click)="remove(sheet.id); $event.stopPropagation()"
                    aria-label="Remove sheet"
                  >
                    ✕
                  </button>
                </li>
              }
            </ul>

            <div class="omr__actions">
              <button class="btn" type="button" [disabled]="!canGrade()" (click)="gradeAll()">
                {{ busy() ? 'Grading…' : 'Grade ' + pendingCount() + ' sheet(s)' }}
              </button>
              @if (gradedCount() > 0) {
                <button class="btn btn--line" type="button" (click)="exportCsv()">
                  Export CSV
                </button>
              }
            </div>
            @if (gradedCount() > 1) {
              <p class="tag omr__hint">
                Class mean: {{ meanScore() }}% across {{ gradedCount() }} graded sheet(s)
              </p>
            }
          }
        </section>
      </div>

      <!-- ③ Review ------------------------------------------------------- -->
      @if (selected(); as sheet) {
        <section class="panel result sheet-in">
          <p class="tag">③ Review — {{ sheet.label }}</p>

          @if (sheet.status === 'error') {
            <p class="error-note" role="alert">{{ sheet.error }}</p>
          } @else if (sheet.status !== 'done') {
            <p class="tag omr__hint">Not graded yet.</p>
          } @else if (sheet.result; as r) {
            <p class="result__score">
              <strong>{{ scoreOf(sheet).correct }}</strong> / {{ key().length }} correct
              <span class="tag">({{ scoreOf(sheet).percent }}%)</span>
              @if (hasOverrides(sheet)) {
                <button class="btn btn--line btn--sm" type="button" (click)="clearOverrides(sheet.id)">
                  Reset {{ overrideCount(sheet) }} override(s)
                </button>
              }
            </p>
            <p class="tag omr__hint">
              Bubble shading shows measured fill. Tap a bubble to override a misread;
              ⚠ rows have two near-equal bubbles, − rows read blank.
            </p>

            <div class="review-grid">
              @for (row of reviewRows(sheet); track row.q) {
                <div class="review-grid__row" [class.is-wrong]="!row.ok">
                  <span class="key-grid__q tag">{{ row.q + 1 }}</span>
                  @for (fill of row.fills; track $index; let opt = $index) {
                    <button
                      type="button"
                      class="bubble bubble--review"
                      [class.is-detected]="row.effective === opt"
                      [class.is-key]="row.expected === opt"
                      [style.--fill]="fill"
                      (click)="override(sheet.id, row.q, opt)"
                      [attr.aria-label]="
                        'Q' + (row.q + 1) + ' ' + letters()[opt] + ' — fill ' + (fill * 100).toFixed(0) + '%'
                      "
                    >
                      {{ letters()[opt] }}
                    </button>
                  }
                  <span class="review-grid__verdict">
                    {{ row.ok ? '✓' : '✗' }}
                    @if (row.flag === 'ambiguous') { <span title="two near-equal bubbles">⚠</span> }
                    @if (row.flag === 'blank') { <span title="no bubble above threshold">−</span> }
                    @if (row.overridden) { <span class="tag">edited</span> }
                  </span>
                </div>
              }
            </div>
          }
        </section>
      }
    }
  `,
  styles: `
    .omr__intro {
      max-width: 62ch;
      line-height: 1.55;
      margin-bottom: 1.2rem;
    }

    .omr__layout {
      display: grid;
      grid-template-columns: minmax(260px, 380px) minmax(280px, 1fr);
      gap: 1.2rem;
      align-items: start;

      @media (max-width: 760px) {
        grid-template-columns: 1fr;
      }
    }

    .omr__panel {
      padding: 1.2rem;
    }

    .omr__dims {
      display: flex;
      gap: 1rem;
      margin: 0.8rem 0 1rem;
    }

    .field--inline input {
      width: 5.5rem;
    }

    .omr__hint {
      margin-top: 0.8rem;
      text-transform: none;
      letter-spacing: 0.02em;
    }

    .key-grid,
    .review-grid {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      max-height: 420px;
      overflow-y: auto;
    }

    .key-grid__row,
    .review-grid__row {
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }

    .key-grid__q {
      width: 2rem;
      text-align: right;
      flex-shrink: 0;
    }

    .bubble {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.9rem;
      height: 1.9rem;
      padding: 0;
      border: 1.5px solid var(--line-strong);
      border-radius: 50%;
      background: var(--panel);
      color: var(--ink-dim);
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      cursor: pointer;
      flex-shrink: 0;

      &:hover {
        border-color: var(--accent);
      }

      &.is-key {
        border-color: var(--accent-2);
        background: color-mix(in srgb, var(--accent-2) 18%, var(--panel));
        color: var(--ink);
      }
    }

    .bubble--review {
      /* measured fill ratio shades the bubble — detection evidence */
      background: color-mix(in srgb, var(--ink) calc(var(--fill, 0) * 100%), var(--panel));

      &.is-detected {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 30%, transparent);
        color: var(--accent-deep);
      }

      &.is-key:not(.is-detected) {
        border-style: dashed;
      }
    }

    .sheet-list {
      list-style: none;
      margin: 0.9rem 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      max-height: 300px;
      overflow-y: auto;
    }

    .sheet-list__row {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.4rem 0.55rem;
      border: 1.5px solid var(--line);
      border-radius: 10px;
      cursor: pointer;

      &.is-selected {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 6%, var(--panel));
      }
    }

    .sheet-list__thumb {
      width: 38px;
      height: 38px;
      object-fit: cover;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #fff;
      flex-shrink: 0;
    }

    .sheet-list__label {
      flex: 1;
      min-width: 0;
      border: none;
      border-bottom: 1px dashed transparent;
      background: transparent;
      color: var(--ink);
      font-family: var(--font-body);
      font-size: 0.86rem;

      &:hover,
      &:focus {
        outline: none;
        border-bottom-color: var(--accent);
      }
    }

    .sheet-list__status {
      flex-shrink: 0;

      &.is-error {
        color: var(--red);
      }
    }

    .sheet-list__remove {
      border: none;
      background: transparent;
      color: var(--ink-dim);
      cursor: pointer;
      font-size: 0.8rem;
      padding: 0.2rem;

      &:hover {
        color: var(--red);
      }
    }

    .omr__actions {
      display: flex;
      gap: 0.7rem;
      margin-top: 1rem;
    }

    .result {
      margin-top: 1.6rem;
      padding: 1.2rem;
    }

    .result__score {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      font-size: 1.3rem;
      margin: 0.6rem 0 0.4rem;
    }

    .review-grid__row.is-wrong .review-grid__verdict {
      color: var(--red);
    }

    .review-grid__verdict {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      margin-left: 0.4rem;
      font-size: 0.85rem;
    }
  `,
})
export class OmrTab {
  private readonly api = inject(StudioApi);
  protected readonly config = inject(SiteConfig);

  protected readonly numOptions = signal(4);
  protected readonly key = signal<Array<number | null>>(Array.from({ length: 10 }, () => null));
  protected readonly sheets = signal<SheetEntry[]>([]);
  protected readonly selectedId = signal<number | null>(null);
  protected readonly busy = signal(false);
  private nextId = 1;

  protected readonly letters = computed(() =>
    Array.from({ length: this.numOptions() }, (_, i) => String.fromCharCode(65 + i)),
  );
  protected readonly keyComplete = computed(() => this.key().every((a) => a !== null));
  protected readonly pendingCount = computed(
    () => this.sheets().filter((s) => s.status === 'pending' || s.status === 'error').length,
  );
  protected readonly gradedCount = computed(
    () => this.sheets().filter((s) => s.status === 'done').length,
  );
  protected readonly canGrade = computed(
    () => this.keyComplete() && this.pendingCount() > 0 && !this.busy(),
  );
  protected readonly selected = computed(
    () => this.sheets().find((s) => s.id === this.selectedId()) ?? null,
  );

  // ---- answer key -----------------------------------------------------

  protected setKey(question: number, option: number): void {
    this.key.update((key) =>
      key.map((a, i) => (i === question ? (a === option ? null : option) : a)),
    );
  }

  protected resizeKey(length: number): void {
    if (!Number.isFinite(length) || length < 1 || length > 100) return;
    this.key.update((key) =>
      Array.from({ length }, (_, i) => key[i] ?? null),
    );
    this.invalidateResults();
  }

  protected setNumOptions(count: number): void {
    if (!Number.isFinite(count) || count < 2 || count > 8) return;
    this.numOptions.set(count);
    // Answers beyond the new option count are no longer valid.
    this.key.update((key) => key.map((a) => (a !== null && a >= count ? null : a)));
    this.invalidateResults();
  }

  /** Key or layout changed — graded results no longer apply. */
  private invalidateResults(): void {
    this.sheets.update((sheets) =>
      sheets.map((s) =>
        s.status === 'done' || s.status === 'error'
          ? { ...s, status: 'pending' as const, result: undefined, error: undefined, overrides: {} }
          : s,
      ),
    );
  }

  // ---- sheet queue ------------------------------------------------------

  protected onFiles(event: Event): void {
    const input = event.target as HTMLInputElement;
    const picked = Array.from(input.files ?? []);
    if (picked.length === 0) return;
    const added = picked.map((file): SheetEntry => ({
      id: this.nextId++,
      file,
      label: file.name.replace(/\.[^.]+$/, ''),
      preview: URL.createObjectURL(file),
      status: 'pending',
      overrides: {},
    }));
    this.sheets.update((sheets) => [...sheets, ...added]);
    if (this.selectedId() === null) this.selectedId.set(added[0].id);
    input.value = '';
  }

  protected relabel(id: number, label: string): void {
    this.sheets.update((sheets) => sheets.map((s) => (s.id === id ? { ...s, label } : s)));
  }

  protected remove(id: number): void {
    const sheet = this.sheets().find((s) => s.id === id);
    if (sheet) URL.revokeObjectURL(sheet.preview);
    this.sheets.update((sheets) => sheets.filter((s) => s.id !== id));
    if (this.selectedId() === id) this.selectedId.set(this.sheets()[0]?.id ?? null);
  }

  protected async gradeAll(): Promise<void> {
    if (!this.canGrade()) return;
    this.busy.set(true);
    const keyJson = JSON.stringify(this.key());
    try {
      for (const sheet of this.sheets()) {
        if (sheet.status === 'done' || sheet.status === 'grading') continue;
        this.patch(sheet.id, { status: 'grading', error: undefined });
        try {
          const result = await this.api.gradeOmr(sheet.file, keyJson, this.numOptions());
          this.patch(sheet.id, { status: 'done', result, overrides: {} });
        } catch (err) {
          this.patch(sheet.id, {
            status: 'error',
            error: apiErrorMessage(err, 'Could not grade this sheet.'),
          });
        }
      }
    } finally {
      this.busy.set(false);
    }
  }

  private patch(id: number, changes: Partial<SheetEntry>): void {
    this.sheets.update((sheets) =>
      sheets.map((s) => (s.id === id ? { ...s, ...changes } : s)),
    );
  }

  // ---- review + overrides ----------------------------------------------

  /** Effective answer for a question — instructor override wins. */
  private effectiveAnswer(sheet: SheetEntry, question: number): number | null {
    if (question in sheet.overrides) return sheet.overrides[question];
    return sheet.result?.detected_answers[question] ?? null;
  }

  protected override(id: number, question: number, option: number): void {
    this.sheets.update((sheets) =>
      sheets.map((s) => {
        if (s.id !== id || !s.result) return s;
        const detected = s.result.detected_answers[question] ?? null;
        const current = question in s.overrides ? s.overrides[question] : detected;
        const next = current === option ? null : option;
        const overrides = { ...s.overrides };
        if (next === detected) {
          delete overrides[question]; // back to what the machine read
        } else {
          overrides[question] = next;
        }
        return { ...s, overrides };
      }),
    );
  }

  protected clearOverrides(id: number): void {
    this.patch(id, { overrides: {} });
  }

  protected hasOverrides(sheet: SheetEntry): boolean {
    return Object.keys(sheet.overrides).length > 0;
  }

  protected overrideCount(sheet: SheetEntry): number {
    return Object.keys(sheet.overrides).length;
  }

  protected scoreOf(sheet: SheetEntry): { correct: number; percent: string } {
    const key = this.key();
    const correct = key.reduce<number>(
      (sum, expected, q) => sum + (this.effectiveAnswer(sheet, q) === expected ? 1 : 0),
      0,
    );
    return {
      correct,
      percent: key.length ? ((correct / key.length) * 100).toFixed(1) : '0.0',
    };
  }

  protected reviewRows(sheet: SheetEntry): Array<{
    q: number;
    fills: number[];
    effective: number | null;
    expected: number | null;
    ok: boolean;
    flag: 'ambiguous' | 'blank' | null;
    overridden: boolean;
  }> {
    const result = sheet.result;
    if (!result) return [];
    return this.key().map((expected, q) => {
      const fills = result.fill_grid[q] ?? [];
      const effective = this.effectiveAnswer(sheet, q);
      const sorted = [...fills].sort((a, b) => b - a);
      let flag: 'ambiguous' | 'blank' | null = null;
      if (result.detected_answers[q] === null) flag = 'blank';
      else if (sorted.length > 1 && sorted[0] - sorted[1] < AMBIGUOUS_GAP) flag = 'ambiguous';
      return {
        q,
        fills,
        effective,
        expected,
        ok: effective === expected,
        flag,
        overridden: q in sheet.overrides,
      };
    });
  }

  // ---- export -------------------------------------------------------------

  protected meanScore(): string {
    const graded = this.sheets().filter((s) => s.status === 'done');
    if (graded.length === 0) return '0.0';
    const total = graded.reduce((sum, s) => sum + Number(this.scoreOf(s).percent), 0);
    return (total / graded.length).toFixed(1);
  }

  protected exportCsv(): void {
    const letters = this.letters();
    const header = [
      'sheet',
      'correct',
      'total',
      'percent',
      ...this.key().map((_, q) => `q${q + 1}`),
    ];
    const lines = [header.join(',')];
    for (const sheet of this.sheets()) {
      if (sheet.status !== 'done') continue;
      const score = this.scoreOf(sheet);
      const answers = this.key().map((_, q) => {
        const a = this.effectiveAnswer(sheet, q);
        return a === null ? 'blank' : letters[a] ?? String(a);
      });
      const label = '"' + sheet.label.replaceAll('"', '""') + '"';
      lines.push([label, score.correct, this.key().length, score.percent, ...answers].join(','));
    }
    saveBlob(lines.join('\n') + '\n', 'omr-grades.csv');
  }
}

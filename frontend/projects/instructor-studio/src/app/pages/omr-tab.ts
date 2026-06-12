import { Component, inject, signal } from '@angular/core';

import { StudioApi, OmrGradeResult } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { SiteConfig } from '../core/site-config';

/**
 * Upload a bubble-sheet photo and grade it against a JSON answer key.
 * Layout must be a uniform grid: one question per row, N bubbles per row.
 */
@Component({
  selector: 'st-omr-tab',
  template: `
    @if (!config.flagEnabled('omr_grading')) {
      <p class="tag" style="padding: 1.2rem 0">OMR grading is turned off for this deployment.</p>
    } @else {
      <p class="tag omr__intro">
        Photograph a grid-layout answer sheet — one row per question, bubbles left to right.
        Provide the correct answers as a JSON array of <strong>0-based</strong> indices
        (e.g. <code>[1,0,3,2]</code> for four options A–D).
      </p>

      <form class="omr__form" (submit)="grade($event)">
        <label class="field">
          <span class="tag">Answer key (JSON array)</span>
          <textarea
            rows="3"
            [value]="answerKey()"
            (input)="answerKey.set($any($event.target).value)"
            placeholder='[1, 0, 3, 2, 1]'
            spellcheck="false"
          ></textarea>
        </label>

        <label class="field">
          <span class="tag">Options per question</span>
          <input
            type="number"
            min="2"
            max="10"
            [value]="numOptions()"
            (input)="numOptions.set(+$any($event.target).value)"
          />
        </label>

        <label class="field">
          <span class="tag">Sheet photo</span>
          <input type="file" accept="image/*" (change)="onFile($event)" />
        </label>

        @if (preview(); as src) {
          <img class="omr__preview" [src]="src" alt="Answer sheet preview" />
        }

        @if (error(); as message) {
          <p class="error-note" role="alert">{{ message }}</p>
        }

        <button class="btn btn--line" type="submit" [disabled]="busy() || !file()">
          {{ busy() ? 'Grading…' : 'Grade sheet' }}
        </button>
      </form>

      @if (result(); as r) {
        <section class="panel result sheet-in">
          <p class="tag">Result</p>
          <p class="result__score">
            <strong>{{ r.correct }}</strong> / {{ r.total_questions }} correct
            <span class="tag">({{ r.score }}%)</span>
          </p>
          <table class="result__table">
            <thead>
              <tr>
                <th class="tag">Q</th>
                <th class="tag">Detected</th>
                <th class="tag">Key</th>
                <th class="tag">OK</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(r); track row.q) {
                <tr [class.is-wrong]="!row.ok">
                  <td>{{ row.q }}</td>
                  <td>{{ row.detected }}</td>
                  <td>{{ row.expected }}</td>
                  <td>{{ row.ok ? '✓' : '✗' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      }
    }
  `,
  styles: `
    .omr__intro {
      max-width: 58ch;
      line-height: 1.55;
      margin-bottom: 1.2rem;

      code {
        font-family: var(--font-mono);
        font-size: 0.85em;
      }
    }

    .omr__form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      max-width: 420px;
    }

    .omr__preview {
      max-width: 100%;
      max-height: 280px;
      object-fit: contain;
      border: 1.5px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .result {
      margin-top: 1.6rem;
      padding: 1.2rem;
    }

    .result__score {
      font-size: 1.3rem;
      margin: 0.6rem 0 1rem;
    }

    .result__table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;

      th, td {
        padding: 0.45rem 0.6rem;
        border-bottom: 1px solid var(--line);
        text-align: left;
      }

      tr.is-wrong td {
        color: var(--danger, #b23a2c);
      }
    }
  `,
})
export class OmrTab {
  private readonly api = inject(StudioApi);
  protected readonly config = inject(SiteConfig);

  protected readonly answerKey = signal('[1, 0, 2, 1]');
  protected readonly numOptions = signal(4);
  protected readonly file = signal<File | null>(null);
  protected readonly preview = signal<string | null>(null);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly result = signal<OmrGradeResult | null>(null);
  private lastKey: number[] = [];

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const picked = input.files?.[0] ?? null;
    this.file.set(picked);
    this.result.set(null);
    this.error.set(null);
    if (this.preview()) URL.revokeObjectURL(this.preview()!);
    this.preview.set(picked ? URL.createObjectURL(picked) : null);
  }

  protected async grade(event: Event): Promise<void> {
    event.preventDefault();
    const image = this.file();
    if (!image) return;
    this.busy.set(true);
    this.error.set(null);
    this.result.set(null);
    try {
      const key = JSON.parse(this.answerKey().trim()) as number[];
      if (!Array.isArray(key) || key.length === 0) {
        throw new Error('Answer key must be a non-empty JSON array.');
      }
      this.lastKey = key;
      const graded = await this.api.gradeOmr(image, this.answerKey().trim(), this.numOptions());
      this.result.set(graded);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not grade the sheet.'));
    } finally {
      this.busy.set(false);
    }
  }

  protected rows(r: OmrGradeResult): Array<{
    q: number;
    detected: string;
    expected: number;
    ok: boolean;
  }> {
    return r.detected_answers.map((got, index) => ({
      q: index + 1,
      detected: got === null ? 'blank' : String(got),
      expected: this.lastKey[index] ?? 0,
      ok: got === this.lastKey[index],
    }));
  }
}

import { Component, computed, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { renderMarkdown } from '../core/markdown';
import {
  PaperQuestion,
  PaperSubject,
  PastPapersApi,
  subjectName,
} from '../core/pastpapers';

@Component({
  selector: 'mm-past-papers',
  template: `
    <section class="page-head rise hero-panel">
      <span class="hero-panel__sticker" aria-hidden="true">📄</span>
      <p class="mono-label">Real Cambridge questions · official mark schemes</p>
      <h1>Past-paper practice</h1>
    </section>

    @if (error(); as message) {
      <p class="error-note" role="alert">{{ message }}</p>
    }

    @if (!subject()) {
      @if (loading()) {
        <div class="skeleton" style="height: 120px; border-radius: 12px;"></div>
      } @else {
        <div class="subjects">
          @for (s of subjects(); track s.subject_code) {
            <button type="button" class="subject card rise" (click)="pick(s.subject_code)">
              <strong>{{ name(s.subject_code) }}</strong>
              <span class="mono-label">{{ s.subject_code }} · {{ s.questions }} questions</span>
            </button>
          }
        </div>
      }
    } @else {
      <div class="bar">
        <button type="button" class="btn btn--ghost" (click)="reset()">← Subjects</button>
        <span class="mono-label">{{ name(subject()!) }} · question {{ page() }} of {{ count() }}</span>
        <span class="bar__nav">
          <button type="button" class="btn btn--ghost" [disabled]="page() <= 1 || loading()" (click)="go(-1)">Prev</button>
          <button type="button" class="btn btn--accent" [disabled]="page() >= count() || loading()" (click)="go(1)">Next</button>
        </span>
      </div>

      @if (question(); as q) {
        <article class="card paper rise">
          <p class="mono-label">Cambridge {{ q.subject_code }} · {{ q.year }} {{ q.session }} · Paper {{ q.variant }} · Q{{ q.question_number }}</p>
          <div class="paper__body" [innerHTML]="rendered(q.question_markdown)"></div>
          @if (scheme(); as ms) {
            <div class="scheme">
              <p class="mono-label">Official mark scheme</p>
              <div [innerHTML]="rendered(ms)"></div>
            </div>
          } @else {
            <button type="button" class="btn btn--accent" [disabled]="revealing()" (click)="revealScheme()">
              {{ revealing() ? 'Fetching…' : 'Reveal mark scheme' }}
            </button>
          }
        </article>
      } @else if (loading()) {
        <div class="skeleton" style="height: 220px; border-radius: 12px;"></div>
      }
    }
  `,
  styles: `
    .page-head h1 { font-size: clamp(2rem, 4.5vw, 3rem); margin: 0.4rem 0 1.2rem; }
    .subjects { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
    .subject { display: flex; flex-direction: column; gap: 0.3rem; align-items: flex-start;
      padding: 1.2rem; border: 1.5px solid var(--line-strong); border-radius: 12px;
      background: var(--card); cursor: pointer; text-align: left; font: inherit; color: inherit; }
    .subject strong { font-size: 1.1rem; }
    .bar { display: flex; align-items: center; justify-content: space-between; gap: 0.8rem;
      flex-wrap: wrap; margin-bottom: 1rem; }
    .bar__nav { display: flex; gap: 0.5rem; }
    .paper { padding: 1.4rem; border: 1.5px solid var(--line-strong); border-radius: 12px;
      background: var(--card); }
    .paper__body { margin: 0.8rem 0 1.2rem; line-height: 1.65; }
    .scheme { border-top: 2px dashed var(--line-strong); margin-top: 1rem; padding-top: 1rem; }
    .scheme div { line-height: 1.65; }
  `,
})
export class PastPapersPage {
  private readonly api = inject(PastPapersApi);
  private readonly sanitizer = inject(DomSanitizer);

  protected readonly subjects = signal<PaperSubject[]>([]);
  protected readonly subject = signal<string | null>(null);
  protected readonly question = signal<PaperQuestion | null>(null);
  protected readonly scheme = signal<string | null>(null);
  protected readonly count = signal(0);
  protected readonly page = signal(1);
  protected readonly loading = signal(false);
  protected readonly revealing = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly name = subjectName;

  constructor() {
    void this.loadSubjects();
  }

  private async loadSubjects(): Promise<void> {
    this.loading.set(true);
    try {
      const body = await this.api.subjects();
      this.subjects.set(body.subjects);
      this.error.set(null);
    } catch {
      this.error.set('The past-paper service is waking up — try again in a minute.');
    } finally {
      this.loading.set(false);
    }
  }

  protected pick(code: string): void {
    this.subject.set(code);
    this.page.set(1);
    void this.loadQuestion();
  }

  protected reset(): void {
    this.subject.set(null);
    this.question.set(null);
    this.scheme.set(null);
  }

  protected go(delta: number): void {
    this.page.update((p) => p + delta);
    void this.loadQuestion();
  }

  private async loadQuestion(): Promise<void> {
    const code = this.subject();
    if (!code) return;
    this.loading.set(true);
    this.scheme.set(null);
    this.question.set(null);
    try {
      const body = await this.api.questions(code, this.page());
      this.count.set(body.count);
      this.question.set(body.results[0] ?? null);
      this.error.set(null);
    } catch {
      this.error.set('The past-paper service is waking up — try again in a minute.');
    } finally {
      this.loading.set(false);
    }
  }

  protected async revealScheme(): Promise<void> {
    const q = this.question();
    if (!q) return;
    this.revealing.set(true);
    try {
      const full = await this.api.reveal(q.id);
      this.scheme.set(full.mark_scheme_markdown ?? '');
    } catch {
      this.error.set('Could not fetch the mark scheme — try again.');
    } finally {
      this.revealing.set(false);
    }
  }

  protected rendered(text: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(renderMarkdown(text));
  }
}

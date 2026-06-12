import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { renderMarkdown } from '../core/markdown';
import { Course, Lesson } from '../core/models';

@Component({
  selector: 'mm-lesson',
  imports: [RouterLink],
  template: `
    @if (loading()) {
      <p class="mono-label">Turning to the right page…</p>
    } @else if (!course() || !lesson()) {
      <div class="missing rise">
        <h1>Lesson not found.</h1>
        <a routerLink="/" class="btn btn--ghost">← Back to catalog</a>
      </div>
    } @else if (lesson(); as l) {
      <article class="sheet rise">
        <header class="sheet__head">
          <a [routerLink]="['/courses', course()!.slug]" class="mono-label sheet__crumb">
            ← {{ course()!.title }}
          </a>
          <p class="mono-label">Lesson {{ pad(lessonNumber()) }} of {{ pad(course()!.lessons.length) }}</p>
          <h1>{{ l.title }}</h1>
        </header>

        @if (!enrollment()) {
          <div class="locked">
            <p>This lesson is part of the course notebook — enroll to read it.</p>
            <a class="btn btn--accent" [routerLink]="['/courses', course()!.slug]">Go enroll</a>
          </div>
        } @else {
          <div class="sheet__content" [innerHTML]="renderedContent(l.content)"></div>

          @if (l.video_url) {
            <a class="btn btn--ghost sheet__video" [href]="l.video_url" target="_blank" rel="noopener">
              ▶ Watch the companion video
            </a>
          }

          @if (error(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          }

          <footer class="sheet__footer">
            <div class="sheet__nav">
              @if (prevLesson(); as prev) {
                <a class="btn btn--ghost" [routerLink]="['/courses', course()!.slug, 'lessons', prev.id]">
                  ← {{ prev.title }}
                </a>
              }
              @if (nextLesson(); as next) {
                <a class="btn btn--ghost" [routerLink]="['/courses', course()!.slug, 'lessons', next.id]">
                  {{ next.title }} →
                </a>
              }
            </div>
            @if (isComplete()) {
              <span class="stamp">Completed</span>
            } @else {
              <button class="btn btn--accent" (click)="markComplete()" [disabled]="busy()">
                {{ busy() ? 'Saving…' : 'Mark as complete ✓' }}
              </button>
            }
          </footer>
        }
      </article>
    }
  `,
  styles: `
    .missing {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
      padding: 2rem 0;
    }

    .sheet {
      max-width: 760px;
      margin: 0 auto;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 14px;
      padding: clamp(1.5rem, 4vw, 3rem);
      box-shadow: var(--shadow-card);
    }

    .sheet__crumb {
      text-decoration: none;
      display: inline-block;
      margin-bottom: 1.2rem;
      &:hover { color: var(--accent); }
    }

    .sheet__head h1 {
      font-size: clamp(1.9rem, 4vw, 2.9rem);
      margin-top: 0.5rem;
      padding-bottom: 1.2rem;
      border-bottom: 2px solid var(--line-strong);
    }

    .locked {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
      padding: 2rem 0 0.5rem;
      color: var(--ink-soft);
    }

    .sheet__content {
      padding: 1.6rem 0;
      font-size: 1.05rem;
      line-height: 1.75;

      :global(strong) { font-weight: 700; }
      :global(code) {
        font-family: var(--font-mono);
        font-size: 0.92em;
        background: var(--paper-deep);
        padding: 0.1em 0.35em;
        border-radius: 4px;
      }
      :global(.md-quote) {
        display: block;
        border-left: 3px solid var(--accent);
        padding-left: 0.9rem;
        color: var(--ink-soft);
        margin: 0.5rem 0;
      }
    }

    .sheet__video {
      margin-bottom: 1.5rem;
    }

    .sheet__footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      padding-top: 1.4rem;
      border-top: 1px dashed var(--line-strong);
    }

    .sheet__nav {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;

      .btn { font-size: 0.8rem; padding: 0.45rem 0.95rem; }
    }
  `,
})
export class LessonPage {
  private readonly api = inject(LearningApi);
  private readonly route = inject(ActivatedRoute);

  protected readonly course = signal<Course | null>(null);
  protected readonly lessonId = signal<number | null>(null);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly lesson = computed<Lesson | null>(() => {
    const c = this.course();
    const id = this.lessonId();
    return c?.lessons.find((l) => l.id === id) ?? null;
  });

  protected readonly enrollment = computed(() => {
    const c = this.course();
    return c ? this.api.enrollments().find((e) => e.course === c.id) : undefined;
  });

  protected readonly lessonNumber = computed(() => {
    const c = this.course();
    const l = this.lesson();
    return c && l ? c.lessons.indexOf(l) + 1 : 0;
  });

  protected readonly prevLesson = computed<Lesson | null>(() => {
    const c = this.course();
    const n = this.lessonNumber();
    return c && n > 1 ? c.lessons[n - 2] : null;
  });

  protected readonly nextLesson = computed<Lesson | null>(() => {
    const c = this.course();
    const n = this.lessonNumber();
    return c && n > 0 && n < c.lessons.length ? c.lessons[n] : null;
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      const id = Number(params.get('id'));
      this.lessonId.set(Number.isFinite(id) ? id : null);
      if (slug && this.course()?.slug !== slug) {
        void this.load(slug);
      }
    });
  }

  private async load(slug: string): Promise<void> {
    this.loading.set(true);
    try {
      this.course.set(await this.api.getCourse(slug));
    } catch {
      this.course.set(null);
    } finally {
      this.loading.set(false);
    }
  }

  protected pad(n: number): string {
    return String(n).padStart(2, '0');
  }

  protected renderedContent(content: string): string {
    return renderMarkdown(content);
  }

  protected isComplete(): boolean {
    const id = this.lessonId();
    return id !== null && (this.enrollment()?.completed_lessons.includes(id) ?? false);
  }

  protected async markComplete(): Promise<void> {
    const enrollment = this.enrollment();
    const id = this.lessonId();
    if (!enrollment || id === null) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.api.completeLesson(enrollment.id, id);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not save your progress — try again.'));
    } finally {
      this.busy.set(false);
    }
  }
}

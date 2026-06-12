import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CountUp, staggerDelay } from '../core/animations';
import { StudioApi } from '../core/api';
import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { Course } from '../core/models';

@Component({
  selector: 'st-dashboard',
  imports: [RouterLink, CountUp],
  template: `
    <section class="head sheet-in">
      <p class="tag">Course drawer</p>
      <h1>Your courses</h1>
    </section>

    @if (loading()) {
      <p class="tag" role="status">Pulling blueprints…</p>
      <div class="layout" aria-hidden="true">
        <div class="list">
          @for (s of [0, 1, 2]; track s) {
            <div class="panel">
              <div class="skeleton skeleton--title"></div>
              <div class="skeleton skeleton--line"></div>
              <div class="skeleton skeleton--line skeleton--short"></div>
            </div>
          }
        </div>
        <div class="panel">
          <div class="skeleton skeleton--chip"></div>
          <div class="skeleton skeleton--title" style="margin-top: 0.8rem"></div>
          <div class="skeleton skeleton--line"></div>
          <div class="skeleton skeleton--line skeleton--short"></div>
        </div>
      </div>
    } @else {
      @if (courses().length > 0) {
        <div class="stats sheet-in">
          <div class="stat">
            <span class="stat__num" [stCountUp]="courses().length"></span>
            <span class="tag">courses</span>
          </div>
          <div class="stat">
            <span class="stat__num" [stCountUp]="totalLessons()"></span>
            <span class="tag">lessons</span>
          </div>
          <div class="stat">
            <span class="stat__num" [stCountUp]="totalQuizzes()"></span>
            <span class="tag">quizzes</span>
          </div>
          <div class="stat">
            <span class="stat__num stat__num--live" [stCountUp]="liveCount()"></span>
            <span class="tag">live</span>
          </div>
        </div>
      }
      <div class="layout">
        <div class="list">
          @if (courses().length === 0) {
            <div class="panel empty sheet-in">
              <h2>Nothing on the desk yet.</h2>
              <p>Draft your first course with the form on the right.</p>
            </div>
          }
          @for (course of courses(); track course.id; let i = $index) {
            <a
              class="panel course sheet-in"
              [routerLink]="['/courses', course.slug]"
              [style.animation-delay.ms]="stagger(i)"
            >
              <div class="course__head">
                <h2>{{ course.title }}</h2>
                <span class="status-dot" [class.is-live]="course.is_published"></span>
              </div>
              <p class="course__desc">{{ course.description }}</p>
              <div class="course__meta">
                <span class="tag">{{ course.lessons.length }} lessons</span>
                <span class="tag">{{ course.quizzes.length }} quizzes</span>
                <span class="tag">{{ course.is_published ? 'LIVE' : 'DRAFT' }}</span>
              </div>
            </a>
          }
        </div>

        <aside class="panel composer sheet-in" style="animation-delay: 120ms">
          <p class="tag">New blueprint</p>
          <h2>Draft a course</h2>
          <form (submit)="create($event)">
            <label class="field">
              <span class="tag">Title</span>
              <input
                type="text"
                required
                [value]="title()"
                (input)="onTitle($any($event.target).value)"
              />
            </label>
            <label class="field">
              <span class="tag">Slug</span>
              <input
                type="text"
                required
                [value]="slug()"
                (input)="slug.set($any($event.target).value)"
              />
            </label>
            <label class="field">
              <span class="tag">Description</span>
              <textarea
                required
                [value]="description()"
                (input)="description.set($any($event.target).value)"
              ></textarea>
            </label>

            @if (error(); as message) {
              <p class="error-note" role="alert">{{ message }}</p>
            }

            <button class="btn" type="submit" [disabled]="busy()">
              {{ busy() ? 'Drafting…' : 'Create draft' }}
            </button>
          </form>
        </aside>
      </div>
    }
  `,
  styles: `
    .head h1 {
      font-size: clamp(1.9rem, 4vw, 2.8rem);
      margin-top: 0.5rem;
    }

    .stats {
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
      margin-top: 1.3rem;
      padding: 0.9rem 1.2rem;
      border: 1px dashed var(--line-strong);
      border-radius: 10px;
      background: var(--panel-raised);
    }

    .stat {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }

    .stat__num {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 640;
      color: var(--amber);
      font-variant-numeric: tabular-nums;
      min-width: 1ch;
    }

    .stat__num--live { color: var(--teal); }

    .layout {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 1.4rem;
      margin-top: 1.6rem;
      align-items: start;
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .empty {
      h2 { font-size: 1.3rem; margin-bottom: 0.4rem; }
      p { color: var(--ink-dim); }
    }

    .course {
      display: block;
      text-decoration: none;
      transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;

      &:hover {
        border-color: var(--amber);
        transform: translateX(4px);
        box-shadow: var(--shadow-md);
      }
    }

    .course__head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;

      h2 { font-size: 1.3rem; }
    }

    .course__desc {
      color: var(--ink-dim);
      font-size: 0.9rem;
      margin: 0.4rem 0 0.8rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .course__meta {
      display: flex;
      gap: 1.1rem;
      padding-top: 0.7rem;
      border-top: 1px dashed var(--line-strong);
    }

    .composer h2 {
      font-size: 1.4rem;
      margin: 0.4rem 0 1.1rem;
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }

    @media (max-width: 880px) {
      .layout { grid-template-columns: 1fr; }
    }
  `,
})
export class DashboardPage {
  private readonly api = inject(StudioApi);
  protected readonly auth = inject(AuthService);

  protected readonly courses = signal<Course[]>([]);
  protected readonly totalLessons = computed(() =>
    this.courses().reduce((sum, c) => sum + c.lessons.length, 0),
  );
  protected readonly totalQuizzes = computed(() =>
    this.courses().reduce((sum, c) => sum + c.quizzes.length, 0),
  );
  protected readonly liveCount = computed(
    () => this.courses().filter((c) => c.is_published).length,
  );
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly title = signal('');
  protected readonly slug = signal('');
  protected readonly description = signal('');

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    try {
      this.courses.set(await this.api.myCourses());
    } finally {
      this.loading.set(false);
    }
  }

  /** Entrance-stagger delay (ms) for the nth course card, capped at ~10. */
  protected stagger(index: number): number {
    return staggerDelay(index, 60);
  }

  protected onTitle(value: string): void {
    const wasAuto =
      !this.slug() || this.slug() === this.slugify(this.title());
    this.title.set(value);
    if (wasAuto) this.slug.set(this.slugify(value));
  }

  private slugify(value: string): string {
    return value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  protected async create(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.api.createCourse({
        title: this.title(),
        slug: this.slug(),
        description: this.description(),
        is_published: false,
      });
      this.title.set('');
      this.slug.set('');
      this.description.set('');
      await this.load();
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not create the course.'));
    } finally {
      this.busy.set(false);
    }
  }
}

import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { StudioApi } from '../core/api';
import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';
import { Course } from '../core/models';

@Component({
  selector: 'st-dashboard',
  imports: [RouterLink],
  template: `
    <section class="head sheet-in">
      <p class="tag">Course drawer</p>
      <h1>Your courses</h1>
    </section>

    @if (loading()) {
      <p class="tag">Pulling blueprints…</p>
    } @else {
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
              [style.animation-delay.ms]="i * 60"
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
      transition: border-color 0.15s ease, transform 0.15s ease;

      &:hover {
        border-color: var(--amber);
        transform: translateX(4px);
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

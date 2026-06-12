import {
  Component,
  ElementRef,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { Router } from '@angular/router';

import { SearchApi, SearchResults } from '../core/search';

const DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 2;

interface SearchOption {
  kind: 'course' | 'lesson';
  label: string;
  sub: string;
  url: string;
}

@Component({
  selector: 'mm-global-search',
  host: {
    '[class.search-host--menu]': 'menuMode()',
    '(document:click)': 'onDocumentClick($event)',
  },
  template: `
    <div class="search" role="search">
      <span class="search__icon" aria-hidden="true">🔍</span>
      <input
        #box
        type="search"
        class="search__input"
        placeholder="Search…"
        autocomplete="off"
        role="combobox"
        aria-label="Search courses and lessons"
        aria-autocomplete="list"
        aria-controls="global-search-results"
        [attr.aria-expanded]="open()"
        [attr.aria-activedescendant]="activeId()"
        [value]="term()"
        (input)="onInput($event)"
        (keydown)="onKeydown($event)"
        (focus)="onFocus()"
      />

      @if (open()) {
        <div class="search__panel" id="global-search-results">
          @if (tooShort()) {
            <p class="search__hint">Keep typing — at least 2 characters.</p>
          } @else if (searching()) {
            <p class="search__hint" role="status">Searching…</p>
          } @else if (noMatches()) {
            <p class="search__hint" role="status">No matches for “{{ term().trim() }}”</p>
          } @else if (results(); as r) {
            <ul class="search__list" role="listbox" aria-label="Search results">
              @if (r.courses.length > 0) {
                <li class="search__group mono-label" role="presentation">Courses</li>
                @for (course of r.courses; track course.slug; let i = $index) {
                  <li
                    role="option"
                    class="search__option"
                    [id]="'global-search-opt-' + i"
                    [class.is-active]="active() === i"
                    [attr.aria-selected]="active() === i"
                    (click)="go(i)"
                    (mousemove)="active.set(i)"
                  >
                    <span class="search__label">{{ course.title }}</span>
                    <span class="search__sub">{{ course.instructor }}</span>
                  </li>
                }
              }
              @if (r.lessons.length > 0) {
                <li class="search__group mono-label" role="presentation">Lessons</li>
                @for (lesson of r.lessons; track lesson.id; let i = $index) {
                  <li
                    role="option"
                    class="search__option"
                    [id]="'global-search-opt-' + (r.courses.length + i)"
                    [class.is-active]="active() === r.courses.length + i"
                    [attr.aria-selected]="active() === r.courses.length + i"
                    (click)="go(r.courses.length + i)"
                    (mousemove)="active.set(r.courses.length + i)"
                  >
                    <span class="search__label">{{ lesson.title }}</span>
                    <span class="search__sub">in {{ lesson.course_title }}</span>
                  </li>
                }
              }
            </ul>
          }
        </div>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }

    .search {
      position: relative;
      display: flex;
      align-items: center;
    }

    .search__icon {
      position: absolute;
      left: 0.7rem;
      font-size: 0.8rem;
      pointer-events: none;
    }

    .search__input {
      width: 8.5rem;
      padding: 0.48rem 0.8rem 0.48rem 2.1rem;
      border: 1.5px solid var(--line-strong);
      border-radius: 999px;
      background: var(--card);
      color: var(--ink);
      font-family: var(--font-body);
      font-size: 0.88rem;
      transition: width var(--speed) var(--ease), border-color var(--speed) var(--ease),
        box-shadow var(--speed) var(--ease);

      &::placeholder {
        color: var(--ink-soft);
      }

      &:hover {
        border-color: color-mix(in srgb, var(--accent) 45%, var(--line-strong));
      }

      &:focus {
        width: 15rem;
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 14%, transparent);
      }
    }

    :host(.search-host--menu) .search__input,
    :host(.search-host--menu) .search__input:focus {
      width: 100%;
    }

    .search__panel {
      position: absolute;
      top: calc(100% + 10px);
      right: 0;
      z-index: 70;
      width: min(380px, calc(100vw - 2rem));
      overflow: hidden;
      border: 1.5px solid var(--line-strong);
      border-radius: 16px;
      background: var(--card);
      box-shadow: var(--shadow-lift);
      animation: search-panel-in 160ms var(--ease) both;
    }

    :host(.search-host--menu) .search__panel {
      left: 0;
      right: 0;
      width: auto;
    }

    @keyframes search-panel-in {
      from {
        opacity: 0;
        transform: translateY(-6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .search__hint {
      padding: 0.9rem 1rem;
      color: var(--ink-soft);
      font-size: 0.85rem;
    }

    .search__list {
      margin: 0;
      padding: 0.35rem 0;
      list-style: none;
      max-height: min(50dvh, 340px);
      overflow-y: auto;
    }

    .search__group {
      padding: 0.55rem 1rem 0.25rem;
    }

    .search__option {
      display: flex;
      flex-direction: column;
      gap: 0.05rem;
      padding: 0.5rem 1rem;
      cursor: pointer;

      &.is-active {
        background: color-mix(in srgb, var(--accent) 10%, transparent);
      }
    }

    .search__label {
      font-size: 0.88rem;
      font-weight: 600;
    }

    .search__sub {
      color: var(--ink-soft);
      font-size: 0.76rem;
    }

    @media (prefers-reduced-motion: reduce) {
      .search__panel {
        animation: none;
      }

      .search__input,
      .search__input:focus {
        transition: none;
      }
    }
  `,
})
export class GlobalSearch {
  /** True when rendered inside the mobile hamburger menu (full-width). */
  readonly menuMode = input(false);

  private readonly api = inject(SearchApi);
  private readonly router = inject(Router);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  private readonly box = viewChild.required<ElementRef<HTMLInputElement>>('box');

  protected readonly term = signal('');
  protected readonly open = signal(false);
  protected readonly searching = signal(false);
  protected readonly results = signal<SearchResults | null>(null);
  protected readonly active = signal(-1);

  protected readonly tooShort = computed(
    () => this.term().trim().length > 0 && this.term().trim().length < MIN_QUERY_LENGTH,
  );

  protected readonly options = computed<SearchOption[]>(() => {
    const r = this.results();
    if (!r) return [];
    return [
      ...r.courses.map<SearchOption>((c) => ({
        kind: 'course',
        label: c.title,
        sub: c.instructor,
        url: `/courses/${c.slug}`,
      })),
      ...r.lessons.map<SearchOption>((l) => ({
        kind: 'lesson',
        label: l.title,
        sub: l.course_title,
        url: `/courses/${l.course_slug}`,
      })),
    ];
  });

  protected readonly noMatches = computed(() => {
    const r = this.results();
    return (
      r !== null &&
      r.courses.length === 0 &&
      r.lessons.length === 0 &&
      this.term().trim().length >= MIN_QUERY_LENGTH
    );
  });

  protected readonly activeId = computed(() =>
    this.active() >= 0 ? `global-search-opt-${this.active()}` : null,
  );

  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private requestSeq = 0;

  protected onInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.term.set(value);
    if (this.debounceTimer !== null) clearTimeout(this.debounceTimer);

    const query = value.trim();
    if (query.length < MIN_QUERY_LENGTH) {
      this.requestSeq++;
      this.results.set(null);
      this.searching.set(false);
      this.active.set(-1);
      this.open.set(query.length > 0);
      return;
    }

    this.searching.set(true);
    this.open.set(true);
    this.debounceTimer = setTimeout(() => void this.run(query), DEBOUNCE_MS);
  }

  protected onFocus(): void {
    if (this.term().trim().length > 0) {
      this.open.set(true);
    }
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      if (this.open()) {
        event.stopPropagation();
        this.open.set(false);
      }
      return;
    }

    const count = this.options().length;

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!this.open() || count === 0) return;
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      this.active.update((i) => (i + delta + count) % count);
      return;
    }

    if (event.key === 'Enter') {
      if (!this.open() || count === 0) return;
      event.preventDefault();
      this.go(this.active() >= 0 ? this.active() : 0);
    }
  }

  protected onDocumentClick(event: Event): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.open.set(false);
    }
  }

  protected go(index: number): void {
    const option = this.options()[index];
    if (!option) return;
    this.open.set(false);
    this.term.set('');
    this.results.set(null);
    this.active.set(-1);
    this.box().nativeElement.blur();
    void this.router.navigateByUrl(option.url);
  }

  private async run(query: string): Promise<void> {
    const seq = ++this.requestSeq;
    try {
      const res = await this.api.search(query);
      if (seq !== this.requestSeq) return;
      this.results.set(res);
      this.active.set(-1);
    } catch {
      if (seq !== this.requestSeq) return;
      this.results.set({ query, courses: [], lessons: [] });
      this.active.set(-1);
    } finally {
      if (seq === this.requestSeq) this.searching.set(false);
    }
  }
}

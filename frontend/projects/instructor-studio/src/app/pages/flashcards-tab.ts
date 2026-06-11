import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';

import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course, Flashcard, FlashcardSource } from '../core/models';

const SOURCE_BADGE: Record<FlashcardSource, string> = {
  llm: 'AI',
  heuristic: 'auto',
  instructor: 'manual',
};

/**
 * Flashcard authoring for one course: AI/heuristic drafts awaiting approval,
 * the published deck, a manual composer, and an async "generate from lesson"
 * control. Rendered as a tab inside the course workbench.
 */
@Component({
  selector: 'st-flashcards-tab',
  template: `
    @if (error(); as message) {
      <p class="error-note" role="alert" style="margin-bottom: 1rem">{{ message }}</p>
    }

    <section class="panel generate">
      <p class="tag">Generate from lesson</p>
      @if (course().lessons.length === 0) {
        <p class="tag" style="margin-top: 0.6rem">Add a lesson first to generate flashcards.</p>
      } @else {
        <div class="generate__row">
          <label class="field">
            <span class="tag">Lesson</span>
            <select
              [value]="generateLessonId() ?? ''"
              (change)="generateLessonId.set(+$any($event.target).value)"
            >
              @for (lesson of course().lessons; track lesson.id) {
                <option [value]="lesson.id">{{ lesson.order }}. {{ lesson.title }}</option>
              }
            </select>
          </label>
          <button class="btn btn--sm" type="button" (click)="generate()" [disabled]="busy()">
            ✨ Generate flashcards
          </button>
        </div>
        @if (generationQueued()) {
          <p class="tag queued" role="status">
            Generation queued — drafts will appear here shortly.
            <button class="btn btn--line btn--sm" type="button" (click)="refresh()" [disabled]="busy()">
              Refresh
            </button>
          </p>
        }
      }
    </section>

    @if (loading()) {
      <p class="tag" style="padding: 1.2rem 0">Shuffling the deck…</p>
    } @else {
      <section class="deck">
        <h2 class="tag deck__title">Drafts awaiting approval ({{ drafts().length }})</h2>
        @if (drafts().length === 0) {
          <p class="tag" style="padding: 0.4rem 0">No drafts — generate from a lesson or add cards manually.</p>
        }
        @for (card of drafts(); track card.id) {
          <div class="panel card">
            @if (editingId() === card.id) {
              <form (submit)="saveEdit($event, card)">
                <p class="tag">Editing card</p>
                <label class="field">
                  <span class="tag">Topic</span>
                  <input type="text" maxlength="100" placeholder="Kinematics" [value]="editTopic()" (input)="editTopic.set($any($event.target).value)" />
                </label>
                <label class="field">
                  <span class="tag">Front</span>
                  <textarea required [value]="editFront()" (input)="editFront.set($any($event.target).value)"></textarea>
                </label>
                <label class="field">
                  <span class="tag">Back</span>
                  <textarea required [value]="editBack()" (input)="editBack.set($any($event.target).value)"></textarea>
                </label>
                <div class="card__actions">
                  <button class="btn btn--sm" type="submit" [disabled]="busy()">Save changes</button>
                  <button class="btn btn--line btn--sm" type="button" (click)="cancelEdit()" [disabled]="busy()">
                    Cancel
                  </button>
                </div>
              </form>
            } @else {
              <div class="card__head">
                <span class="badge" [class.badge--manual]="card.source === 'instructor'">
                  {{ sourceBadge(card.source) }}
                </span>
                @if (card.topic) {
                  <span class="tag card__topic">{{ card.topic }}</span>
                }
                <div class="card__actions">
                  <button class="btn btn--sm" (click)="approve(card)" [disabled]="busy()">Approve</button>
                  <button class="btn btn--line btn--sm" (click)="startEdit(card)" [disabled]="busy()">Edit</button>
                  <button class="btn btn--danger btn--sm" (click)="remove(card)" [disabled]="busy()">Delete</button>
                </div>
              </div>
              <p class="card__front">{{ card.front }}</p>
              <p class="card__back">{{ card.back }}</p>
            }
          </div>
        }
      </section>

      <section class="deck">
        <h2 class="tag deck__title">Published deck ({{ published().length }})</h2>
        @if (published().length === 0) {
          <p class="tag" style="padding: 0.4rem 0">No published cards yet — approve a draft to go live.</p>
        }
        @for (card of published(); track card.id) {
          <div class="panel card">
            @if (editingId() === card.id) {
              <form (submit)="saveEdit($event, card)">
                <p class="tag">Editing card</p>
                <label class="field">
                  <span class="tag">Topic</span>
                  <input type="text" maxlength="100" placeholder="Kinematics" [value]="editTopic()" (input)="editTopic.set($any($event.target).value)" />
                </label>
                <label class="field">
                  <span class="tag">Front</span>
                  <textarea required [value]="editFront()" (input)="editFront.set($any($event.target).value)"></textarea>
                </label>
                <label class="field">
                  <span class="tag">Back</span>
                  <textarea required [value]="editBack()" (input)="editBack.set($any($event.target).value)"></textarea>
                </label>
                <div class="card__actions">
                  <button class="btn btn--sm" type="submit" [disabled]="busy()">Save changes</button>
                  <button class="btn btn--line btn--sm" type="button" (click)="cancelEdit()" [disabled]="busy()">
                    Cancel
                  </button>
                </div>
              </form>
            } @else {
              <div class="card__head">
                <span class="badge badge--live">LIVE</span>
                <span class="badge" [class.badge--manual]="card.source === 'instructor'">
                  {{ sourceBadge(card.source) }}
                </span>
                @if (card.topic) {
                  <span class="tag card__topic">{{ card.topic }}</span>
                }
                <div class="card__actions">
                  <button class="btn btn--line btn--sm" (click)="unpublish(card)" [disabled]="busy()">Unpublish</button>
                  <button class="btn btn--line btn--sm" (click)="startEdit(card)" [disabled]="busy()">Edit</button>
                  <button class="btn btn--danger btn--sm" (click)="remove(card)" [disabled]="busy()">Delete</button>
                </div>
              </div>
              <p class="card__front">{{ card.front }}</p>
              <p class="card__back">{{ card.back }}</p>
            }
          </div>
        }
      </section>

      <div class="panel composer">
        <p class="tag">New card</p>
        <form (submit)="add($event)">
          <label class="field">
            <span class="tag">Topic (optional)</span>
            <input type="text" maxlength="100" placeholder="Kinematics" [value]="newTopic()" (input)="newTopic.set($any($event.target).value)" />
          </label>
          <label class="field">
            <span class="tag">Front — the prompt side</span>
            <textarea required [value]="newFront()" (input)="newFront.set($any($event.target).value)"></textarea>
          </label>
          <label class="field">
            <span class="tag">Back — the answer side</span>
            <textarea required [value]="newBack()" (input)="newBack.set($any($event.target).value)"></textarea>
          </label>
          <label class="check">
            <input type="checkbox" [checked]="newPublished()" (change)="newPublished.set($any($event.target).checked)" />
            <span class="tag">Publish immediately</span>
          </label>
          <button class="btn" type="submit" [disabled]="busy()">Add card</button>
        </form>
      </div>
    }
  `,
  styles: `
    .generate {
      margin-bottom: 1.2rem;
    }

    .generate__row {
      display: flex;
      align-items: flex-end;
      gap: 1rem;
      flex-wrap: wrap;
      margin-top: 0.6rem;

      .field { min-width: 240px; }
    }

    .queued {
      display: flex;
      align-items: center;
      gap: 0.8rem;
      flex-wrap: wrap;
      margin-top: 0.9rem;
      color: var(--teal);
    }

    .deck {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-bottom: 1.6rem;
    }

    .deck__title {
      color: var(--amber);
      font-size: 0.78rem;
    }

    .card form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-top: 0.5rem;
    }

    .card__head {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .card__actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-left: auto;
    }

    .badge {
      font-family: var(--font-mono);
      font-size: 0.68rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border: 1px solid var(--amber);
      color: var(--amber);
      border-radius: 99px;
      padding: 0.1rem 0.55rem;
    }

    .badge--manual {
      border-color: var(--line-strong);
      color: var(--ink-dim);
    }

    .badge--live {
      border-color: var(--teal);
      color: var(--teal);
    }

    .card__topic {
      border: 1px solid var(--line-strong);
      border-radius: 99px;
      padding: 0.05rem 0.5rem;
    }

    .card__front {
      margin: 0.7rem 0 0.3rem;
      font-weight: 600;
      white-space: pre-wrap;
    }

    .card__back {
      margin: 0;
      color: var(--ink-dim);
      font-size: 0.92rem;
      white-space: pre-wrap;
    }

    .composer form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      margin-top: 0.7rem;

      .btn { align-self: flex-start; }
    }

    .check {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;

      input { accent-color: var(--amber); }
    }
  `,
})
export class FlashcardsTab {
  private readonly api = inject(StudioApi);

  readonly course = input.required<Course>();

  protected readonly cards = signal<Flashcard[]>([]);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly drafts = computed(() => this.cards().filter((c) => !c.is_published));
  protected readonly published = computed(() => this.cards().filter((c) => c.is_published));

  // Generate-from-lesson state.
  protected readonly generateLessonId = signal<number | null>(null);
  protected readonly generationQueued = signal(false);

  // Edit-in-place form state.
  protected readonly editingId = signal<number | null>(null);
  protected readonly editTopic = signal('');
  protected readonly editFront = signal('');
  protected readonly editBack = signal('');

  // Composer form state.
  protected readonly newTopic = signal('');
  protected readonly newFront = signal('');
  protected readonly newBack = signal('');
  protected readonly newPublished = signal(true);

  constructor() {
    effect(() => {
      const course = this.course();
      if (untracked(this.generateLessonId) === null && course.lessons.length > 0) {
        this.generateLessonId.set(course.lessons[0].id);
      }
      void this.load(course.id);
    });
  }

  protected sourceBadge(source: FlashcardSource): string {
    return SOURCE_BADGE[source];
  }

  private async load(courseId: number): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      this.cards.set(await this.api.flashcards(courseId));
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not load flashcards.'));
    } finally {
      this.loading.set(false);
    }
  }

  private async run(action: () => Promise<unknown>, failure: string): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
      this.cards.set(await this.api.flashcards(this.course().id));
    } catch (err) {
      this.error.set(apiErrorMessage(err, failure));
    } finally {
      this.busy.set(false);
    }
  }

  protected refresh(): void {
    void this.run(async () => undefined, 'Could not refresh flashcards.');
  }

  protected generate(): void {
    const lessonId = this.generateLessonId();
    if (lessonId === null) return;
    void this.run(async () => {
      await this.api.generateFlashcards(lessonId);
      this.generationQueued.set(true);
    }, 'Could not queue flashcard generation.');
  }

  protected add(event: Event): void {
    event.preventDefault();
    const front = this.newFront().trim();
    const back = this.newBack().trim();
    if (!front || !back) {
      this.error.set('A card needs both a front and a back.');
      return;
    }
    void this.run(async () => {
      await this.api.createFlashcard({
        course: this.course().id,
        topic: this.newTopic().trim(),
        front,
        back,
        is_published: this.newPublished(),
      });
      this.newTopic.set('');
      this.newFront.set('');
      this.newBack.set('');
      this.newPublished.set(true);
    }, 'Could not add the card.');
  }

  protected startEdit(card: Flashcard): void {
    this.editingId.set(card.id);
    this.editTopic.set(card.topic);
    this.editFront.set(card.front);
    this.editBack.set(card.back);
  }

  protected cancelEdit(): void {
    this.editingId.set(null);
  }

  protected saveEdit(event: Event, card: Flashcard): void {
    event.preventDefault();
    void this.run(async () => {
      await this.api.updateFlashcard(card.id, {
        topic: this.editTopic().trim(),
        front: this.editFront().trim(),
        back: this.editBack().trim(),
      });
      this.editingId.set(null);
    }, 'Could not save the card.');
  }

  protected approve(card: Flashcard): void {
    void this.run(
      () => this.api.updateFlashcard(card.id, { is_published: true }),
      'Could not approve the card.',
    );
  }

  protected unpublish(card: Flashcard): void {
    void this.run(
      () => this.api.updateFlashcard(card.id, { is_published: false }),
      'Could not unpublish the card.',
    );
  }

  protected remove(card: Flashcard): void {
    if (!confirm('Delete this flashcard?')) return;
    void this.run(() => this.api.deleteFlashcard(card.id), 'Could not delete the card.');
  }
}

import { Component, computed, effect, inject, input, signal } from '@angular/core';

import { staggerDelay } from '../core/animations';
import { StudioApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course, ProctorLog, ProctorSession } from '../core/models';

const VERDICT_LABEL: Record<ProctorLog['verdict'], string> = {
  ok: 'OK',
  no_face: 'No face',
  multiple_faces: 'Multiple faces',
};

/**
 * Exam-session proctoring timelines for the quizzes of one course.
 * Each student's webcam checks render as a chronological strip of dots:
 * green = ok, amber = no face, red = multiple faces.
 */
@Component({
  selector: 'st-proctoring-tab',
  template: `
    @if (course().quizzes.length === 0) {
      <p class="tag" style="padding: 1.2rem 0">Create a quiz first to see exam sessions.</p>
    } @else {
      <div class="picker">
        <label class="field">
          <span class="tag">Quiz</span>
          <select [value]="selectedQuizId() ?? ''" (change)="selectQuiz($any($event.target).value)">
            @for (quiz of course().quizzes; track quiz.id) {
              <option [value]="quiz.id">{{ quiz.title }}</option>
            }
          </select>
        </label>
      </div>

      @if (error(); as message) {
        <p class="error-note" role="alert" style="margin-bottom: 1rem">{{ message }}</p>
      }

      @if (loading()) {
        <p class="tag" style="padding: 1.2rem 0">Developing the contact sheet…</p>
      } @else if (sessions().length === 0) {
        <p class="tag" style="padding: 1.2rem 0">No proctoring data for this quiz yet.</p>
      } @else {
        <div class="legend tag">
          <span><i class="dot dot--ok" aria-hidden="true"></i> ok</span>
          <span><i class="dot dot--no-face" aria-hidden="true"></i> no face</span>
          <span><i class="dot dot--multi" aria-hidden="true"></i> multiple faces</span>
        </div>

        <ul class="sessions">
          @for (session of sortedSessions(); track session.enrollment; let si = $index) {
            <li
              class="panel session sheet-in"
              [class.has-violations]="session.violations > 0"
              [style.animation-delay.ms]="sessionDelay(si)"
            >
              <div class="session__head">
                <strong>{{ session.student_name || session.student_email }}</strong>
                <span class="tag">{{ session.student_email }}</span>
                @if (session.violations > 0) {
                  <span class="badge" role="status">
                    {{ session.violations }} violation{{ session.violations === 1 ? '' : 's' }}
                  </span>
                } @else {
                  <span class="tag badge--clean">clean session</span>
                }
              </div>
              <div class="strip" role="img" [attr.aria-label]="stripLabel(session)">
                @for (log of session.logs; track log.id; let di = $index) {
                  <span
                    class="dot"
                    [class.dot--ok]="log.verdict === 'ok'"
                    [class.dot--no-face]="log.verdict === 'no_face'"
                    [class.dot--multi]="log.verdict === 'multiple_faces'"
                    [title]="logTitle(log)"
                    [style.animation-delay.ms]="dotDelay(di, session.logs.length)"
                  ></span>
                }
              </div>
            </li>
          }
        </ul>
      }
    }
  `,
  styles: `
    .picker {
      margin-bottom: 1.2rem;

      .field { max-width: 340px; }
    }

    .legend {
      display: flex;
      gap: 1.4rem;
      margin-bottom: 0.9rem;

      span {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
      }
    }

    .sessions {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }

    .session {
      padding: 1rem 1.2rem;

      &.has-violations {
        border-color: rgba(178, 58, 44, 0.45);
        background: linear-gradient(rgba(178, 58, 44, 0.04), rgba(178, 58, 44, 0.04)), var(--panel);
      }
    }

    .session__head {
      display: flex;
      align-items: baseline;
      gap: 0.8rem;
      flex-wrap: wrap;
      margin-bottom: 0.7rem;
    }

    .badge {
      margin-left: auto;
      font-family: var(--font-mono);
      font-size: 0.68rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--red);
      border: 1px solid var(--red);
      border-radius: 99px;
      padding: 0.1rem 0.6rem;
    }

    .badge--clean {
      margin-left: auto;
      color: var(--teal);
    }

    .strip {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 4px;
      padding: 0.55rem 0.7rem;
      border: 1px dashed var(--line);
      border-radius: 6px;
      background: var(--desk);
    }

    .dot {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--ink-dim);
      flex: 0 0 auto;
      transition: transform 160ms ease, box-shadow 160ms ease;
    }

    .strip .dot {
      animation: dot-pop 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;

      &:hover {
        transform: scale(1.5);
        box-shadow: 0 1px 4px rgba(31, 28, 22, 0.25);
      }
    }

    @keyframes dot-pop {
      from { opacity: 0; transform: scale(0.4); }
      to { opacity: 1; transform: scale(1); }
    }

    .dot--ok { background: var(--teal); }
    .dot--no-face { background: var(--amber); }
    .dot--multi { background: var(--red); }
  `,
})
export class ProctoringTab {
  private readonly api = inject(StudioApi);

  readonly course = input.required<Course>();

  protected readonly selectedQuizId = signal<number | null>(null);
  protected readonly sessions = signal<ProctorSession[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Students with violations float to the top, worst first, then by name. */
  protected readonly sortedSessions = computed(() =>
    [...this.sessions()].sort((a, b) => {
      if (b.violations !== a.violations) return b.violations - a.violations;
      return (a.student_name || a.student_email).localeCompare(b.student_name || b.student_email);
    }),
  );

  constructor() {
    effect(() => {
      const quizzes = this.course().quizzes;
      const current = this.selectedQuizId();
      if (quizzes.length === 0) {
        this.selectedQuizId.set(null);
        this.sessions.set([]);
        return;
      }
      if (current === null || !quizzes.some((q) => q.id === current)) {
        this.selectedQuizId.set(quizzes[0].id);
      }
    });

    effect(() => {
      const quizId = this.selectedQuizId();
      if (quizId !== null) void this.load(quizId);
    });
  }

  protected selectQuiz(value: string): void {
    const id = Number(value);
    if (Number.isFinite(id)) this.selectedQuizId.set(id);
  }

  private async load(quizId: number): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const sessions = await this.api.quizProctoring(quizId);
      if (this.selectedQuizId() === quizId) this.sessions.set(sessions);
    } catch (err) {
      this.sessions.set([]);
      this.error.set(apiErrorMessage(err, 'Could not load proctoring data.'));
    } finally {
      this.loading.set(false);
    }
  }

  /** Entrance-stagger delay (ms) for the nth session card, capped at ~10. */
  protected sessionDelay(index: number): number {
    return staggerDelay(index);
  }

  /**
   * Left-to-right cascade so each timeline "replays": ~45ms per dot, but
   * compressed for long strips so the whole sweep finishes within ~1.2s.
   */
  protected dotDelay(index: number, count: number): number {
    return index * Math.min(45, 1200 / Math.max(count, 1));
  }

  protected logTitle(log: ProctorLog): string {
    const time = new Date(log.created_at).toLocaleTimeString();
    return `${time} · ${VERDICT_LABEL[log.verdict]} (${log.faces} face${log.faces === 1 ? '' : 's'})`;
  }

  protected stripLabel(session: ProctorSession): string {
    const name = session.student_name || session.student_email;
    return `Proctoring timeline for ${name}: ${session.logs.length} checks, ${session.violations} violations`;
  }
}

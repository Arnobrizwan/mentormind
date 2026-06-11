import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { LearningApi } from '../core/api';
import { apiErrorMessage } from '../core/errors';
import { Course, Quiz, QuizAttempt } from '../core/models';
import { SiteConfig } from '../core/site-config';

@Component({
  selector: 'mm-quiz',
  imports: [RouterLink],
  template: `
    @if (loading()) {
      <p class="mono-label">Sharpening pencils…</p>
    } @else if (!quiz()) {
      <div class="missing rise">
        <h1>Quiz not found.</h1>
        <a routerLink="/" class="btn btn--ghost">← Back to catalog</a>
      </div>
    } @else if (quiz(); as q) {
      <article class="exam rise">
        <header class="exam__head">
          <a [routerLink]="['/courses', course()!.slug]" class="mono-label exam__crumb">
            ← {{ course()!.title }}
          </a>
          <p class="mono-label">Examination booklet</p>
          <h1>{{ q.title }}</h1>
          @if (q.description) {
            <p class="exam__desc">{{ q.description }}</p>
          }
        </header>

        @if (!result() && proctorState() !== 'idle') {
          <aside class="proctor" aria-live="polite">
            @if (proctorState() === 'on') {
              <div class="proctor__status">
                <span class="proctor__dot" aria-hidden="true"></span>
                <span class="mono-label">Proctoring on</span>
              </div>
              <video
                #proctorVideo
                class="proctor__preview"
                autoplay
                muted
                playsinline
                aria-label="Your webcam preview"
              ></video>
              @if (proctorWarning(); as warning) {
                <p class="proctor__warning" role="status">{{ warning }}</p>
              }
            } @else if (proctorState() === 'unavailable') {
              <p class="proctor__notice">
                Camera unavailable — proctoring is off. You can continue the quiz.
              </p>
            }
          </aside>
        }

        @if (result(); as attempt) {
          <section class="result">
            <div class="result__score" [class.result__score--pass]="attempt.score >= passThreshold()">
              <span class="result__number">{{ attempt.score }}<small>%</small></span>
              <span class="mono-label">
                {{ attempt.correct_answers }} / {{ attempt.total_questions }} correct
              </span>
            </div>
            <h2>{{ verdict(attempt) }}</h2>
            <div class="result__actions">
              <button class="btn btn--accent" (click)="retake()">Retake quiz</button>
              <a class="btn btn--ghost" [routerLink]="['/courses', course()!.slug]">Back to course</a>
              <a class="btn btn--ghost" routerLink="/dashboard">My Desk</a>
            </div>
          </section>
        } @else {
          <form (submit)="submit($event)">
            <ol class="questions">
              @for (question of q.questions; track question.id; let qi = $index) {
                <li class="question">
                  <p class="question__text">
                    <span class="mono-label question__no">Q{{ qi + 1 }}</span>
                    {{ question.text }}
                  </p>
                  <div class="options" role="radiogroup" [attr.aria-label]="question.text">
                    @for (option of question.options; track $index; let oi = $index) {
                      <button
                        type="button"
                        class="option"
                        role="radio"
                        [attr.aria-checked]="answers()[question.id] === oi"
                        [class.is-picked]="answers()[question.id] === oi"
                        (click)="pick(question.id, oi)"
                      >
                        <span class="option__key mono-label">{{ letter(oi) }}</span>
                        {{ option }}
                      </button>
                    }
                  </div>
                </li>
              }
            </ol>

            @if (error(); as message) {
              <p class="error-note" role="alert">{{ message }}</p>
            }

            <footer class="exam__footer">
              <span class="mono-label">{{ answeredCount() }} / {{ q.questions.length }} answered</span>
              <button
                class="btn btn--accent"
                type="submit"
                [disabled]="busy() || answeredCount() < q.questions.length"
              >
                {{ busy() ? 'Grading…' : 'Hand in paper' }}
              </button>
            </footer>
          </form>
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

    .exam {
      max-width: 720px;
      margin: 0 auto;
    }

    .exam__crumb {
      text-decoration: none;
      display: inline-block;
      margin-bottom: 1.2rem;
      &:hover { color: var(--accent); }
    }

    .exam__head h1 {
      font-size: clamp(2rem, 4.5vw, 3rem);
      margin: 0.4rem 0 0.8rem;
    }

    .exam__desc {
      color: var(--ink-soft);
      padding-bottom: 1.4rem;
      border-bottom: 2px solid var(--line-strong);
    }

    .proctor {
      display: flex;
      align-items: center;
      gap: 0.9rem;
      flex-wrap: wrap;
      margin-top: 1.2rem;
      padding: 0.7rem 0.9rem;
      background: var(--card);
      border: 1.5px dashed var(--line-strong);
      border-radius: 10px;
    }

    .proctor__status {
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }

    .proctor__dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--sage);
      animation: proctor-pulse 2s infinite;
    }

    @keyframes proctor-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.35; }
    }

    .proctor__preview {
      width: 120px;
      border-radius: 8px;
      border: 1.5px solid var(--line-strong);
      display: block;
      background: var(--ink);
    }

    .proctor__warning {
      color: var(--danger);
      font-size: 0.88rem;
    }

    .proctor__notice {
      color: var(--ink-soft);
      font-size: 0.88rem;
    }

    .questions {
      list-style: none;
      margin: 0;
      padding: 1.4rem 0 0;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }

    .question__text {
      font-weight: 600;
      font-size: 1.08rem;
      margin-bottom: 0.9rem;
      display: flex;
      gap: 0.8rem;
      align-items: baseline;
    }

    .question__no {
      color: var(--accent);
      font-weight: 700;
    }

    .options {
      display: grid;
      gap: 0.55rem;
    }

    .option {
      display: flex;
      align-items: center;
      gap: 0.9rem;
      width: 100%;
      text-align: left;
      padding: 0.8rem 1rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 10px;
      font-family: var(--font-body);
      font-size: 0.97rem;
      color: var(--ink);
      cursor: pointer;
      transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;

      &:hover {
        border-color: var(--accent);
        transform: translateX(3px);
      }

      &.is-picked {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 8%, transparent);

        .option__key {
          background: var(--accent);
          color: var(--paper);
          border-color: var(--accent);
        }
      }
    }

    .option__key {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.7rem;
      height: 1.7rem;
      border: 1.5px solid var(--line-strong);
      border-radius: 6px;
      flex-shrink: 0;
      transition: background 0.15s ease, color 0.15s ease;
    }

    .exam__footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-top: 2rem;
      padding-top: 1.2rem;
      border-top: 1px dashed var(--line-strong);
    }

    .result {
      padding: 2.5rem 0;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1.2rem;
    }

    .result__score {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.4rem;
      width: 190px;
      height: 190px;
      justify-content: center;
      border: 3px solid var(--accent);
      border-radius: 50%;
      transform: rotate(-3deg);
      color: var(--accent-deep);

      &--pass {
        border-color: var(--sage);
        color: var(--sage-deep);
      }
    }

    .result__number {
      font-family: var(--font-display);
      font-size: 3.4rem;
      font-weight: 640;
      line-height: 1;

      small { font-size: 1.4rem; }
    }

    .result h2 {
      font-size: 1.8rem;
    }

    .result__actions {
      display: flex;
      gap: 0.7rem;
      flex-wrap: wrap;
      justify-content: center;
    }
  `,
})
export class QuizPage {
  private readonly api = inject(LearningApi);
  private readonly route = inject(ActivatedRoute);
  private readonly config = inject(SiteConfig);

  /** Pass cutoff (%) — operators tune it live via the quiz-pass-threshold setting. */
  protected readonly passThreshold = computed(() => {
    const configured = Number(this.config.settings()['quiz-pass-threshold']);
    return Number.isFinite(configured) && configured > 0 ? configured : 50;
  });

  protected readonly course = signal<Course | null>(null);
  protected readonly quizId = signal<number | null>(null);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly answers = signal<Record<number, number>>({});
  protected readonly result = signal<QuizAttempt | null>(null);

  protected readonly quiz = computed<Quiz | null>(() => {
    const c = this.course();
    const id = this.quizId();
    return c?.quizzes.find((q) => q.id === id) ?? null;
  });

  protected readonly answeredCount = computed(() => Object.keys(this.answers()).length);

  // --- Proctoring -----------------------------------------------------------
  private static readonly FRAME_INTERVAL_MS = 12_000;

  protected readonly proctorState = signal<'idle' | 'on' | 'unavailable'>('idle');
  private readonly proctorVerdict = signal<'ok' | 'no_face' | 'multiple_faces' | null>(null);
  private readonly stream = signal<MediaStream | null>(null);
  private readonly proctorVideo = viewChild<ElementRef<HTMLVideoElement>>('proctorVideo');
  private frameTimer: number | null = null;
  /**
   * Bumped by stopProctoring() (including on destroy) so a getUserMedia call
   * that resolves after the permission prompt outlived the session discards
   * its stream instead of leaking the camera.
   */
  private proctorSession = 0;

  protected readonly proctorWarning = computed(() => {
    switch (this.proctorVerdict()) {
      case 'no_face':
        return 'Make sure your face is visible.';
      case 'multiple_faces':
        return 'Only you should be in frame.';
      default:
        return null;
    }
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const slug = params.get('slug');
      const id = Number(params.get('id'));
      const nextId = Number.isFinite(id) ? id : null;
      if (this.quizId() !== nextId) {
        // The router reuses this component across quiz routes — drop the
        // previous quiz's answers/result so they don't bleed into this one.
        this.answers.set({});
        this.result.set(null);
        this.error.set(null);
      }
      this.quizId.set(nextId);
      if (slug && this.course()?.slug !== slug) {
        void this.load(slug);
      } else if (this.quiz() && !this.result()) {
        // Same course, new quiz: load() is skipped, so make sure proctoring
        // is running again (it stops after a submit). No-op if already live.
        void this.startProctoring();
      }
    });

    // The preview <video> lives inside an @if block, so wire the stream to it
    // whenever both exist.
    effect(() => {
      const el = this.proctorVideo()?.nativeElement;
      const stream = this.stream();
      if (el && stream && el.srcObject !== stream) {
        el.srcObject = stream;
        void el.play().catch(() => undefined);
      }
    });

    inject(DestroyRef).onDestroy(() => this.stopProctoring());
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
    if (this.quiz() && !this.result()) {
      void this.startProctoring();
    }
  }

  private async startProctoring(): Promise<void> {
    if (this.stream()) return;
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      this.proctorState.set('unavailable');
      return;
    }
    const session = this.proctorSession;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640 } });
      if (this.proctorSession !== session) {
        // The component was destroyed (or proctoring stopped) while the
        // permission prompt was open — release the camera and bail out.
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      this.stream.set(stream);
      this.proctorState.set('on');
      this.frameTimer = window.setInterval(
        () => this.captureFrame(),
        QuizPage.FRAME_INTERVAL_MS,
      );
    } catch {
      // Permission denied or no camera — proctoring is optional, the quiz goes on.
      this.proctorState.set('unavailable');
    }
  }

  /** Fire-and-forget: a failed frame must never disrupt quiz taking. */
  private captureFrame(): void {
    const q = this.quiz();
    const video = this.proctorVideo()?.nativeElement;
    if (!q || !video || video.videoWidth === 0) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        this.api
          .sendProctorFrame(q.id, blob)
          .then((res) => this.proctorVerdict.set(res.verdict))
          .catch(() => undefined);
      },
      'image/jpeg',
      0.7,
    );
  }

  private stopProctoring(): void {
    this.proctorSession += 1;
    if (this.frameTimer !== null) {
      window.clearInterval(this.frameTimer);
      this.frameTimer = null;
    }
    this.stream()?.getTracks().forEach((track) => track.stop());
    this.stream.set(null);
    this.proctorVerdict.set(null);
    this.proctorState.set('idle');
  }

  protected letter(index: number): string {
    return String.fromCharCode(65 + index);
  }

  protected pick(questionId: number, optionIndex: number): void {
    this.answers.update((current) => ({ ...current, [questionId]: optionIndex }));
  }

  protected verdict(attempt: QuizAttempt): string {
    if (attempt.score === 100) return 'Flawless. The mentor is impressed.';
    if (attempt.score >= 75) return 'Strong work — nearly there.';
    if (attempt.score >= this.passThreshold()) return 'A solid pass. Review and retake?';
    return 'The notebook is open — review and try again.';
  }

  protected async submit(event: Event): Promise<void> {
    event.preventDefault();
    const q = this.quiz();
    if (!q || this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      this.result.set(await this.api.submitQuiz(q.id, this.answers()));
      this.stopProctoring();
    } catch (err) {
      this.error.set(
        apiErrorMessage(err, 'Submission failed — are you enrolled in this course?'),
      );
    } finally {
      this.busy.set(false);
    }
  }

  protected retake(): void {
    this.answers.set({});
    this.result.set(null);
    void this.startProctoring();
  }
}

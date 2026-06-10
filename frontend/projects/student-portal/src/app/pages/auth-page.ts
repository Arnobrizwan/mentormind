import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { LearningApi } from '../core/api';
import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';

@Component({
  selector: 'mm-auth-page',
  template: `
    <section class="auth rise">
      <div class="auth__pitch">
        <p class="mono-label">Admissions · open all year</p>
        <h1>
          Pull up a chair.<br />
          Class is <em>always</em> in session.
        </h1>
        <p class="auth__sub">
          One account unlocks every course, quiz, and mentor on MentorMind. No
          waitlists, no tuition — just learning.
        </p>
      </div>

      <div class="auth__card">
        <div class="auth__tabs" role="tablist">
          <button
            type="button"
            role="tab"
            [attr.aria-selected]="mode() === 'login'"
            [class.is-active]="mode() === 'login'"
            (click)="switchMode('login')"
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            [attr.aria-selected]="mode() === 'register'"
            [class.is-active]="mode() === 'register'"
            (click)="switchMode('register')"
          >
            Create account
          </button>
        </div>

        <form (submit)="submit($event)">
          @if (mode() === 'register') {
            <label class="field">
              <span class="mono-label">Display name</span>
              <input
                type="text"
                autocomplete="name"
                placeholder="Ada Lovelace"
                [value]="displayName()"
                (input)="displayName.set($any($event.target).value)"
              />
            </label>
          }
          <label class="field">
            <span class="mono-label">Email</span>
            <input
              type="email"
              required
              autocomplete="email"
              placeholder="you@example.com"
              [value]="email()"
              (input)="email.set($any($event.target).value)"
            />
          </label>
          <label class="field">
            <span class="mono-label">Password</span>
            <input
              type="password"
              required
              [attr.autocomplete]="mode() === 'login' ? 'current-password' : 'new-password'"
              placeholder="••••••••"
              [value]="password()"
              (input)="password.set($any($event.target).value)"
            />
          </label>

          @if (error(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          }

          <button class="btn btn--accent auth__submit" type="submit" [disabled]="busy()">
            {{ busy() ? 'One moment…' : mode() === 'login' ? 'Sign in' : 'Enroll me' }}
          </button>
        </form>
      </div>
    </section>
  `,
  styles: `
    .auth {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: clamp(2rem, 6vw, 5rem);
      align-items: center;
      padding-top: clamp(1rem, 4vw, 3rem);
    }

    .auth__pitch h1 {
      font-size: clamp(2.4rem, 5vw, 3.8rem);
      margin: 0.8rem 0 1.2rem;

      em {
        font-style: italic;
        color: var(--accent);
        /* marker highlight */
        background: linear-gradient(transparent 62%, var(--marker) 62%, var(--marker) 92%, transparent 92%);
      }
    }

    .auth__sub {
      max-width: 38ch;
      color: var(--ink-soft);
      font-size: 1.05rem;
    }

    .auth__card {
      background: var(--card);
      border: 1.5px solid var(--ink);
      border-radius: 14px;
      padding: 1.8rem;
      box-shadow: var(--shadow-card);
    }

    .auth__tabs {
      display: flex;
      gap: 0.4rem;
      margin-bottom: 1.4rem;
      border-bottom: 1px solid var(--line);

      button {
        flex: 1;
        padding: 0.6rem 0;
        border: 0;
        background: none;
        font-family: var(--font-body);
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--ink-soft);
        cursor: pointer;
        border-bottom: 3px solid transparent;
        margin-bottom: -1px;

        &.is-active {
          color: var(--ink);
          border-bottom-color: var(--accent);
        }
      }
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .auth__submit {
      justify-content: center;
      margin-top: 0.4rem;
    }

    @media (max-width: 860px) {
      .auth {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class AuthPage {
  private readonly auth = inject(AuthService);
  private readonly api = inject(LearningApi);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly mode = signal<'login' | 'register'>('login');
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly displayName = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected switchMode(mode: 'login' | 'register'): void {
    this.mode.set(mode);
    this.error.set(null);
  }

  protected async submit(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      if (this.mode() === 'login') {
        await this.auth.login(this.email(), this.password());
      } else {
        await this.auth.register(this.email(), this.password(), this.displayName());
      }
      await this.api.refreshEnrollments();
      const next = this.route.snapshot.queryParamMap.get('next') ?? '/dashboard';
      await this.router.navigateByUrl(next);
    } catch (err) {
      this.error.set(
        apiErrorMessage(
          err,
          this.mode() === 'login'
            ? 'Sign-in failed — check your email and password.'
            : 'Registration failed — try a different email or stronger password.',
        ),
      );
    } finally {
      this.busy.set(false);
    }
  }
}

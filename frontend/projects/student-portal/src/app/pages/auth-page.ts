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
        @if (mode() === 'login' || mode() === 'register') {
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
        } @else if (mode() === 'forgot') {
          <h2 style="margin-bottom: 1rem; font-size: 1.3rem;">Forgot Password</h2>
        } @else if (mode() === 'reset') {
          <h2 style="margin-bottom: 1rem; font-size: 1.3rem;">Reset Password</h2>
        }

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
          @if (mode() !== 'reset') {
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
          }
          @if (mode() !== 'forgot') {
            <label class="field">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="mono-label">{{ mode() === 'reset' ? 'New Password' : 'Password' }}</span>
                @if (mode() === 'login') {
                  <a href="#" (click)="switchMode('forgot'); $event.preventDefault();" style="font-size: 0.8rem; color: var(--accent);">Forgot?</a>
                }
              </div>
              <input
                type="password"
                required
                [attr.autocomplete]="mode() === 'login' ? 'current-password' : 'new-password'"
                placeholder="••••••••"
                [value]="password()"
                (input)="password.set($any($event.target).value)"
              />
            </label>
          }

          @if (error(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          }
          @if (successMessage(); as message) {
            <p class="success-note" role="status" style="color: var(--teal); font-size: 0.85rem; margin: 0.4rem 0;">{{ message }}</p>
          }

          <button class="btn btn--accent auth__submit" type="submit" [disabled]="busy()">
            {{ busy() ? 'One moment…' : mode() === 'login' ? 'Sign in' : mode() === 'register' ? 'Enroll me' : mode() === 'forgot' ? 'Send reset link' : 'Reset password' }}
          </button>

          @if (mode() === 'forgot' || mode() === 'reset') {
            <a href="#" (click)="switchMode('forgot'); switchMode('login'); $event.preventDefault();" style="font-size: 0.85rem; color: var(--accent); margin-top: 0.5rem; text-align: center; display: block;">Back to sign in</a>
          }
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
      border: 1.5px solid var(--line-strong);
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

  protected readonly mode = signal<'login' | 'register' | 'forgot' | 'reset'>('login');
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly displayName = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly successMessage = signal<string | null>(null);
  protected readonly uid = signal('');
  protected readonly token = signal('');

  constructor() {
    const mode = this.route.snapshot.queryParamMap.get('mode');
    const uid = this.route.snapshot.queryParamMap.get('uid');
    const token = this.route.snapshot.queryParamMap.get('token');
    if (mode === 'reset' && uid && token) {
      this.mode.set('reset');
      this.uid.set(uid);
      this.token.set(token);
    }
  }

  protected switchMode(mode: 'login' | 'register' | 'forgot' | 'reset'): void {
    this.mode.set(mode);
    this.error.set(null);
    this.successMessage.set(null);
  }

  protected async submit(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    this.successMessage.set(null);
    try {
      if (this.mode() === 'login') {
        await this.auth.login(this.email(), this.password());
        await this.api.refreshEnrollments();
        const next = this.route.snapshot.queryParamMap.get('next') ?? '/dashboard';
        await this.router.navigateByUrl(next);
      } else if (this.mode() === 'register') {
        await this.auth.register(this.email(), this.password(), this.displayName());
        await this.api.refreshEnrollments();
        const next = this.route.snapshot.queryParamMap.get('next') ?? '/dashboard';
        await this.router.navigateByUrl(next);
      } else if (this.mode() === 'forgot') {
        const res = await this.auth.requestPasswordReset(this.email());
        let msg = 'If the email exists, a password reset link has been sent.';
        if (res && res.debug_link) {
          msg += ` (Debug link: ${res.debug_link})`;
        }
        this.successMessage.set(msg);
      } else if (this.mode() === 'reset') {
        await this.auth.confirmPasswordReset({
          uid: this.uid(),
          token: this.token(),
          password: this.password(),
        });
        this.successMessage.set('Password reset successfully! Please sign in with your new password.');
        this.mode.set('login');
      }
    } catch (err) {
      this.error.set(
        apiErrorMessage(
          err,
          this.mode() === 'login'
            ? 'Sign-in failed — check your email and password.'
            : this.mode() === 'register'
            ? 'Registration failed — try a different email or stronger password.'
            : 'Action failed — please try again.',
        ),
      );
    } finally {
      this.busy.set(false);
    }
  }
}

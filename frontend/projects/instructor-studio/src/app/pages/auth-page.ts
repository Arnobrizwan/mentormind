import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../core/auth';
import { apiErrorMessage } from '../core/errors';

@Component({
  selector: 'st-auth-page',
  template: `
    <section class="gate sheet-in">
      <div class="gate__card panel">
        <p class="tag">Studio access</p>
        @if (mode() === 'login') {
          <h1>Sign in to your drafting desk.</h1>
          <p class="gate__hint">
            Instructor accounts are provisioned by an admin (Django admin →
            add user to the <code>Instructors</code> group).
          </p>
        } @else if (mode() === 'forgot') {
          <h1>Forgot Password</h1>
          <p class="gate__hint">Enter your email to receive a password reset link.</p>
        } @else if (mode() === 'reset') {
          <h1>Reset Password</h1>
          <p class="gate__hint">Enter your new password.</p>
        }

        <form (submit)="submit($event)">
          @if (mode() !== 'reset') {
            <label class="field">
              <span class="tag">Email</span>
              <input
                type="email"
                required
                autocomplete="email"
                [value]="email()"
                (input)="email.set($any($event.target).value)"
              />
            </label>
          }
          @if (mode() !== 'forgot') {
            <label class="field">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="tag">{{ mode() === 'reset' ? 'New Password' : 'Password' }}</span>
                @if (mode() === 'login') {
                  <a href="#" (click)="switchMode('forgot'); $event.preventDefault();" style="font-size: 0.8rem; color: var(--accent);">Forgot?</a>
                }
              </div>
              <input
                type="password"
                required
                [attr.autocomplete]="mode() === 'login' ? 'current-password' : 'new-password'"
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

          <button class="btn" type="submit" [disabled]="busy()">
            {{ busy() ? 'Checking credentials…' : mode() === 'login' ? 'Enter the studio' : mode() === 'forgot' ? 'Send reset link' : 'Reset password' }}
          </button>

          @if (mode() === 'forgot' || mode() === 'reset') {
            <a href="#" (click)="switchMode('login'); $event.preventDefault();" style="font-size: 0.85rem; color: var(--accent); margin-top: 0.5rem; text-align: center; display: block;">Back to sign in</a>
          }
        </form>
      </div>
    </section>
  `,
  styles: `
    .gate {
      display: flex;
      justify-content: center;
      padding-top: clamp(1rem, 8vh, 5rem);
    }

    .gate__card {
      width: min(440px, 100%);
      padding: 2rem;

      h1 {
        font-size: 1.7rem;
        margin: 0.6rem 0 0.8rem;
      }
    }

    .gate__hint {
      color: var(--ink-dim);
      font-size: 0.86rem;
      margin-bottom: 1.4rem;

      code {
        font-family: var(--font-mono);
        color: var(--amber);
      }
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .btn {
      justify-content: center;
    }
  `,
})
export class AuthPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly mode = signal<'login' | 'forgot' | 'reset'>('login');
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly successMessage = signal<string | null>(null);
  protected readonly uid = signal('');
  protected readonly token = signal('');

  constructor() {
    // The instructor guard bounces signed-in non-instructors here.
    if (this.route.snapshot.queryParamMap.has('denied')) {
      this.error.set('Access denied — this account does not have instructor access.');
    }
    const mode = this.route.snapshot.queryParamMap.get('mode');
    const uid = this.route.snapshot.queryParamMap.get('uid');
    const token = this.route.snapshot.queryParamMap.get('token');
    if (mode === 'reset' && uid && token) {
      this.mode.set('reset');
      this.uid.set(uid);
      this.token.set(token);
    }
  }

  protected switchMode(mode: 'login' | 'forgot' | 'reset'): void {
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
        const next = this.route.snapshot.queryParamMap.get('next') ?? '/';
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
      this.error.set(apiErrorMessage(err, this.mode() === 'login' ? 'Sign-in failed — check your credentials.' : 'Action failed — please try again.'));
    } finally {
      this.busy.set(false);
    }
  }
}

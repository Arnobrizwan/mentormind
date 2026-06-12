import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../core/auth';

@Component({
  selector: 'ac-auth-page',
  template: `
    <section class="gate boot-in">
      <div class="gate__card bay">
        <p class="label">// restricted area</p>
        @if (mode() === 'login') {
          <h1>operator login</h1>
        } @else if (mode() === 'forgot') {
          <h1>forgot password</h1>
        } @else if (mode() === 'reset') {
          <h1>reset password</h1>
        }

        <form (submit)="submit($event)">
          @if (mode() !== 'reset') {
            <label class="field">
              <span class="label">email</span>
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
                <span class="label">{{ mode() === 'reset' ? 'new password' : 'password' }}</span>
                @if (mode() === 'login') {
                  <a href="#" (click)="switchMode('forgot'); $event.preventDefault();" style="font-size: 0.8rem; color: var(--phosphor);">forgot?</a>
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
            <p class="success-note" role="status" style="color: var(--phosphor); font-size: 0.85rem; margin: 0.4rem 0;">{{ message }}</p>
          }

          <button class="btn" type="submit" [disabled]="busy()">
            {{ busy() ? 'processing…' : mode() === 'login' ? 'authenticate' : mode() === 'forgot' ? 'send reset link' : 'reset password' }}
          </button>

          @if (mode() === 'forgot' || mode() === 'reset') {
            <a href="#" (click)="switchMode('login'); $event.preventDefault();" style="font-size: 0.85rem; color: var(--phosphor); margin-top: 0.5rem; text-align: center; display: block;">back to login</a>
          }
        </form>

        @if (mode() === 'login') {
          <p class="gate__hint label">staff accounts only — everyone else bounces off the API.</p>
        }
      </div>
    </section>
  `,
  styles: `
    .gate {
      display: flex;
      justify-content: center;
      padding-top: clamp(1rem, 9vh, 5.5rem);
    }

    .gate__card {
      width: min(420px, 100%);
      padding: 1.8rem;

      h1 {
        font-size: 1.5rem;
        margin: 0.5rem 0 1.3rem;
        color: var(--phosphor);
      }
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .btn { justify-content: center; }

    .gate__hint {
      margin-top: 1.1rem;
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
    // The staff guard bounces signed-in non-staff users here.
    if (this.route.snapshot.queryParamMap.has('denied')) {
      this.error.set('access denied — this account does not have operator rights.');
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
        let msg = 'if the email exists, a password reset link has been sent.';
        if (res && res.debug_link) {
          msg += ` (debug link: ${res.debug_link})`;
        }
        this.successMessage.set(msg);
      } else if (this.mode() === 'reset') {
        await this.auth.confirmPasswordReset({
          uid: this.uid(),
          token: this.token(),
          password: this.password(),
        });
        this.successMessage.set('password reset successfully! please login with your new password.');
        this.mode.set('login');
      }
    } catch (err) {
      this.error.set(
        err instanceof HttpErrorResponse && err.status === 401
          ? 'access denied — wrong credentials.'
          : 'action failed — please try again.'
      );
    } finally {
      this.busy.set(false);
    }
  }
}

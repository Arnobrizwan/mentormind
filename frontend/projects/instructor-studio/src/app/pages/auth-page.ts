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
        <h1>Sign in to your drafting desk.</h1>
        <p class="gate__hint">
          Instructor accounts are provisioned by an admin (Django admin →
          add user to the <code>Instructors</code> group).
        </p>

        <form (submit)="submit($event)">
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
          <label class="field">
            <span class="tag">Password</span>
            <input
              type="password"
              required
              autocomplete="current-password"
              [value]="password()"
              (input)="password.set($any($event.target).value)"
            />
          </label>

          @if (error(); as message) {
            <p class="error-note" role="alert">{{ message }}</p>
          }

          <button class="btn" type="submit" [disabled]="busy()">
            {{ busy() ? 'Checking credentials…' : 'Enter the studio' }}
          </button>
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

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    // The instructor guard bounces signed-in non-instructors here.
    if (this.route.snapshot.queryParamMap.has('denied')) {
      this.error.set('Access denied — this account does not have instructor access.');
    }
  }

  protected async submit(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.auth.login(this.email(), this.password());
      const next = this.route.snapshot.queryParamMap.get('next') ?? '/';
      await this.router.navigateByUrl(next);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Sign-in failed — check your credentials.'));
    } finally {
      this.busy.set(false);
    }
  }
}

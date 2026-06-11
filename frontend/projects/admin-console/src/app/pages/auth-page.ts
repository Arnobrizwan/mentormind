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
        <h1>operator login</h1>

        <form (submit)="submit($event)">
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
          <label class="field">
            <span class="label">password</span>
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
            {{ busy() ? 'authenticating…' : 'authenticate' }}
          </button>
        </form>

        <p class="gate__hint label">staff accounts only — everyone else bounces off the API.</p>
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

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    // The staff guard bounces signed-in non-staff users here.
    if (this.route.snapshot.queryParamMap.has('denied')) {
      this.error.set('access denied — this account does not have operator rights.');
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
      this.error.set(
        err instanceof HttpErrorResponse && err.status === 401
          ? 'access denied — wrong credentials.'
          : 'login failed — is the API reachable?',
      );
    } finally {
      this.busy.set(false);
    }
  }
}

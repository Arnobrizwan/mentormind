import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { LearningApi } from './core/api';
import { AuthService } from './core/auth';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly auth = inject(AuthService);
  private readonly api = inject(LearningApi);
  private readonly router = inject(Router);

  constructor() {
    if (this.auth.isLoggedIn()) {
      void this.api.refreshEnrollments();
    }
  }

  protected logout(): void {
    this.auth.logout();
    this.api.enrollments.set([]);
    void this.router.navigateByUrl('/');
  }
}

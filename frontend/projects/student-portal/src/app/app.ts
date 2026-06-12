import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { LearningApi } from './core/api';
import { AuthService } from './core/auth';
import { Connectivity } from './core/connectivity';
import { SlowApiService } from './core/slow-api';
import { SiteConfig } from './core/site-config';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly config = inject(SiteConfig);
  protected readonly connectivity = inject(Connectivity);
  protected readonly slowApi = inject(SlowApiService);
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

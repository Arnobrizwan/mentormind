import { Component, effect, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { LearningApi } from './core/api';
import { AuthService } from './core/auth';
import { Connectivity } from './core/connectivity';
import { EngagementApi } from './core/engagement';
import { RevisionApi } from './core/revision';
import { LocaleService } from './core/locale';
import { SiteConfig } from './core/site-config';
import { SlowApiService } from './core/slow-api';
import { GlobalSearch } from './shell/global-search';
import { NotificationsBell } from './shell/notifications-bell';
import { UserMenu } from './shell/user-menu';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, GlobalSearch, NotificationsBell, UserMenu],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  host: {
    '(document:keydown.escape)': 'closeMenu()',
  },
})
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly locale = inject(LocaleService);
  protected readonly config = inject(SiteConfig);
  protected readonly connectivity = inject(Connectivity);
  protected readonly slowApi = inject(SlowApiService);
  protected readonly engagement = inject(EngagementApi);
  private readonly api = inject(LearningApi);
  private readonly revision = inject(RevisionApi);
  private readonly router = inject(Router);

  /** Due-card count for the Revision nav badge — 0 hides it. */
  protected readonly dueCount = signal(0);

  /** Mobile hamburger menu state. */
  protected readonly mobileOpen = signal(false);

  protected readonly year = new Date().getFullYear();

  constructor() {
    // Refresh login-scoped header data whenever the auth state flips true
    // (boot restore or interactive sign-in). Everything is non-blocking.
    effect(() => {
      if (this.auth.isLoggedIn()) {
        void this.api.refreshEnrollments();
        void this.engagement.refresh();
        void this.revision
          .queue()
          .then((q) => this.dueCount.set(q.due_count))
          .catch(() => this.dueCount.set(0));
      } else {
        this.dueCount.set(0);
      }
    });

    // Close the mobile menu after any navigation.
    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.mobileOpen.set(false);
      }
    });
  }

  protected toggleMenu(): void {
    this.mobileOpen.update((v) => !v);
  }

  protected closeMenu(): void {
    this.mobileOpen.set(false);
  }

  protected logout(): void {
    this.auth.logout();
    this.api.enrollments.set([]);
    this.engagement.me.set(null);
    this.closeMenu();
    void this.router.navigateByUrl('/');
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { User } from './models';

const ACCESS_KEY = 'mm_studio_access';
const REFRESH_KEY = 'mm_studio_refresh';

interface TokenPair {
  access: string;
  refresh: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  readonly user = signal<User | null>(null);
  readonly isLoggedIn = computed(() => this.user() !== null);
  readonly isInstructor = computed(() => {
    const u = this.user();
    return !!u && (u.roles.includes('Instructors') || u.is_staff);
  });

  private refreshing: Promise<boolean> | null = null;

  get accessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  get refreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  async restore(): Promise<void> {
    if (!this.accessToken) return;
    try {
      await this.loadMe();
    } catch {
      if (await this.tryRefresh()) {
        try {
          await this.loadMe();
        } catch {
          this.logout();
        }
      } else {
        this.logout();
      }
    }
  }

  async login(email: string, password: string): Promise<void> {
    const tokens = await firstValueFrom(
      this.http.post<TokenPair>('/api/v1/auth/token/', { email, password }),
    );
    localStorage.setItem(ACCESS_KEY, tokens.access);
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
    await this.loadMe();
  }

  async loadMe(): Promise<void> {
    this.user.set(await firstValueFrom(this.http.get<User>('/api/v1/auth/me/')));
  }

  tryRefresh(): Promise<boolean> {
    const refresh = this.refreshToken;
    if (!refresh) return Promise.resolve(false);

    this.refreshing ??= fetch('/api/v1/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (!res.ok) {
          this.logout();
          return false;
        }
        const data = (await res.json()) as Partial<TokenPair>;
        if (data.access) localStorage.setItem(ACCESS_KEY, data.access);
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
        return Boolean(data.access);
      })
      .catch(() => false)
      .finally(() => {
        this.refreshing = null;
      });

    return this.refreshing;
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this.user.set(null);
  }
}

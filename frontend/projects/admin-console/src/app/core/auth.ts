import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { API_BASE_URL } from './api-base-url';

const REFRESH_KEY = 'mm_admin_refresh';
/** The access token used to be persisted under this key — clean it up. */
const LEGACY_ACCESS_KEY = 'mm_admin_access';

export interface User {
  id: number;
  email: string;
  display_name: string;
  roles: string[];
  is_staff: boolean;
}

interface TokenPair {
  access: string;
  refresh: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = inject(API_BASE_URL);

  readonly user = signal<User | null>(null);
  readonly isLoggedIn = computed(() => this.user() !== null);
  readonly isStaff = computed(() => this.user()?.is_staff ?? false);

  /** Flips true once the boot-time restore() has finished (success or not). */
  readonly ready = signal(false);

  /**
   * True when the last token refresh failed for a retryable reason (network
   * error or 5xx). The session is kept — a later request can retry.
   */
  readonly refreshRetryable = signal(false);

  private refreshing: Promise<boolean> | null = null;

  /** Access token lives in memory only — never persisted (XSS hardening). */
  private accessTokenValue: string | null = null;

  private resolveReady!: () => void;
  private readonly readyPromise = new Promise<void>((resolve) => {
    this.resolveReady = resolve;
  });

  get accessToken(): string | null {
    return this.accessTokenValue;
  }

  get refreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  /** Resolves once restore() has completed — auth guards await this. */
  whenReady(): Promise<void> {
    return this.readyPromise;
  }

  /**
   * Restore session on app boot. Kicked off without awaiting from
   * provideAppInitializer so public routes render immediately; guards await
   * whenReady() before deciding. Only the refresh token is persisted, so we
   * mint a fresh in-memory access token from it.
   */
  async restore(): Promise<void> {
    try {
      localStorage.removeItem(LEGACY_ACCESS_KEY);
      if (!this.refreshToken) return;
      if (await this.tryRefresh()) {
        try {
          await this.loadMe();
        } catch {
          // Transient failure loading the profile — keep the session tokens.
        }
      }
    } finally {
      this.ready.set(true);
      this.resolveReady();
    }
  }

  async login(email: string, password: string): Promise<void> {
    const tokens = await firstValueFrom(
      this.http.post<TokenPair>('/api/v1/auth/token/', { email, password }),
    );
    this.accessTokenValue = tokens.access;
    localStorage.setItem(REFRESH_KEY, tokens.refresh);
    await this.loadMe();
  }

  async loadMe(): Promise<void> {
    this.user.set(await firstValueFrom(this.http.get<User>('/api/v1/auth/me/')));
  }

  /**
   * Exchange the refresh token for a new access token. Uses fetch directly so
   * the call never recurses through the auth interceptor. Concurrent 401s
   * share a single in-flight refresh. Only a definitive 401/403 from the
   * refresh endpoint ends the session — network errors and 5xx keep it and
   * surface a retryable state via refreshRetryable.
   */
  tryRefresh(): Promise<boolean> {
    const refresh = this.refreshToken;
    if (!refresh) return Promise.resolve(false);

    this.refreshing ??= fetch(`${this.apiBaseUrl}/api/v1/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          // Refresh token is definitively invalid — end the session.
          this.logout();
          return false;
        }
        if (!res.ok) {
          // 5xx / unexpected status — keep the session, allow a retry.
          this.refreshRetryable.set(true);
          return false;
        }
        const data = (await res.json()) as Partial<TokenPair>;
        if (data.access) this.accessTokenValue = data.access;
        // ROTATE_REFRESH_TOKENS is on server-side — keep the new one.
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
        this.refreshRetryable.set(false);
        return Boolean(data.access);
      })
      .catch(() => {
        // Network error — keep the session, allow a retry.
        this.refreshRetryable.set(true);
        return false;
      })
      .finally(() => {
        this.refreshing = null;
      });

    return this.refreshing;
  }

  logout(): void {
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(LEGACY_ACCESS_KEY);
    this.accessTokenValue = null;
    this.user.set(null);
  }

  async requestPasswordReset(email: string): Promise<any> {
    return firstValueFrom(
      this.http.post('/api/v1/auth/password-reset/', { email })
    );
  }

  async confirmPasswordReset(payload: any): Promise<any> {
    return firstValueFrom(
      this.http.post('/api/v1/auth/password-reset-confirm/', payload)
    );
  }
}

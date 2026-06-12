import { Injectable, signal } from '@angular/core';

export type ThemeId = 'light' | 'dark';

const STORAGE_KEY = 'mm_theme';

/**
 * Light/dark theming. The DIGITEX poster brand has a dark variant driven
 * entirely by the CSS custom properties in styles.scss — this service only
 * flips html[data-theme] (index.html sets it pre-boot to avoid a flash).
 * No stored choice means we follow the OS preference, live.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly media =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;

  readonly theme = signal<ThemeId>(this.initial());

  constructor() {
    this.apply(this.theme());
    this.media?.addEventListener('change', (event) => {
      if (!this.stored()) {
        this.theme.set(event.matches ? 'dark' : 'light');
        this.apply(this.theme());
      }
    });
  }

  toggle(): void {
    const next: ThemeId = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private mode — theme still applies for this visit */
    }
    this.apply(next);
  }

  private stored(): ThemeId | null {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return value === 'dark' || value === 'light' ? value : null;
    } catch {
      return null;
    }
  }

  private initial(): ThemeId {
    return this.stored() ?? (this.media?.matches ? 'dark' : 'light');
  }

  private apply(theme: ThemeId): void {
    document.documentElement.setAttribute('data-theme', theme);
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', theme === 'dark' ? '#16101e' : '#ff5ca3');
  }
}

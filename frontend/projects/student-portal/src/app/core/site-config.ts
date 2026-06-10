import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

const DEFAULT_NAME = 'MentorMinds';
const DEFAULT_TAGLINE = 'the AI tutor that never sleeps';

/** Boot-time site configuration: public settings + feature flags from the
 * settings engine. Everything has a hardcoded fallback so the app still
 * renders when the API is unreachable. */
@Injectable({ providedIn: 'root' })
export class SiteConfig {
  private readonly http = inject(HttpClient);

  readonly settings = signal<Record<string, unknown>>({});
  readonly flags = signal<Record<string, boolean>>({});

  readonly siteName = computed(() => String(this.settings()['site-name'] ?? DEFAULT_NAME));
  readonly tagline = computed(() => String(this.settings()['tagline'] ?? DEFAULT_TAGLINE));

  /** Two-part wordmark split on the camel-case boundary (Mentor|Mind). */
  readonly brandParts = computed<[string, string]>(() => {
    const name = this.siteName();
    const match = name.match(/^([A-Z][a-z]+)([A-Z].*)$/);
    return match ? [match[1], match[2]] : [name, ''];
  });

  flagEnabled(key: string, fallback = true): boolean {
    return this.flags()[key] ?? fallback;
  }

  /** Never blocks or fails the boot — offline falls back to defaults. */
  async load(): Promise<void> {
    const [settings, flags] = await Promise.all([
      firstValueFrom(this.http.get<Record<string, unknown>>('/api/v1/settings/public/')).catch(
        () => ({}),
      ),
      firstValueFrom(this.http.get<Record<string, boolean>>('/api/v1/flags/')).catch(() => ({})),
    ]);
    this.settings.set(settings);
    this.flags.set(flags);
    document.title = `${this.siteName()} — Student Portal`;
  }
}

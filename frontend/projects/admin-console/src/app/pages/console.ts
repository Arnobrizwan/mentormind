import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';

import { AdminApi, FeatureFlag, SiteSetting, SystemStatus } from '../core/api';
import { AuthService } from '../core/auth';

const POLL_MS = 5000;

@Component({
  selector: 'ac-console',
  template: `
    @if (forbidden()) {
      <div class="bay boot-in">
        <h1>⚠ insufficient clearance</h1>
        <p class="label" style="margin-top: 0.6rem">
          this account is not staff. grant is_staff in django admin, then sign back in.
        </p>
      </div>
    } @else {
      <!-- system board -->
      <section class="boot-in">
        <div class="strip">
          <h1>
            system
            @if (system(); as s) {
              <span class="strip__verdict" [class.is-bad]="!s.healthy">
                {{ s.healthy ? '● NOMINAL' : '● DEGRADED' }}
              </span>
            }
          </h1>
          @if (system(); as s) {
            <span class="label">via {{ s.instance }} · live, 5s poll</span>
          }
        </div>
        <div class="lights">
          @for (entry of systemEntries(); track entry.name) {
            <div
              class="light bay"
              [class.light--ok]="['ok', 'eager_mode'].includes(entry.value.status)"
              [class.light--bad]="entry.value.status === 'error'"
            >
              <span class="light__name">{{ entry.name.replaceAll('_', ' ') }}</span>
              <span class="label">
                {{ entry.value.status }}
                @if (entry.value.latency_ms !== undefined) { · {{ entry.value.latency_ms }}ms }
              </span>
            </div>
          }
        </div>
      </section>

      @if (error(); as message) {
        <p class="error-note" role="alert" style="margin-top: 1rem">{{ message }}</p>
      }

      <div class="decks">
        <!-- feature flags -->
        <section class="bay boot-in" style="animation-delay: 80ms">
          <div class="deck-head">
            <h2>feature_flags</h2>
            <span class="label">{{ flags().length }} registered</span>
          </div>

          @for (flag of flags(); track flag.id) {
            <div class="row">
              <button
                type="button"
                class="switch"
                [class.is-on]="flag.enabled"
                role="switch"
                [attr.aria-checked]="flag.enabled"
                [attr.aria-label]="'toggle ' + flag.key"
                (click)="toggleFlag(flag)"
                [disabled]="busy()"
              ></button>
              <div class="row__body">
                <strong>{{ flag.key }}</strong>
                @if (flag.description) {
                  <span class="label">{{ flag.description }}</span>
                }
              </div>
              <button class="btn btn--alarm btn--sm" (click)="removeFlag(flag)" [disabled]="busy()">rm</button>
            </div>
          }

          <form class="adder" (submit)="addFlag($event)">
            <label class="field" style="flex: 1">
              <span class="label">new flag key</span>
              <input type="text" required placeholder="proctoring" [value]="flagKey()" (input)="flagKey.set($any($event.target).value)" />
            </label>
            <button class="btn btn--sm" type="submit" [disabled]="busy()">add</button>
          </form>
        </section>

        <!-- site settings -->
        <section class="bay boot-in" style="animation-delay: 160ms">
          <div class="deck-head">
            <h2>site_settings</h2>
            <span class="label">{{ settings().length }} keys</span>
          </div>

          @for (setting of settings(); track setting.id) {
            <div class="row row--setting">
              <div class="row__body">
                <strong>{{ setting.key }}</strong>
                <span class="label">{{ setting.is_public ? 'public' : 'private' }}</span>
              </div>
              <input
                class="value-input"
                type="text"
                [value]="asText(setting.value)"
                (change)="saveSetting(setting, $any($event.target).value)"
                [disabled]="busy()"
              />
              <button class="btn btn--alarm btn--sm" (click)="removeSetting(setting)" [disabled]="busy()">rm</button>
            </div>
          }

          <form class="adder" (submit)="addSetting($event)">
            <label class="field" style="flex: 1">
              <span class="label">key</span>
              <input type="text" required placeholder="site-name" [value]="settingKey()" (input)="settingKey.set($any($event.target).value)" />
            </label>
            <label class="field" style="flex: 1">
              <span class="label">value</span>
              <input type="text" required placeholder="MentorMind" [value]="settingValue()" (input)="settingValue.set($any($event.target).value)" />
            </label>
            <label class="adder__pub label">
              <input type="checkbox" [checked]="settingPublic()" (change)="settingPublic.set($any($event.target).checked)" />
              public
            </label>
            <button class="btn btn--sm" type="submit" [disabled]="busy()">add</button>
          </form>
        </section>
      </div>
    }
  `,
  styles: `
    .strip {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
      margin-bottom: 1rem;

      h1 {
        font-size: 1.6rem;
        display: flex;
        gap: 1rem;
        align-items: baseline;
      }
    }

    .strip__verdict {
      font-size: 0.85rem;
      color: var(--phosphor);

      &.is-bad { color: var(--alarm); }
    }

    .lights {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
      gap: 0.7rem;
    }

    .light {
      padding: 0.8rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.1rem;
    }

    .light--ok { border-color: rgba(70, 217, 126, 0.5); }
    .light--bad { border-color: var(--alarm); }

    .light__name {
      font-weight: 600;
      font-size: 0.88rem;
    }

    .light--ok .light__name { color: var(--phosphor); }
    .light--bad .light__name { color: var(--alarm); }

    .decks {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.2rem;
      margin-top: 1.6rem;
      align-items: start;
    }

    .deck-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.9rem;

      h2 {
        font-size: 1.1rem;
        color: var(--phosphor);
      }
    }

    .row {
      display: flex;
      align-items: center;
      gap: 0.9rem;
      padding: 0.65rem 0;
      border-bottom: 1px dashed var(--line);
    }

    .row__body {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;

      strong { font-size: 0.9rem; }
    }

    .value-input {
      width: 38%;
      padding: 0.4rem 0.6rem;
      border: 1px solid var(--line-strong);
      border-radius: 4px;
      background: var(--void);
      color: var(--amber);
      font-family: var(--font-mono);
      font-size: 0.8rem;

      &:focus {
        outline: none;
        border-color: var(--amber);
      }
    }

    .adder {
      display: flex;
      align-items: flex-end;
      gap: 0.7rem;
      padding-top: 1rem;
      flex-wrap: wrap;
    }

    .adder__pub {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding-bottom: 0.55rem;
    }

    @media (max-width: 920px) {
      .decks { grid-template-columns: 1fr; }
    }
  `,
})
export class ConsolePage {
  private readonly api = inject(AdminApi);
  private readonly auth = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly system = signal<SystemStatus | null>(null);
  protected readonly flags = signal<FeatureFlag[]>([]);
  protected readonly settings = signal<SiteSetting[]>([]);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly forbidden = signal(false);

  protected readonly flagKey = signal('');
  protected readonly settingKey = signal('');
  protected readonly settingValue = signal('');
  protected readonly settingPublic = signal(true);

  constructor() {
    void this.bootstrap();
    const timer = setInterval(() => void this.pollSystem(), POLL_MS);
    this.destroyRef.onDestroy(() => clearInterval(timer));
  }

  private async bootstrap(): Promise<void> {
    await this.pollSystem();
    try {
      const [flags, settings] = await Promise.all([this.api.flags(), this.api.settings()]);
      this.flags.set(flags);
      this.settings.set(settings);
    } catch (err) {
      if (err instanceof HttpErrorResponse && err.status === 403) {
        this.forbidden.set(true);
      } else {
        this.error.set('could not load flags/settings — is the API up?');
      }
    }
  }

  private async pollSystem(): Promise<void> {
    try {
      this.system.set(await this.api.system());
    } catch (err) {
      if (err instanceof HttpErrorResponse && err.error?.components) {
        this.system.set(err.error as SystemStatus);
      }
    }
  }

  protected systemEntries() {
    const s = this.system();
    return s ? Object.entries(s.components).map(([name, value]) => ({ name, value })) : [];
  }

  private async run(action: () => Promise<unknown>, failure: string): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
      this.flags.set(await this.api.flags());
      this.settings.set(await this.api.settings());
    } catch (err) {
      this.error.set(
        err instanceof HttpErrorResponse && typeof err.error?.detail === 'string'
          ? err.error.detail
          : failure,
      );
    } finally {
      this.busy.set(false);
    }
  }

  protected toggleFlag(flag: FeatureFlag): void {
    void this.run(
      () => this.api.updateFlag(flag.id, { enabled: !flag.enabled }),
      `could not toggle ${flag.key}.`,
    );
  }

  protected addFlag(event: Event): void {
    event.preventDefault();
    const key = this.flagKey().trim();
    if (!key) return;
    void this.run(async () => {
      await this.api.createFlag({ key, enabled: false, description: '' });
      this.flagKey.set('');
    }, 'could not create the flag.');
  }

  protected removeFlag(flag: FeatureFlag): void {
    void this.run(() => this.api.deleteFlag(flag.id), `could not delete ${flag.key}.`);
  }

  protected asText(value: unknown): string {
    return typeof value === 'string' ? value : JSON.stringify(value);
  }

  /** Accept raw JSON when it parses, fall back to storing the string. */
  private parseValue(raw: string): unknown {
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }

  protected saveSetting(setting: SiteSetting, raw: string): void {
    void this.run(
      () => this.api.updateSetting(setting.id, { value: this.parseValue(raw) }),
      `could not update ${setting.key}.`,
    );
  }

  protected addSetting(event: Event): void {
    event.preventDefault();
    const key = this.settingKey().trim();
    if (!key) return;
    void this.run(async () => {
      await this.api.createSetting({
        key,
        value: this.parseValue(this.settingValue()),
        is_public: this.settingPublic(),
      });
      this.settingKey.set('');
      this.settingValue.set('');
    }, 'could not create the setting.');
  }

  protected removeSetting(setting: SiteSetting): void {
    void this.run(() => this.api.deleteSetting(setting.id), `could not delete ${setting.key}.`);
  }
}

import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

interface ComponentStatus {
  status: string;
  detail?: string;
  latency_ms?: number;
}

interface SystemStatus {
  instance: string;
  healthy: boolean;
  components: Record<string, ComponentStatus>;
}

const POLL_MS = 5000;

@Component({
  selector: 'ac-system',
  imports: [RouterLink],
  template: `
    <p class="label"><a routerLink="/" class="crumb">← console</a></p>
    <h1 class="screen-title">
      $ system --watch
      @if (status(); as s) {
        <span class="verdict" [class.verdict--down]="!s.healthy">
          [{{ s.healthy ? 'ALL CLEAR' : 'DEGRADED' }}]
        </span>
      } @else {
        <span class="verdict">[LISTENING…]</span>
      }
    </h1>
    @if (status(); as s) {
      <p class="label">answered by {{ s.instance }} · poll #{{ polls() }} · refreshes every 5s</p>
    }

    @if (error(); as message) {
      <p class="error-note" role="alert">{{ message }}</p>
    }

    @if (status(); as s) {
      <div class="grid">
        @for (entry of entries(); track entry.name) {
          <div
            class="cell"
            [class.cell--ok]="isGood(entry.value.status)"
            [class.cell--err]="entry.value.status === 'error'"
          >
            <span class="cell__light" aria-hidden="true"></span>
            <div class="cell__body">
              <span class="cell__name">{{ label(entry.name) }}</span>
              <span class="label">
                {{ entry.value.status }}
                @if (entry.value.latency_ms !== undefined) {
                  · {{ entry.value.latency_ms }}ms
                }
              </span>
              @if (entry.value.detail) {
                <span class="cell__detail">{{ entry.value.detail }}</span>
              }
            </div>
          </div>
        }
      </div>
    }
  `,
  styles: `
    .crumb {
      color: var(--text-dim);
      text-decoration: none;
      &:hover { color: var(--phosphor); }
    }

    .screen-title {
      font-family: var(--font-mono);
      font-size: clamp(1.4rem, 3.4vw, 2.1rem);
      margin: 0.7rem 0 0.4rem;
    }

    .verdict { color: var(--phosphor); }
    .verdict--down { color: var(--alarm); }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 0.9rem;
      margin-top: 1.5rem;
    }

    .cell {
      display: flex;
      gap: 0.85rem;
      align-items: flex-start;
      padding: 1rem 1.1rem;
      background: var(--bay);
      border: 1px solid var(--line);
      border-radius: 8px;
    }

    .cell--ok { border-color: var(--phosphor); }
    .cell--err { border-color: var(--alarm); }

    .cell__light {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-top: 6px;
      background: var(--text-dim);
      flex-shrink: 0;
    }

    .cell--ok .cell__light {
      background: var(--phosphor);
      box-shadow: 0 0 8px var(--phosphor-dim);
      animation: sys-pulse 2.4s ease-in-out infinite;
    }

    .cell--err .cell__light {
      background: var(--alarm);
      box-shadow: 0 0 8px rgba(255, 107, 94, 0.4);
    }

    @keyframes sys-pulse {
      50% { opacity: 0.45; }
    }

    @media (prefers-reduced-motion: reduce) {
      .cell__light { animation: none; }
    }

    .cell__body {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }

    .cell__name { font-weight: 600; }

    .cell__detail {
      font-size: 0.78rem;
      color: var(--alarm);
      word-break: break-word;
    }
  `,
})
export class SystemPage {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly status = signal<SystemStatus | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly polls = signal(0);

  constructor() {
    void this.poll();
    const timer = setInterval(() => void this.poll(), POLL_MS);
    this.destroyRef.onDestroy(() => clearInterval(timer));
  }

  private async poll(): Promise<void> {
    try {
      const result = await firstValueFrom(this.http.get<SystemStatus>('/api/v1/system/'));
      this.status.set(result);
      this.error.set(null);
    } catch (err) {
      // A 503 still carries the component breakdown — show it.
      if (err instanceof HttpErrorResponse && err.error?.components) {
        this.status.set(err.error as SystemStatus);
        this.error.set(null);
      } else {
        this.error.set('The status endpoint is unreachable — is the API up?');
      }
    } finally {
      this.polls.update((n) => n + 1);
    }
  }

  protected entries(): { name: string; value: ComponentStatus }[] {
    const s = this.status();
    return s ? Object.entries(s.components).map(([name, value]) => ({ name, value })) : [];
  }

  protected isGood(status: string): boolean {
    return ['ok', 'eager_mode'].includes(status);
  }

  protected label(name: string): string {
    return name.replaceAll('_', ' ');
  }
}

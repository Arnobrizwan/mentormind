import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
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
  selector: 'mm-system',
  template: `
    <section class="board rise">
      <p class="mono-label">The Machine Room — live, refreshes every 5s</p>
      <h1>
        System status:
        @if (status(); as s) {
          <em [class.is-down]="!s.healthy">{{ s.healthy ? 'all clear.' : 'degraded.' }}</em>
        } @else {
          <em>listening…</em>
        }
      </h1>
      @if (status(); as s) {
        <p class="board__meta mono-label">
          answered by {{ s.instance }} · poll #{{ polls() }}
        </p>
      }
    </section>

    @if (error(); as message) {
      <p class="error-note" role="alert">{{ message }}</p>
    }

    @if (status(); as s) {
      <div class="grid">
        @for (entry of entries(); track entry.name; let i = $index) {
          <div
            class="cell rise"
            [class.cell--ok]="isGood(entry.value.status)"
            [class.cell--err]="entry.value.status === 'error'"
            [style.animation-delay.ms]="i * 60"
          >
            <span class="cell__light" aria-hidden="true"></span>
            <div class="cell__body">
              <span class="cell__name">{{ label(entry.name) }}</span>
              <span class="mono-label">
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
    .board h1 {
      font-size: clamp(2.2rem, 5vw, 3.6rem);
      margin: 0.8rem 0 0.6rem;

      em {
        font-style: italic;
        color: var(--sage-deep);
      }

      em.is-down {
        color: var(--danger);
      }
    }

    .board__meta {
      margin-bottom: 1.5rem;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 1rem;
      margin-top: 1.6rem;
    }

    .cell {
      display: flex;
      gap: 0.9rem;
      align-items: flex-start;
      padding: 1.1rem 1.2rem;
      background: var(--card);
      border: 1.5px solid var(--line-strong);
      border-radius: 12px;
      box-shadow: var(--shadow-card);
    }

    .cell--ok { border-color: var(--sage); }
    .cell--err { border-color: var(--danger); }

    .cell__light {
      width: 11px;
      height: 11px;
      border-radius: 50%;
      margin-top: 6px;
      background: var(--ink-soft);
      flex-shrink: 0;
    }

    .cell--ok .cell__light {
      background: var(--sage);
      box-shadow: 0 0 0 4px rgba(60, 107, 88, 0.18);
      animation: pulse 2.4s ease-in-out infinite;
    }

    .cell--err .cell__light {
      background: var(--danger);
      box-shadow: 0 0 0 4px rgba(165, 42, 28, 0.2);
    }

    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 0 3px rgba(60, 107, 88, 0.1); }
      50% { box-shadow: 0 0 0 6px rgba(60, 107, 88, 0.25); }
    }

    .cell__body {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }

    .cell__name {
      font-weight: 700;
      font-size: 1.02rem;
    }

    .cell__detail {
      font-size: 0.78rem;
      color: var(--danger);
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

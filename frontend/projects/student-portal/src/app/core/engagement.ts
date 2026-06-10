import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface BadgeEntry {
  key: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  progress: number;
  threshold: number;
  hint: string | null;
}

export interface EngagementMe {
  points_total: number;
  streak: number;
  daily_login_claimed: boolean;
  badges: BadgeEntry[];
  recent_events: { action: string; points: number; at: string }[];
}

@Injectable({ providedIn: 'root' })
export class EngagementApi {
  private readonly http = inject(HttpClient);

  readonly me = signal<EngagementMe | null>(null);

  async refresh(): Promise<void> {
    this.me.set(
      await firstValueFrom(this.http.get<EngagementMe>('/api/v1/engagement/me/')).catch(
        () => null,
      ),
    );
  }

  async claimDailyLogin(): Promise<{ claimed: boolean; points: number }> {
    const result = await firstValueFrom(
      this.http.post<{ claimed: boolean; points: number; points_total: number }>(
        '/api/v1/engagement/daily-login/',
        {},
      ),
    );
    await this.refresh();
    return result;
  }
}

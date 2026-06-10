import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface FeatureFlag {
  id: number;
  key: string;
  enabled: boolean;
  description: string;
  updated_at: string;
}

export interface SiteSetting {
  id: number;
  key: string;
  value: unknown;
  is_public: boolean;
  description: string;
  updated_at: string;
}

export interface ComponentStatus {
  status: string;
  detail?: string;
  latency_ms?: number;
}

export interface SystemStatus {
  instance: string;
  healthy: boolean;
  components: Record<string, ComponentStatus>;
}

@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);

  system(): Promise<SystemStatus> {
    return firstValueFrom(this.http.get<SystemStatus>('/api/v1/system/'));
  }

  flags(): Promise<FeatureFlag[]> {
    return firstValueFrom(this.http.get<FeatureFlag[]>('/api/v1/flags/manage/'));
  }

  createFlag(data: Partial<FeatureFlag>): Promise<FeatureFlag> {
    return firstValueFrom(this.http.post<FeatureFlag>('/api/v1/flags/manage/', data));
  }

  updateFlag(id: number, data: Partial<FeatureFlag>): Promise<FeatureFlag> {
    return firstValueFrom(this.http.patch<FeatureFlag>(`/api/v1/flags/manage/${id}/`, data));
  }

  deleteFlag(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/flags/manage/${id}/`));
  }

  settings(): Promise<SiteSetting[]> {
    return firstValueFrom(this.http.get<SiteSetting[]>('/api/v1/settings/manage/'));
  }

  createSetting(data: Partial<SiteSetting>): Promise<SiteSetting> {
    return firstValueFrom(this.http.post<SiteSetting>('/api/v1/settings/manage/', data));
  }

  updateSetting(id: number, data: Partial<SiteSetting>): Promise<SiteSetting> {
    return firstValueFrom(
      this.http.patch<SiteSetting>(`/api/v1/settings/manage/${id}/`, data),
    );
  }

  deleteSetting(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/settings/manage/${id}/`));
  }
}

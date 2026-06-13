import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

interface PushConfig {
  enabled: boolean;
  public_key: string;
  subscribed: boolean;
}

/** VAPID application-server key is base64url; the browser wants a BufferSource.
 * Backed by an explicit ArrayBuffer so the type is not the SharedArrayBuffer
 * union that pushManager.subscribe() rejects. */
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
  const buffer = new ArrayBuffer(raw.length);
  const out = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

/**
 * PWA study reminders over Web Push. The whole feature is gated on the
 * server reporting `enabled` (VAPID keys configured) AND the browser
 * supporting Notification + ServiceWorker + PushManager — otherwise the
 * profile opt-in stays hidden.
 */
@Injectable({ providedIn: 'root' })
export class PushApi {
  private readonly http = inject(HttpClient);

  /** Server has VAPID keys AND this browser can do push. */
  readonly available = signal(false);
  readonly subscribed = signal(false);
  private publicKey = '';

  get supported(): boolean {
    return (
      typeof window !== 'undefined' &&
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  get blocked(): boolean {
    return this.supported && Notification.permission === 'denied';
  }

  async refresh(): Promise<void> {
    if (!this.supported) {
      this.available.set(false);
      return;
    }
    const config = await firstValueFrom(
      this.http.get<PushConfig>('/api/v1/notifications/push/config/'),
    ).catch(() => null);
    if (!config?.enabled) {
      this.available.set(false);
      return;
    }
    this.publicKey = config.public_key;
    this.available.set(true);
    // Trust the live browser subscription over the server's view.
    const sub = await this.currentSubscription();
    this.subscribed.set(!!sub || config.subscribed);
  }

  private async currentSubscription(): Promise<PushSubscription | null> {
    const reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  }

  /** Ask permission, subscribe in the browser, register with the backend. */
  async enable(): Promise<void> {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') throw new Error('permission-denied');

    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(this.publicKey),
    });
    await firstValueFrom(
      this.http.post('/api/v1/notifications/push/subscribe/', sub.toJSON()),
    );
    this.subscribed.set(true);
  }

  async disable(): Promise<void> {
    const sub = await this.currentSubscription();
    const endpoint = sub?.endpoint;
    if (sub) await sub.unsubscribe();
    // Only tell the backend to remove THIS device's row. If the live
    // subscription is already gone we have no endpoint to name — skip the
    // call (the server prunes dead rows on the next send) rather than risk a
    // body without an endpoint, which the API now rejects anyway.
    if (endpoint) {
      await firstValueFrom(
        this.http.request('delete', '/api/v1/notifications/push/subscribe/', {
          body: { endpoint },
        }),
      ).catch(() => undefined);
    }
    this.subscribed.set(false);
  }
}

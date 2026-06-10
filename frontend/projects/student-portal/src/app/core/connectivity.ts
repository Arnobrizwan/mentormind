import { Injectable, signal } from '@angular/core';

/**
 * Online/offline state for the offline banner. Uses Capacitor's Network
 * plugin on native (iOS/Android) and the browser's online/offline events
 * on the web — same signal either way. The tutor and catalog keep working
 * from cache offline; this just surfaces the state to the user.
 */
@Injectable({ providedIn: 'root' })
export class Connectivity {
  readonly online = signal(true);

  constructor() {
    void this.init();
  }

  private async init(): Promise<void> {
    // Web fallback — always available.
    if (typeof navigator !== 'undefined' && 'onLine' in navigator) {
      this.online.set(navigator.onLine);
      window.addEventListener('online', () => this.online.set(true));
      window.addEventListener('offline', () => this.online.set(false));
    }

    // Native: Capacitor Network plugin gives accurate cellular/wifi state.
    try {
      const { Network } = await import('@capacitor/network');
      const status = await Network.getStatus();
      this.online.set(status.connected);
      await Network.addListener('networkStatusChange', (s) =>
        this.online.set(s.connected),
      );
    } catch {
      // Plugin absent on plain web build — the browser events above suffice.
    }
  }
}

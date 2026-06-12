import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Native shell config for the MentorMind student app (iOS + Android).
 * `webDir` points at the student-portal production build; `npx cap sync`
 * copies it into the native projects.
 *
 * For live-reload against a running API during development, set
 * server.url to your machine's LAN address (see ionic/capacitor docs).
 *
 * API origin on native: the web view runs from capacitor://localhost, so
 * relative /api/... calls cannot reach the backend. The app reads
 * `window.MM_API_BASE_URL` at boot (see student-portal
 * src/app/core/api-base-url.ts) — set it to your HTTPS API origin via a
 * script tag in the built index.html before `cap sync`, e.g.
 *   <script>window.MM_API_BASE_URL = 'https://api.mentormind.dev';</script>
 */
const config: CapacitorConfig = {
  appId: 'dev.mentormind.app',
  appName: 'MentorMind',
  webDir: 'dist/student-portal/browser',
  backgroundColor: '#ffffff',
  ios: {
    contentInset: 'always',
  },
  plugins: {
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#ff5ca3',
    },
  },
};

export default config;

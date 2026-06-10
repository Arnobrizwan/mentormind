import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Native shell config for the MentorMind student app (iOS + Android).
 * `webDir` points at the student-portal production build; `npx cap sync`
 * copies it into the native projects.
 *
 * For live-reload against a running API during development, set
 * server.url to your machine's LAN address (see ionic/capacitor docs).
 */
const config: CapacitorConfig = {
  appId: 'dev.mentormind.app',
  appName: 'MentorMind',
  webDir: 'dist/student-portal/browser',
  backgroundColor: '#ffffff',
  android: {
    allowMixedContent: true,
  },
  ios: {
    contentInset: 'always',
  },
  plugins: {
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#e6007e',
    },
  },
};

export default config;

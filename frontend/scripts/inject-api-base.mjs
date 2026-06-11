/**
 * Injects the API origin into the built student-portal index.html for
 * native (Capacitor) builds — the WebView loads from capacitor://localhost,
 * so relative /api calls need window.MM_API_BASE_URL set before Angular
 * boots (see src/app/core/api-base-url.ts).
 *
 * Usage (before `cap sync`):
 *   MM_API_BASE_URL=https://api.mentormind.dev node scripts/inject-api-base.mjs
 *
 * No-op with a warning when MM_API_BASE_URL is unset, so plain web builds
 * are unaffected.
 */
import { readFileSync, writeFileSync } from 'node:fs';

const INDEX = new URL('../dist/student-portal/browser/index.html', import.meta.url);
const origin = process.env.MM_API_BASE_URL?.trim();

if (!origin) {
  console.warn(
    '[inject-api-base] MM_API_BASE_URL not set — native app will use ' +
      'same-origin /api calls, which do not work from capacitor://localhost.',
  );
  process.exit(0);
}
if (!/^https?:\/\//.test(origin)) {
  console.error(`[inject-api-base] MM_API_BASE_URL must be http(s): ${origin}`);
  process.exit(1);
}

let html = readFileSync(INDEX, 'utf8');
// Idempotent: replace an existing injection or add a fresh one.
html = html.replace(/<script data-mm-api>.*?<\/script>/s, '');
const tag = `<script data-mm-api>window.MM_API_BASE_URL=${JSON.stringify(origin)};</script>`;
html = html.replace('<head>', `<head>${tag}`);
writeFileSync(INDEX, html);
console.log(`[inject-api-base] API origin set to ${origin}`);

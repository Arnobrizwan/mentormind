import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const here = dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 2245, height: 3179 }, deviceScaleFactor: 1 });
await page.goto('file://' + join(here, 'poster.html'));
await page.waitForTimeout(1500); // let fonts settle
await page.screenshot({ path: join(here, 'MentorMinds-DIGITEX2026-poster.png'), clip: { x: 0, y: 0, width: 2245, height: 3179 } });
await browser.close();
console.log('rendered MentorMinds-DIGITEX2026-poster.png');

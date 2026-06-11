import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Crop just the phone hero out of the poster so it can be dropped into the
// editable .pptx as a polished image (it can't be rebuilt as native shapes).
const here = dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 2245, height: 3179 }, deviceScaleFactor: 2 });
await page.goto('file://' + join(here, 'poster.html?static=1'));
await page.waitForTimeout(1200);
await page.screenshot({
  path: join(here, 'phone.png'),
  clip: { x: 838, y: 1220, width: 585, height: 1018 },
});
await browser.close();
console.log('rendered phone.png');

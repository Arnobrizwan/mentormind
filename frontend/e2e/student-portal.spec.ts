import { test, expect } from '@playwright/test';

test.describe('Student portal smoke', () => {
  test('catalog page renders', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('banner').getByRole('link', { name: /Mentor/i })).toBeVisible();
    await expect(page.getByRole('main').getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('auth page is reachable', async ({ page }) => {
    await page.goto('/auth');
    await expect(page.getByRole('main').getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible();
  });

  test('service worker registers in production build', async ({ page, baseURL }) => {
    await page.goto('/');
    const registered = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) return false;
      const reg = await navigator.serviceWorker.getRegistration();
      return !!reg;
    });
    // SW only ships in production builds with sw.js in /public.
    if (baseURL?.includes('4173')) {
      expect(registered).toBe(true);
    }
  });
});

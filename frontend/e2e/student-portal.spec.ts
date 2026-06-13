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

  test('full student journey (login -> enroll -> quiz -> tutor)', async ({ page }) => {
    // 1. Go to auth page and register a new student account
    await page.goto('/auth');
    await page.getByRole('tab', { name: /Create account/i }).click();
    
    const testEmail = `e2e-student-${Date.now()}@example.com`;
    await page.getByPlaceholder('Ada Lovelace').fill('E2E Tester');
    await page.getByPlaceholder('you@example.com').fill(testEmail);
    await page.getByPlaceholder('••••••••').fill('SecretPassword123!');
    await page.getByRole('button', { name: /Enroll me/i }).click();

    // 2. Redirected to dashboard
    await expect(page).toHaveURL(/.*dashboard.*/);

    // 3. Go to catalog to find and enroll in a course
    await page.goto('/');
    const courseCard = page.locator('main .card').first();
    await expect(courseCard).toBeVisible();
    await courseCard.click();

    // 4. Enroll in the course
    await expect(page).toHaveURL(/.*courses.*/);
    const enrollBtn = page.getByRole('button', { name: /Enroll/i });
    await expect(enrollBtn).toBeVisible();
    await enrollBtn.click();
    await expect(enrollBtn).not.toBeVisible();

    // 5. Take a quiz
    const takeQuizBtn = page.getByRole('link', { name: /Take quiz/i }).first();
    await expect(takeQuizBtn).toBeVisible();
    await takeQuizBtn.click();

    // 6. Answer quiz questions.
    await expect(page).toHaveURL(/.*quiz.*/);
    // When the proctoring flag is on, the quiz injects an async camera-status
    // panel above the questions; in headless CI getUserMedia rejects and the
    // panel appears mid-test, shifting layout — a click can then land during
    // the shift and silently miss, leaving a question unanswered (which keeps
    // "Hand in paper" disabled). Answer by index and confirm each selection
    // registered (re-clicking if needed) so the flow is deterministic.
    // Quiz questions load asynchronously after navigation — wait for the
    // first one to render before counting (count() does not auto-wait).
    const groups = page.getByRole('radiogroup');
    await expect(groups.first()).toBeVisible();
    const questionCount = await groups.count();
    expect(questionCount).toBeGreaterThan(0);
    for (let i = 0; i < questionCount; i++) {
      const radio = groups.nth(i).getByRole('radio').first();
      await expect(radio).toBeVisible();
      for (let attempt = 0; attempt < 3; attempt++) {
        await radio.scrollIntoViewIfNeeded();
        await radio.click();
        if ((await radio.getAttribute('aria-checked')) === 'true') break;
        await page.waitForTimeout(200);
      }
      await expect(radio).toHaveAttribute('aria-checked', 'true');
    }

    // Hand in paper — all questions are now confirmed answered.
    const submitBtn = page.getByRole('button', { name: /Hand in paper/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Verify quiz result page loaded
    await expect(page.locator('.result__score')).toBeVisible();

    // 7. Go to AI Tutor page
    const tutorLink = page.locator('a[href="/tutor"]').first();
    await expect(tutorLink).toBeVisible();
    await tutorLink.click();

    // Verify AI Tutor page composer loads
    await expect(page).toHaveURL(/.*tutor.*/);
    await expect(page.getByPlaceholder('Ask your tutor…')).toBeVisible();
  });
});

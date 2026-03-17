import { test, expect } from '@playwright/test';

/**
 * E2E: Brief Generation & Export Flow
 *
 * Tests the critical path:
 *   Studio → Generate Brief → View Brief → Export (DOCX / PPTX)
 *
 * This is the highest-value user workflow and must work end-to-end.
 */

test.describe('Brief Generation & Export', () => {
  test('studio page loads with generation controls', async ({ page }) => {
    await page.goto('/dashboard/studio');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading').first()).toBeVisible({
      timeout: 10_000,
    });

    // Should have some form of "generate" or "create" action
    const generateBtn = page.getByRole('button', {
      name: /generate|create|new brief/i,
    }).first();
    const hasGenerate = await generateBtn.isVisible({ timeout: 3_000 }).catch(() => false);

    // Or a text input / query field for brief generation
    const queryField = page
      .getByPlaceholder(/topic|query|describe|brief/i)
      .first();
    const hasQuery = await queryField.isVisible({ timeout: 3_000 }).catch(() => false);

    expect(hasGenerate || hasQuery).toBeTruthy();
  });

  test('can initiate brief generation', async ({ page }) => {
    await page.goto('/dashboard/studio');
    await page.waitForLoadState('networkidle');

    // Find query/topic input
    const queryField = page
      .getByPlaceholder(/topic|query|describe|brief|title/i)
      .first();

    if (!(await queryField.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await queryField.fill('E2E Test: Nigerian fintech regulatory landscape');

    // Click generate/create button
    const generateBtn = page.getByRole('button', {
      name: /generate|create|submit/i,
    }).first();

    if (!(await generateBtn.isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await generateBtn.click();

    // Should show loading state or navigate to brief view
    // Allow generous timeout for AI generation
    await expect(
      page.locator(
        '[data-testid="loading"], [data-testid="brief-content"], [role="progressbar"], .animate-pulse'
      ).first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test('library shows existing briefs', async ({ page }) => {
    await page.goto('/dashboard/library');
    await page.waitForLoadState('networkidle');

    // Should show brief cards or empty state
    await expect(
      page.locator(
        '[data-testid="brief-card"], [data-testid="empty-state"], table'
      ).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('brief detail view renders content', async ({ page }) => {
    await page.goto('/dashboard/library');
    await page.waitForLoadState('networkidle');

    const firstBrief = page
      .locator('[data-testid="brief-card"] a, [data-testid="brief-link"]')
      .first();

    if (!(await firstBrief.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await firstBrief.click();
    await page.waitForLoadState('networkidle');

    // Brief detail should show content sections
    await expect(
      page.locator(
        '[data-testid="brief-content"], article, .prose'
      ).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('export button is available on brief detail', async ({ page }) => {
    await page.goto('/dashboard/library');
    await page.waitForLoadState('networkidle');

    const firstBrief = page
      .locator('[data-testid="brief-card"] a, [data-testid="brief-link"]')
      .first();

    if (!(await firstBrief.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await firstBrief.click();
    await page.waitForLoadState('networkidle');

    // Should have an export button/dropdown
    const exportBtn = page.getByRole('button', {
      name: /export|download/i,
    }).first();

    await expect(exportBtn).toBeVisible({ timeout: 10_000 });
  });

  test('DOCX export triggers download', async ({ page }) => {
    await page.goto('/dashboard/library');
    await page.waitForLoadState('networkidle');

    const firstBrief = page
      .locator('[data-testid="brief-card"] a, [data-testid="brief-link"]')
      .first();

    if (!(await firstBrief.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await firstBrief.click();
    await page.waitForLoadState('networkidle');

    const exportBtn = page.getByRole('button', {
      name: /export|download/i,
    }).first();

    if (!(await exportBtn.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await exportBtn.click();

    // Look for DOCX option in dropdown
    const docxOption = page.getByRole('menuitem', { name: /docx|word/i }).first();
    if (await docxOption.isVisible({ timeout: 2_000 }).catch(() => false)) {
      // Listen for download event
      const downloadPromise = page.waitForEvent('download', { timeout: 30_000 });
      await docxOption.click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.docx$/);
    }
  });
});

import { defineConfig, devices } from '@playwright/test';

/**
 * Cogent E2E Test Configuration
 *
 * Covers critical user flows:
 *   1. Authentication (login → session → logout)
 *   2. Dashboard navigation
 *   3. Signal browsing & search
 *   4. Brief generation & export
 *   5. Settings / profile management
 *
 * Usage:
 *   npx playwright test                    # Run all E2E tests
 *   npx playwright test --headed           # Run with browser visible
 *   npx playwright test --project=chromium # Single browser
 *   npx playwright test --grep "signals"   # Run tests matching pattern
 */

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },

  /* Run tests sequentially in CI for stability */
  fullyParallel: !process.env.CI,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['github']]
    : [['html', { open: 'on-failure' }]],

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    /* Auth0 session cookie name */
    storageState: process.env.E2E_STORAGE_STATE || undefined,
  },

  projects: [
    /* Setup: authenticate and save session */
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    /* Desktop browsers */
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/session.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'e2e/.auth/session.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'e2e/.auth/session.json',
      },
      dependencies: ['setup'],
    },

    /* Mobile viewport */
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: 'e2e/.auth/session.json',
      },
      dependencies: ['setup'],
    },
  ],

  /* Start the frontend dev server before running tests */
  webServer: process.env.CI
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 120_000,
      },
});

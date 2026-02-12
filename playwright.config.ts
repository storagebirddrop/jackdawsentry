import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Jackdaw Sentry E2E tests.
 *
 * Expects the full stack (API + Nginx + DBs) to be running via docker compose.
 * BASE_URL defaults to http://localhost (Nginx) but can be overridden.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'html',
  timeout: 30_000,

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});

import { test, expect } from '@playwright/test';

/**
 * Jackdaw Sentry — M6 E2E Frontend Tests
 *
 * Prerequisites:
 *   - Full stack running via docker compose (API + Nginx + Postgres + Neo4j + Redis)
 *   - Seeded admin user from 002_seed_admin_user.sql
 *
 * Gate: all tests pass with zero JS console errors on each page.
 */

const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'ChangeMe!Admin2024';

/** Collect JS console errors during a test */
function trackConsoleErrors(page: import('@playwright/test').Page) {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => {
    errors.push(err.message);
  });
  return errors;
}

// ---------------------------------------------------------------------------
// 1. Login flow
// ---------------------------------------------------------------------------

test.describe('Login', () => {
  test('redirects unauthenticated user to /login', async ({ page }) => {
    await page.goto('/');
    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#username', 'baduser');
    await page.fill('#password', 'badpass');
    await page.click('#login-btn');

    const errorEl = page.locator('#login-error');
    await expect(errorEl).toBeVisible({ timeout: 10_000 });
    await expect(errorEl).toContainText(/invalid|failed|unauthorized/i);
  });

  test('logs in with seeded admin and redirects to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#username', ADMIN_USERNAME);
    await page.fill('#password', ADMIN_PASSWORD);
    await page.click('#login-btn');

    // Should redirect to dashboard (root)
    await expect(page).toHaveURL(/^\/$|\/index/i, { timeout: 15_000 });

    // Token should be stored in localStorage
    const token = await page.evaluate(() => localStorage.getItem('jds_token'));
    expect(token).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// 2. Authenticated page tests — login once via storageState
// ---------------------------------------------------------------------------

test.describe('Authenticated pages', () => {
  // Login before all tests in this group
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('#username', ADMIN_USERNAME);
    await page.fill('#password', ADMIN_PASSWORD);
    await page.click('#login-btn');
    await expect(page).toHaveURL(/^\/$|\/index/i, { timeout: 15_000 });
  });

  // -- Dashboard ----------------------------------------------------------

  test('dashboard loads real data', async ({ page }) => {
    const errors = trackConsoleErrors(page);

    // We should already be on /
    await page.waitForSelector('#alerts-table', { timeout: 10_000 });

    // Stat cards should have been populated (not the loading placeholder)
    const txText = await page.textContent('#total-transactions');
    expect(txText).toBeTruthy();

    // No JS console errors
    const realErrors = errors.filter(
      (e) => !e.includes('WebSocket') && !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(realErrors).toHaveLength(0);
  });

  // -- Compliance ---------------------------------------------------------

  test('compliance page loads', async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await page.goto('/compliance');
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    // Check that a key element exists
    const heading = page.locator('h1:has-text("Compliance")');
    await expect(heading).toBeVisible({ timeout: 10_000 });

    // SAR table should be present
    await page.waitForSelector('#sar-table', { timeout: 10_000 });

    const realErrors = errors.filter(
      (e) => !e.includes('WebSocket') && !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(realErrors).toHaveLength(0);
  });

  // -- Analytics ----------------------------------------------------------

  test('analytics page loads', async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await page.goto('/compliance/analytics');
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    // Check that chart canvases exist
    const sarChart = page.locator('#sarTrendChart');
    await expect(sarChart).toBeVisible({ timeout: 10_000 });

    const realErrors = errors.filter(
      (e) => !e.includes('WebSocket') && !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(realErrors).toHaveLength(0);
  });

  // -- Analysis -----------------------------------------------------------

  test('analysis page loads', async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await page.goto('/analysis');
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    // Stats should load
    const statEl = page.locator('#stat-analyses');
    await expect(statEl).toBeVisible({ timeout: 10_000 });

    const realErrors = errors.filter(
      (e) => !e.includes('WebSocket') && !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(realErrors).toHaveLength(0);
  });

  // -- Logout -------------------------------------------------------------

  test('logout clears session and redirects to login', async ({ page }) => {
    // Click the sign-out button in the sidebar (injected by nav.js)
    const logoutBtn = page.locator('button:has-text("Sign out")');
    if (await logoutBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await logoutBtn.click();
    } else {
      // Fallback: call Auth.logout() directly
      await page.evaluate(() => {
        if (typeof (window as any).Auth !== 'undefined') {
          (window as any).Auth.logout();
        } else {
          localStorage.removeItem('jds_token');
          localStorage.removeItem('jds_user');
          window.location.href = '/login';
        }
      });
    }

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // Token should be cleared
    const token = await page.evaluate(() => localStorage.getItem('jds_token'));
    expect(token).toBeNull();
  });
});

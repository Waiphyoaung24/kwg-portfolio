import assert from 'node:assert/strict';
import contract from '../ops/trading/fixtures/status-contract.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test.beforeEach(async ({ browser }) => {
  await browser.route('**/api/trading/**', route => {
    assert.equal(route.request.method, 'GET', 'Page test must never submit a trading control request');
    return route.fallback();
  });
});

test('vault trading renders the shared fresh-status contract', async ({ app, screen }) => {
  await app.open('/vault/trading');
  await expect(screen.getByRole('heading', 'Live demo feed')).toBeVisible();
  await expect(screen.getByText('4100.25 / 4100.50')).toBeVisible();
  await expect(screen.getByText('Connected to demo')).toBeVisible();
  await expect(screen.getByText('Long setup')).toBeVisible();
  await expect(screen.getByRole('main')).toContainText(/Signals do not place orders/);
  await app.screenshot('vault-trading-fresh');
});

for (const status of [401, 302]) {
  test(`status ${status} clears previously shown prices and requests sign-in`, async ({ app, screen, browser }) => {
    await app.open('/vault/trading');
    await expect(screen.getByText('4100.25 / 4100.50')).toBeVisible();
    await browser.route('**/api/trading/status', route => route.fulfill({
      status, headers: status === 302 ? { Location: '/fixture-sign-in' } : {}, body: '',
    }));
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('#state')).toHaveText(/sign-in required/i);
    await expect(browser.locator('#price')).toHaveText('—');
    await expect(screen.getByRole('link', 'Sign in to status')).toBeVisible();
    await expect(browser.locator('#prepare-trade')).toBeDisabled();
    await expect(browser.locator('#start-trade')).toBeDisabled();
  });
}

test('manual pending order is shown without implying execution is off', async ({ app, screen, browser }) => {
  const item = contract.cases.find(item => item.name === 'manual demo execution pending')!;
  const payload = structuredClone(item.payload);
  const shift = Math.floor(Date.now() / 1000) - contract.now;
  payload.checked_at += shift;
  payload.health.sampled_at += shift;
  payload.execution!.updated_at += shift;
  await browser.route('**/api/trading/status', route => route.fulfill({ body: JSON.stringify(payload), contentType: 'application/json' }));
  await app.open('/vault/trading');
  await screen.getByText('Technical details', { exact: false }).tap();
  await expect(browser.locator('#strategy')).toHaveText('Signals only · manual demo order active');
  await screen.getByText('Manual demo order controls').tap();
  await expect(browser.locator('#execution-state')).toHaveText(/pending/i);
  await expect(browser.locator('#prepare-trade')).toBeDisabled();
});

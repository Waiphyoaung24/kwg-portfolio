import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('pilot shows results and requests pause without reaching a broker', async ({ app, screen, browser }) => {
  const payload = structuredClone(fixture);
  const shift = Math.floor(Date.now() / 1000) - payload.checked_at;
  payload.checked_at += shift;
  payload.health.sampled_at += shift;
  payload.health.tick_time += shift;
  payload.health.tick_time_msc += shift * 1000;
  payload.pilot.updated_at += shift;
  payload.pilot.started_at += shift;
  payload.pilot.ends_at += shift;
  for (const trade of payload.pilot.recent_trades) {
    trade.opened_at += shift;
    trade.closed_at += shift;
  }
  payload.execution.updated_at += shift;
  let paused = false;
  await browser.route('**/api/trading/**', route => {
    if (route.request.method === 'POST') {
      assert.ok(route.request.url.endsWith('/api/trading/pilot-pause'));
      paused = true;
      payload.pilot.status = 'paused';
      payload.pilot.reason = 'Paused by owner';
      return route.fulfill({ status: 202, contentType: 'application/json', body: '{"status":"pause_requested"}' });
    }
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await app.open('/vault/trading');
  await expect(screen.getByRole('heading', 'Autonomous demo pilot')).toBeVisible();
  await expect(browser.locator('#pilot-realized')).toHaveText('-4.50 USD');
  await expect(browser.locator('#manual-controls')).toBeHidden();
  await screen.getByRole('button', 'Pause new entries').tap();
  await expect(browser.locator('#pilot-state')).toHaveText('PAUSED');
  assert.equal(paused, true);
  await app.screenshot('autonomous-demo-pilot-paused');
  await browser.route('**/api/trading/status', route => route.fulfill({ status: 401, body: '' }));
  await screen.getByRole('button', 'Refresh status').tap();
  await expect(browser.locator('#pilot-realized')).toHaveText('—');
  await expect(browser.locator('#pilot-pause')).toBeDisabled();
  await expect(browser.locator('#price')).toHaveText('—');
});

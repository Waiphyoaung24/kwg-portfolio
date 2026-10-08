import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

for (const width of [1280, 390]) {
  test(`console charts, replay isolation and stale clearing at ${width}px`, async ({ app, screen, browser }) => {
    await browser.setViewport({ width, height: 900 });
    const payload = structuredClone(fixture);
    const now = Math.floor(Date.now() / 1000);
    const shift = now - fixture.checked_at;
    payload.pilot.started_at += shift;
    payload.pilot.ends_at += shift;
    for (const trade of payload.pilot.recent_trades) {
      trade.opened_at += shift;
      trade.closed_at += shift;
    }
    let request = 0;
    await browser.route('**/api/trading/**', route => {
      assert.equal(route.request.method, 'GET', 'Console test must not send orders or pause the pilot');
      const at = Math.floor(Date.now() / 1000);
      payload.checked_at = payload.health.sampled_at = payload.pilot.updated_at = payload.execution.updated_at = at;
      payload.health.tick_time = now - 8 + Math.min(request++, 8);
      payload.health.tick_time_msc = payload.health.tick_time * 1000;
      payload.health.bid = 4100.25 + request * .05;
      payload.health.ask = payload.health.bid + .25;
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
    });
    await app.open('/vault/trading');
    await expect(screen.getByRole('tab', 'Live quotes')).toBeVisible();
    await expect(browser.locator('#pilot-intent')).toHaveText('Managing a demo trade');
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('.trading-charts__bid')).toBeVisible();
    await expect(browser.locator('#replay-play')).toBeHidden();
    const layout = await browser.evaluate(() => ({ height: document.documentElement.scrollHeight, width: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert.ok(layout.width <= layout.viewport, 'Console must not overflow horizontally');
    await browser.setViewport({ width, height: layout.height });
    await browser.evaluate(() => { window.scrollTo(0, 0); return null; });
    await app.screenshot(`console-quotes-${width}`);
    await browser.setViewport({ width, height: 900 });
    await screen.getByRole('tab', 'Live quotes').press('ArrowRight');
    await expect(screen.getByRole('heading', 'Recent trade results')).toBeVisible();
    await expect(browser.locator('.trading-charts__trades')).toContainText('-4.50 USD');
    await screen.getByRole('tab', 'Synthetic replay').tap();
    await expect(browser.locator('#replay-play')).toBeVisible();
    await screen.getByRole('button', 'Next candle').tap();
    await expect(browser.locator('#replay-progress')).toContainText('Candle 2');
    await screen.getByRole('tab', 'Live quotes').tap();
    await browser.route('**/api/trading/status', route => route.fulfill({ status: 401, body: '' }));
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('.trading-charts__bid')).toBeHidden();
    await expect(browser.locator('#price')).toHaveText('—');
    await expect(browser.locator('#pilot-pause')).toBeDisabled();
    await screen.getByRole('tab', 'Trade results').tap();
    await expect(screen.getByRole('heading', 'No current trade report')).toBeVisible();
  });
}

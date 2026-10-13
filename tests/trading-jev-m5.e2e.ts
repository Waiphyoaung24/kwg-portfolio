import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

for (const width of [1280, 375]) {
  test(`Gold M5 Jev scorecard at ${width}px`, async ({ app, screen, browser }) => {
    await browser.setViewport({ width, height: 900 });
    const payload = structuredClone(fixture) as any;
    const shift = Math.floor(Date.now() / 1000) - fixture.checked_at;
    payload.pilot.started_at += shift;
    payload.pilot.ends_at += shift;
    payload.pilot.recent_trades = [];
    Object.assign(payload.pilot, { strategy: 'gold-ema-v1-m5-trend-jev', jev_mode: 'shadow' });
    await browser.route('**/api/trading/**', route => {
      assert.equal(route.request.method, 'GET', 'Scorecard test must never submit a trading request');
      if (!route.request.url.includes('/api/trading/status')) return route.fallback();
      const at = Math.floor(Date.now() / 1000);
      payload.checked_at = payload.health.sampled_at = payload.pilot.updated_at = payload.execution.updated_at = at;
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
    });
    await app.open('/vault/trading');
    await expect(screen.getByRole('heading', 'Jev shadow scorecard')).toBeVisible();
    await expect(browser.locator('#jev-m5-mode')).toHaveText('Shadow');
    await expect(browser.locator('#jev-m5-kept')).toHaveText('↑ +$2.25 · 6 trades');
    await expect(browser.locator('#jev-m5-all')).toHaveText('↓ −$1.50 · 9 trades');
    await expect(browser.locator('#jev-m5-verdict')).toHaveText('Gate not met');
    await expect(browser.locator('#jev-m5-checks li')).toHaveCount(3);
    await expect(browser.locator('#jev-m5-checks')).toContainText('Bad receipts 3/12 reach the 20% limit');
    await expect(browser.locator('#jev-m5-budget')).toHaveText('$5.00 of $5.00 left');
    await expect(browser.locator('#jev-m5-summary')).toContainText('Synthetic local preview');
    await expect(screen.getByText('Demo only. Jev can block an entry; it never opens one.')).toBeVisible();
    const summary = browser.locator('#jev-m5-panel summary');
    await summary.press('Enter');
    await expect(browser.locator('#jev-m5-receipts')).toHaveText('OK 9 · Timeout 1 · Unavailable 0 · Budget exhausted 0 · Invalid 0 · Missing 1 · Late 0');
    await expect(browser.locator('#jev-m5-counts')).toHaveText('Pending 1 · No Jev state 1 · Closed without P/L 1');
    const focus = await browser.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      const style = getComputedStyle(el);
      return { inPanel: !!el.closest('#jev-m5-panel'), visible: el.matches(':focus-visible'),
        outline: style.outlineStyle, width: parseFloat(style.outlineWidth), height: el.getBoundingClientRect().height };
    });
    assert.ok(focus.inPanel && focus.visible && focus.outline !== 'none' && focus.width > 0, `Keyboard focus must be visible: ${JSON.stringify(focus)}`);
    assert.ok(focus.height >= 44, 'Disclosure needs a 44px touch target');
    const layout = await browser.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert.ok(layout.width <= layout.viewport, 'Scorecard must not overflow horizontally');
    await app.screenshot(`jev-m5-scorecard-${width}`);
  });
}

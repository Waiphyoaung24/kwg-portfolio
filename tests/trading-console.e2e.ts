import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

for (const width of [1280, 390]) {
  test(`console charts and stale clearing at ${width}px`, async ({ app, screen, browser }) => {
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
    await expect(screen.getByRole('heading', 'Open demo position')).toBeVisible();
    await expect(browser.locator('#position-side')).toHaveText('BUY');
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('.trading-charts__chart')).toBeVisible();
    await expect(browser.locator('#position-rail')).toHaveAttribute('aria-valuetext', /of the way from entry to/);
    const views = await browser.evaluate(() => Array.from(document.querySelectorAll('[role="tab"]'), tab => tab.textContent?.trim()));
    assert.deepEqual(views, ['Live quotes', 'Trade results']);
    const layout = await browser.evaluate(() => ({ height: document.documentElement.scrollHeight, width: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert.ok(layout.width <= layout.viewport, 'Console must not overflow horizontally');
    const controls = await browser.evaluate(() => Array.from(document.querySelectorAll('.btn, .desk-segment a, .desk-nav__links a, .desk-disclosure summary'))
      .filter(el => el.getClientRects().length > 0)
      .map(el => ({ label: el.textContent?.trim(), height: el.getBoundingClientRect().height })));
    assert.ok(controls.every(control => control.height >= 44), `Controls must have 44px touch targets: ${JSON.stringify(controls.filter(control => control.height < 44))}`);
    await browser.setViewport({ width, height: layout.height });
    await browser.evaluate(() => { window.scrollTo(0, 0); return null; });
    await app.screenshot(`console-quotes-${width}`);
    await browser.setViewport({ width, height: 900 });
    await screen.getByRole('tab', 'Live quotes').press('ArrowRight');
    await expect(screen.getByRole('heading', 'Recent trade results')).toBeVisible();
    await expect(browser.locator('.trading-charts__trades')).toContainText('-4.50 USD');
    await expect(browser.locator('.apexcharts-canvas')).toBeVisible();
    const resultsChartId = await browser.evaluate(() => {
      const canvas = document.querySelector('.apexcharts-canvas')!;
      const instances = (window as any).Apex._chartInstances;
      const chart = instances.find((entry: any) => entry.chart.el.contains(canvas)).chart;
      if (chart.w.config.chart.animations.enabled) throw new Error('Completed results must not animate on mount or resize');
      const original = chart.updateOptions.bind(chart);
      chart.el.setAttribute('data-results-updates', '0');
      chart.updateOptions = (...args: any[]) => {
        chart.el.setAttribute('data-results-updates', String(Number(chart.el.getAttribute('data-results-updates')) + 1));
        return original(...args);
      };
      return canvas.id;
    });
    const beforeRefresh = request;
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('#price')).toContainText((4100.25 + (beforeRefresh + 1) * .05).toFixed(2));
    await expect(browser.locator('[data-results-updates]')).toHaveAttribute('data-results-updates', '0');
    await expect(browser.locator('.apexcharts-canvas')).toHaveAttribute('id', resultsChartId);
    payload.pilot.recent_trades.push({ side: 'sell', opened_at: now - 120, closed_at: now - 60, realized_net_usd: 2.75 });
    payload.pilot.completed_trades = 2;
    payload.pilot.realized_net_usd = -1.75;
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('.trading-charts__trades')).toContainText('2.75 USD');
    await expect(browser.locator('.apexcharts-bar-area')).toHaveCount(2);
    await expect(browser.locator('.apexcharts-canvas')).toHaveAttribute('id', resultsChartId);
    await expect(browser.locator('[data-results-updates]')).toHaveAttribute('data-results-updates', '1');
    await screen.getByRole('tab', 'Live quotes').tap();
    await browser.route('**/api/trading/status', route => route.fulfill({ status: 401, body: '' }));
    await screen.getByRole('button', 'Refresh status').tap();
    await expect(browser.locator('.trading-charts__chart')).toBeHidden();
    await expect(browser.locator('#price')).toHaveText('—');
    await expect(browser.locator('#pilot-pause')).toBeDisabled();
    await screen.getByRole('tab', 'Trade results').tap();
    await expect(screen.getByRole('heading', 'No current trade report')).toBeVisible();
  });
}

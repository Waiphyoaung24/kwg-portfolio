import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('Gold and Bitcoin views isolate prices, history, pause and sound baseline', async ({ app, screen, browser }) => {
  let wrongSymbol = false;
  let btcPaused = false;
  const selected: string[] = [];
  await browser.route('**/api/trading/**', route => {
    if (route.request.method === 'POST') {
      assert.ok(route.request.url.endsWith('/api/trading/pilot-pause'));
      assert.deepEqual(JSON.parse(route.request.postData ?? '{}'), { symbol: 'BTCUSD' });
      btcPaused = true;
      return route.fulfill({ status: 202, contentType: 'application/json', body: '{"status":"pause_requested"}' });
    }
    assert.equal(route.request.method, 'GET');
    const btc = new URL(route.request.url).searchParams.get('symbol') === 'BTCUSD';
    selected.push(btc ? 'BTCUSD' : 'XAUUSD-VIP');
    const payload = structuredClone(fixture);
    const now = Math.floor(Date.now()/1000), shift = now-payload.checked_at;
    payload.checked_at = payload.health.sampled_at = payload.health.tick_time = payload.execution.updated_at = payload.pilot.updated_at = now;
    payload.health.tick_time_msc = now * 1000;
    payload.pilot.started_at += shift;
    payload.pilot.ends_at += shift;
    payload.pilot.recent_trades = [];
    payload.symbol = btc && !wrongSymbol ? 'BTCUSD' : 'XAUUSD-VIP';
    payload.pilot.strategy = btc ? 'btc-ema-v1-m15-trend-3' : 'gold-ema-v1-m1-trend-3';
    if (btc && btcPaused) {
      payload.pilot.status = 'paused';
      payload.pilot.reason = 'Paused by owner';
    }
    payload.health.bid = btc ? 82790.5 : 4100.25;
    payload.health.ask = btc ? 82807.49 : 4100.5;
    payload.pilot.completed_trades = btc ? 0 : 6;
    payload.pilot.realized_net_usd = btc ? 0 : -17.51;
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await app.open('/vault/trading');
  await expect(browser.locator('#pilot-count')).toHaveText('6');
  await screen.getByRole('link', 'Bitcoin · M15').tap();
  await expect(screen.getByRole('heading', 'Bitcoin, under observation.')).toBeVisible();
  await expect(browser.locator('#price')).toHaveText('82790.50 / 82807.49');
  await expect(browser.locator('#pilot-count')).toHaveText('0');
  await expect(browser.locator('#pilot-realized')).toHaveText('0.00 USD');
  await expect(browser.locator('#pilot-timeframe')).toHaveText('Completed 15-minute candles only - M15 demo');
  await expect(screen.getByRole('button', 'Trade sound: Off')).toBeVisible();
  await expect(browser.locator('#manual-controls')).toBeHidden();
  assert.equal(btcPaused, false, 'Navigation must not change execution');
  await screen.getByRole('button', 'Pause new entries').tap();
  await expect(browser.locator('#pilot-state')).toHaveText('PAUSED');
  assert.equal(btcPaused, true);
  wrongSymbol = true;
  await screen.getByRole('button', 'Refresh status').tap();
  await expect(browser.locator('#price')).toHaveText('—');
  await expect(browser.locator('#pilot-pause')).toBeDisabled();
  wrongSymbol = false;
  await screen.getByRole('link', 'Gold · M1').tap();
  await expect(browser.locator('#price')).toHaveText('4100.25 / 4100.50');
  await expect(browser.locator('#pilot-count')).toHaveText('6');
  assert.ok(selected.includes('BTCUSD') && selected.includes('XAUUSD-VIP'));
  await app.screenshot('two-symbol-gold-view');
});

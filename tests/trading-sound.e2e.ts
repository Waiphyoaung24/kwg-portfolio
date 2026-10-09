import assert from 'node:assert/strict';
import fixture from '../ops/trading/fixtures/pilot-status.json';
import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('quiet entry sound previews, deduplicates and mutes', async ({ app, screen, browser }) => {
  const payload = structuredClone(fixture);
  const now = Math.floor(Date.now() / 1000);
  payload.execution.opened_at = now - 20;
  payload.pilot.started_at = now - 3600;
  payload.pilot.ends_at = now + 3600;
  await browser.route('**/api/trading/**', route => {
    assert.equal(route.request.method, 'GET');
    const at = Math.floor(Date.now() / 1000);
    payload.checked_at = payload.health.sampled_at = payload.health.tick_time =
      payload.execution.updated_at = payload.pilot.updated_at = at;
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await browser.setViewport({ width: 390, height: 900 });
  await app.open('/vault/trading');
  await expect(browser.locator('#pilot-intent')).toHaveText('Managing a demo trade');
  await expect(browser.locator('#trade-sound')).toHaveText('Trade sound: Off');
  await browser.evaluate(() => {
    (window as any).soundCalls = [];
    HTMLMediaElement.prototype.play = function () {
      (window as any).soundCalls.push({ volume: this.volume, src: this.src });
      return Promise.resolve();
    };
    return null;
  });
  await screen.getByRole('button', 'Trade sound: Off').tap();
  await expect(browser.locator('#trade-sound')).toHaveText('Trade sound: On');
  const calls = () => browser.evaluate(() => (window as any).soundCalls);
  assert.equal((await calls()).length, 1, 'Enabling previews the selected sound');
  await screen.getByRole('button', 'Refresh status').tap();
  assert.equal((await calls()).length, 1, 'Existing position stays silent');
  payload.execution.opened_at = now - 10;
  await screen.getByRole('button', 'Refresh status').tap();
  assert.equal((await calls()).length, 2);
  await screen.getByRole('button', 'Refresh status').tap();
  assert.equal((await calls()).length, 2, 'No duplicate entry sound');
  for (const call of await calls()) {
    assert.equal(call.volume, .35);
    assert.ok(call.src.endsWith('/audio/trade-entry.mp3'));
  }
  await screen.getByRole('button', 'Trade sound: On').tap();
  payload.execution.opened_at = now - 5;
  await screen.getByRole('button', 'Refresh status').tap();
  assert.equal((await calls()).length, 2, 'Muted entry stays silent');
  const layout = await browser.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }));
  assert.ok(layout.width <= layout.viewport);
  await app.screenshot('trade-sound-mobile');
  await browser.setViewport({ width: 1280, height: 900 });
  await app.screenshot('trade-sound-desktop');
  await browser.evaluate(() => {
    HTMLMediaElement.prototype.play = () => Promise.reject(new Error('Audio blocked'));
    return null;
  });
  await screen.getByRole('button', 'Trade sound: Off').tap();
  await expect(browser.locator('#trade-sound-note')).toContainText('Sound unavailable');
  await expect(browser.locator('#trade-sound')).toHaveText('Trade sound: Off');
});

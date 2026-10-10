import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { selectedInstrument } from './trading-instruments.mjs';
import { normalizeStatus } from '../../ops/trading/worker/src/index.js';
import { chartSnapshot } from './trading-chart.mjs';
import { entryNotifications } from './trading-sound.mjs';

test('BTC is explicit; a gold payload cannot populate its view', () => {
  assert.equal(selectedInstrument().symbol, 'XAUUSD-VIP');
  assert.equal(selectedInstrument('?symbol=BTCUSD').name, 'Bitcoin');
  for (const input of ['?symbol=BTCUUSD', '?symbol=BTCUSD&symbol=XAUUSD-VIP', '?symbol=']) {
    assert.throws(() => selectedInstrument(input));
  }
  const report = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/pilot-status.json', import.meta.url)));
  assert.throws(() => normalizeStatus(report, report.checked_at, 'BTCUSD'));
  report.symbol = 'BTCUSD';
  report.pilot.strategy = 'btc-ema-v1-m15-trend-3';
  assert.throws(() => normalizeStatus(report, report.checked_at));
  assert.equal(normalizeStatus(report, report.checked_at, 'BTCUSD').symbol, 'BTCUSD');
  assert.equal(chartSnapshot(report, report.checked_at).trades.length, report.pilot.recent_trades.length);
  const sound = entryNotifications('BTCUSD');
  assert.equal(sound(report, report.checked_at), false);
  report.execution.opened_at = report.checked_at - 1;
  assert.equal(sound(report, report.checked_at), true);
  assert.equal(sound({ ...report, symbol: 'XAUUSD-VIP' }, report.checked_at), false);
});

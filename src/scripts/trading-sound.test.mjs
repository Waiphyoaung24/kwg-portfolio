import assert from 'node:assert/strict';
import { test } from 'node:test';
import { entryNotifications } from './trading-sound.mjs';

const report = (opened, status = 'open', checked = 100) => ({
  mode: 'autonomous-demo', symbol: 'XAUUSD-VIP', checked_at: checked,
  execution: { status, opened_at: opened, updated_at: checked },
});
test('baseline is silent; each confirmed entry alerts once, including closes between polls', () => {
  const check = entryNotifications();
  assert.equal(check(report(50), 100), false);
  assert.equal(check(report(60), 100), true);
  assert.equal(check(report(60), 100), false);
  assert.equal(check(report(60, 'closed'), 100), false);
  assert.equal(check(report(70, 'closed'), 100), true);
  assert.equal(check(report(65), 100), false);
  assert.equal(check(report(80, 'pending'), 100), false);
  assert.equal(check(report(80), 100), true);
});
test('hidden, stale and disconnected reports suppress catch-up alerts', () => {
  for (const invalid of [null, report(70, 'open', 50)]) {
    const check = entryNotifications();
    check(report(50), 100);
    assert.equal(check(invalid, 100), false);
    assert.equal(check(report(80), 100), false);
    assert.equal(check(report(90), 100), true);
  }
  const check = entryNotifications();
  check(report(50), 100);
  assert.equal(check(report(70), 100, false), false);
  assert.equal(check(report(80), 100), false);
  assert.equal(check(report(110), 100), false);
});

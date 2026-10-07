import assert from 'node:assert/strict';
import { tradeLevels } from './trading-levels.mjs';

const buy = tradeLevels('buy', 100, 90, 130);
assert.deepEqual(buy.map(level => level.price), [90, 100, 130]);
assert.equal(buy[0].y, 224);
assert.equal(buy[2].y, 36);
assert.equal(buy[1].y, 177);
const sell = tradeLevels('sell', 100, 110, 80);
assert.equal(sell[0].y, 36);
assert.equal(sell[2].y, 224);
assert.equal(tradeLevels('buy', 129.99, 90, 130)[1].labelY, 64);
assert.equal(tradeLevels('sell', 80.01, 110, 80)[1].labelY, 196);
for (const values of [
  ['buy', 100, 110, 130], ['sell', 100, 90, 80], ['buy', 100, 100, 130],
  ['buy', NaN, 90, 130], ['buy', Infinity, 90, 130], ['buy', 100, 0, 130], ['buy', 100, 0.001, 130],
  ['buy', '100', 90, 130], ['unknown', 100, 90, 130], ['buy', 100, 90, 1000001],
]) assert.equal(tradeLevels(...values), null);
console.log('Trade levels: accurate buy/sell scale and invalid-input empty states passed');

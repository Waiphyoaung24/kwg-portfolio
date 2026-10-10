import assert from 'node:assert/strict';
import { positionRail } from './trading-position.mjs';

const sell = positionRail('sell', 4196.32, 4198.65, 4192.83, 4194.63, 4194.90);
assert.equal(sell.price, 4194.90);
assert.ok(Math.abs(sell.progress - 0.4069) < 1e-3);
assert.ok(sell.at > sell.entryAt);
const buy = positionRail('buy', 100, 90, 130, 95, 95.2);
assert.equal(buy.progress, -0.5);
assert.equal(buy.at, 12.5);
assert.equal(buy.entryAt, 25);
assert.equal(positionRail('buy', 100, 90, 130, 140, 140).at, 100);
assert.equal(positionRail('buy', 100, 90, 130, NaN, 1), null);
assert.equal(positionRail('—', 100, 90, 130, 1, 1), null);

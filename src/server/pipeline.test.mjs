import assert from 'node:assert';
const { currentStage, blockedOnWho, daysWaiting, preContractWarning } = await import('./pipeline.mjs');

const S = (ord, name, owner_type, status, blocked_since = null) => ({ ord, name, owner_type, status, blocked_since });

// currentStage: earliest non-done/non-skipped
const a = [S(1, 'Proposal', 'internal', 'done'), S(2, 'BRS', 'client', 'waiting_on_client'), S(3, 'Dev', 'internal', 'not_started')];
assert.strictEqual(currentStage(a).ord, 2);
assert.strictEqual(currentStage([S(1, 'x', 'internal', 'done')]), null);
// skipped is treated as passed
assert.strictEqual(currentStage([S(1, 'x', 'internal', 'skipped'), S(2, 'y', 'internal', 'in_progress')]).ord, 2);

// blockedOnWho
assert.strictEqual(blockedOnWho(a), 'client');                       // current is waiting_on_client
assert.strictEqual(blockedOnWho([S(1, 'x', 'internal', 'in_progress')]), 'you');
assert.strictEqual(blockedOnWho([S(1, 'x', 'client', 'not_started')]), 'client'); // client-owned = waiting on them
assert.strictEqual(blockedOnWho([S(1, 'x', 'internal', 'done')]), 'nobody');

// daysWaiting
const now = new Date('2026-07-10T00:00:00Z');
assert.strictEqual(daysWaiting('2026-07-01T00:00:00Z', now), 9);
assert.strictEqual(daysWaiting(null, now), 0);

// preContractWarning: Development active while Contract not done
const risky = [S(5, 'Contract', 'shared', 'in_progress'), S(9, 'Development', 'internal', 'in_progress')];
assert.strictEqual(preContractWarning(risky), true);
const safe = [S(5, 'Contract', 'shared', 'done'), S(9, 'Development', 'internal', 'in_progress')];
assert.strictEqual(preContractWarning(safe), false);
console.log('pipeline.test OK');

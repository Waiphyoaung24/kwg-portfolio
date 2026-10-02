import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { MAX_REPORT_BYTES, reviewReports, comparisonExplanation } from './trading-review.mjs';

const report = { runs: {} };
const deltas = {};
for (const scenario of ['lower', 'middle', 'stress']) {
  report.runs[scenario] = { windows: {} }; deltas[scenario] = {};
  for (const window of ['development', 'validation']) {
    report.runs[scenario].windows[window] = { summary: { trades: 3, net_pnl_usd: 12.5, return_pct: .0125, close_sampled_drawdown_pct: .1 } };
    deltas[scenario][window] = { trades: 0, net_pnl_usd: 0, return_pct: 0, close_sampled_drawdown_pct: 0 };
  }
}
const raw = JSON.stringify(report);
const digest = createHash('sha256').update(raw).digest('hex');
const comparison = { mode: 'synthetic-offline-comparison', qualification: 'unqualified', promotion_status: 'blocked',
  human_promotion_approval_required: true, model_requests: 0, fake_requests: 1,
  risk_sha256: '865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7',
  policy_sha256: '39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d',
  manifest_sha256: digest, baseline_sha256: digest, candidate_sha256: digest,
  proposal_sha256: digest, cost_sha256: digest, clock_sha256: digest, deltas,
  gates: ['synthetic_data', 'batch2_unqualified', 'unknown_oauth_cost', 'production_isolation_unverified', 'human_promotion_approval_required'] };
const files = (changes = {}) => [new File([JSON.stringify({ ...comparison, ...changes })], 'comparison.json'),
  new File([raw], 'baseline.json'), new File([raw], 'candidate.json')];
assert.equal((await reviewReports(files())).rows.length, 6);
assert.match(comparisonExplanation(['lower', 'middle', 'stress'].map(scenario => ({ scenario, window: 'validation', difference: -10 }))), /earned less/);
assert.doesNotMatch(comparisonExplanation([{ window: 'validation', difference: 10 }]), /earned less/);
await assert.rejects(reviewReports(files({ promotion_status: 'approved' })), /Unsupported/);
await assert.rejects(reviewReports(files({ risk_sha256: 'f'.repeat(64) })), /Unsupported/);
await assert.rejects(reviewReports(files({ model_requests: 1 })), /Unsupported/);
await assert.rejects(reviewReports(files({ gates: Array(5).fill('synthetic_data') })), /Unsupported/);
await assert.rejects(reviewReports(files().slice(1)), /Select/);
const mismatched = files(); mismatched[2] = new File([`${raw}\n`], 'candidate.json');
await assert.rejects(reviewReports(mismatched), /hash mismatch/);
const wrong = structuredClone(deltas); wrong.lower.validation.net_pnl_usd = 1;
await assert.rejects(reviewReports(files({ deltas: wrong })), /reconcile/);
const malformed = files(); malformed[0] = new File(['{'], 'comparison.json');
await assert.rejects(reviewReports(malformed), /Invalid JSON/);
const oversized = files(); oversized[0] = { name: 'comparison.json', size: MAX_REPORT_BYTES + 1 };
await assert.rejects(reviewReports(oversized), /8 MiB/);
console.log('Offline review: valid summaries, hashes, fixed policy, blocked promotion and malformed files checked.');

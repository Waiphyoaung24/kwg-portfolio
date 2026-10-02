// Local consistency checks only: hashes are not signatures or broker provenance.
export const MAX_REPORT_BYTES = 8 * 1024 * 1024;
const risk = '865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7';
const policy = '39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d';
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const sha = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
const gateLabels = {
  synthetic_data: 'Synthetic data: no real-market qualification',
  batch2_unqualified: 'Batch 2 qualification deferred',
  unknown_oauth_cost: 'Backend additional-spend ceiling unverified',
  production_isolation_unverified: 'Production credential/network isolation unverified',
  human_promotion_approval_required: 'Exact-artifact human approval required',
};

export function comparisonExplanation(rows) {
  const validation = rows.filter(row => row.window === 'validation');
  if (validation.length === 3 && validation.every(row => row.difference < 0)) {
    return 'In this fictional test, the proposed change earned less than the original strategy under all three cost assumptions. This does not measure your account performance.';
  }
  return 'These fictional results compare one proposed change with the original strategy. They do not measure your account performance or establish that either strategy is ready to trade.';
}

export async function reviewReports(files) {
  const names = ['comparison.json', 'baseline.json', 'candidate.json'];
  if (files.length !== 3 || !names.every(name => files.filter(file => file.name === name).length === 1)) {
    throw new Error('Select comparison.json, baseline.json and candidate.json together.');
  }
  const raw = {};
  const reports = {};
  for (const file of files) {
    if (!file.size || file.size > MAX_REPORT_BYTES) throw new Error('Each report must be between 1 byte and 8 MiB.');
    raw[file.name] = await file.arrayBuffer();
    try { reports[file.name] = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw[file.name])); }
    catch { throw new Error('Invalid JSON. Select the original rehearsal reports.'); }
  }
  const comparison = reports['comparison.json'];
  if (!comparison || comparison.mode !== 'synthetic-offline-comparison' ||
      comparison.qualification !== 'unqualified' || comparison.promotion_status !== 'blocked' ||
      comparison.human_promotion_approval_required !== true || comparison.model_requests !== 0 ||
      comparison.fake_requests !== 1 || comparison.risk_sha256 !== risk || comparison.policy_sha256 !== policy ||
      !['manifest', 'baseline', 'candidate', 'proposal', 'cost', 'clock'].every(key => hash(comparison[`${key}_sha256`])) ||
      !Array.isArray(comparison.gates) || comparison.gates.length !== Object.keys(gateLabels).length ||
      !Object.keys(gateLabels).every(key => comparison.gates.filter(gate => gate === key).length === 1)) {
    throw new Error('Unsupported comparison. Use the synthetic, unqualified, promotion-blocked rehearsal format with unchanged risk and policy.');
  }
  for (const name of ['baseline', 'candidate']) {
    if (await sha(raw[`${name}.json`]) !== comparison[`${name}_sha256`]) throw new Error(`${name} hash mismatch. Select files from the same attempt.`);
  }
  const rows = [];
  for (const scenario of ['lower', 'middle', 'stress']) {
    for (const window of ['development', 'validation']) {
      const baseline = reports['baseline.json']?.runs?.[scenario]?.windows?.[window]?.summary;
      const candidate = reports['candidate.json']?.runs?.[scenario]?.windows?.[window]?.summary;
      const delta = comparison.deltas?.[scenario]?.[window];
      for (const key of ['trades', 'net_pnl_usd', 'return_pct', 'close_sampled_drawdown_pct']) {
        if (!finite(baseline?.[key]) || !finite(candidate?.[key]) || !finite(delta?.[key]) ||
            Math.abs(candidate[key] - baseline[key] - delta[key]) > 1e-8) throw new Error('Report summaries do not reconcile with the comparison.');
      }
      if (![baseline.trades, candidate.trades].every(value => Number.isSafeInteger(value) && value >= 0) ||
          ![baseline.close_sampled_drawdown_pct, candidate.close_sampled_drawdown_pct].every(value => value >= 0 && value <= 100)) {
        throw new Error('Invalid trade count or drawdown in report.');
      }
      rows.push({ scenario, window, baseline: baseline.net_pnl_usd, candidate: candidate.net_pnl_usd,
        difference: delta.net_pnl_usd, trades: `${baseline.trades} / ${candidate.trades}` });
    }
  }
  return { rows, gates: Object.values(gateLabels), identities: ['manifest', 'baseline', 'candidate', 'proposal', 'risk', 'policy', 'cost', 'clock']
    .map(key => [key, comparison[`${key}_sha256`]]) };
}

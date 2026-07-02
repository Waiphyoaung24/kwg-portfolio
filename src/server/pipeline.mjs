const PASSED = new Set(['done', 'skipped']);

export function currentStage(stages) {
  return [...stages].sort((a, b) => a.ord - b.ord).find((s) => !PASSED.has(s.status)) ?? null;
}

export function blockedOnWho(stages) {
  const cs = currentStage(stages);
  if (!cs) return 'nobody';
  if (cs.status === 'waiting_on_client') return 'client';
  if (cs.owner_type === 'client') return 'client';
  return 'you';
}

export function daysWaiting(blockedSince, now) {
  if (!blockedSince) return 0;
  return Math.max(0, Math.floor((now.getTime() - new Date(blockedSince).getTime()) / 86400000));
}

export function preContractWarning(stages) {
  const contract = stages.find((s) => /contract/i.test(s.name));
  const dev = stages.find((s) => /development/i.test(s.name));
  return (
    !!dev && (dev.status === 'in_progress' || dev.status === 'done') &&
    !!contract && contract.status !== 'done' && contract.status !== 'skipped'
  );
}

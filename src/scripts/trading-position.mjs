// Where the live exit price sits on a stop -> entry -> target rail.
// A sell closes at the ask, a buy at the bid. Rail positions are 0..100, stop to target.
export function positionRail(side, entry, sl, tp, bid, ask) {
  const price = side === 'sell' ? ask : side === 'buy' ? bid : NaN;
  if (![price, entry, sl, tp].every(Number.isFinite) || sl === tp || entry === tp || entry === sl) return null;
  const at = value => Math.min(100, Math.max(0, (sl - value) / (sl - tp) * 100));
  const toward = (price - entry) / (tp - entry);
  return { price, at: at(price), entryAt: at(entry),
    progress: toward >= 0 ? toward : -(price - entry) / (sl - entry) };
}

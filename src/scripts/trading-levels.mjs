// SVG coordinates use a fixed viewBox; prices always come from the form or report.
export function tradeLevels(side, entry, stop, target) {
  if (![entry, stop, target].every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0.01 && value <= 1000000)) return null;
  if (side === 'buy' ? !(stop < entry && entry < target)
    : side === 'sell' ? !(target < entry && entry < stop) : true) return null;
  const low = Math.min(stop, target);
  const high = Math.max(stop, target);
  return [
    { name: 'Stop loss', price: stop },
    { name: 'Entry', price: entry },
    { name: 'Take profit', price: target },
  ].map(level => {
    const y = 36 + (high - level.price) / (high - low) * 188;
    return { ...level, y, labelY: level.name === 'Entry' ? Math.max(64, Math.min(196, y)) : y };
  });
}

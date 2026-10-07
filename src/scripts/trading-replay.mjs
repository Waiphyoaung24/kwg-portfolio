// Presentation of a saved simulator run. This module never evaluates live prices or sends orders.
export function replayFrame(fixture, index) {
  const bars = fixture.bars.slice(0, Math.max(1, Math.min(fixture.bars.length, index + 1)));
  const time = bars.at(-1).time;
  const trade = fixture.trade;
  const signalled = time >= trade.signal_bar;
  const entered = time >= trade.entry_bar;
  const closed = time >= trade.exit_bar;
  const side = trade.side === 1 ? 'Buy' : 'Sell';
  const events = ['Watching completed M15 candles.'];
  if (signalled) events.push(`${side} signal from the saved EMA20/50 simulation.`);
  if (entered) events.push(`Paper entry ${trade.entry.toFixed(2)} · ${trade.lots} lot · stop ${trade.stop.toFixed(2)} · target ${trade.target.toFixed(2)}.`);
  if (closed) events.push(`Paper trade closed · ${trade.exit_reason.replaceAll('_', ' ')} · ${trade.net_pnl.toFixed(2)} USD simulated net.`);
  return { bars, events, entered, closed,
    state: closed ? 'Paper trade closed' : entered ? `${side} paper trade open` : signalled ? `${side} signal` : 'Waiting for a signal',
    price: bars.at(-1).close.toFixed(2),
    result: closed ? `${trade.net_pnl.toFixed(2)} USD` : '—',
    progress: `Candle ${bars.length} of ${fixture.bars.length}` };
}

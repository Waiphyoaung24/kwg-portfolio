// Only approved market/setup fields may leave the private status origin.
export function m15Snapshot(feed, now = Date.now() / 1000) {
  const s = feed?.sample;
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  if (finite(feed?.checked_at) && (now-feed.checked_at < 0 || now-feed.checked_at > 15))
    throw Error(`Stale M15 heartbeat age ${Math.round((now-feed.checked_at)*1000)}ms`);
  if (!s || feed.status !== 'ready' || !finite(feed.checked_at) || now - feed.checked_at < 0 || now - feed.checked_at > 15 ||
      s.symbol !== 'XAUUSD-VIP' || s.timeframe !== 'M15' || !Array.isArray(s.bars) || s.bars.length !== 250 ||
      ![s.bid, s.ask, s.captured_at].every(finite) || s.bid <= 0 || s.ask < s.bid ||
      !['none', 'long', 'short'].includes(s.signal) || typeof s.eligible !== 'boolean' || typeof s.slope_pass !== 'boolean') throw Error('Invalid M15 feed');
  const bars = s.bars.map((b, i) => {
    if (!Number.isInteger(b.time) || b.time <= 0 || b.time % 900 || (i && b.time <= s.bars[i-1].time) ||
        !['open','high','low','close'].every(k => finite(b[k]) && b[k] > 0 && b[k] <= 1e6) ||
        b.high < Math.max(b.open,b.close,b.low) || b.low > Math.min(b.open,b.close)) throw Error('Invalid candle');
    return {time:b.time,open:b.open,high:b.high,low:b.low,close:b.close};
  });
  if (bars.at(-1).time !== Math.floor(now / 900)*900-900 || s.captured_at > now || s.captured_at < bars.at(-1).time+900) throw Error('Stale M15 candle');
  const numbers = (source, keys) => Object.fromEntries(keys.map(k => {
    if (!finite(source?.[k]) || Math.abs(source[k]) > 1e9) throw Error('Invalid market number');
    return [k,source[k]];
  }));
  return {symbol:s.symbol,timeframe:'M15',checked_at:feed.checked_at,captured_at:s.captured_at,
    bar_time:bars.at(-1).time,bars,bid:s.bid,ask:s.ask,signal:s.signal,eligible:s.eligible,slope_pass:s.slope_pass,
    indicators:numbers(s.indicators,['ema20','ema50','atr14']),
    costs:numbers(s.costs,['commission','slippage','overnight','spread_multiplier']),
    specification:numbers(s.specification,['point','trade_contract_size','trade_tick_size','volume_min','volume_max','volume_step']),
    risk:{stop_atr:2,target_atr:3,entry_equity_fraction:.001},
    qualification:'unverified costs and next-open fills; observation only, not a tradable-edge claim'};
}

export async function readM15(env) {
  const url = new URL(env.STATUS_ORIGIN_URL);
  if (url.protocol !== 'https:') throw Error('Invalid origin');
  url.pathname='/jev-m15'; url.search='';
  const response = await fetch(url,{headers:{'CF-Access-Client-ID':env.STATUS_ACCESS_CLIENT_ID,
    'CF-Access-Client-Secret':env.STATUS_ACCESS_CLIENT_SECRET},redirect:'manual',signal:AbortSignal.timeout(5000)});
  if (!response.ok) throw Error(`M15 origin HTTP ${response.status}`);
  return m15Snapshot(await response.json());
}

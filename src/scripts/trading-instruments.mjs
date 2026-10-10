export function selectedInstrument(search = '') {
  const params = new URLSearchParams(search);
  const symbol = params.get('symbol') ?? 'XAUUSD-VIP';
  if (params.getAll('symbol').length > 1) throw new Error('Choose one symbol');
  if (symbol === 'XAUUSD-VIP') return { symbol, name: 'Gold', query: '' };
  if (symbol === 'BTCUSD') return { symbol, name: 'Bitcoin', query: '?symbol=BTCUSD' };
  throw new Error('Unsupported demo symbol');
}

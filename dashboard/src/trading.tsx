import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Tabs } from 'radix-ui';
import { Activity, ChartNoAxesColumn, Play, Radio } from 'lucide-react';
import { appendQuote, quotePlot } from '../../src/scripts/trading-chart.mjs';

type Quote = { at: number; bid: number; ask: number };
type Trade = { side: string; closed_at: number; realized_net_usd: number };
type Snapshot = { quote: Quote | null; trades: Trade[] | null };
const time = (at: number) => new Date(at * 1000).toISOString().slice(11, 19);

function TradingCharts() {
  const [samples, setSamples] = useState<Quote[]>([]);
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [tab, setTab] = useState('quotes');
  const replay = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const receive = (event: Event) => {
      const data = (event as CustomEvent<Snapshot>).detail;
      setSamples(previous => appendQuote(previous, data.quote));
      setTrades(data.trades);
    };
    window.addEventListener('trading-snapshot', receive);
    window.dispatchEvent(new Event('trading-chart-ready'));
    // Move the existing Astro replay intact so its event handlers and SVG stay shared.
    const source = document.getElementById('trading-replay-source');
    const section = source?.querySelector('section');
    if (section) replay.current?.append(section);
    return () => {
      window.removeEventListener('trading-snapshot', receive);
      if (section) source?.append(section);
    };
  }, []);
  const plot = quotePlot(samples);
  const latest = samples.at(-1);
  const ordered = trades?.slice().sort((a, b) => a.closed_at - b.closed_at) ?? [];
  const scale = Math.max(1, ...ordered.map(t => Math.abs(t.realized_net_usd)));
  return <Tabs.Root className="trading-charts" value={tab} onValueChange={setTab}>
    <Tabs.List className="trading-charts__tabs" aria-label="Trading views">
      <Tabs.Trigger className="pill-btn" value="quotes"><Activity aria-hidden="true" />Live quotes</Tabs.Trigger>
      <Tabs.Trigger className="pill-btn" value="results"><ChartNoAxesColumn aria-hidden="true" />Trade results</Tabs.Trigger>
      <Tabs.Trigger className="pill-btn" value="replay"><Play aria-hidden="true" />Synthetic replay</Tabs.Trigger>
    </Tabs.List>
    <Tabs.Content value="quotes" className="trading-charts__content">
      <div className="trading-charts__heading"><h3>Gold / US dollar</h3><span className="micro">Page-session quotes</span></div>
      <div className="trading-charts__legend"><span>Solid · bid</span><span>Dashed · ask</span><span>{latest ? `Spread ${(latest.ask - latest.bid).toFixed(2)} USD` : 'Waiting for fresh quotes'}</span></div>
      {plot && samples.length > 1 ? <figure>
        <div className="trading-charts__plot"><div className="trading-charts__scale"><span>{plot.high.toFixed(2)}</span><span>{((plot.low + plot.high) / 2).toFixed(2)}</span><span>{plot.low.toFixed(2)}</span></div>
          <svg viewBox="0 0 640 240" role="img" aria-label={`Bid and ask from ${time(plot.first)} to ${time(plot.last)} UTC. Latest bid ${latest!.bid.toFixed(2)}, ask ${latest!.ask.toFixed(2)} US dollars.`}>
            {[20,120,220].map(y => <line key={y} x1="12" x2="628" y1={y} y2={y} className="trading-charts__grid" />)}
            <polyline points={plot.bid} className="trading-charts__bid" /><polyline points={plot.ask} className="trading-charts__ask" />
          </svg></div>
        <figcaption><span>{time(plot.first)} UTC</span><span>{time(plot.last)} UTC</span></figcaption>
      </figure> : <div className="trading-charts__empty"><Radio aria-hidden="true" /><h3>{latest ? 'First quote received' : 'Waiting for a fresh quote'}</h3><p>{latest ? 'The chart begins with the next distinct quote.' : 'Verified bid and ask samples will appear here.'}</p></div>}
      <p className="trading-charts__note">Quotes collected while this page is open. No historical candles; gaps and stale data reset the chart.</p>
    </Tabs.Content>
    <Tabs.Content value="results" className="trading-charts__content">
      <div className="trading-charts__heading"><h3>Recent trade results</h3><span className="micro">Net USD / closed trade</span></div>
      {ordered.length ? <figure><svg className="trading-charts__bars" viewBox="0 0 640 240" role="img" aria-label="Net results for the reported recent trades. Values are listed below.">
        <line x1="12" x2="628" y1="120" y2="120" className="trading-charts__grid" />
        {ordered.map((t, i) => { const h = Math.abs(t.realized_net_usd) / scale * 96; const w = 616 / ordered.length; return <rect key={`${t.closed_at}-${i}`} x={12+i*w+w*.2} y={t.realized_net_usd >= 0 ? 120-h : 120} width={w*.6} height={Math.max(h,1)} className={t.realized_net_usd >= 0 ? 'trading-charts__gain' : 'trading-charts__loss'} />; })}
      </svg><figcaption>Above zero: profit. Below zero: loss. Recent trades only, not a full equity curve.</figcaption>
      <ol className="trading-charts__trades">{ordered.map((t,i) => <li key={`${t.closed_at}-${i}`}><span>{t.side === 'buy' ? 'Buy' : 'Sell'} · {new Date(t.closed_at*1000).toISOString().replace('T',' ').slice(0,19)} UTC</span><span>{t.realized_net_usd.toFixed(2)} USD</span></li>)}</ol></figure>
      : <div className="trading-charts__empty"><ChartNoAxesColumn aria-hidden="true" /><h3>{trades ? 'No completed trades yet' : 'No current trade report'}</h3><p>{trades ? 'Results appear after a trade closes and is reconciled.' : 'Waiting for a fresh pilot report.'}</p></div>}
    </Tabs.Content>
    <Tabs.Content value="replay" forceMount hidden={tab !== 'replay'} className="trading-charts__content"><div ref={replay} /></Tabs.Content>
  </Tabs.Root>;
}

const root = document.getElementById('trading-charts');
if (root) createRoot(root).render(<TradingCharts />);

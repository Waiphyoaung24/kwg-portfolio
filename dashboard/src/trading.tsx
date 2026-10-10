import { selectedInstrument } from '../../src/scripts/trading-instruments.mjs';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Tabs } from 'radix-ui';
import ApexCharts from 'apexcharts/core';
import 'apexcharts/line';
import 'apexcharts/bar';
import 'apexcharts/features/annotations';
import { IconActivity, IconChartBar, IconPlayerPlay, IconAntennaBars5 } from '@tabler/icons-react';
import { appendQuote } from '../../src/scripts/trading-chart.mjs';

type Quote = { at: number; bid: number; ask: number };
type Trade = { side: string; closed_at: number; realized_net_usd: number };
type Levels = { side: string; entry: number; sl: number; tp: number };
type Snapshot = { quote: Quote | null; trades: Trade[] | null; levels: Levels | null };
const time = (at: number) => new Date(at * 1000).toISOString().slice(11, 19);

// ApexCharts derives gradient shades from the colour string, so the desk palette is repeated
// here as hex (source of truth: the trading page's --desk-* variables).
const GREEN = '#0f7a45', MUTED = '#4a6656', RED = '#d92d20', INK = '#0b2a1c', LINE = '#d5eadc';
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
// Charts draw in once on first render; live updates never animate because they arrive every few seconds.
const base = {
  chart: { height: 280, background: 'transparent', fontFamily: 'inherit', foreColor: MUTED, toolbar: { show: false }, zoom: { enabled: false }, parentHeightOffset: 0,
    animations: still ? { enabled: false } : { enabled: true, speed: 900, animateGradually: { enabled: true, delay: 60 }, dynamicAnimation: { enabled: false } } },
  theme: { mode: 'light' as const },
  grid: { strokeDashArray: 4, borderColor: LINE, padding: { left: 8, right: 8 } },
  dataLabels: { enabled: false },
  legend: { show: false },
};

function level(y: number, text: string, color: string, dashed: boolean) {
  return { y, borderColor: color, strokeDashArray: dashed ? 6 : 0,
    label: { text: `${text} ${y.toFixed(2)}`, position: 'left', textAnchor: 'start', borderColor: color, style: { color: '#fff', background: color, fontFamily: 'Geist Mono, monospace' } } };
}

function quoteOptions(samples: Quote[], levels: Levels | null) {
  const prices = samples.flatMap(s => [s.bid, s.ask]).concat(levels ? [levels.entry, levels.sl, levels.tp] : []);
  return {
    series: [{ name: 'Bid', data: samples.map(s => [s.at * 1000, s.bid]) }, { name: 'Ask', data: samples.map(s => [s.at * 1000, s.ask]) }],
    // Pad the axis so the entry, stop and target lines stay inside the plot.
    yaxis: { min: Math.min(...prices) - 0.3, max: Math.max(...prices) + 0.3, labels: { formatter: (v: number) => v.toFixed(2) } },
    annotations: { yaxis: levels ? [level(levels.sl, 'Stop', RED, true), level(levels.entry, 'Entry', INK, false), level(levels.tp, 'Target', GREEN, true)] : [] },
  };
}

function QuoteChart({ samples, levels }: { samples: Quote[]; levels: Levels | null }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<ApexCharts | null>(null);
  const mounted = useRef(false);
  useEffect(() => {
    chart.current = new ApexCharts(el.current!, { ...base, chart: { ...base.chart, type: 'area' }, ...quoteOptions(samples, levels),
      colors: [GREEN, MUTED],
      stroke: { width: [2.5, 1.5], curve: 'smooth', dashArray: [0, 5] },
      fill: { type: ['gradient', 'solid'], opacity: [1, 0], gradient: { shadeIntensity: 0, opacityFrom: 0.3, opacityTo: 0, stops: [0, 100] } },
      xaxis: { type: 'datetime', labels: { datetimeUTC: true, format: 'HH:mm:ss' }, tooltip: { enabled: false }, axisBorder: { color: LINE }, axisTicks: { color: LINE } },
      tooltip: { x: { format: 'HH:mm:ss' }, y: { formatter: (v: number) => `${v.toFixed(2)} USD` } } });
    void chart.current.render();
    return () => { chart.current?.destroy(); chart.current = null; mounted.current = false; };
  }, []);
  useEffect(() => {
    // Skip the first run so the draw-in animation from render() is not cancelled.
    if (!mounted.current) { mounted.current = true; return; }
    void chart.current?.updateOptions(quoteOptions(samples, levels), false, false);
  }, [samples, levels]);
  return <div ref={el} aria-hidden="true" />;
}

function ResultsChart({ trades }: { trades: Trade[] }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const chart = new ApexCharts(el.current!, { ...base, chart: { ...base.chart, type: 'bar', height: 240 },
      series: [{ name: 'Net USD', data: trades.map(t => t.realized_net_usd) }],
      plotOptions: { bar: { columnWidth: '46%', borderRadius: 6, colors: { ranges: [{ from: -1e9, to: -0.000001, color: RED }, { from: 0, to: 1e9, color: GREEN }] } } },
      xaxis: { categories: trades.map(t => time(t.closed_at)), labels: { rotate: 0, hideOverlappingLabels: true }, axisBorder: { color: LINE }, axisTicks: { color: LINE } },
      yaxis: { labels: { formatter: (v: number) => v.toFixed(2) } },
      tooltip: { y: { formatter: (v: number) => `${v.toFixed(2)} USD` } } });
    void chart.render();
    return () => chart.destroy();
  }, [trades]);
  return <div ref={el} aria-hidden="true" />;
}

function TradingCharts() {
  const selected = selectedInstrument(location.search);
  const [samples, setSamples] = useState<Quote[]>([]);
  const [trades, setTrades] = useState<Trade[] | null>(null);
  const [levels, setLevels] = useState<Levels | null>(null);
  const [tab, setTab] = useState('quotes');
  const replay = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const indicator = useRef<HTMLSpanElement>(null);
  // Slide one highlight under the active tab instead of swapping backgrounds.
  useLayoutEffect(() => {
    const place = () => {
      const active = list.current?.querySelector<HTMLElement>('[data-state="active"]');
      if (active && indicator.current) { indicator.current.style.width = `${active.offsetWidth}px`; indicator.current.style.transform = `translateX(${active.offsetLeft}px)`; }
    };
    place();
    // Re-measure when fonts load or the layout changes width.
    const observer = new ResizeObserver(place);
    observer.observe(list.current!);
    return () => observer.disconnect();
  }, [tab]);
  useEffect(() => {
    const receive = (event: Event) => {
      const data = (event as CustomEvent<Snapshot>).detail;
      setSamples(previous => appendQuote(previous, data.quote));
      setTrades(data.trades);
      setLevels(previous => JSON.stringify(previous) === JSON.stringify(data.levels) ? previous : data.levels);
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
  const latest = samples.at(-1);
  const ordered = trades?.slice().sort((a, b) => a.closed_at - b.closed_at) ?? [];
  const tabClass = 'trading-charts__tab';
  return <Tabs.Root className="trading-charts" value={tab} onValueChange={setTab}>
    <Tabs.List ref={list} className="trading-charts__tabs" aria-label="Trading views">
      <span ref={indicator} className="trading-charts__indicator" aria-hidden="true" />
      <Tabs.Trigger className={tabClass} value="quotes"><IconActivity className="icon" aria-hidden="true" />Live quotes</Tabs.Trigger>
      <Tabs.Trigger className={tabClass} value="results"><IconChartBar className="icon" aria-hidden="true" />Trade results</Tabs.Trigger>
      {selected.symbol === 'XAUUSD-VIP' && <Tabs.Trigger className={tabClass} value="replay"><IconPlayerPlay className="icon" aria-hidden="true" />Synthetic replay</Tabs.Trigger>}
    </Tabs.List>
    <Tabs.Content value="quotes" className="trading-charts__content">
      <div className="d-flex flex-wrap justify-content-between align-items-baseline gap-2"><h3 className="trading-charts__title">{selected.name} / US dollar</h3><span className="desk-muted small">Page-session quotes</span></div>
      <div className="d-flex flex-wrap gap-3 desk-muted small my-2"><span>Solid: bid</span><span>Dashed: ask</span>{levels && <span>Lines: stop, entry, target</span>}<span>{latest ? `Spread ${(latest.ask - latest.bid).toFixed(2)} USD` : 'Waiting for fresh quotes'}</span></div>
      {samples.length > 1 ? <figure className="m-0 trading-charts__chart">
        <p className="visually-hidden">{`Bid and ask from ${time(samples[0].at)} to ${time(latest!.at)} UTC. Latest bid ${latest!.bid.toFixed(2)}, ask ${latest!.ask.toFixed(2)} US dollars.${levels ? ` Stop ${levels.sl.toFixed(2)}, entry ${levels.entry.toFixed(2)}, target ${levels.tp.toFixed(2)}.` : ''}`}</p>
        <QuoteChart samples={samples} levels={levels} />
      </figure> : <div className="empty py-5"><div className="empty-icon"><IconAntennaBars5 className="icon" aria-hidden="true" /></div><h3 className="empty-title">{latest ? 'First quote received' : 'Waiting for a fresh quote'}</h3><p className="empty-subtitle desk-muted">{latest ? 'The chart begins with the next distinct quote.' : 'Verified bid and ask samples will appear here.'}</p></div>}
      <p className="desk-muted small mt-2 mb-0">Quotes collected while this page is open. No historical candles. Gaps and stale data reset the chart.</p>
    </Tabs.Content>
    <Tabs.Content value="results" className="trading-charts__content">
      <div className="d-flex flex-wrap justify-content-between align-items-baseline gap-2"><h3 className="trading-charts__title">Recent trade results</h3><span className="desk-muted small">Net USD per closed trade</span></div>
      {ordered.length ? <figure className="m-0"><p className="visually-hidden">Net results for the reported recent trades. Values are listed below.</p><ResultsChart trades={ordered} />
      <figcaption className="desk-muted small">Green bars: profit. Red bars: loss. Recent trades only, not a full equity curve.</figcaption>
      <ol className="list-group list-group-flush trading-charts__trades mt-3">{ordered.map((t, i) => <li key={`${t.closed_at}-${i}`} className="list-group-item d-flex flex-wrap justify-content-between gap-2 px-0"><span>{t.side === 'buy' ? 'Buy' : 'Sell'} {new Date(t.closed_at * 1000).toISOString().replace('T', ' ').slice(0, 19)} UTC</span><span className={`desk-num ${t.realized_net_usd >= 0 ? 'text-green' : 'text-loss'}`}>{t.realized_net_usd.toFixed(2)} USD</span></li>)}</ol></figure>
      : <div className="empty py-5"><div className="empty-icon"><IconChartBar className="icon" aria-hidden="true" /></div><h3 className="empty-title">{trades ? 'No completed trades yet' : 'No current trade report'}</h3><p className="empty-subtitle desk-muted">{trades ? 'Results appear after a trade closes and is reconciled.' : 'Waiting for a fresh pilot report.'}</p></div>}
    </Tabs.Content>
    <Tabs.Content value="replay" forceMount hidden={tab !== 'replay'} className="trading-charts__content"><div ref={replay} /></Tabs.Content>
  </Tabs.Root>;
}

const root = document.getElementById('trading-charts');
if (root) createRoot(root).render(<TradingCharts />);

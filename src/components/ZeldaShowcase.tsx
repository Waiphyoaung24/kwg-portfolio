// Zelda (Hyrule UI) showcase island — renders a curated subset of the
// zelda-hyrule-ui components. Imported only by /vault/zelda, so the library CSS
// below is bundled to that route and never leaks into the brutalist vault pages.
import 'zelda-hyrule-ui/dist/index.css';

import { useState } from 'react';
import {
  Button,
  Card,
  HealthBar,
  StaminaWheel,
  RupeeCounter,
  Divider,
  Loading,
  Logo,
  SheikahRune,
  NumberInput,
} from 'zelda-hyrule-ui';

const RUNES = ['roundBomb', 'cubeBomb', 'magnesis', 'stasis', 'cryonis', 'camera'] as const;
type Rune = (typeof RUNES)[number];

const wrap: React.CSSProperties = { display: 'grid', gap: 40 };
const row: React.CSSProperties = { display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'center' };
const h2: React.CSSProperties = {
  margin: '0 0 4px',
  fontSize: 13,
  letterSpacing: '0.16em',
  textTransform: 'uppercase',
  opacity: 0.6,
};

export default function ZeldaShowcase() {
  const [rune, setRune] = useState<Rune>('magnesis');
  const [qty, setQty] = useState(3);

  return (
    <div style={wrap}>
      <section>
        <h2 style={h2}>Buttons</h2>
        <div style={row}>
          <Button variant="primary">Primary</Button>
          <Button variant="sheikah">Sheikah</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button loading>Loading</Button>
          <Button disabled>Disabled</Button>
        </div>
      </section>

      <section>
        <h2 style={h2}>Cards</h2>
        <div style={row}>
          <Card variant="default" title="Default">A basic Hyrule card.</Card>
          <Card variant="sheikah" title="Sheikah">Ancient tech glow.</Card>
          <Card variant="item" title="Item">Slot-style container.</Card>
          <Card variant="golden" title="Golden">Rare / legendary.</Card>
        </div>
      </section>

      <section>
        <h2 style={h2}>Stats &amp; meters</h2>
        <div style={row}>
          <HealthBar current={7} max={10} bonus={3} />
          <StaminaWheel value={0.62} />
          <RupeeCounter amount={250} color="gold" />
          <RupeeCounter amount={40} color="green" />
        </div>
      </section>

      <section>
        <h2 style={h2}>Dividers</h2>
        <div style={{ display: 'grid', gap: 16, maxWidth: 420 }}>
          <Divider variant="sheikah" />
          <Divider variant="golden" />
          <Divider variant="subtle" />
          <Divider variant="ornament" />
        </div>
      </section>

      <section>
        <h2 style={h2}>Runes (interactive)</h2>
        <div style={row}>
          <SheikahRune
            runes={[...RUNES]}
            activeRune={rune}
            onSelect={(r) => setRune(r as Rune)}
          />
          <span style={{ opacity: 0.7 }}>active: {rune}</span>
        </div>
      </section>

      <section>
        <h2 style={h2}>Input &amp; loading</h2>
        <div style={row}>
          <NumberInput value={qty} min={0} max={99} onChange={setQty} />
          <Loading tip="Loading…" size="middle" />
          <Logo variant="mark" width={72} />
        </div>
      </section>
    </div>
  );
}

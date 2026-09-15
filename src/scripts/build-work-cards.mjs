// Builds the two /works card sets from each project's logo. Background and
// logo, never a screenshot (docs/superpowers/plans/2026-09-15-works-live-sections.md,
// S6 and S8).
//
//   public/works/cards/<id>.webp   1920x1080, hero ring: the project's own
//                                  capture, blurred and darkened, logo centred
//   public/works/strip/<id>.webp   1280x720, brands strip: a dark gradient
//                                  tinted to the brand, logo centred
//
// The repo holds no logo files, so each logo is keyed out of the poster that
// already shows it. Boxes are pixel regions of those posters; each key turns a
// pixel's colour into how much of it is logo. Re-run after changing a poster.
//
//   node src/scripts/build-work-cards.mjs
import sharp from 'sharp';
import { mkdirSync } from 'node:fs';

const HERO = { w: 1920, h: 1080, dir: 'public/works/cards' };
const STRIP = { w: 1280, h: 720, dir: 'public/works/strip' };

const smooth = (lo, hi, x) => {
  const t = Math.min(Math.max((x - lo) / (hi - lo), 0), 1);
  return t * t * (3 - 2 * t);
};
const luma = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

/** Ways to tell a logo pixel from what is behind it, each 0 to 1. */
const keys = {
  /** A white or gold mark on a dimmed background. */
  bright: (lo, hi) => (r, g, b) => smooth(lo, hi, luma(r, g, b)),
  /** A red mark, which is too dark to key by brightness. */
  red: (lo, hi) => (r, g, b) => smooth(lo, hi, r - Math.max(g, b)),
};

const PARALLEL = {
  src: 'public/works/parallel-poster.webp',
  box: [690, 460, 540, 160],
  key: keys.bright(110, 180),
};

// `tint` is the brand colour the strip card's gradient starts from.
const cards = [
  {
    id: 'miracle-cutting-machine',
    background: 'public/works/site-mcm-hero.webp',
    tint: '#3a3a40',
    logo: {
      src: 'public/works/miracle-cutting-machine-poster.webp',
      box: [840, 490, 240, 205],
      key: keys.bright(90, 170),
    },
  },
  {
    id: 'parallel',
    background: 'public/works/site-parallel-hero.webp',
    tint: '#44474d',
    logo: PARALLEL,
  },
  {
    id: 'redhorse-group',
    background: 'public/works/site-redhorse-hero.webp',
    tint: '#6b1217',
    logo: {
      src: 'public/works/redhorse-group-poster.webp',
      box: [875, 490, 170, 205],
      key: keys.red(40, 110),
    },
  },
  {
    id: 'castranova-pos',
    background: 'public/works/product/castranova-dashboard.webp',
    tint: '#6a4a12',
    logo: {
      src: 'public/works/castranova-pos-poster.png',
      box: [750, 500, 420, 185],
      key: keys.bright(70, 130),
    },
  },
  {
    id: 'parallel-hrm',
    background: 'public/works/product/parallel-hrm.webp',
    // A white dashboard: darker, or the white wordmark loses its ground.
    dim: 0.26,
    tint: '#33384a',
    logo: PARALLEL,
    caption: 'HRM',
  },
  {
    id: 'mrspinel-staff',
    background: 'public/works/product/mrspinel-desktop.webp',
    dim: 0.3,
    tint: '#1b3570',
    logo: {
      src: 'public/works/mrspinel-staff-poster.webp',
      box: [852, 508, 216, 170],
      key: keys.bright(170, 220),
    },
  },
  {
    id: 'gaigai',
    background: 'public/works/product/gaigai-tablet.webp',
    tint: '#145a32',
    logo: {
      src: 'public/works/gaigai-poster.webp',
      box: [865, 465, 195, 190],
      key: keys.bright(160, 215),
    },
  },
];

/** The capture as a soft, dark field: no legible detail survives. */
const blurredCapture = (src, { w, h }, dim = 0.45) =>
  sharp(src)
    .resize(w, h, { fit: 'cover' })
    .blur(45)
    .modulate({ brightness: dim, saturation: 0.85 })
    .toBuffer();

/** A dark gradient that opens from the brand colour at the top left. */
const brandGradient = (tint, { w, h }) =>
  sharp(
    Buffer.from(
      `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="g" cx="28%" cy="12%" r="115%">
            <stop offset="0" stop-color="${tint}"/>
            <stop offset="0.55" stop-color="#121212"/>
            <stop offset="1" stop-color="#0a0a0a"/>
          </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g)"/>
      </svg>`,
    ),
  ).toBuffer();

/**
 * The logo cut from its poster onto transparency, scaled to at most `share`
 * of the frame's width and height.
 */
const cutLogo = async (
  { src, box: [left, top, width, height], key },
  { w, h },
  share,
) => {
  const { data, info } = await sharp(src)
    .extract({ left, top, width, height })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const rgba = Buffer.alloc(info.width * info.height * 4);
  for (let i = 0, j = 0; i < data.length; i += 3, j += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    rgba[j] = r;
    rgba[j + 1] = g;
    rgba[j + 2] = b;
    rgba[j + 3] = Math.round(key(r, g, b) * 255);
  }

  const scale = Math.min(
    (w * share.w) / info.width,
    (h * share.h) / info.height,
  );
  return sharp(rgba, {
    raw: { width: info.width, height: info.height, channels: 4 },
  })
    .resize(Math.round(info.width * scale), Math.round(info.height * scale), {
      kernel: 'lanczos3',
    })
    .png()
    .toBuffer({ resolveWithObject: true });
};

const vignette = ({ w, h }) =>
  Buffer.from(
    `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="v" cx="50%" cy="50%" r="75%">
          <stop offset="0" stop-color="#000" stop-opacity="0.35"/>
          <stop offset="1" stop-color="#000" stop-opacity="0.85"/>
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#v)"/>
    </svg>`,
  );

const captionSvg = (text, { w, h }) => {
  const size = Math.round(h * 0.043);
  return Buffer.from(
    `<svg width="${w}" height="${size * 2}" xmlns="http://www.w3.org/2000/svg">
      <text x="50%" y="${Math.round(size * 1.35)}" text-anchor="middle"
        fill="#ffffff" fill-opacity="0.9" font-family="Arial, Helvetica, sans-serif"
        font-size="${size}" font-weight="700" letter-spacing="${Math.round(size * 0.4)}">${text}</text>
    </svg>`,
  );
};

/** The logo, and its caption if any, centred together over `base`. */
const compose = async (card, frame, base, share, extra = []) => {
  const logo = await cutLogo(card.logo, frame, share);
  const captionH = card.caption ? Math.round(frame.h * 0.086) : 0;
  const logoTop = Math.round((frame.h - logo.info.height - captionH) / 2);

  const layers = [
    ...extra,
    {
      input: logo.data,
      left: Math.round((frame.w - logo.info.width) / 2),
      top: logoTop,
    },
  ];
  if (card.caption) {
    layers.push({
      input: captionSvg(card.caption, frame),
      left: 0,
      top: logoTop + logo.info.height + Math.round(frame.h * 0.01),
    });
  }

  const file = `${frame.dir}/${card.id}.webp`;
  await sharp(base).composite(layers).webp({ quality: 82 }).toFile(file);
  console.log(`wrote ${file}`);
};

mkdirSync(HERO.dir, { recursive: true });
mkdirSync(STRIP.dir, { recursive: true });

for (const card of cards) {
  await compose(
    card,
    HERO,
    await blurredCapture(card.background, HERO, card.dim),
    { w: 0.4, h: 0.26 },
    [{ input: vignette(HERO) }],
  );
  // Strip cards sit smaller on screen, so the logo takes more of the frame.
  await compose(card, STRIP, await brandGradient(card.tint, STRIP), {
    w: 0.48,
    h: 0.32,
  });
}

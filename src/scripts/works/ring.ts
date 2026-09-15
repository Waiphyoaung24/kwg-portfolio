// The /works hero: a ring of curved cards, drawn with three.js.
//
// Rebuilt from measurements of stylized.cortiz.dev's home carousel — its
// settings-panel defaults, read off the deployed bundle — not from its code.
// The numbers in DESKTOP, MOBILE and FEEL are those defaults. The shaders are
// written here and are simpler than the reference's: no depth of field, no
// ripple simulation, no screen curvature.
import * as THREE from 'three';
import {
  nearestTargetFor,
  settleTarget,
  slotOffset,
  wrapIndex,
} from './ring-math';
import { NOISE } from './glsl';

export interface RingItem {
  title: string;
  description: string;
  poster: string;
}

export interface RingOptions {
  reduced: boolean;
  /** Called whenever the front card changes, from any cause. */
  onChange: (index: number) => void;
  /** Called on a drag, so the page can reset its autoplay clock. */
  onInteract: () => void;
  /** Whether titles are drawn onto the cards (desktop) or left to the DOM. */
  onPreset: (textInPanel: boolean) => void;
  /** The WebGL context died; the page should fall back to its DOM view. */
  onLost: () => void;
  /** The front card's two backdrop colours, whenever they change. */
  onTone: (tone: [THREE.Color, THREE.Color]) => void;
}

export interface Ring {
  goTo(index: number): void;
  step(dir: 1 | -1): void;
}

interface Preset {
  radius: number;
  arc: number;
  height: number;
  panelY: number;
  tiltX: number;
  tiltZ: number;
  camDist: number;
  camY: number;
  lookY: number;
  fov: number;
  textInPanel: boolean;
}

const DEG = Math.PI / 180;

const DESKTOP: Preset = {
  radius: 7.2,
  arc: 74,
  height: 4.7,
  panelY: 0.3,
  tiltX: 4,
  tiltZ: 4,
  // The reference frames a full 100dvh; this hero loses the site header, so
  // the camera sits a little further back and looks a little lower.
  camDist: 18.6,
  camY: 1.3,
  lookY: -1.8,
  fov: 30,
  textInPanel: true,
};

const MOBILE: Preset = {
  radius: 3,
  arc: 97,
  height: 4.8,
  panelY: 1.5,
  tiltX: 15.5,
  tiltZ: 0,
  camDist: 19.7,
  camY: 1,
  lookY: -0.2,
  fov: 33,
  textInPanel: false,
};

const FEEL = {
  /** radians of spin per px of drag */
  drag: 0.005,
  snap: 7,
  /** px/s past which a release moves on a card */
  flick: 1000,
  dimSides: 0.55,
  yawMax: 4,
  pitchMax: 2.5,
  parallaxSmooth: 3.5,
};

/** Slots sit a quarter turn apart, as the reference's four do. */
const STEP = 90 * DEG;
const MOBILE_MAX = 900;

// ── Shaders ──────────────────────────────────────────────────────────────────

const PANEL_VERT = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorld;
  varying vec3 vNormal;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    vNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

// Colours pass straight through: textures are left untagged and nothing
// converts on the way out, so a poster's bytes land on screen as they are.
const PANEL_FRAG = /* glsl */ `
  uniform sampler2D uMap;
  uniform float uImgAspect;
  uniform float uAspect;
  uniform float uDim;
  uniform vec3 uCam;
  varying vec2 vUv;
  varying vec3 vWorld;
  varying vec3 vNormal;

  float roundedBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
  }

  vec2 cover(vec2 uv) {
    vec2 r = uAspect > uImgAspect
      ? vec2(1.0, uImgAspect / uAspect)
      : vec2(uAspect / uImgAspect, 1.0);
    return (uv - 0.5) * r + 0.5;
  }

  void main() {
    // Panel space: height 1, width the aspect, origin at the centre.
    vec2 p = (vUv - 0.5) * vec2(uAspect, 1.0);
    vec2 halfSize = vec2(uAspect, 1.0) * 0.5;
    float outer = roundedBox(p, halfSize, 0.16);
    float aa = max(fwidth(outer), 1e-4);
    float mask = 1.0 - smoothstep(-aa, aa, outer);
    if (mask < 0.004) discard;

    // The picture sits inset; the band around it is the pane's glass edge.
    const float inset = 0.05;
    float inner = roundedBox(p, halfSize - inset, 0.13);
    float innerMask = 1.0 - smoothstep(-aa, aa, inner);

    vec3 picture = texture2D(uMap, clamp(cover(vUv), 0.0, 1.0)).rgb;
    // Darken toward the foot so type drawn there always has a ground.
    picture *= 1.0 - smoothstep(0.42, 0.0, vUv.y) * 0.55;

    // Glass: the picture seen through a milky, slightly magnified edge.
    vec2 glassUv = (cover(vUv) - 0.5) * 0.94 + 0.5;
    vec3 glass = mix(texture2D(uMap, clamp(glassUv, 0.0, 1.0)).rgb, vec3(0.86, 0.86, 0.9), 0.16) * 1.06;
    vec3 color = mix(glass, picture, innerMask);

    // A key light's glint and a cool rim, so the pane reads as an object.
    vec3 n = normalize(vNormal);
    vec3 v = normalize(uCam - vWorld);
    vec3 l = normalize(vec3(-7.0, 5.0, 11.0) - vWorld);
    float glint = pow(max(dot(reflect(-l, n), v), 0.0), 26.0) * 0.35;
    float rim = pow(1.0 - max(dot(n, v), 0.0), 4.0) * 0.32;
    color += glint + vec3(0.36, 0.55, 1.0) * rim;

    // Hairline on the outer edge, warm and a little over-bright.
    float band = 1.0 - smoothstep(0.0, 0.006, abs(outer + 0.006));
    color = mix(color, vec3(1.0, 0.92, 0.8), band * 0.75);

    gl_FragColor = vec4(color * uDim, mask);
  }
`;

const TEXT_FRAG = /* glsl */ `
  uniform sampler2D uMap;
  uniform float uReveal;
  varying vec2 vUv;
  void main() {
    // A left-to-right wipe with a small rise, so the title lands, not blinks.
    float wipe = smoothstep(vUv.x - 0.14, vUv.x + 0.02, uReveal * 1.16);
    vec2 uv = vUv + vec2(0.0, (1.0 - uReveal) * 0.035);
    float alpha = texture2D(uMap, uv).a * wipe;
    if (alpha < 0.004) discard;
    gl_FragColor = vec4(vec3(1.0), alpha);
  }
`;

const GROUND_VERT = /* glsl */ `
  varying vec2 vLocal;
  void main() {
    vLocal = position.xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const GROUND_FRAG = /* glsl */ `
  uniform float uPhase;
  varying vec2 vLocal;
  ${NOISE}
  void main() {
    float r = length(vLocal);
    if (r > 45.0) discard;
    float warp = fbm(vLocal * 0.075 + vec2(uPhase, -uPhase * 0.7));
    float phase = (r + (warp - 0.5) * 3.2) * 0.35;
    float fr = fract(phase);
    float dist = min(fr, 1.0 - fr);
    float w = max(fwidth(phase), 1e-5);
    float line = 1.0 - smoothstep(0.008, 0.008 + w, dist);
    // Past half a period per pixel there is only aliasing left; fade it.
    line *= 1.0 - smoothstep(0.15, 0.5, w);
    float fade = smoothstep(45.0, 18.0, r) * smoothstep(1.0, 5.0, r);
    gl_FragColor = vec4(vec3(1.0), line * fade * 0.22);
  }
`;

// ── Helpers ──────────────────────────────────────────────────────────────────

const wrapLines = (
  g: CanvasRenderingContext2D,
  text: string,
  max: number,
): string[] => {
  const lines: string[] = [];
  let line = '';
  for (const word of text.split(' ')) {
    const next = line ? `${line} ${word}` : word;
    if (g.measureText(next).width > max && line) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
};

/** Title bottom-left, description bottom-right, white on transparent. */
const drawText = (item: RingItem, aspect: number): THREE.CanvasTexture => {
  const canvas = document.createElement('canvas');
  canvas.width = 2048;
  canvas.height = Math.round(2048 / aspect);
  const g = canvas.getContext('2d');
  const h = canvas.height;
  if (g) {
    g.fillStyle = '#ffffff';
    g.textBaseline = 'alphabetic';

    const size = 0.13 * h;
    g.font = `${size}px Anton, Impact, sans-serif`;
    g.textAlign = 'left';
    const title = wrapLines(g, item.title.toUpperCase(), canvas.width * 0.5);
    title.forEach((line, i) => {
      g.fillText(
        line,
        0.1 * h,
        h - 0.11 * h - (title.length - 1 - i) * size * 1.02,
      );
    });

    const desc = 0.024 * h;
    g.font = `500 ${desc}px "IBM Plex Mono", monospace`;
    g.textAlign = 'right';
    g.globalAlpha = 0.92;
    const lines = wrapLines(g, item.description, canvas.width * 0.38);
    lines.forEach((line, i) => {
      g.fillText(
        line,
        canvas.width - 0.1 * h,
        h - 0.2 * h - (lines.length - 1 - i) * desc * 1.5,
      );
    });
  }
  return new THREE.CanvasTexture(canvas);
};

/** Two wash colours from a poster: its hue, held to a quiet saturation. */
const toneOf = (img: CanvasImageSource): [THREE.Color, THREE.Color] => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 16;
  const g = canvas.getContext('2d', { willReadFrequently: true });
  const base = new THREE.Color(0.2, 0.22, 0.26);
  if (g) {
    g.drawImage(img, 0, 0, 16, 16);
    const d = g.getImageData(0, 0, 16, 16).data;
    let r = 0;
    let gr = 0;
    let b = 0;
    for (let i = 0; i < d.length; i += 4) {
      r += d[i];
      gr += d[i + 1];
      b += d[i + 2];
    }
    const n = (d.length / 4) * 255;
    base.setRGB(r / n, gr / n, b / n);
  }
  const hsl = base.getHSL({ h: 0, s: 0, l: 0 });
  const s = Math.min(hsl.s, 0.4);
  return [
    new THREE.Color().setHSL(hsl.h, s, 0.44),
    new THREE.Color().setHSL(hsl.h, s * 0.8, 0.27),
  ];
};

const ease = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));

// ── The ring ─────────────────────────────────────────────────────────────────

interface Slot {
  group: THREE.Group;
  panel: THREE.ShaderMaterial;
  text: THREE.ShaderMaterial | null;
  reveal: number;
}

export const mountRing = (
  host: HTMLElement,
  items: RingItem[],
  opts: RingOptions,
): Ring | null => {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    return null;
  }

  const count = items.length;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  // Transparent: the page backdrop (backdrop.ts) shows through.
  renderer.setClearColor(0x000000, 0);
  const canvas = renderer.domElement;
  host.appendChild(canvas);

  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    opts.onLost();
  });

  const anisotropy = renderer.capabilities.getMaxAnisotropy();
  const loader = new THREE.TextureLoader();

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 200);
  const stage = new THREE.Group();
  scene.add(stage);

  const ground = new THREE.ShaderMaterial({
    vertexShader: GROUND_VERT,
    fragmentShader: GROUND_FRAG,
    transparent: true,
    depthWrite: false,
    uniforms: { uPhase: { value: 0 } },
  });
  const groundMesh = new THREE.Mesh(new THREE.CircleGeometry(45, 128), ground);
  groundMesh.rotation.x = -90 * DEG;
  stage.add(groundMesh);

  // Cards are loaded once and survive a preset rebuild; only the geometry and
  // the type, which depend on the card's shape, are redrawn. A card is a
  // background and a logo (src/scripts/build-work-cards.mjs), never a film:
  // a film would cover the logo.
  const media = items.map((item) => {
    const entry = {
      map: loader.load(item.poster),
      aspect: 16 / 9,
      tone: null as [THREE.Color, THREE.Color] | null,
    };
    entry.map.anisotropy = anisotropy;
    const img = new Image();
    img.onload = () => {
      entry.aspect = img.naturalWidth / img.naturalHeight;
      entry.tone = toneOf(img);
    };
    img.src = item.poster;
    return entry;
  });

  let preset: Preset = DESKTOP;
  let slots: Slot[] = [];
  const disposables: { dispose(): void }[] = [];

  const build = (next: Preset) => {
    preset = next;
    disposables.forEach((d) => d.dispose());
    disposables.length = 0;
    slots.forEach((slot) => stage.remove(slot.group));

    const arc = preset.arc * DEG;
    const aspect = (preset.radius * arc) / preset.height;
    const panelGeo = new THREE.CylinderGeometry(
      preset.radius,
      preset.radius,
      preset.height,
      48,
      1,
      true,
      -arc / 2,
      arc,
    );
    const textGeo = new THREE.CylinderGeometry(
      preset.radius + 0.02,
      preset.radius + 0.02,
      preset.height,
      48,
      1,
      true,
      -arc / 2,
      arc,
    );
    disposables.push(panelGeo, textGeo);

    stage.rotation.set(preset.tiltX * DEG, 0, preset.tiltZ * DEG);
    groundMesh.position.y = preset.panelY - preset.height / 2 - 0.4;
    camera.fov = preset.fov;
    camera.position.set(0, preset.camY, preset.camDist);
    camera.lookAt(0, preset.lookY, 0);
    camera.updateProjectionMatrix();

    slots = items.map((item, i) => {
      const group = new THREE.Group();
      group.position.y = preset.panelY;

      const panel = new THREE.ShaderMaterial({
        vertexShader: PANEL_VERT,
        fragmentShader: PANEL_FRAG,
        transparent: true,
        uniforms: {
          uMap: { value: media[i].map },
          uImgAspect: { value: media[i].aspect },
          uAspect: { value: aspect },
          uDim: { value: 1 },
          uCam: { value: camera.position.clone() },
        },
      });
      disposables.push(panel);
      group.add(new THREE.Mesh(panelGeo, panel));

      let text: THREE.ShaderMaterial | null = null;
      if (preset.textInPanel) {
        const map = drawText(item, aspect);
        map.anisotropy = anisotropy;
        text = new THREE.ShaderMaterial({
          vertexShader: PANEL_VERT,
          fragmentShader: TEXT_FRAG,
          transparent: true,
          depthWrite: false,
          uniforms: { uMap: { value: map }, uReveal: { value: 0 } },
        });
        disposables.push(map, text);
        const mesh = new THREE.Mesh(textGeo, text);
        mesh.renderOrder = 1;
        group.add(mesh);
      }

      stage.add(group);
      return { group, panel, text, reveal: 0 };
    });

    opts.onPreset(preset.textInPanel);
  };

  // ── Size ────────────────────────────────────────────────────────────────
  const resize = () => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const wanted = window.innerWidth <= MOBILE_MAX ? MOBILE : DESKTOP;
    if (wanted !== preset || slots.length === 0) build(wanted);
    // Resizing wipes the canvas; draw now so Safari never paints it blank
    // while its toolbar resizes the dvh hero mid-scroll.
    renderer.render(scene, camera);
  };
  new ResizeObserver(resize).observe(host);
  resize();

  // ── Input ───────────────────────────────────────────────────────────────
  let position = 0;
  let target = 0;
  let active = 0;
  let dragging = false;
  let lastX = 0;
  let lastT = 0;
  let velocity = 0;
  const pointer = { x: 0, y: 0 };
  const parallax = { x: 0, y: 0 };

  window.addEventListener('pointermove', (e) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
  });

  canvas.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    canvas.setPointerCapture(e.pointerId);
    dragging = true;
    lastX = e.clientX;
    lastT = e.timeStamp;
    velocity = 0;
    opts.onInteract();
  });

  canvas.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - lastX;
    const dt = Math.max(e.timeStamp - lastT, 1);
    position -= (dx * FEEL.drag) / STEP;
    velocity = 0.6 * velocity + 0.4 * ((dx / dt) * 1000);
    lastX = e.clientX;
    lastT = e.timeStamp;
  });

  const release = () => {
    if (!dragging) return;
    dragging = false;
    // Dragging right shows the previous card, so the travel is inverted.
    target = settleTarget(position, -velocity, FEEL.flick);
  };
  canvas.addEventListener('pointerup', release);
  canvas.addEventListener('pointercancel', release);

  // ── Frame loop ──────────────────────────────────────────────────────────
  // Runs only while the hero is on screen and the tab is visible.
  let visible = true;
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  }).observe(host);

  let last = performance.now();
  let lastTone: [THREE.Color, THREE.Color] | null = null;
  const frame = (now: number) => {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (!visible || document.hidden) return;

    if (!dragging) {
      position = opts.reduced
        ? target
        : THREE.MathUtils.damp(position, target, FEEL.snap, dt);
    }

    const front = wrapIndex(dragging ? position : target, count);
    if (front !== active) {
      active = front;
      opts.onChange(active);
    }

    slots.forEach((slot, i) => {
      const offset = slotOffset(i, position, count);
      const near = Math.abs(offset);
      slot.group.rotation.y = offset * STEP;
      slot.group.visible = near < 1.6;
      slot.panel.uniforms.uDim.value = 1 - FEEL.dimSides * Math.min(near, 1);
      slot.panel.uniforms.uImgAspect.value = media[i].aspect;

      if (slot.text) {
        const on = i === active && !dragging;
        slot.reveal = opts.reduced
          ? Number(on)
          : on
            ? Math.min(slot.reveal + dt / 0.9, 1)
            : Math.max(slot.reveal - dt * 4, 0);
        slot.text.uniforms.uReveal.value = ease(slot.reveal);
      }
    });

    if (!opts.reduced) {
      parallax.x = THREE.MathUtils.damp(
        parallax.x,
        pointer.x,
        FEEL.parallaxSmooth,
        dt,
      );
      parallax.y = THREE.MathUtils.damp(
        parallax.y,
        pointer.y,
        FEEL.parallaxSmooth,
        dt,
      );
      stage.rotation.y = parallax.x * FEEL.yawMax * DEG;
      stage.rotation.x = (preset.tiltX + parallax.y * FEEL.pitchMax) * DEG;
      ground.uniforms.uPhase.value += dt * 0.05;
    }

    // The page backdrop drifts toward the front card's colours.
    const tone = media[active].tone;
    if (tone && tone !== lastTone) {
      lastTone = tone;
      opts.onTone(tone);
    }

    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);

  return {
    goTo(index) {
      target = nearestTargetFor(index, target, count);
    },
    step(dir) {
      target = Math.round(target) + dir;
    },
  };
};

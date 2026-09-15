// The brands rail: logo cards on a strip that drifts on its own, follows a
// drag, bends with its speed, and greys every card but the one under the
// pointer. Card height, gap, corner, aspect, drag sensitivity, decay and grey
// are stylized.cortiz.dev's "Breakdowns Rail" defaults. Drift, bend and flick
// are set here in px, since the reference's units are its own; the bend was
// tuned by eye against it. Cards are built by src/scripts/build-work-cards.mjs.
import * as THREE from 'three';
import { ROUNDED_BOX } from './glsl';
import { wrapSpan } from './ring-math';

export interface RailItem {
  src: string;
}

const R = {
  cardHeight: 0.66,
  cardAspect: 16 / 9,
  gap: 0.09,
  corner: 0.055,
  dragSensitivity: 0.65,
  decay: 3.6,
  /** Full bend, in card heights. */
  bend: 0.05,
  bendSmooth: 5.5,
  grey: 0.56,
};
/** px per second, leftward, while nothing holds the rail. */
const DRIFT = 36;
/** Rail heights per second of travel at which the bend is full. */
const BEND_FULL = 1.1;
/** Rail heights per second a released flick may keep. */
const FLICK_CAP = 3;

const VERT = /* glsl */ `
  uniform float uBend;
  uniform float uCenterY;
  uniform float uHalfH;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    // The middle of the strip lags its travel; the top and bottom edges hold.
    float yn = clamp((world.y - uCenterY) / uHalfH, -1.0, 1.0);
    world.x += uBend * (1.0 - yn * yn);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const FRAG = /* glsl */ `
  uniform sampler2D uMap;
  uniform float uAspect;
  uniform float uRadius;
  uniform float uGrey;
  varying vec2 vUv;
  ${ROUNDED_BOX}
  void main() {
    vec2 p = (vUv - 0.5) * vec2(uAspect, 1.0);
    float d = roundedBox(p, vec2(uAspect, 1.0) * 0.5, uRadius);
    float aa = max(fwidth(d), 1e-4);
    float mask = 1.0 - smoothstep(-aa, aa, d);
    if (mask < 0.004) discard;
    vec3 color = texture2D(uMap, vUv).rgb;
    float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
    gl_FragColor = vec4(mix(color, vec3(luma), uGrey), mask);
  }
`;

export const mountRail = (
  host: HTMLElement,
  items: RailItem[],
  reduced: boolean,
): boolean => {
  if (items.length === 0) return false;
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    return false;
  }
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  // Pixel units, origin bottom-left.
  const camera = new THREE.OrthographicCamera(0, 1, 1, 0, -10, 10);
  const shared = {
    uBend: { value: 0 },
    uCenterY: { value: 0.5 },
    uHalfH: { value: 0.5 },
  };
  const geometry = new THREE.PlaneGeometry(1, 1, 1, 16);
  const loader = new THREE.TextureLoader();

  const cards = items.map((item) => {
    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      uniforms: {
        ...shared,
        uMap: { value: loader.load(item.src) },
        uAspect: { value: R.cardAspect },
        uRadius: { value: R.corner },
        uGrey: { value: 0 },
      },
    });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    return { mesh, material };
  });

  let width = 1;
  let height = 1;
  const resize = () => {
    width = host.clientWidth;
    height = host.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.right = width;
    camera.top = height;
    camera.updateProjectionMatrix();
    shared.uCenterY.value = height / 2;
    shared.uHalfH.value = (height * R.cardHeight) / 2;
  };
  new ResizeObserver(resize).observe(host);
  resize();

  // ── Input ───────────────────────────────────────────────────────────────
  let offset = 0;
  let velocity = 0;
  let dragging = false;
  let lastX = 0;
  let lastT = 0;
  let bend = 0;
  const pointer = { x: 0, y: 0, inside: false };

  host.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    host.setPointerCapture(e.pointerId);
    dragging = true;
    lastX = e.clientX;
    lastT = e.timeStamp;
    velocity = 0;
  });

  host.addEventListener('pointermove', (e) => {
    const rect = host.getBoundingClientRect();
    pointer.x = e.clientX - rect.left;
    pointer.y = e.clientY - rect.top;
    pointer.inside = true;
    if (!dragging) return;
    const dx = (e.clientX - lastX) * R.dragSensitivity;
    const dt = Math.max(e.timeStamp - lastT, 1);
    offset += dx;
    velocity = 0.6 * velocity + 0.4 * ((dx / dt) * 1000);
    lastX = e.clientX;
    lastT = e.timeStamp;
  });

  const release = () => {
    if (!dragging) return;
    dragging = false;
    const cap = FLICK_CAP * height;
    velocity = THREE.MathUtils.clamp(velocity, -cap, cap);
  };
  host.addEventListener('pointerup', release);
  host.addEventListener('pointercancel', release);
  host.addEventListener('pointerleave', () => {
    pointer.inside = false;
  });

  // ── Frame loop ──────────────────────────────────────────────────────────
  let visible = false;
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  }).observe(host);

  let last = performance.now();
  const frame = (now: number) => {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (!visible || document.hidden) return;

    const drift = reduced ? 0 : DRIFT;
    if (!dragging) {
      velocity *= Math.exp(-R.decay * dt);
      offset += (velocity - drift) * dt;
    }
    const travel = dragging ? velocity : velocity - drift;

    const cardH = height * R.cardHeight;
    const cardW = cardH * R.cardAspect;
    const pitch = cardW + height * R.gap;
    const total = pitch * cards.length;
    const top = (height - cardH) / 2;

    const bendTarget = reduced
      ? 0
      : -R.bend *
        cardH *
        THREE.MathUtils.clamp(travel / (BEND_FULL * height), -1, 1);
    bend = THREE.MathUtils.damp(bend, bendTarget, R.bendSmooth, dt);
    shared.uBend.value = bend;

    let hovered = -1;
    cards.forEach(({ mesh }, i) => {
      const left = wrapSpan(i * pitch + offset, total) - pitch;
      mesh.position.set(left + cardW / 2, height / 2, 0);
      mesh.scale.set(cardW, cardH, 1);
      const over =
        pointer.inside &&
        !dragging &&
        pointer.x >= left &&
        pointer.x <= left + cardW &&
        pointer.y >= top &&
        pointer.y <= top + cardH;
      if (over) hovered = i;
    });

    cards.forEach(({ material }, i) => {
      const grey = hovered < 0 || i === hovered ? 0 : R.grey;
      material.uniforms.uGrey.value = reduced
        ? grey
        : THREE.MathUtils.damp(material.uniforms.uGrey.value, grey, 4, dt);
    });

    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);
  return true;
};

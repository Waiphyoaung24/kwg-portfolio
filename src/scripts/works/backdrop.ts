// The /works backdrop: one fixed canvas behind every section.
//
// A drifting noise wash in the front card's colours behind the hero, handed
// over to the site's black as the hero scrolls away, with a faint light
// lattice on top throughout. The wash and the hand-over timing are
// stylized.cortiz.dev's; it hands over to paper, this page to black.
import * as THREE from 'three';
import { NOISE } from './glsl';

/** The site canvas, #0a0a0a. */
const BLACK = new THREE.Color(0x0a / 255, 0x0a / 255, 0x0a / 255);
/** Hero scroll progress over which the hand-over runs. */
const HANDOVER_START = 0.08;
const HANDOVER_END = 0.87;
/** Lattice cell, CSS px. */
const CELL = 198;

const VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

// Colours pass straight through, as in ring.ts: nothing converts on output.
const FRAG = /* glsl */ `
  uniform vec3 uA;
  uniform vec3 uB;
  uniform vec3 uBlack;
  uniform float uPhase;
  uniform float uHandover;
  uniform float uDpr;
  uniform vec2 uRes;
  varying vec2 vUv;
  ${NOISE}
  void main() {
    float aspect = uRes.x / max(uRes.y, 1.0);
    vec2 p = (vUv - 0.5) * vec2(aspect, 1.0) * 1.8;
    vec2 warp = vec2(fbm(p + vec2(uPhase, 0.0)), fbm(p + vec2(5.2, -uPhase * 0.8)));
    float n = fbm(p + (warp - 0.5) * 2.3);
    float t = clamp((n - 0.5) * 1.72 + 0.5, 0.0, 1.0);
    vec3 color = mix(uB, uA, t);

    float r = length((vUv - 0.5) * vec2(aspect, 1.0)) / length(vec2(aspect, 1.0) * 0.5);
    float vig = pow(smoothstep(0.44, 1.0, r), 1.6);
    color = mix(color, vec3(0.043, 0.047, 0.063), vig * 0.6);

    color = mix(color, uBlack, uHandover);

    // The lattice, with a small square at every crossing.
    vec2 cell = mod(vUv * uRes / uDpr, ${CELL.toFixed(1)});
    vec2 edge = min(cell, ${CELL.toFixed(1)} - cell);
    float line = 1.0 - smoothstep(0.0, 1.0, min(edge.x, edge.y));
    float spot = 1.0 - smoothstep(2.5, 3.5, max(edge.x, edge.y));
    color = mix(color, vec3(1.0), max(line * 0.06, spot * 0.14));

    gl_FragColor = vec4(color, 1.0);
  }
`;

export interface Backdrop {
  setTone(tone: [THREE.Color, THREE.Color]): void;
}

export const mountBackdrop = (
  host: HTMLElement,
  hero: HTMLElement,
  reduced: boolean,
): Backdrop | null => {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer();
  } catch {
    return null;
  }

  const dpr = Math.min(window.devicePixelRatio, 1.5);
  renderer.setPixelRatio(dpr);
  host.appendChild(renderer.domElement);

  const target = {
    a: new THREE.Color(0.3, 0.34, 0.4),
    b: new THREE.Color(0.12, 0.13, 0.16),
  };

  const material = new THREE.ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: FRAG,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      uA: { value: target.a.clone() },
      uB: { value: target.b.clone() },
      uBlack: { value: BLACK },
      uPhase: { value: 0 },
      uHandover: { value: 0 },
      uDpr: { value: dpr },
      uRes: { value: new THREE.Vector2(1, 1) },
    },
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material));
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const resize = () => {
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    material.uniforms.uRes.value.set(
      window.innerWidth * dpr,
      window.innerHeight * dpr,
    );
  };
  window.addEventListener('resize', resize);
  resize();

  let last = performance.now();

  const frame = (now: number) => {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (document.hidden) return;

    const progress = window.scrollY / Math.max(hero.offsetHeight, 1);
    material.uniforms.uHandover.value = THREE.MathUtils.smoothstep(
      progress,
      HANDOVER_START,
      HANDOVER_END,
    );

    const k = 1 - Math.exp(-1.6 * dt);
    material.uniforms.uA.value.lerp(target.a, k);
    material.uniforms.uB.value.lerp(target.b, k);
    if (!reduced) material.uniforms.uPhase.value += dt * 0.07;

    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);

  return {
    setTone([a, b]) {
      target.a.copy(a);
      target.b.copy(b);
    },
  };
};

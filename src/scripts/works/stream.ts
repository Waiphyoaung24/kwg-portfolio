// The intro's stream: work posters drifting out of the distance and past the
// camera, washed toward the page's black. Values are stylized.cortiz.dev's "Home Intro"
// defaults. Its per-card motion blur and colour fringe are left out; cards are
// drawn sharp at the reference opacity, on a canvas rendered below full
// resolution so they stay soft.
import * as THREE from 'three';
import { ROUNDED_BOX } from './glsl';

const S = {
  count: 10,
  width: 2.8,
  aspect: 1.6,
  corner: 0.05,
  opacity: 0.73,
  tint: 0.45,
  speed: 5.8,
  spawnDepth: 34,
  passBy: 3,
  spreadInner: 1.6,
  spreadOuter: 6.5,
  scaleMin: 0.55,
  scaleMax: 1.2,
  rollMax: 12,
  spinMax: 3,
  tiltMax: 22,
  fadeIn: 12,
  scrollBoost: 1.5,
  parallax: 5.25,
  parallaxTilt: 0.6,
  parallaxSmooth: 1,
  cameraDistance: 8.7,
  fov: 42,
};

const DEG = Math.PI / 180;
/** The site canvas, #0a0a0a: cards are washed toward the page they sit on. */
const PAGE = new THREE.Color(0x0a / 255, 0x0a / 255, 0x0a / 255);

const VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAG = /* glsl */ `
  uniform sampler2D uMap;
  uniform float uImgAspect;
  uniform float uAspect;
  uniform float uRadius;
  uniform float uOpacity;
  uniform float uTint;
  uniform vec3 uTintColor;
  varying vec2 vUv;
  ${ROUNDED_BOX}
  void main() {
    vec2 p = (vUv - 0.5) * vec2(uAspect, 1.0);
    float d = roundedBox(p, vec2(uAspect, 1.0) * 0.5, uRadius);
    float aa = max(fwidth(d), 1e-4);
    float alpha = (1.0 - smoothstep(-aa, aa, d)) * uOpacity;
    if (alpha < 0.004) discard;
    vec2 r = uAspect > uImgAspect
      ? vec2(1.0, uImgAspect / uAspect)
      : vec2(uAspect / uImgAspect, 1.0);
    vec3 color = texture2D(uMap, (vUv - 0.5) * r + 0.5).rgb;
    gl_FragColor = vec4(mix(color, uTintColor, uTint), alpha);
  }
`;

interface Card {
  mesh: THREE.Mesh;
  material: THREE.ShaderMaterial;
  spin: number;
}

const rand = (max: number) => (Math.random() * 2 - 1) * max;

/** A new place in the stream: far away, or anywhere along it on first fill. */
const place = (card: Card, anywhere: boolean) => {
  const angle = Math.random() * Math.PI * 2;
  const inner = S.spreadInner ** 2;
  const radius = Math.sqrt(
    inner + Math.random() * (S.spreadOuter ** 2 - inner),
  );
  const z = anywhere
    ? THREE.MathUtils.lerp(-S.spawnDepth, S.passBy, Math.random())
    : -S.spawnDepth;
  card.mesh.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius, z);
  card.mesh.rotation.set(
    rand(S.tiltMax) * DEG,
    rand(S.tiltMax) * DEG,
    rand(S.rollMax) * DEG,
  );
  card.mesh.scale.setScalar(
    THREE.MathUtils.lerp(S.scaleMin, S.scaleMax, Math.random()),
  );
  card.spin = rand(S.spinMax) * DEG;
};

export const mountStream = (
  host: HTMLElement,
  posters: string[],
  reduced: boolean,
): boolean => {
  if (posters.length === 0) return false;
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    return false;
  }
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1) * 0.8);
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(S.fov, 1, 0.1, 400);
  camera.position.z = S.cameraDistance;

  const loader = new THREE.TextureLoader();
  const textures = posters.map((src) => loader.load(src));
  const geometry = new THREE.PlaneGeometry(S.width, S.width / S.aspect);

  const cards: Card[] = Array.from({ length: S.count }, (_, i) => {
    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      uniforms: {
        uMap: { value: textures[i % textures.length] },
        uImgAspect: { value: 16 / 9 },
        uAspect: { value: S.aspect },
        uRadius: { value: S.corner },
        uOpacity: { value: 0 },
        uTint: { value: S.tint },
        uTintColor: { value: PAGE },
      },
    });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    const card: Card = { mesh, material, spin: 0 };
    place(card, true);
    return card;
  });

  const resize = () => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    // Resizing wipes the canvas; draw now so it never paints blank.
    renderer.render(scene, camera);
  };
  new ResizeObserver(resize).observe(host);
  resize();

  const pointer = { x: 0, y: 0 };
  const parallax = { x: 0, y: 0 };
  window.addEventListener('pointermove', (e) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
  });

  let visible = false;
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  }).observe(host);

  let last = performance.now();
  let lastScroll = window.scrollY;

  const frame = (now: number) => {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    // Viewports scrolled since the last frame.
    const scrolled = Math.abs(window.scrollY - lastScroll) / window.innerHeight;
    lastScroll = window.scrollY;
    if (!visible || document.hidden) return;

    // Scrolling pushes the stream along, as if the reader moved through it.
    const boost =
      1 + S.scrollBoost * Math.min(scrolled / Math.max(dt, 1e-3), 2);
    const speed = reduced ? 0 : S.speed * boost;

    cards.forEach((card) => {
      const { mesh, material } = card;
      mesh.position.z += speed * dt;
      if (!reduced) mesh.rotation.z += card.spin * dt;
      if (mesh.position.z > S.passBy) place(card, false);

      const born = THREE.MathUtils.clamp(
        (mesh.position.z + S.spawnDepth) / S.fadeIn,
        0,
        1,
      );
      const leaving = THREE.MathUtils.clamp(
        (S.passBy - mesh.position.z) / 1.5,
        0,
        1,
      );
      material.uniforms.uOpacity.value = S.opacity * born * leaving;

      const image = (material.uniforms.uMap.value as THREE.Texture).image as
        | HTMLImageElement
        | undefined;
      if (image?.width)
        material.uniforms.uImgAspect.value = image.width / image.height;
    });

    if (!reduced) {
      parallax.x = THREE.MathUtils.damp(
        parallax.x,
        pointer.x,
        S.parallaxSmooth,
        dt,
      );
      parallax.y = THREE.MathUtils.damp(
        parallax.y,
        pointer.y,
        S.parallaxSmooth,
        dt,
      );
    }
    const look = 1 - S.parallaxTilt;
    camera.position.set(
      parallax.x * S.parallax,
      -parallax.y * S.parallax,
      S.cameraDistance,
    );
    camera.lookAt(
      parallax.x * S.parallax * look,
      -parallax.y * S.parallax * look,
      0,
    );

    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);
  return true;
};

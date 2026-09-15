// The contact section's film, on a pane that bows a little toward its
// corners — stylized.cortiz.dev's page curve (.23), applied to this pane
// alone. The film plays only while the pane is on screen, and never under
// reduced motion; the poster stands in.
import * as THREE from 'three';
import { ROUNDED_BOX } from './glsl';

const CURVE = 0.23;
const MEDIA_ASPECT = 16 / 9;
/** The canvas is 20% taller than the media box, 10% bleed each way. */
const BLEED = 1.2;

const VERT = /* glsl */ `
  uniform float uCurve;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    vec3 p = position;
    float dx = uv.x - 0.5;
    p.y *= (1.0 + uCurve * dx * dx) / (1.0 + uCurve * 0.25);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`;

const FRAG = /* glsl */ `
  uniform sampler2D uMap;
  uniform float uImgAspect;
  uniform float uAspect;
  uniform float uRadius;
  varying vec2 vUv;
  ${ROUNDED_BOX}
  void main() {
    vec2 p = (vUv - 0.5) * vec2(uAspect, 1.0);
    float d = roundedBox(p, vec2(uAspect, 1.0) * 0.5, uRadius);
    float aa = max(fwidth(d), 1e-4);
    float mask = 1.0 - smoothstep(-aa, aa, d);
    if (mask < 0.004) discard;
    vec2 r = uAspect > uImgAspect
      ? vec2(1.0, uImgAspect / uAspect)
      : vec2(uAspect / uImgAspect, 1.0);
    gl_FragColor = vec4(texture2D(uMap, (vUv - 0.5) * r + 0.5).rgb, mask);
  }
`;

export const mountPanel = (
  host: HTMLElement,
  src: string,
  poster: string,
  reduced: boolean,
): boolean => {
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
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 10);
  camera.position.z = 1;

  const material = new THREE.ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: FRAG,
    transparent: true,
    uniforms: {
      uMap: { value: new THREE.TextureLoader().load(poster) },
      uImgAspect: { value: MEDIA_ASPECT },
      uAspect: { value: MEDIA_ASPECT },
      uRadius: { value: 0.06 },
      uCurve: { value: CURVE },
    },
  });
  scene.add(
    new THREE.Mesh(new THREE.PlaneGeometry(2, 2 / BLEED, 32, 8), material),
  );

  let video: HTMLVideoElement | null = null;
  if (!reduced) {
    const film = document.createElement('video');
    film.muted = true;
    film.loop = true;
    film.playsInline = true;
    film.preload = 'auto';
    film.src = src;
    film.addEventListener(
      'loadeddata',
      () => {
        material.uniforms.uMap.value = new THREE.VideoTexture(film);
        material.uniforms.uImgAspect.value = film.videoWidth / film.videoHeight;
      },
      { once: true },
    );
    video = film;
  }

  const resize = () => {
    if (!host.clientWidth || !host.clientHeight) return;
    renderer.setSize(host.clientWidth, host.clientHeight, false);
  };
  new ResizeObserver(resize).observe(host);
  resize();

  let visible = false;
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (!video) return;
    if (visible) void video.play().catch(() => undefined);
    else video.pause();
  }).observe(host);

  const frame = () => {
    requestAnimationFrame(frame);
    if (!visible || document.hidden) return;
    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);
  return true;
};

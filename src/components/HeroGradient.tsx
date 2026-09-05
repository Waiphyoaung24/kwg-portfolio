// Hero backdrop: ShaderGradient sphere in the system's greys. Colours come
// from the CSS tokens so _vars.scss stays the single source. Rendered
// client:only (WebGL, no SSR).
import { ShaderGradient, ShaderGradientCanvas } from '@shadergradient/react';

export default function HeroGradient() {
  const css = getComputedStyle(document.documentElement);
  const token = (name: string) => css.getPropertyValue(name).trim();
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  return (
    <ShaderGradientCanvas
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      pixelDensity={1}
      pointerEvents="none"
    >
      <ShaderGradient
        animate={reduceMotion ? 'off' : 'on'}
        type="sphere"
        wireframe={false}
        shader="defaults"
        uTime={0}
        uSpeed={0.3}
        uStrength={0.3}
        uDensity={0.8}
        uFrequency={5.5}
        uAmplitude={3.2}
        positionX={-0.1}
        positionY={0}
        positionZ={0}
        rotationX={0}
        rotationY={130}
        rotationZ={70}
        color1={token('--c-canvas-soft')}
        color2={token('--c-ink')}
        color3={token('--c-canvas-mid')}
        reflection={0.1}
        cAzimuthAngle={270}
        cPolarAngle={180}
        cDistance={0.5}
        cameraZoom={15.1}
        // 3d, not env: the env presets tint the greys blue.
        lightType="3d"
        brightness={1}
        grain="on"
        toggleAxis={false}
        zoomOut={false}
        hoverState=""
        enableTransition={false}
      />
    </ShaderGradientCanvas>
  );
}

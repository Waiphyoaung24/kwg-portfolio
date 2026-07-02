declare module '*.glsl';

/// <reference path="../.astro/types.d.ts" />

declare module '*.sql?raw' {
  const contents: string;
  export default contents;
}

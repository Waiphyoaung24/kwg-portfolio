precision mediump float;

#define PI 3.14159265359

attribute vec3 aVertexPosition;
attribute vec2 aTextureCoord;

uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
uniform mat4 uTextureMatrix0;

uniform float uTime;
// Signed travel, roughly -1..1. Drag and scroll both write it.
uniform float uVelocity;

varying vec3 vVertexPosition;
varying vec2 vTextureCoord;

void main() {
  vec3 p = aVertexPosition;

  // A centre-weighted bulge that relaxes to nothing at the edges, so the
  // plane never tears away from the rectangle the DOM reserved for it.
  float falloff = cos(p.x * PI * 0.5) * cos(p.y * PI * 0.5);

  // At rest the plane breathes almost imperceptibly; under travel it leans.
  p.z += falloff * (0.012 * sin(uTime * 0.01) + uVelocity * 0.28);
  p.x += falloff * uVelocity * 0.06;

  gl_Position = uPMatrix * uMVMatrix * vec4(p, 1.0);

  vVertexPosition = p;
  vTextureCoord = (uTextureMatrix0 * vec4(aTextureCoord, 0.0, 1.0)).xy;
}

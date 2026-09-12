precision mediump float;

uniform sampler2D uSampler0;
uniform float uVelocity;

varying vec3 vVertexPosition;
varying vec2 vTextureCoord;

void main() {
  // A slight horizontal smear in the direction of travel. Three taps, not a
  // loop: this runs per pixel on every frame of a drag.
  float smear = uVelocity * 0.012;
  vec4 a = texture2D(uSampler0, vTextureCoord + vec2(smear, 0.0));
  vec4 b = texture2D(uSampler0, vTextureCoord);
  vec4 c = texture2D(uSampler0, vTextureCoord - vec2(smear, 0.0));

  gl_FragColor = (a + b + c) / 3.0;
}

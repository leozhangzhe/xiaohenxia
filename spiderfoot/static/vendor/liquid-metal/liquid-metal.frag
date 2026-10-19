
precision highp float;

varying vec2 v_uv;
uniform vec2 u_resolution;
uniform vec2 u_pointer;
uniform float u_pointer_strength;
uniform float u_time;
uniform float u_distortion;
uniform float u_scale;
uniform vec3 u_base;
uniform vec3 u_metal;
uniform vec3 u_highlight;

float hash21(vec2 p) {
  p = fract(p * vec2(123.34, 345.45));
  p += dot(p, p + 34.345);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
    mix(hash21(i + vec2(0.0, 1.0)), hash21(i + 1.0), u.x),
    u.y
  );
}

float fbm(vec2 p) {
  float value = 0.0;
  float weight = 0.52;
  mat2 rotation = mat2(0.80, -0.60, 0.60, 0.80);
  for (int octave = 0; octave < 4; octave++) {
    value += noise(p) * weight;
    p = rotation * p * 2.03 + 17.17;
    weight *= 0.5;
  }
  return value;
}

float liquidField(vec2 p, float time) {
  vec2 drift = vec2(time * 0.045, -time * 0.032);
  vec2 firstWarp = vec2(
    fbm(p * 0.72 + drift),
    fbm(p * 0.76 + vec2(5.2, 1.3) - drift.yx)
  );
  vec2 secondWarp = vec2(
    fbm(p * 0.78 + firstWarp * 2.7 + vec2(1.7, 9.2) + drift * 1.3),
    fbm(p * 0.74 + firstWarp * 2.5 + vec2(8.3, 2.8) - drift * 1.1)
  );
  return fbm(p * 0.68 + secondWarp * (2.75 * u_distortion));
}

void main() {
  float aspect = u_resolution.x / max(u_resolution.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(aspect, 1.0) * u_scale;
  vec2 pointer = (u_pointer - 0.5) * vec2(aspect, 1.0) * u_scale;
  vec2 delta = p - pointer;
  float pointerFalloff = exp(-dot(delta, delta) * 2.6);
  float distanceFromPointer = max(length(delta), 0.001);
  p += (delta / distanceFromPointer) * pointerFalloff * u_distortion * 0.16 * u_pointer_strength;

  float field = liquidField(p, u_time);
  float shadow = smoothstep(0.18, 0.42, field);
  float silver = smoothstep(0.38, 0.64, field);
  float specular = smoothstep(0.60, 0.82, field);
  vec3 color = mix(vec3(0.0), u_base, shadow);
  color = mix(color, u_metal, silver * 0.88);
  color = mix(color, u_highlight, specular * 0.94);

  float softReflection = smoothstep(0.0, 0.13, 0.13 - abs(field - 0.51));
  color = mix(color, u_highlight, softReflection * 0.12);
  color += (hash21(gl_FragCoord.xy + floor(u_time * 12.0)) - 0.5) * 0.004;

  float vignette = 1.0 - smoothstep(0.48, 1.08, length((v_uv - 0.5) * vec2(0.82, 1.0)));
  color *= 0.76 + vignette * 0.24;
  gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}

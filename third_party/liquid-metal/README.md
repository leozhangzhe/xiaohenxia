# Liquid Metal / Nacre UI

- Published component: https://21st.dev/@johnmamanao/components/liquid-metal-shader
- Upstream React source: https://github.com/johnmamanao/nacre-ui/blob/main/components/ui/liquid-metal-shader.tsx
- Upstream license: https://github.com/johnmamanao/nacre-ui/blob/main/LICENSE
- Supplied export captured: 2026-10-19; imported into this project: 2026-10-19.
- License: MIT, copyright (c) 2026 Nacre UI contributors. The supplied license is
  preserved verbatim at `spiderfoot/static/vendor/liquid-metal/LICENSE`.
- `liquid-metal-shader.original.tsx` and `.original.module.css` preserve the supplied
  React component. `source-identity.json` and original GLSL files are in the vendor
  directory. Vertex/fragment shaders are unchanged, including their hash identities.

## Integration changes

The React public component API and clipping surface are retained as unmounted source.
Login/register use their pre-shader SVG gradient and do not load these WebGL assets.
CherryPy business templates mount one shared `AppBackground` renderer per document.
`spiderfoot/static/js/app-background.js` derives its full-screen triangle / uniforms /
pointer easing from the supplied native renderer. It adds deferred startup, bounded
resolution, frame caps, adaptive degradation, reduced-motion, focus/visibility pause,
context fallback, single-instance replacement, bfcache restoration and complete
resource disposal. There are no textures, external fonts, downloaded binaries, CDN
requests or additional npm dependencies. Sample controls are not shipped.

The optional, unmounted auth profile remains available to isolated renderer tests.
Production workspace uses interactive=false, speed=.2, original distortion=.6 and
scale=.92, original silver palette, max ratio 1.25 / 440k pixels. Business panels
use 64% dark tint / 16px blur, with 68% tint / 8px blur on mobile. The global overlay
uses only 18–30% dark tint (34% on mobile); page titles and breadcrumbs remain
fully transparent, without any local dark scrim.
This reveals the shader while protecting text on the foreground glass panels.
Mobile/low-memory/low-core devices use 45% of the pixel budget, at most .85
ratio, 18 FPS and 60% of profile speed. Workspace desktop cap is 20 FPS. The area
budget takes priority over ratio: a 1920×1080 screen deliberately renders below 1x.
Sustained low cadence halves pixel work, then freezes the final rendered frame.
Known software renderers receive a 50k / 30k pixel budget and a 12 FPS ceiling.
Reduced-motion first load uses a CSS still without creating a WebGL context.
Blur, hidden pages, off-screen hosts and the existing pause button stop RAF.

No input values, credentials, task data or API requests enter this visual module.
Read-only data attributes expose render state, frame count, actual drawing cadence,
resolution and ratio for inspection. They are not a production parameter panel.

## Verification

`test/stage6/background_runner.cjs` exercises actual renderer code against a controlled
GPU/DOM seam. `test/stage6/background_browser_harness.py` is a **test-only localhost
server**, not a business route: it forces media/WebGL capabilities before loading
the same production assets for real browser fallback/lifecycle verification.

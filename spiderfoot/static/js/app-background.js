/* One document / one renderer. Local Nacre UI GLSL, MIT; vendor/liquid-metal/LICENSE. */
(function (win) {
  'use strict';
  let active = null;
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const rgb = hex => [1,3,5].map(i => parseInt(hex.slice(i, i+2), 16)/255);
  /** Hardened lifecycle for the supplied renderer; the original GLSL is unchanged. */
  class LiquidMetal {
    constructor(root, options) {
      this.root = root;
      this.options = options;
      for (const key of ['fps','resolution','pixelRatio']) delete root.dataset[key];
      root.dataset.webgl='false';
      this.canvas = root.appendChild(win.document.createElement('canvas'));
      this.canvas.setAttribute('aria-hidden', 'true');
      this.cleanups = [];
      this.shaders = [];
      this.motion = win.matchMedia('(prefers-reduced-motion: reduce)');
      this.small = win.matchMedia('(max-width: 680px)');
      this.low = (win.navigator.hardwareConcurrency || 8) <= 4 || (win.navigator.deviceMemory || 8) <= 4;
      this.focused = win.document.hasFocus();
      this.visible = true;
      this.disposed = false;
      this.frames = 0;
      this.elapsed = 0;
      this.quality = 1;
      this.pointer = {x:.5,y:.5,cx:.5,cy:.5,strength:0,current:0};
      this.draw = this.draw.bind(this);
      this.listen(win.document, 'visibilitychange', () => this.sync());
      this.listen(win, 'blur', () => {this.focused=false; this.sync();});
      this.listen(win, 'focus', () => {this.focused=true; this.sync();});
      this.listen(this.motion, 'change', () => this.sync(true));
      this.listen(this.small, 'change', () => this.sync(true));
      if (options.interactive) {
        // Listen passively outside the canvas: it never captures form input or focus.
        this.listen(win, 'pointermove', event => {
          if (this.motion.matches || this.small.matches || event.pointerType === 'touch') return;
          const box = root.getBoundingClientRect();
          this.pointer.x = clamp((event.clientX-box.left)/box.width, 0, 1);
          this.pointer.y = 1-clamp((event.clientY-box.top)/box.height, 0, 1);
          this.pointer.strength = .55;
        }, {passive:true});
        this.listen(win.document, 'pointerleave', () => {this.pointer.strength=0;});
      }
      this.listen(this.canvas, 'webglcontextlost', event => {
        event.preventDefault(); this.stop(); this.release(false);
        this.root.dataset.webgl='false'; this.state('fallback');
      });
      this.listen(this.canvas, 'webglcontextrestored', () => this.sync(true));
      this.resizeObserver = new ResizeObserver(() => {this.dirty=true; this.sync();});
      this.resizeObserver.observe(root);
      this.visibilityObserver = new IntersectionObserver(([entry]) => {
        this.visible=Boolean(entry && entry.isIntersecting); this.sync();
      });
      this.visibilityObserver.observe(root);
      this.state('pending');
      // Present the CSS background and usable form before compiling a GPU program.
      const initialize = () => {this.idle=undefined; this.ready=true; this.sync(true);};
      if (win.requestIdleCallback) this.idle=win.requestIdleCallback(initialize, {timeout:600});
      else this.timer=win.setTimeout(initialize, 120);
    }
    listen(target, name, fn, options) {
      target.addEventListener(name, fn, options);
      this.cleanups.push(() => target.removeEventListener(name, fn, options));
    }
    state(value) {
      this.root.dataset.renderState = value;
      this.root.dataset.frames = String(this.frames);
      this.root.dataset.quality = this.software ? 'software' : this.small.matches || this.low ? 'economy' : 'adaptive';
    }
    initialize() {
      if (this.disposed || this.gl) return;
      let gl;
      try {
        gl = this.canvas.getContext('webgl', {alpha:false, antialias:false, depth:false,
          stencil:false, preserveDrawingBuffer:false, powerPreference:'low-power'});
        if (!gl) throw new Error('WebGL unavailable');
        this.gl=gl;
        const debug=gl.getExtension('WEBGL_debug_renderer_info');
        const renderer=debug ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)) : '';
        this.software=/swiftshader|llvmpipe|software|basic render/i.test(renderer);
        const sources=win.LiquidMetalShaderSources;
        for (const [type, source] of [[gl.VERTEX_SHADER,sources.vertex],[gl.FRAGMENT_SHADER,sources.fragment]]) {
          const shader=gl.createShader(type);
          if (!shader) throw new Error('Shader unavailable');
          this.shaders.push(shader); gl.shaderSource(shader, source); gl.compileShader(shader);
          if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error('Shader compilation failed');
        }
        this.program=gl.createProgram();
        if (!this.program) throw new Error('Program unavailable');
        this.shaders.forEach(shader => gl.attachShader(this.program, shader));
        gl.linkProgram(this.program);
        if (!gl.getProgramParameter(this.program,gl.LINK_STATUS)) throw new Error('Program link failed');
        this.shaders.forEach(shader => gl.deleteShader(shader)); this.shaders=[];
        this.buffer=gl.createBuffer();
        if (!this.buffer) throw new Error('Buffer unavailable');
        gl.useProgram(this.program); gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
        gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
        const position=gl.getAttribLocation(this.program,'a_position');
        gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
        this.uniforms=Object.fromEntries(['resolution','pointer','pointer_strength','time','distortion','scale','base','metal','highlight'].map(key=>[key,gl.getUniformLocation(this.program,'u_'+key)]));
        this.root.dataset.webgl='true'; this.dirty=true;
      } catch (_) {
        // Expected capability fallback, without raw GPU logs or page/input details.
        this.release(true); this.failed=true; this.root.dataset.webgl='false'; this.state('fallback');
      }
    }
    release(loseContext) {
      const gl=this.gl;
      if (!gl) return;
      this.shaders.forEach(shader => gl.deleteShader(shader)); this.shaders=[];
      if (this.buffer) gl.deleteBuffer(this.buffer);
      if (this.program) gl.deleteProgram(this.program);
      this.buffer=null; this.program=null; this.gl=null;
      if (loseContext) {
        const extension=gl.getExtension('WEBGL_lose_context');
        if (extension) extension.loseContext();
      }
    }
    pause(value) {this.paused=Boolean(value); this.sync();}
    sync(resize) {
      if (this.disposed) return;
      if (resize) this.dirty=true;
      this.stop();
      if (!this.ready) return;
      if (win.document.hidden || !this.focused || !this.visible || this.paused) {this.state('paused'); return;}
      if (this.motion.matches) {
        // A stable, authored CSS still requires no GPU context on reduced-motion first load.
        this.state('reduced'); return;
      }
      if (!this.gl && !this.failed) this.initialize();
      if (!this.gl) return;
      this.lastTime=0; this.sampleStart=0; this.sampleFrames=0;
      this.state('running'); this.raf=win.requestAnimationFrame(this.draw);
    }
    stop() {if (this.raf !== undefined) win.cancelAnimationFrame(this.raf); this.raf=undefined;}
    draw(timestamp) {
      this.raf=undefined;
      if (this.disposed || !this.gl) return;
      const s=this.options, p=this.pointer, gl=this.gl, u=this.uniforms;
      const economy=this.small.matches || this.low;
      const fps=this.software ? 12 : economy ? 18 : s.fps;
      const delta=this.lastTime ? timestamp-this.lastTime : 1000/fps;
      if (delta >= 1000/fps-1) {
        this.lastTime=timestamp;
        this.elapsed+=Math.min(delta/1000,.12)*s.speed*(economy ? .6 : 1);
        if (this.dirty) {
          const box=this.root.getBoundingClientRect();
          const budget=(this.software ? (s.interactive ? 50000 : 30000) : s.maxPixels)*(economy ? .45 : 1)*this.quality;
          const ratio=Math.min(win.devicePixelRatio || 1, s.pixelRatio, economy ? .85 : 1.5,
            Math.sqrt(budget/Math.max(1,box.width*box.height)));
          this.canvas.width=Math.max(1,Math.round(box.width*ratio));
          this.canvas.height=Math.max(1,Math.round(box.height*ratio));
          this.root.dataset.pixelRatio=ratio.toFixed(3);
          this.root.dataset.resolution=this.canvas.width+'×'+this.canvas.height;
          this.dirty=false;
        }
        const ease=1-Math.exp(-Math.min(delta/1000,.12)*5);
        p.cx+=(p.x-p.cx)*ease; p.cy+=(p.y-p.cy)*ease;
        p.current+=((s.interactive&&!economy ? p.strength : 0)-p.current)*ease;
        gl.viewport(0,0,this.canvas.width,this.canvas.height);
        gl.uniform2f(u.resolution,this.canvas.width,this.canvas.height);
        gl.uniform2f(u.pointer,p.cx,p.cy); gl.uniform1f(u.pointer_strength,p.current);
        gl.uniform1f(u.time,this.elapsed); gl.uniform1f(u.distortion,s.distortion); gl.uniform1f(u.scale,s.scale);
        gl.uniform3fv(u.base,rgb(s.baseColor || '#13131e'));
        gl.uniform3fv(u.metal,rgb(s.metalColor || '#9fa9c8'));
        gl.uniform3fv(u.highlight,rgb(s.highlightColor || '#e4e9ff'));
        gl.drawArrays(gl.TRIANGLES,0,3);
        this.frames++; this.root.dataset.frames=String(this.frames);
        if (!this.sampleStart) this.sampleStart=timestamp;
        this.sampleFrames++;
        if (timestamp-this.sampleStart >= 2500) {
          const actual=(this.sampleFrames-1)*1000/(timestamp-this.sampleStart);
          this.root.dataset.fps=actual.toFixed(1);
          // GPU backpressure slows RAF; reduce pixel work, then freeze if still too slow.
          if (actual < fps*.58) {
            if (this.quality > .3) {this.quality*=.55; this.dirty=true;}
            else {this.state('low-performance-still'); return;}
          }
          this.sampleStart=timestamp; this.sampleFrames=0;
        }
      }
      this.raf=win.requestAnimationFrame(this.draw);
    }
    destroy() {
      if (this.disposed) return;
      this.disposed=true; this.stop();
      if (this.idle !== undefined) win.cancelIdleCallback(this.idle);
      if (this.timer !== undefined) win.clearTimeout(this.timer);
      this.cleanups.forEach(fn=>fn()); this.cleanups=[];
      this.resizeObserver.disconnect(); this.visibilityObserver.disconnect();
      this.release(true); this.canvas.width=1; this.canvas.height=1; this.canvas.remove();
      this.state('destroyed'); this.root.dataset.webgl='false';
    }
  }
  const profiles = {
    auth: {interactive:true, speed:.46, distortion:.49, scale:1.15, pixelRatio:1.5, maxPixels:860000, fps:30},
    workspace: {interactive:false, speed:.2, distortion:.6, scale:.92,
      baseColor:'#1a1a1a', metalColor:'#ccd0e2', highlightColor:'#ffffff',
      pixelRatio:1.25, maxPixels:440000, fps:20}
  };
  function mount(root, options = {}) {
    if (active && active.root === root) return active.handle;
    if (active) active.handle.destroy();
    const mode = options.mode === 'workspace' ? 'workspace' : 'auth';
    root.classList.add('app-background');
    root.dataset.mode = mode;
    root.setAttribute('aria-hidden', 'true');
    const renderer = new LiquidMetal(root, {...profiles[mode], ...options,
      // Profiles set hard safety ceilings even if a consumer passes a larger ratio.
      pixelRatio:Math.min(options.pixelRatio || profiles[mode].pixelRatio, profiles[mode].pixelRatio)
    });
    const sync = () => renderer.pause(win.document.documentElement.dataset.vaultPaused === 'true');
    const observer = new MutationObserver(sync);
    observer.observe(win.document.documentElement, {attributes:true, attributeFilter:['data-vault-paused']});
    sync();
    const onHide = event => {
      handle.destroy();
      if (event.persisted) win.addEventListener('pageshow', function restore() {
        win.removeEventListener('pageshow', restore);
        if (root.isConnected) mount(root, options);
      });
    };
    const handle = {destroy() {
      observer.disconnect();
      win.removeEventListener('pagehide', onHide);
      renderer.destroy();
      if (active && active.handle === handle) active = null;
    }};
    win.addEventListener('pagehide', onHide);
    active = {root, handle};
    return handle;
  }
  win.AppBackground = {mount, destroy() {if (active) active.handle.destroy();}};
  function boot() {
    const root = win.document.querySelector('[data-app-background="workspace"]');
    if (root) mount(root, {mode:'workspace'});
  }
  if (win.document.readyState === 'loading') win.document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})(window);

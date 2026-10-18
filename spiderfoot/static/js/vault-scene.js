/* Holographic Identity Vault. Original procedural Canvas 2D; no remote assets. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.VaultScene = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  function create(canvas, env, options) {
    options = options || {};
    var ctx;
    try { ctx = canvas.getContext('2d', {alpha:true}); } catch (_) { ctx = null; }
    var disposed=false, raf=0, frames=0, samples=0, elapsed=0, last=0, tick=0;
    var reduced=env.matchMedia('(prefers-reduced-motion: reduce)'), small=env.matchMedia('(max-width: 680px)');
    var offscreen=false, stopped=false, quality='full', listeners=[], observer, boost=0, impulse=0, error=0;
    var cursor={x:0,y:0,inside:false}, view={x:0,y:0}, width=1,height=1,dpr=1;
    var points=[], count=options.mini?150:960;
    for(var i=0;i<count;i++) {
      var y=1-(i+.5)*2/count, radius=Math.sqrt(1-y*y), a=i*2.399963229728653;
      points.push([Math.cos(a)*radius,y,Math.sin(a)*radius]);
    }
    function attr(key,value){canvas.setAttribute('data-'+key,String(value));}
    function listen(target,name,fn){target.addEventListener(name,fn);listeners.push(function(){target.removeEventListener(name,fn);});}
    function staticMode(){return !ctx||reduced.matches||small.matches||quality==='static'||stopped;}
    function status(){
      attr('renderer',!ctx?'static-no-canvas':reduced.matches?'static-reduced':small.matches?'static-mobile':stopped?'static-paused':quality);
      attr('active',Boolean(raf));attr('frames',frames);attr('dpr',dpr);attr('particles',staticMode()?0:quality==='low'?Math.ceil(count/2):count);
    }
    function resize(){var box=canvas.getBoundingClientRect();width=Math.max(1,box.width);height=Math.max(1,box.height);dpr=Math.min(env.devicePixelRatio||1,1.5);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);if(ctx)ctx.setTransform(dpr,0,0,dpr,0,0);status();}
    function project(x,y,z,r,rotation){
      var cos=Math.cos(rotation),sin=Math.sin(rotation),rx=x*cos+z*sin,rz=z*cos-x*sin;
      var tilt=view.y*.08,py=y*Math.cos(tilt)-rz*Math.sin(tilt),depth=rz*Math.cos(tilt)+y*Math.sin(tilt);
      var scale=3.6/(3.6-depth);
      return [width/2+(rx+view.x*.035)*r*scale,height/2+(py+view.y*.025)*r*scale,depth,scale];
    }
    function draw(t){
      ctx.clearRect(0,0,width,height);
      view.x+=(cursor.x-view.x)*.045;view.y+=(cursor.y-view.y)*.045;
      var r=Math.min(width*.28,height*.34), rotation=t*.028+view.x*.10, breath=1+Math.sin(t*.6)*.008;
      var cyan=options.cyan, color=error>0?'255,113,141':cyan?'89,233,231':'139,159,255';
      var glow=ctx.createRadialGradient(width/2,height/2,r*.1,width/2,height/2,r*1.7);
      glow.addColorStop(0,'rgba('+color+','+(.13+boost*.04)+')');glow.addColorStop(.55,'rgba(72,94,195,.065)');glow.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle=glow;ctx.fillRect(0,0,width,height);
      // Three parallel data planes: depth without the intersecting atom-symbol silhouette.
      for(var band=0;band<3;band++) {
        var angle=t*(.07+band*.022)*(band%2?-1:1), tilt=.24+band*.045;
        ctx.beginPath();
        for(var j=0;j<=100;j++) {var a=j/100*Math.PI*2, rr=1.30+band*.15;
          var p=project(Math.cos(a)*rr,Math.sin(a)*Math.sin(tilt)*rr+(band-1)*.19,Math.sin(a)*Math.cos(tilt)*rr,r,-.22);
          if(!j)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1]);}
        ctx.strokeStyle='rgba('+color+','+(.12-band*.022)+')';ctx.lineWidth=.65;ctx.stroke();
        for(var k=0;k<2;k++) {var n=angle+k*Math.PI,rr2=1.35+band*.14;
          var q=project(Math.cos(n)*rr2,Math.sin(n)*Math.sin(tilt)*rr2+(band-1)*.19,Math.sin(n)*Math.cos(tilt)*rr2,r,-.22);
          ctx.fillStyle=band===1?'#7ee5e4':'#afbaff';ctx.beginPath();ctx.arc(q[0],q[1],1.9,0,Math.PI*2);ctx.fill();
          if(cursor.inside&&Math.abs(q[0]-(width/2+view.x*width*.4))<100){ctx.beginPath();ctx.moveTo(q[0],q[1]);ctx.lineTo(width/2+view.x*r*.35,height/2+view.y*r*.35);ctx.strokeStyle='rgba('+color+',.12)';ctx.stroke();}}
      }
      for(var index=0;index<points.length;index+=(quality==='low'?2:1)) {
        var point=points[index],shrink=impulse>0?1-Math.sin(impulse*Math.PI)*.16:1;
        var pt=project(point[0]*breath*shrink,point[1]*breath*shrink,point[2]*breath*shrink,r,rotation);
        var alpha=.035+(pt[2]+1)*.14+boost*.045;
        ctx.fillStyle='rgba('+(index%7===0?'87,223,233':color)+','+Math.min(.95,alpha)+')';
        ctx.beginPath();ctx.arc(pt[0],pt[1],(.38+(pt[2]+1)*.26)*pt[3],0,Math.PI*2);ctx.fill();
      }
      // Authored synthetic fingerprint: open ridges, asymmetric flow and a quiet shield perimeter.
      // These are geometry, not captured or inferred biometric information.
      ctx.save();ctx.translate(width/2+view.x*r*.025,height/2+view.y*r*.018);ctx.scale(r/116,r/116);
      ctx.rotate(-.07+view.x*.035);ctx.lineCap='round';
      var scan=Math.sin(t*.52)*96;
      for(var f=0;f<20;f++){
        var w=7+f*3.55,h=17+f*4.05,bottom=20+f*1.55;
        ctx.beginPath();ctx.moveTo(-w-6,bottom+18-f*.36);
        ctx.bezierCurveTo(-w+4,bottom,-w,-h*.35,-w,-h*.48);
        ctx.bezierCurveTo(-w-2,-h*1.32,w*.78,-h*1.38,w+2,-h*.36);
        ctx.bezierCurveTo(w+12,bottom*.7,w-f*.6,bottom+24,w-12-f*.45,bottom+42-f*.75);
        ctx.lineWidth=f%4===0?1.25:.8;
        ctx.strokeStyle='rgba('+(f%4===0?'181,219,255':cyan?'115,223,224':'129,166,242')+','+(.67-f*.016+boost*.09)+')';ctx.stroke();
      }
      ctx.beginPath();ctx.moveTo(-5,41);ctx.bezierCurveTo(5,17,-4,-14,8,-11);ctx.bezierCurveTo(20,-5,11,44,2,58);ctx.strokeStyle='rgba(197,233,255,.8)';ctx.lineWidth=1.2;ctx.stroke();
      ctx.beginPath();ctx.moveTo(0,-105);ctx.lineTo(80,-78);ctx.lineTo(74,15);ctx.quadraticCurveTo(65,72,0,108);ctx.quadraticCurveTo(-65,72,-74,15);ctx.lineTo(-80,-78);ctx.closePath();ctx.strokeStyle='rgba('+color+',.14)';ctx.lineWidth=.75;ctx.stroke();
      // One slow light plane reveals the fingerprint; it never signifies a successful login.
      var span=Math.sqrt(Math.max(0,1-(scan/116)*(scan/116)))*107;
      ctx.beginPath();ctx.moveTo(-span,scan);ctx.lineTo(span,scan);ctx.strokeStyle='rgba(135,234,244,.48)';ctx.lineWidth=.8;ctx.stroke();
      ctx.beginPath();ctx.moveTo(-span*.92,scan+2);ctx.lineTo(span*.92,scan+2);ctx.strokeStyle='rgba(105,199,239,.08)';ctx.lineWidth=8;ctx.stroke();ctx.restore();
      if(impulse>0)impulse=Math.max(0,impulse-.045);
      if(error>0)error=Math.max(0,error-.08);
    }
    function frame(now){
      raf=0;if(disposed||env.document.hidden||offscreen||staticMode()){status();return;}
      // High refresh displays must not turn a decorative scene into a 200 FPS workload.
      if(last&&now-last<16){raf=env.requestAnimationFrame(frame);return;}
      if(last){var delta=now-last;if(delta<250){elapsed+=delta;samples++;tick+=delta/1000;}}
      last=now;draw(tick);frames++;
      if(samples>=90){var fps=1000*samples/elapsed;attr('fps',fps.toFixed(1));if(fps<45){if(quality==='low')quality='static';else quality='low';}samples=0;elapsed=0;}
      if(!staticMode())raf=env.requestAnimationFrame(frame);else if(ctx)ctx.clearRect(0,0,width,height);status();
    }
    function sync(){
      if(raf)env.cancelAnimationFrame(raf);raf=0;last=0;
      if(ctx&&!staticMode()&&!env.document.hidden&&!offscreen&&!disposed)raf=env.requestAnimationFrame(frame);
      if(ctx&&staticMode())ctx.clearRect(0,0,width,height);status();
    }
    resize();listen(env,'resize',resize);listen(env.document,'visibilitychange',sync);listen(reduced,'change',sync);listen(small,'change',sync);
    var surface=options.surface;
    if(surface){listen(surface,'pointermove',function(e){var b=surface.getBoundingClientRect();cursor.x=(e.clientX-b.left)/b.width*2-1;cursor.y=(e.clientY-b.top)/b.height*2-1;cursor.inside=true;});listen(surface,'pointerleave',function(){cursor.inside=false;cursor.x=cursor.y=0;});}
    if(env.IntersectionObserver){observer=new env.IntersectionObserver(function(entries){offscreen=!entries[0].isIntersecting;sync();});observer.observe(canvas);}
    sync();
    return {
      pause:function(value){stopped=value;sync();},
      feedback:function(type){if(type==='hover')boost=.7;else if(type==='leave')boost=0;else if(type==='submit')impulse=1;else if(type==='error')error=1;},
      destroy:function(){if(disposed)return;disposed=true;if(raf)env.cancelAnimationFrame(raf);raf=0;listeners.forEach(function(remove){remove();});listeners=[];if(observer)observer.disconnect();points=[];if(ctx)ctx.clearRect(0,0,width,height);canvas.width=canvas.height=1;ctx=null;attr('disposed',true);attr('listeners',0);status();},
      snapshot:function(){return {disposed:disposed,active:Boolean(raf),listeners:listeners.length,frames:frames,quality:quality,static:staticMode()};}
    };
  }
  return {create:create};
});

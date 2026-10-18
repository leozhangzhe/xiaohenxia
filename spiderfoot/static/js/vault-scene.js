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
    var cursor={x:0,y:0,inside:false}, width=1,height=1,dpr=1;
    var points=[], count=options.mini?150:580;
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
      var tilt=cursor.y*.08,py=y*Math.cos(tilt)-rz*Math.sin(tilt),depth=rz*Math.cos(tilt)+y*Math.sin(tilt);
      var scale=3.6/(3.6-depth);
      return [width/2+(rx+cursor.x*.035)*r*scale,height/2+(py+cursor.y*.025)*r*scale,depth,scale];
    }
    function draw(t){
      ctx.clearRect(0,0,width,height);
      var r=Math.min(width*.29,height*.34), rotation=t*.075+cursor.x*.12, breath=1+Math.sin(t*.8)*.012;
      var cyan=options.cyan, color=error>0?'255,113,141':cyan?'89,233,231':'139,159,255';
      var glow=ctx.createRadialGradient(width/2,height/2,r*.1,width/2,height/2,r*1.7);
      glow.addColorStop(0,'rgba('+color+','+(.10+boost*.05)+')');glow.addColorStop(.5,'rgba(94,75,213,.06)');glow.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle=glow;ctx.fillRect(0,0,width,height);
      // Three real geometric orbits, intentionally independent of task completion.
      for(var band=0;band<3;band++) {
        var angle=t*(.09+band*.035)*(band%2?-1:1), tilt=.28+band*.55;
        ctx.beginPath();
        for(var j=0;j<=100;j++) {var a=j/100*Math.PI*2, rr=1.35+band*.14;
          var p=project(Math.cos(a)*rr,Math.sin(a)*Math.sin(tilt)*rr,Math.sin(a)*Math.cos(tilt)*rr,r,band*.8);
          if(!j)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1]);}
        ctx.strokeStyle='rgba('+color+',.17)';ctx.lineWidth=.7;ctx.stroke();
        for(var k=0;k<2;k++) {var n=angle+k*Math.PI,rr2=1.35+band*.14;
          var q=project(Math.cos(n)*rr2,Math.sin(n)*Math.sin(tilt)*rr2,Math.sin(n)*Math.cos(tilt)*rr2,r,band*.8);
          ctx.fillStyle=band===1?'#66e5de':'#b2b7ff';ctx.beginPath();ctx.arc(q[0],q[1],2.6,0,Math.PI*2);ctx.fill();
          if(cursor.inside){ctx.beginPath();ctx.moveTo(q[0],q[1]);ctx.lineTo(width/2+cursor.x*r*.35,height/2+cursor.y*r*.35);ctx.strokeStyle='rgba('+color+',.13)';ctx.stroke();}}
      }
      for(var index=0;index<points.length;index+=(quality==='low'?2:1)) {
        var point=points[index],shrink=impulse>0?1-Math.sin(impulse*Math.PI)*.16:1;
        var pt=project(point[0]*breath*shrink,point[1]*breath*shrink,point[2]*breath*shrink,r,rotation);
        var alpha=.15+(pt[2]+1)*.27+boost*.1;
        ctx.fillStyle='rgba('+(index%7===0?'87,223,233':color)+','+Math.min(.95,alpha)+')';
        ctx.beginPath();ctx.arc(pt[0],pt[1],(.65+(pt[2]+1)*.55)*pt[3],0,Math.PI*2);ctx.fill();
      }
      // Fingerprint contours inside the identity sphere. No biometric data.
      ctx.save();ctx.translate(width/2,height/2);ctx.scale(r/130,r/130);
      ctx.strokeStyle='rgba('+color+',.62)';ctx.lineWidth=1.2;
      for(var f=0;f<8;f++){ctx.beginPath();ctx.ellipse(0,8,17+f*7,25+f*8,-.18,.30+f*.02,Math.PI*1.91);ctx.stroke();}
      ctx.beginPath();ctx.moveTo(-5,12);ctx.bezierCurveTo(3,-28,29,-8,19,30);ctx.bezierCurveTo(11,54,4,66,-2,72);ctx.stroke();
      ctx.strokeStyle='rgba(135,224,243,.47)';ctx.beginPath();ctx.moveTo(0,-84);ctx.lineTo(64,-60);ctx.lineTo(57,18);ctx.quadraticCurveTo(48,61,0,87);ctx.quadraticCurveTo(-48,61,-57,18);ctx.lineTo(-64,-60);ctx.closePath();ctx.stroke();ctx.restore();
      var wave=(t*.13)%1;ctx.beginPath();ctx.ellipse(width/2,height/2,r*(1+wave*.9),r*(.28+wave*.12),-.2,0,Math.PI*2);ctx.strokeStyle='rgba('+color+','+((1-wave)*.21)+')';ctx.stroke();
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

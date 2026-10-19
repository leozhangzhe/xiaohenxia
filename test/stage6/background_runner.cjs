'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
class Events {
  constructor(){this.events={};}
  addEventListener(k,fn){(this.events[k] ||= new Set()).add(fn);}
  removeEventListener(k,fn){this.events[k]?.delete(fn);}
  emit(k,event={}){for(const fn of [...(this.events[k] || [])])fn(event);}
  count(){return Object.values(this.events).reduce((n,s)=>n+s.size,0);}
}
class Element extends Events {
  constructor(){super();this.dataset={};this.children=[];this.isConnected=true;this.classList={add(){}};}
  setAttribute(){}
  appendChild(child){child.parent=this;this.children.push(child);return child;}
  remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
  getBoundingClientRect(){return {left:0,top:0,width:1920,height:1080};}
}
function fixture(opts={}) {
  const win=new Events(),doc=new Events(),root=new Element();
  let next=0, draws=0, programs=0, buffers=0, shaders=0, contexts=0, observers=0;
  const raf=new Map(),idle=new Map();
  const gl=new Proxy({
    createShader(){shaders++;return {};},deleteShader(){shaders--;},
    createProgram(){programs++;return {};},deleteProgram(){programs--;},
    createBuffer(){buffers++;return {};},deleteBuffer(){buffers--;},
    getShaderParameter(){return !opts.compileFail;},getProgramParameter(){return true;},
    getExtension(){return {loseContext(){contexts--;}};},
    drawArrays(){draws++;},getAttribLocation(){return 0;},getUniformLocation(){return {};}
  },{get:(o,k)=>o[k] ?? (()=>{})});
  doc.documentElement=new Element();doc.hidden=false;doc.hasFocus=()=>true;
  doc.readyState='complete';doc.querySelector=()=>null;
  doc.createElement=()=>{const e=new Element();e.getContext=()=>{if(opts.noGL)return null;contexts++;return gl;};return e;};
  const motion=Object.assign(new Events(),{matches:!!opts.reduce});
  const small=Object.assign(new Events(),{matches:!!opts.mobile});
  Object.assign(win,{document:doc,navigator:{hardwareConcurrency:opts.low?2:8,deviceMemory:8},
    matchMedia:q=>q.includes('reduced')?motion:small,devicePixelRatio:3,
    requestAnimationFrame:fn=>{raf.set(++next,fn);return next;},cancelAnimationFrame:id=>raf.delete(id),
    requestIdleCallback:fn=>{idle.set(++next,fn);return next;},cancelIdleCallback:id=>idle.delete(id)});
  class Observer {constructor(fn){this.fn=fn;observers++;}observe(){}disconnect(){if(!this.closed){observers--;this.closed=true;}}}
  const sandbox={window:win,MutationObserver:Observer,ResizeObserver:Observer,IntersectionObserver:Observer};
  const base=path.resolve(__dirname,'../../spiderfoot/static');
  vm.runInNewContext(fs.readFileSync(base+'/vendor/liquid-metal/liquid-metal.js','utf8'),sandbox);
  vm.runInNewContext(fs.readFileSync(base+'/js/app-background.js','utf8'),sandbox);
  return {win,doc,root,motion,small,raf,idle,
    init(){for(const fn of [...idle.values()])fn();idle.clear();},
    step(t){const list=[...raf.values()];raf.clear();list.forEach(fn=>fn(t));},
    stats:()=>({draws,programs,buffers,shaders,contexts,observers}),
    listeners:()=>win.count()+doc.count()+motion.count()+small.count()+root.children.reduce((n,c)=>n+c.count(),0)};
}
const cases={
  lifecycle(){const f=fixture(),h=f.win.AppBackground.mount(f.root);assert.equal(f.raf.size,0);f.init();f.step(40);assert.equal(f.stats().draws,1);h.destroy();h.destroy();assert.deepEqual(f.stats(),{draws:1,programs:0,buffers:0,shaders:0,contexts:0,observers:0});assert.equal(f.listeners(),0);assert.equal(f.raf.size+f.idle.size+f.root.children.length,0);},
  reduced(){const f=fixture({reduce:true});f.win.AppBackground.mount(f.root);f.init();assert.equal(f.root.dataset.renderState,'reduced');assert.equal(f.stats().contexts+f.raf.size,0);f.motion.matches=false;f.motion.emit('change');f.step(40);assert.equal(f.stats().draws,1);f.motion.matches=true;f.motion.emit('change');assert.equal(f.raf.size,0);f.win.AppBackground.destroy();},
  fallback(){for(const options of [{noGL:true},{compileFail:true}]){const f=fixture(options);f.win.AppBackground.mount(f.root);f.init();assert.equal(f.root.dataset.renderState,'fallback');assert.equal(f.root.dataset.webgl,'false');assert.equal(f.raf.size,0);f.win.AppBackground.destroy();assert.equal(f.stats().shaders+f.stats().programs+f.stats().contexts,0);}},
  pause(){const f=fixture();f.win.AppBackground.mount(f.root);f.init();f.step(40);f.doc.hidden=true;f.doc.emit('visibilitychange');assert.equal(f.raf.size,0);f.step(80);assert.equal(f.stats().draws,1);f.doc.hidden=false;f.doc.emit('visibilitychange');assert.equal(f.raf.size,1);f.win.emit('blur');assert.equal(f.raf.size,0);f.win.emit('focus');assert.equal(f.raf.size,1);f.win.AppBackground.destroy();},
  singleton(){const f=fixture(),a=f.win.AppBackground.mount(f.root);assert.equal(a,f.win.AppBackground.mount(f.root));assert.equal(f.root.children.length,1);f.init();const second=new Element();f.win.AppBackground.mount(second,{mode:'workspace'});assert.equal(f.root.children.length,0);assert.equal(second.children.length,1);assert.equal(f.root.dataset.renderState,'destroyed');f.win.AppBackground.destroy();assert.equal(f.stats().contexts,0);},
  mobile(){const f=fixture({mobile:true});f.win.AppBackground.mount(f.root);f.init();f.step(60);assert(Number(f.root.dataset.pixelRatio)<=.85);assert.equal(f.root.dataset.quality,'economy');assert(f.root.children[0].width*f.root.children[0].height<400000);f.win.AppBackground.destroy();},
  pixels(){for(const mode of ['auth','workspace']){const f=fixture();f.win.AppBackground.mount(f.root,{mode,pixelRatio:9});f.init();f.step(60);assert(Number(f.root.dataset.pixelRatio)<=(mode==='auth'?1.5:1.25));assert(f.root.children[0].width*f.root.children[0].height<= (mode==='auth'?862000:442000));f.win.AppBackground.destroy();}},
  adaptive(){const f=fixture();f.win.AppBackground.mount(f.root);f.init();for(let n=1;n<100;n++)f.step(n*300);assert.equal(f.root.dataset.renderState,'low-performance-still');assert.equal(f.raf.size,0);f.win.AppBackground.destroy();},
  pagehide(){const f=fixture();f.win.AppBackground.mount(f.root);f.init();f.win.emit('pagehide',{persisted:false});assert.equal(f.root.children.length+f.listeners()+f.raf.size,0);assert.equal(f.stats().contexts,0);},
  nonblocking(){const f=fixture();f.win.AppBackground.mount(f.root);assert.equal(f.stats().contexts,0,'GL compilation is deferred beyond the form mount');assert.equal(f.root.count(),0,'no form/root event handlers');assert(!f.doc.events.submit);f.win.AppBackground.destroy();assert.equal(f.idle.size,0);}
};
const name=process.argv[2];cases[name]();console.log(JSON.stringify({case:name,result:'passed'}));

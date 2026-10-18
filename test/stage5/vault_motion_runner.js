'use strict';
const assert=require('assert');
const path=require('path');
const fs=require('fs');
const vm=require('vm');
const sceneAPI=require('../../spiderfoot/static/js/vault-scene.js');
class Events {
  constructor(){this.events={};}
  addEventListener(k,f){(this.events[k]||(this.events[k]=new Set())).add(f);}
  removeEventListener(k,f){if(this.events[k])this.events[k].delete(f);}
  emit(k,e={}){for(const f of this.events[k]||[])f(e);}
  count(){return Object.values(this.events).reduce((n,s)=>n+s.size,0);}
}
class Element extends Events {
  constructor(tag='div'){super();this.tag=tag;this.children=[];this.dataset={};this.style={};this.attrs={};this.className='';this._text='';this.classList={contains:k=>this.className.split(' ').includes(k),add:k=>this.className+=' '+k};}
  set textContent(v){this._text=String(v);this.children=[];}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join('');}
  setAttribute(k,v){this.attrs[k]=String(v);if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,x)=>x.toUpperCase())]=String(v);}
  appendChild(n){this.children.push(n);return n;}
  replaceChildren(...nodes){this.children=nodes;this._text='';}
  getBoundingClientRect(){return {width:600,height:360,left:0,top:0};}
  querySelectorAll(selector){return this.children.flatMap(n=>[...(selector.startsWith('.')&&n.className.split(' ').includes(selector.slice(1))?[n]:[]),...n.querySelectorAll(selector)]);}
  animate(){Element.animated++;return {cancel(){},onfinish:null,oncancel:null};}
}
Element.animated=0;
function context(){return new Proxy({createRadialGradient:()=>({addColorStop(){}})}, {get:(o,k)=>o[k]||(()=>{})});}
function fixture(opts={}){
  const env=new Events();env.document=new Events();env.document.hidden=false;env.devicePixelRatio=3;
  const media={reduce:Object.assign(new Events(),{matches:!!opts.reduce}),small:Object.assign(new Events(),{matches:!!opts.small})};
  env.matchMedia=q=>q.includes('reduced')?media.reduce:media.small;
  let id=0, rafs=new Map();env.requestAnimationFrame=fn=>{rafs.set(++id,fn);return id;};env.cancelAnimationFrame=id=>rafs.delete(id);
  env.step=time=>{const pending=[...rafs.values()];rafs.clear();pending.forEach(f=>f(time));};env.pending=()=>rafs.size;
  const canvas=new Element('canvas');canvas.getContext=type=>{assert.equal(type,'2d','WebGL is not needed or initialized');if(opts.throwCanvas)throw Error('disabled');return opts.noCanvas?null:context();};
  return {env,media,canvas};
}
function lifecycle(){
  for(const option of [{reduce:true},{small:true},{noCanvas:true},{throwCanvas:true}]){const f=fixture(option),s=sceneAPI.create(f.canvas,f.env);assert.equal(f.env.pending(),0);assert(s.snapshot().static);assert.equal(f.canvas.dataset.particles,'0');s.destroy();}
  const f=fixture(),s=sceneAPI.create(f.canvas,f.env,{surface:f.canvas});assert.equal(f.canvas.dataset.dpr,'1.5');assert.equal(f.env.pending(),1);
  f.env.step(16);assert.equal(s.snapshot().frames,1);
  f.env.document.hidden=true;f.env.document.emit('visibilitychange');assert.equal(f.env.pending(),0);f.env.step(100);assert.equal(s.snapshot().frames,1);
  f.env.document.hidden=false;f.env.document.emit('visibilitychange');assert.equal(f.env.pending(),1);
  f.media.reduce.matches=true;f.media.reduce.emit('change');assert.equal(f.env.pending(),0);
  f.media.reduce.matches=false;f.media.reduce.emit('change');assert.equal(f.env.pending(),1);
  s.pause(true);assert.equal(f.env.pending(),0);s.pause(false);assert.equal(f.env.pending(),1);
  s.destroy();s.destroy();assert.equal(f.env.pending(),0);assert.equal(f.env.count()+f.env.document.count()+f.media.reduce.count()+f.media.small.count()+f.canvas.count(),0);
  assert.equal(f.canvas.width,1);assert(s.snapshot().disposed);return 'pause/resume, media changes, DPR, idempotent disposal';
}
function adaptive(){const f=fixture(),s=sceneAPI.create(f.canvas,f.env);for(let i=1;i<=200;i++)f.env.step(i*50);assert.equal(s.snapshot().quality,'static');assert.equal(f.env.pending(),0);s.destroy();return 'low FPS reduces particles then switches to static';}
function refreshCap(){const f=fixture(),s=sceneAPI.create(f.canvas,f.env);for(let i=1;i<=240;i++)f.env.step(i*1000/240);assert(s.snapshot().frames<=61);s.destroy();return '240Hz RAF input does not exceed 60 drawing frames per second';}
function offscreen(){const f=fixture();let observer,disconnected=false;f.env.IntersectionObserver=class{constructor(fn){observer=fn;}observe(){}disconnect(){disconnected=true;}};const s=sceneAPI.create(f.canvas,f.env);observer([{isIntersecting:false}]);assert.equal(f.env.pending(),0);observer([{isIntersecting:true}]);assert.equal(f.env.pending(),1);s.destroy();assert(disconnected);return 'offscreen pauses and observer is disconnected';}
function ui(reduce=false){
  const doc=new Events();doc.hidden=false;doc.documentElement=new Element();doc.body=new Element();doc.elements={};
  doc.createElement=t=>new Element(t);doc.createElementNS=(_,t)=>new Element(t);doc.getElementById=id=>doc.elements[id]||null;doc.querySelector=()=>null;doc.querySelectorAll=()=>[];
  const win=new Events();win.document=doc;win.matchMedia=()=>Object.assign(new Events(),{matches:reduce});
  const sandbox={window:win,Set,Map,WeakSet,module:{exports:{}},Event:class{constructor(type){this.type=type;}}};
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../../spiderfoot/static/js/vault-motion.js'),'utf8'),sandbox);
  return {doc,win,api:win.vaultMotion};
}
function realStates(){
  const {doc,api}=ui();const target=doc.elements['vault-task-network']=new Element();
  const task={id:'synthetic',query:'sy***',status:'running',sources:[{source:'sherlock',status:'running'},{source:'maigret',status:'failed'},{source:'hibp',status:'not_configured'}]};
  api.task(task);let nodes=target.children.filter(n=>n.dataset.source);assert.equal(nodes.length,6);assert.equal(nodes.find(n=>n.dataset.source==='sherlock').dataset.state,'running');assert.equal(nodes.find(n=>n.dataset.source==='maigret').dataset.state,'failed');
  task.sources[0].status='completed';api.task(task);nodes=target.children.filter(n=>n.dataset.source);assert.equal(nodes.find(n=>n.dataset.source==='sherlock').dataset.state,'completed');
  task.sources[0].status='cancelled';api.task(task);assert.equal(target.children.find(n=>n.dataset.source==='sherlock').dataset.state,'cancelled');
  api.unavailable();assert.equal(target.dataset.state,'unavailable');assert(target.textContent.includes('数据不可用'));
  const selection=doc.elements['vault-selection-network']=new Element();api.selection('email');assert.deepEqual(selection.children.filter(n=>n.dataset.state==='selected').map(n=>n.dataset.source),['holehe','hibp']);
  const td=new Element();api.requestTrack(td,{id:'synthetic-request',action_type:'hide',status:'platform_contacted'});const list=td.children[0].children[2];assert.equal(list.children.filter(n=>n.attrs['aria-current']==='step').length,1);assert.equal(list.children.find(n=>n.attrs['aria-current']==='step').textContent,'已联系平台');
  const number=new Element();api.ticker(number,12);assert.equal(number.textContent,'12');api.ticker(number,'unavailable');assert.equal(number.textContent,'12');
  task.query='<img onerror=alert(1)>';api.task(task);assert(target.textContent.includes(task.query));return 'state, cancellation, failure, selection, manual status, safe text';
}
function reduced(){const {api}=ui(true);const n=new Element();Element.animated=0;api.ticker(n,9);assert.equal(n.textContent,'9');assert.equal(Element.animated,0);return 'actual counts remain readable without motion';}
function form(){
  const {doc,win,api}=ui();const canvas=new Element('canvas'),button=new Element('button'),form=new Element('form');let disposed=false,submitted=0;
  canvas.parentElement=new Element();form.checkValidity=()=>true;form.querySelector=()=>button;
  doc.querySelector=selector=>selector==='[data-vault-scene]'?canvas:selector==='.fl-auth-form form'?form:null;
  win.VaultScene={create:()=>({pause(){},feedback(type){if(type==='submit')submitted++;},destroy(){disposed=true;}})};
  win.emit('DOMContentLoaded');let prevented=false;form.emit('submit',{preventDefault(){prevented=true;}});assert.equal(prevented,false);assert.equal(submitted,1);
  win.emit('pagehide');assert(disposed);assert.equal(form.count()+button.count(),0);api.destroy();assert.equal(doc.documentElement.dataset.vaultDisposed,'true');return 'form submit is never intercepted; pagehide releases listeners';
}
const cases={lifecycle,adaptive,refreshCap,offscreen,realStates,reduced,form};
const name=process.argv[2];console.log(JSON.stringify({case:name,result:cases[name]()}));

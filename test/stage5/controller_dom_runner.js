'use strict';
const path=require('path');
class Element {
  constructor(){this.children=[];this._text='';this.style={};this.value='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  appendChild(node){this.children.push(node);return node;}
  replaceChildren(){this.children=[];this._text='';}
}
const elements={};
let ready,lists=0;
global.document={createElement:()=>new Element(),getElementById:id=>elements[id]||(elements[id]=new Element())};
global.addEventListener=(name,fn)=>{ready=fn;};
global.docroot='';
const task={id:'a'.repeat(32),query:'sy***',status:'completed',sources:[{source:'sherlock',status:'completed',message:'done',limitations:'limited'}],results:[]};
global.fetch=async url=>({ok:true,status:200,json:async()=>{
  if(url==='/liveavailability')return [];
  if(url==='/livelist'){lists++;return lists===1?[]:[Object.assign({},task,{status:lists===2?'running':'completed'})];}
  return task;
}});
require(path.resolve(__dirname,'../../spiderfoot/static/js/live-search.js'));
ready();
(async()=>{
  await new Promise(setImmediate);
  document.getElementById('live-kind').value='username';document.getElementById('live-query').value='synthetic_demo';
  elements['live-start'].onclick();
  for(let i=0;i<10;i++)await new Promise(setImmediate);
  console.log(JSON.stringify({message:elements['live-message'].textContent,tasks:elements['live-tasks'].textContent,title:elements['live-title'].textContent}));
})();

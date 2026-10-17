'use strict';
const fs=require('fs'),path=require('path');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
let htmlWrites=0;
class Element {
  constructor(tag){this.tagName=tag;this.children=[];this._text='';this.style={};}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  set innerHTML(value){htmlWrites++;}
  replaceChildren(...nodes){this.children=nodes;this._text='';}
  appendChild(node){this.children.push(node);return node;}
}
global.document={createElement:tag=>new Element(tag)};
const view=require(path.resolve(__dirname,'../../spiderfoot/static/js/live-search.js'));
const root=new Element('div');
view.renderResults(root,input.task,input.source||'',input.type||'');
const links=[];
function walk(node){if(node.tagName==='a')links.push(node.href);node.children.forEach(walk);}
walk(root);
console.log(JSON.stringify({text:root.textContent,links,htmlWrites,cards:root.children.filter(x=>x.tagName==='article').length}));

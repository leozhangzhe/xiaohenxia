const fs=require('fs'),vm=require('vm'),path=require('path');
const scenario=JSON.parse(fs.readFileSync(0,'utf8')||'{}');
class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.style={};this.value='';this._text='';this.attributes={};this.classList={add(){},remove(){}};}
  set textContent(v){this._text=String(v);this.children=[];}
  get textContent(){return this._text+this.children.map(e=>e.textContent).join('');}
  set innerHTML(v){this._html=v;this.children=[];}
  appendChild(e){this.children.push(e);return e;}
  replaceChildren(){this.children=[];this._text='';}
  setAttribute(k,v){this.attributes[k]=String(v);}
  querySelector(){return null;}
}
const elements={},requests=[],events={},writes=[];
const node=id=>elements[id]||(elements[id]=new Element());
const all=e=>[e,...e.children.flatMap(all)];
const context={console,URLSearchParams,FormData,Date,Number,Math,Promise,parseInt,setTimeout,clearTimeout,
  window:{},alertify:{success(){},error(){}},confirm:()=>true,
  document:{getElementById:node,createElement:t=>new Element(t),querySelectorAll:()=>[],addEventListener:(k,f)=>events[k]=f},
  fetch:async(url,options={})=>{
    requests.push({url,method:options.method||'GET'});
    if(options.method==='POST'){writes.push(Object.fromEntries(options.body));return {ok:true,json:async()=>({success:true})};}
    if(scenario.failure&&url.includes('adminlist'))return {ok:false,status:503};
    const u=new URL(url,'https://example.invalid'),page=Number(u.searchParams.get('page')||1),size=Number(u.searchParams.get('page_size')||20);
    const total=scenario.empty?0:1000;
    const items=Array.from({length:Math.max(0,Math.min(size,total-(page-1)*size))},(_,i)=>({
      id:'request-'+((page-1)*size+i),username:'synthetic_admin',action_type:'hide',platform:'<img src=x onerror=alert(1)> synthetic-'+((page-1)*size+i),
      content_preview:'https://example.invalid/synthetic',status:'recorded',user_confirmed:true,
      manual_note:'synthetic note',created_at:1700000000,updated_at:1700000000
    }));
    return {ok:true,json:async()=>({success:true,total,items})};
  }
};
vm.createContext(context);
const template=fs.readFileSync(path.resolve(__dirname,'../../spiderfoot/templates/privacyaction.tmpl'),'utf8');
const script=template.match(/<script>([\s\S]*?)<\/script>/)[1].replaceAll('${docroot}','');
vm.runInContext(script,context);
const flush=async()=>{for(let i=0;i<10;i++)await new Promise(setImmediate);};
(async()=>{
  events.DOMContentLoaded();await flush();
  const snapshot=()=>({adminRows:node('adminRequestList').children.length,adminEditors:all(node('adminRequestList')).filter(e=>['INPUT','SELECT','TEXTAREA'].includes(e.tagName)).length,
    ownRows:node('listBody').children.length,adminText:node('adminRequestList').textContent,pager:node('adminRequestPager').textContent,htmlElements:all(node('adminRequestList')).filter(e=>e.tagName==='IMG').length});
  const before=snapshot();
  if(scenario.next){const next=all(node('adminRequestPager')).find(e=>e.tagName==='BUTTON'&&e.textContent==='下一页');if(next&&!next.disabled){next.onclick();await flush();}}
  if(scenario.edit){const row=node('adminRequestList').children[0];if(row){row.open=true;if(row.ontoggle)row.ontoggle();const save=all(row).find(e=>e.tagName==='BUTTON'&&e.textContent==='保存人工跟进');if(save){save.onclick();await flush();}}}
  console.log(JSON.stringify({before,after:snapshot(),requests,writes}));
})().catch(e=>{console.error(e);process.exitCode=1;});

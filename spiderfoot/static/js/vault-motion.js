/* Presentation only: consumes owner-scoped data already returned by existing APIs. */
(function(root){
  'use strict';
  var doc=root.document, scenes=[], cleanups=[], animations=new Set(), seen=new Set(), previous=new Map(), observed=new WeakSet(), openRequests=new Set();
  var reduced=root.matchMedia?root.matchMedia('(prefers-reduced-motion: reduce)'):{matches:true};
  var paused=false,destroyed=false,mini=null,overviewUnavailable=false;
  var names={spiderfoot:'SpiderFoot',sherlock:'Sherlock',maigret:'Maigret',whatsmyname:'WhatsMyName',holehe:'Holehe',hibp:'HIBP'};
  var labels={waiting:'等待',running:'运行',completed:'完成',partial:'部分完成',failed:'失败',timeout:'超时',not_configured:'未配置',cancelled:'已取消',idle:'未选择'};
  function canMove(){return !destroyed&&!paused&&!reduced.matches&&!doc.hidden;}
  function listen(target,event,fn){target.addEventListener(event,fn);cleanups.push(function(){target.removeEventListener(event,fn);});}
  function element(tag,text,cls){var n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;}
  function animate(n,frames,options){if(!canMove()||!n.animate)return null;var a=n.animate(frames,options);animations.add(a);a.onfinish=a.oncancel=function(){animations.delete(a);};return a;}
  function ticker(n,value,suffix){
    if(!n)return;value=Number(value);if(!Number.isFinite(value))return;suffix=suffix||'';
    var old=Number(n.dataset.vaultValue),changed=n.dataset.vaultValue!==String(value);n.dataset.vaultValue=String(value);
    n.textContent=value+suffix;
    // A visual roll of the actual value, never intermediate fabricated business counts.
    if(changed){animate(n,[{transform:'translateY(7px)',opacity:.25},{transform:'translateY(0)',opacity:1}],{duration:240,easing:'cubic-bezier(.16,1,.3,1)'});if(Number.isFinite(old)&&value>old)n.classList.add('vault-count-changed');}
  }
  function overview(ok){
    overviewUnavailable=overviewUnavailable||!ok;
    var welcome=doc.querySelector('.fl-welcome');if(welcome)welcome.dataset.vaultUnavailable=String(overviewUnavailable);
    if(mini)mini.pause(overviewUnavailable||paused);
  }
  function network(container,task,selection){
    if(!container)return;
    var current=task&&task.id||'selection',fingerprint=JSON.stringify([current,task&&task.query,(task&&task.sources||[]).map(function(s){return [s.source,s.status];}),selection]);
    if(container.dataset.signature===fingerprint)return;container.dataset.signature=fingerprint;
    var svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 640 320');svg.setAttribute('aria-hidden','true');
    var center=element('div',task?task.query:'检索目标','vault-network-center');
    var centerSub=element('small',task?'实际任务 · '+(labels[task.status]||task.status):'按输入类型选择来源');center.appendChild(centerSub);
    container.replaceChildren(svg,center);
    var positions=[[145,56],[320,35],[495,56],[145,264],[320,285],[495,264]];
    Object.keys(names).forEach(function(source,index){
      var info=task&&(task.sources||[]).find(function(s){return s.source===source;}),state=info?info.status:selection&&selection.indexOf(source)>=0?'selected':'idle';
      var p=positions[index],path=doc.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d','M320 160 Q'+p[0]+' 160 '+p[0]+' '+p[1]);path.setAttribute('class','vault-orbit-line '+state);svg.appendChild(path);
      var n=element('div',undefined,'vault-source-node '+state);n.dataset.source=source;n.dataset.state=state;n.style.left=(p[0]/640*100)+'%';n.style.top=(p[1]/320*100)+'%';
      n.appendChild(element('strong',names[source]));n.appendChild(element('small',state==='selected'?'本次来源':labels[state]||state));container.appendChild(n);
      var key=current+':'+source,prior=previous.get(key);if(prior&&prior!==state&&['completed','failed','timeout'].indexOf(state)>=0)animate(n,[{boxShadow:'0 0 0 0 currentColor'},{boxShadow:'0 0 0 12px transparent'}],{duration:300});previous.set(key,state);
    });
    container.dataset.state=task?task.status:'selection';
  }
  function updateTask(task){network(doc.getElementById('vault-task-network'),task);}
  function taskUnavailable(){var n=doc.getElementById('vault-task-network');if(n){n.replaceChildren(element('p','数据不可用，无法展示来源连接。','vault-network-error'));n.dataset.state='unavailable';n.dataset.signature='';}}
  function select(kind){network(doc.getElementById('vault-selection-network'),null,{domain:['spiderfoot'],username:['sherlock','maigret','whatsmyname'],email:['holehe','hibp']}[kind]||[]);}
  function results(container,task){
    Array.from(container.querySelectorAll('.fl-result')).forEach(function(n,i){
      var key=(task.id||'task')+':'+n.textContent;if(seen.has(key))return;seen.add(key);
      animate(n,[{opacity:.4,transform:'translateY(7px)'},{opacity:1,transform:'translateY(0)'}],{duration:220,delay:Math.min(i,5)*25,fill:'backwards',easing:'cubic-bezier(.16,1,.3,1)'});
    });
  }
  function requestTrack(container,item){
    if(!container||item.action_type==='mask')return;
    // State keys below mirror the existing API; no elapsed time advances the timeline.
    var states={draft:'草稿',recorded:'已记录',awaiting_manual:'待人工处理',platform_contacted:'已联系平台',platform_processing:'平台处理中',completed:'已完成',unable:'无法处理'};
    var details=element('details',undefined,'vault-request-track');details.appendChild(element('summary','查看跟进状态'));
    details.appendChild(element('p','仅显示当前记录状态，不推断此前步骤已经执行。','fl-muted fl-small'));
    var list=element('ol'),key='request:'+item.id,prior=previous.get(key);
    details.open=openRequests.has(key);details.ontoggle=function(){if(details.open)openRequests.add(key);else openRequests.delete(key);};
    Object.keys(states).forEach(function(state){var li=element('li',states[state]);li.dataset.state=state;if(state===item.status){li.className='current';li.setAttribute('aria-current','step');if(prior&&prior!==state)animate(li,[{opacity:.35,transform:'translateY(-7px)'},{opacity:1,transform:'translateY(0)'}],{duration:260});}list.appendChild(li);});
    var keys=Object.keys(states),at=keys.indexOf(item.status);
    if(at>=0){var cursor=element('span',undefined,'vault-timeline-cursor');cursor.setAttribute('aria-hidden','true');cursor.style.top=(at*31+12)+'px';list.appendChild(cursor);if(prior&&prior!==item.status){var from=keys.indexOf(prior);if(from>=0)animate(cursor,[{transform:'translateY('+((from-at)*31)+'px)'},{transform:'translateY(0)'}],{duration:280,easing:'cubic-bezier(.16,1,.3,1)'});}}
    previous.set(key,item.status);details.appendChild(list);container.appendChild(details);
  }
  function sync(){
    doc.documentElement.dataset.vaultPaused=String(paused||doc.hidden||reduced.matches);
    scenes.forEach(function(s){s.pause(paused);});if(mini)mini.pause(paused||overviewUnavailable);
    if(!canMove())animations.forEach(function(a){a.cancel();});
  }
  function destroy(){if(destroyed)return;destroyed=true;scenes.forEach(function(s){s.destroy();});if(mini)mini.destroy();animations.forEach(function(a){a.cancel();});animations.clear();cleanups.forEach(function(f){f();});cleanups=[];seen.clear();previous.clear();openRequests.clear();doc.documentElement.dataset.vaultDisposed='true';}
  var api={ticker:ticker,overview:overview,task:updateTask,unavailable:taskUnavailable,selection:select,results:results,requestTrack:requestTrack,destroy:destroy};
  root.vaultMotion=api;if(typeof module!=='undefined')module.exports=api;
  if(!doc||!root.addEventListener)return;
  listen(root,'DOMContentLoaded',function(){
    var auth=doc.querySelector('[data-vault-scene]');
    if(auth&&root.VaultScene){var scene=root.VaultScene.create(auth,root,{surface:auth.parentElement,cyan:doc.body.classList.contains('fl-register')});scenes.push(scene);
      var form=doc.querySelector('.fl-auth-form form'),submit=form&&form.querySelector('[type=submit]');
      if(submit){listen(submit,'pointerenter',function(){scene.feedback('hover');});listen(submit,'pointerleave',function(){scene.feedback('leave');});}
      if(form)listen(form,'submit',function(){if(form.checkValidity())scene.feedback('submit');});
      if(doc.querySelector('.fl-notice.error'))scene.feedback('error');
    }
    var small=doc.querySelector('[data-vault-mini]');if(small&&root.VaultScene)mini=root.VaultScene.create(small,root,{mini:true});
    if(root.IntersectionObserver){var networkObserver=new root.IntersectionObserver(function(entries){entries.forEach(function(entry){entry.target.dataset.vaultOffscreen=String(!entry.isIntersecting);});});doc.querySelectorAll('.vault-network').forEach(function(n){networkObserver.observe(n);});cleanups.push(function(){networkObserver.disconnect();});}
    var toggle=doc.getElementById('vault-motion-toggle');if(toggle)listen(toggle,'click',function(){paused=!paused;toggle.setAttribute('aria-pressed',String(paused));toggle.textContent=paused?'开启视觉动效':'暂停视觉动效';sync();});
    doc.querySelectorAll('.fl-overview .fl-panel,.fl-summary,.fl-request-main>.pg-card').forEach(function(n,i){if(observed.has(n))return;observed.add(n);animate(n,[{opacity:.5,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:240,delay:Math.min(i,4)*30});});
    ['stat-high','pg-high-count','risk-stat-total','stat-error'].forEach(function(id){var risk=doc.getElementById(id);if(risk&&root.MutationObserver){var last=risk.textContent;var watcher=new root.MutationObserver(function(){var next=risk.textContent;if(next!==last&&/^\d+$/.test(next)&&Number(next)>Number(last))animate(risk,[{color:'#a52d37',opacity:.45},{color:'#20233c',opacity:1}],{duration:280});last=next;});watcher.observe(risk,{childList:true,characterData:true,subtree:true});cleanups.push(function(){watcher.disconnect();});}});
    var alerts=doc.getElementById('alert-list-container')||doc.getElementById('risk-alerts-container');
    if(alerts&&root.MutationObserver){var mark=function(){alerts.querySelectorAll('.pg-alert-card.high,[data-risk="HIGH"]').forEach(function(n){var key='risk:'+(n.id||n.textContent);if(seen.has(key))return;seen.add(key);animate(n,[{backgroundColor:'#fff0f2'},{backgroundColor:'#ffffff'}],{duration:280});});};var alertObserver=new root.MutationObserver(mark);alertObserver.observe(alerts,{childList:true,subtree:true});cleanups.push(function(){alertObserver.disconnect();});mark();}
    sync();
  });
  listen(doc,'visibilitychange',sync);if(reduced.addEventListener)listen(reduced,'change',sync);
  listen(root,'pagehide',destroy);listen(root,'pageshow',function(e){if(e.persisted&&destroyed)root.location.reload();});
})(typeof window!=='undefined'?window:globalThis);

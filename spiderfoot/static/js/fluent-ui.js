/* C interface: navigation and owner-scoped overview, existing read APIs only. */
(function () {
  'use strict';
  function node(tag,text,cls){var n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;}
  var sourceNames={spiderfoot:'SpiderFoot',sherlock:'Sherlock',maigret:'Maigret',whatsmyname:'WhatsMyName',holehe:'Holehe',hibp:'HIBP'};
  var states={waiting:'等待',running:'运行中',completed:'已完成',partial:'部分完成',failed:'失败',not_configured:'未配置',timeout:'超时',cancelled:'已取消'};
  function pill(state,text){return node('span',text||states[state]||state,'fl-pill '+state);}
  function time(value){return value&&Number.isFinite(Number(value))?new Date(Number(value)*1000).toLocaleString('zh-CN',{hour12:false}):'暂无时间';}
  function read(path){return fetch(docroot+path,{cache:'no-store',credentials:'same-origin'}).then(function(r){if(!r.ok)throw new Error('unavailable');return r.json();});}
  function fail(id){var target=document.getElementById(id);if(target){target.textContent='数据不可用，请稍后刷新重试。';target.classList.add('fl-empty');}}
  window.fluentUI={node:node,pill:pill,time:time,sourceNames:sourceNames};
  var menu=document.getElementById('fl-menu'),sidebar=document.getElementById('sidebar');
  if(menu&&sidebar)menu.onclick=function(){var open=sidebar.classList.toggle('is-open');menu.setAttribute('aria-expanded',String(open));};
  document.querySelectorAll('.fl-nav.active').forEach(function(a){a.setAttribute('aria-current','page');});
  if(!document.getElementById('fl-recent-tasks'))return;
  read('/livelist').then(function(tasks){
    if(!Array.isArray(tasks))throw new Error('invalid');
    if(window.vaultMotion){window.vaultMotion.overview(true);window.vaultMotion.ticker(document.getElementById('fl-live-count'),tasks.length);}else document.getElementById('fl-live-count').textContent=tasks.length;
    var count=tasks.reduce(function(n,t){return n+(t.results||[]).length;},0);if(window.vaultMotion)window.vaultMotion.ticker(document.getElementById('fl-result-count'),count);else document.getElementById('fl-result-count').textContent=count;
    var target=document.getElementById('fl-recent-tasks');target.replaceChildren();
    if(!tasks.length){target.appendChild(node('p','暂无统一检索任务。开始一次检索，按来源查看结果与限制。','fl-muted fl-small'));return;}
    tasks.slice(0,5).forEach(function(t){
      var row=node('div',undefined,'fl-overview-task'),a=node('a',t.query);a.href=docroot+'/livesearch#results/'+encodeURIComponent(t.id);row.appendChild(a);row.appendChild(pill(t.status));
      row.appendChild(node('small',(t.sources||[]).map(function(s){return sourceNames[s.source]||s.source;}).join(' / ')));
      row.appendChild(node('small','创建 '+time(t.created_at)+' · '+(t.results||[]).length+' 条已保存线索，需人工核验'));target.appendChild(row);
    });
  }).catch(function(){if(window.vaultMotion)window.vaultMotion.overview(false);['fl-live-count','fl-result-count'].forEach(function(id){document.getElementById(id).textContent='不可用';});fail('fl-recent-tasks');});
  read('/liveavailability').then(function(sources){
    if(!Array.isArray(sources))throw new Error('invalid');
    var target=document.getElementById('fl-source-status');target.replaceChildren();
    sources.forEach(function(s){var row=node('div',undefined,'fl-source-row'),head=node('div',undefined,'fl-source-title');head.appendChild(node('strong',sourceNames[s.source]||s.source));head.appendChild(pill(s.installed&&s.configured?'ready':'not_configured',!s.installed?'未安装':!s.configured?'未配置':'安装就绪'));row.appendChild(head);row.appendChild(node('p',s.limitations));target.appendChild(row);});
  }).catch(function(){if(window.vaultMotion)window.vaultMotion.overview(false);fail('fl-source-status');});
  read('/privacyactionlist?page=1&page_size=1').then(function(data){
    if(!data.success)throw new Error('invalid');
    if(window.vaultMotion)window.vaultMotion.ticker(document.getElementById('fl-request-count'),data.total);else document.getElementById('fl-request-count').textContent=data.total;
    var target=document.getElementById('fl-recent-request');target.replaceChildren();var item=(data.items||[])[0];
    if(!item)target.appendChild(node('p','暂无申请记录。','fl-muted fl-small'));
    else{target.appendChild(node('h3',item.platform));target.appendChild(node('p',item.manual_note||item.note||'等待人工核实。','fl-muted fl-small'));target.appendChild(node('p','创建 '+time(item.created_at),'fl-muted fl-small'));}
    var a=node('a','查看申请记录 →','fl-btn');a.href=docroot+'/privacyaction';target.appendChild(a);
  }).catch(function(){if(window.vaultMotion)window.vaultMotion.overview(false);document.getElementById('fl-request-count').textContent='不可用';fail('fl-recent-request');});
})();

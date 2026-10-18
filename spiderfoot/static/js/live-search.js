(function(global) {
  'use strict';
  var labels = {waiting:'等待',running:'运行',completed:'完成',partial:'部分完成',failed:'失败',not_configured:'未配置',timeout:'超时',cancelled:'已取消'};
  function el(tag, text) { var node=document.createElement(tag); if(text!==undefined) node.textContent=String(text); return node; }
  function allowedLink(value) {
    try { var u=new URL(value); return /^https?:$/.test(u.protocol) && !u.username && !u.password ? u.href : null; } catch (_) { return null; }
  }
  var sourceNames={spiderfoot:'SpiderFoot',sherlock:'Sherlock',maigret:'Maigret',whatsmyname:'WhatsMyName',holehe:'Holehe',hibp:'HIBP'};
  function time(ts){return Number.isFinite(Number(ts))&&ts?new Date(Number(ts)*1000).toLocaleString('zh-CN',{hour12:false}):'暂无时间';}
  function pill(status){var n=el('span',labels[status]||status);n.className='fl-pill '+status;return n;}
  function renderResults(container, task, sourceFilter, typeFilter) {
    container.replaceChildren();
    var results=(task.results||[]).filter(function(row){return (!sourceFilter||row.source===sourceFilter)&&(!typeFilter||row.result_type===typeFilter);});
    if(!results.length) {
      var relevant=(task.sources||[]).filter(function(s){return !sourceFilter||s.source===sourceFilter;});
      var unavailable=relevant.some(function(s){return ['failed','timeout','not_configured','partial'].indexOf(s.status)>=0;});
      var active=relevant.some(function(s){return ['waiting','running'].indexOf(s.status)>=0;})||(!sourceFilter&&['waiting','running'].indexOf(task.status)>=0);
      var text=active?'正在检索，已返回的结果会逐步显示。':unavailable?'部分数据源不可用或未配置；请查看各来源状态，不能据此判定无匹配。':task.status==='cancelled'?'任务已取消；仅保留取消前已保存的结果。':'当前数据源未发现匹配，不代表不存在相关信息。';
      var empty=el('p',text);empty.className='fl-empty';container.appendChild(empty);return;
    }
    results.forEach(function(row) {
      var card=el('article');card.className='fl-result';card.appendChild(el('h3',row.title));
      var main=el('div');main.className='fl-result-main';
      [['数据源',sourceNames[row.source]||row.source],['输入类型',row.input_type],['查询摘要',row.query],['结果类型',row.result_type],['数据值',row.value],['结果状态',row.status],['查询时间',time(row.queried_at)],['可信程度说明',row.confidence]]
        .forEach(function(pair){main.appendChild(el('p',pair[0]+'：'+(pair[1]||'暂无')));});
      card.appendChild(main);
      var detail=el('details');detail.appendChild(el('summary','原始链接、来源与误报说明'));
      [['数据源限制',row.limitations],['来源摘要',row.raw_summary],['核验提醒','匹配线索需人工核验身份归属，可能存在误报。']].forEach(function(pair){detail.appendChild(el('p',pair[0]+'：'+(pair[1]||'暂无')));});
      var link=allowedLink(row.original_url);
      if(link){var a=el('a','查看原始链接');a.href=link;a.target='_blank';a.rel='noopener noreferrer';detail.appendChild(a);}
      else detail.appendChild(el('p','该线索未提供可用的 HTTP/HTTPS 原始链接。'));
      card.appendChild(detail);container.appendChild(card);
    });
  }
  global.liveSearchView={renderResults:renderResults,allowedLink:allowedLink};
  if(typeof module!=='undefined') module.exports=global.liveSearchView;
  if(!global.addEventListener) return;
  global.addEventListener('DOMContentLoaded',function() {
    var taskId=null,task=null,timer=null,availability=[];
    var inputSources={domain:['spiderfoot'],username:['sherlock','maigret','whatsmyname'],email:['holehe','hibp']};
    function get(id){return document.getElementById(id);}
    function motion(method){if(global.vaultMotion&&global.vaultMotion[method])global.vaultMotion[method].apply(null,Array.prototype.slice.call(arguments,1));}
    function message(text,error){var n=get('live-message');n.textContent=text;n.className='fl-live-message'+(error?' is-error':'');}
    function request(path,options){return fetch(docroot+path,options).then(function(r){
      if(r.status===400)return r.json().then(function(body){throw new Error(body.error||'输入格式无效。');});
      if(!r.ok)throw new Error(r.status===403?'安全令牌或权限无效，请刷新页面后重试。':r.status===404?'任务不存在或无权访问，请刷新任务列表。':'检索服务暂不可用，请稍后重试。');return r.json();
    });}
    function write(path,data){return request(path,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},body:new URLSearchParams(data)});}
    function setText(id,text){var n=get(id);if(n)n.textContent=text;}
    function route(){
      if(!global.location)return;
      var bits=global.location.hash.slice(1).split('/'),view=['new','progress','results'].indexOf(bits[0])>=0?bits[0]:'new';
      var content={new:['新建检索','选择输入类型，按来源分别查询。仅检索本人或已获授权的目标。'],progress:['多数据源检索进度','来源独立运行；部分失败不影响已完成的结果。'],results:['统一结果中心','每条线索保留来源与时间；规则匹配不等于身份归属。']}[view];
      get('live-new-view').hidden=view!=='new';get('live-task-view').hidden=view==='new';get('live-result-panel').hidden=view!=='results';
      get('live-view-next').hidden=view==='results';get('live-view-next').href='#results'+(taskId?'/'+taskId:'');
      setText('live-page-title',content[0]);setText('live-page-name',content[0]);setText('live-page-description',content[1]);
      if(document.querySelectorAll)document.querySelectorAll('[data-live-view]').forEach(function(a){a.href=docroot+'/livesearch#'+a.dataset.liveView+(a.dataset.liveView!=='new'&&taskId?'/'+taskId:'');a.classList.toggle('active',a.dataset.liveView===view);if(a.dataset.liveView===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
      if(bits[1]&&/^[a-f0-9]{32}$/.test(bits[1])&&bits[1]!==taskId)loadTask(bits[1]);
    }
    function navigate(view,id){if(global.location){global.location.hash=view+(id?'/'+id:'');route();}}
    function choices(){
      var kind=get('live-kind').value||'domain',target=get('live-source-choices');if(!target)return;target.replaceChildren();
      (inputSources[kind]||[]).forEach(function(source){var info=availability.find(function(a){return a.source===source;}),label=el('label');label.className='fl-source-choice';
        var checkbox=el('input');checkbox.type='checkbox';checkbox.checked=true;checkbox.value=source;checkbox.name='live-source';label.appendChild(checkbox);
        var text=el('span');text.appendChild(el('strong',sourceNames[source]));text.appendChild(el('small',info?info.limitations:'读取安装状态中；缺失工具时将明确显示未配置。'));label.appendChild(text);
        if(info){var state=el('span',!info.installed?'未安装':!info.configured?'未配置':'安装就绪');state.className='fl-pill '+(info.installed&&info.configured?'ready':'not_configured');label.appendChild(state);}target.appendChild(label);
      });
      var hints={domain:['输入域名、网站或公开 IP','网站仅查询主机名，统一入口运行 SpiderFoot DNS 模块。'],username:['输入要检索的用户名','支持字母、数字、点、下划线与连字符；规则匹配需要人工核验。'],email:['输入邮箱地址','Holehe 提供注册信号，不是泄露记录；HIBP 需要有效 API Key。']};
      motion('selection',kind);
      if(document.querySelectorAll)document.querySelectorAll('[data-vault-kind]').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.vaultKind===kind));});
      get('live-query').placeholder=hints[kind][0];setText('live-input-hint',hints[kind][1]);
    }
    function filters(){
      [['live-source-filter','source','全部数据源'],['live-type-filter','result_type','全部结果类型']].forEach(function(spec){
        var select=get(spec[0]),old=select.value;select.replaceChildren();var all=el('option',spec[2]);all.value='';select.appendChild(all);
        var values=(task.results||[]).map(function(r){return r[spec[1]];});if(spec[1]==='source')values=values.concat(task.sources.map(function(s){return s.source;}));
        Array.from(new Set(values)).forEach(function(value){var option=el('option',spec[1]==='source'?(sourceNames[value]||value):value);option.value=value;select.appendChild(option);});select.value=old;
      });
    }
    function render(){if(task){var source=get('live-source-filter').value,type=get('live-type-filter').value;renderResults(get('live-results'),task,source,type);var rows=(task.results||[]).filter(function(r){return (!source||r.source===source)&&(!type||r.result_type===type);});if(global.vaultMotion){motion('ticker',get('live-result-count'),rows.length,' 条已返回线索 · 需人工核验');motion('results',get('live-results'),task);}else setText('live-result-count',rows.length+' 条已返回线索 · 需人工核验');}}
    function loadTask(id){
      clearTimeout(timer);taskId=id;
      request('/liveget?id='+encodeURIComponent(id)).then(function(data){
        if(taskId!==id)return;task=data;motion('task',data);get('live-title').textContent=data.query+' · '+(labels[data.status]||data.status);
        var state=get('live-task-status');if(state){state.replaceChildren();state.appendChild(pill(data.status));}
        setText('live-task-meta','创建 '+time(data.created_at)+' · 更新 '+time(data.updated_at));get('live-sources').replaceChildren();var finished=0;
        data.sources.forEach(function(s){var row=el('div');row.className='fl-source-row';var head=el('div');head.className='fl-source-title';head.appendChild(el('strong',sourceNames[s.source]||s.source));head.appendChild(pill(s.status));row.appendChild(head);row.appendChild(el('p',s.message));row.appendChild(el('p',s.limitations));var when=el('p','查询时间：'+time(s.queried_at));when.className='fl-source-time';row.appendChild(when);get('live-sources').appendChild(row);if(['waiting','running'].indexOf(s.status)<0)finished++;});
        setText('live-source-count',finished+' / '+data.sources.length+' 个来源结束；结束不代表目标安全。');var fill=get('live-progress-fill');if(fill)fill.style.transform='scaleX('+(finished/Math.max(1,data.sources.length))+')';
        get('live-cancel').disabled=['waiting','running'].indexOf(data.status)<0;get('live-delete').disabled=false;filters();render();
        if(['waiting','running'].indexOf(data.status)>=0)timer=setTimeout(function(){loadTask(id);},1000);
        else{message('本次检索已结束；请按各来源状态判断覆盖情况。');loadList();}
      }).catch(function(error){if(taskId!==id)return;task=null;motion('unavailable');message(error.message,true);get('live-results').textContent='数据不可用；请刷新任务列表后重试。';get('live-sources').textContent='数据不可用，无法读取来源进度。';get('live-cancel').disabled=true;get('live-delete').disabled=true;setText('live-result-count','数据不可用');setText('live-source-count','进度不可用');});
    }
    function loadList(){return request('/livelist').then(function(data){
      get('live-tasks').replaceChildren();if(!data.length){var empty=el('p','暂无检索任务');empty.className='fl-empty';get('live-tasks').appendChild(empty);}
      data.forEach(function(item){var b=el('button');b.type='button';b.className='fl-task-option';b.appendChild(el('strong',item.query));b.appendChild(pill(item.status));b.appendChild(el('small','创建 '+time(item.created_at)));b.onclick=function(){loadTask(item.id);navigate('progress',item.id);};get('live-tasks').appendChild(b);});
    }).catch(function(error){get('live-tasks').textContent=error.message;});}
    get('live-start').onclick=function(event){
      if(event)event.preventDefault();var form=get('live-form');if(form&&form.reportValidity&&!form.reportValidity())return;
      var data={input_type:get('live-kind').value,query:get('live-query').value};
      if(document.querySelectorAll){var selected=Array.from(document.querySelectorAll('input[name="live-source"]:checked')).map(function(c){return c.value;});if(!selected.length){message('至少选择一个数据源。',true);return;}data.sources=JSON.stringify(selected);}
      get('live-start').disabled=true;message('正在创建任务...');
      write('/livecreate',data).then(function(data){get('live-query').value='';message('任务已创建，正在分别查询各来源。');loadTask(data.id);navigate('progress',data.id);loadList();}).catch(function(error){message(error.message,true);}).finally(function(){get('live-start').disabled=false;});
    };
    var form=get('live-form');if(form)form.onsubmit=function(e){e.preventDefault();get('live-start').onclick(e);};
    get('live-kind').onchange=choices;
    if(document.querySelectorAll)document.querySelectorAll('[data-vault-kind]').forEach(function(b){b.onclick=function(){get('live-kind').value=b.dataset.vaultKind;choices();};});
    get('live-cancel').onclick=function(){if(taskId)write('/livecancel',{id:taskId}).then(function(){loadTask(taskId);loadList();}).catch(function(e){message(e.message,true);});};
    get('live-delete').onclick=function(){if(taskId&&confirm('删除此任务及保存的结果？'))write('/livedelete',{id:taskId}).then(function(){clearTimeout(timer);taskId=null;task=null;motion('unavailable');get('live-title').textContent='请选择任务';get('live-sources').replaceChildren();get('live-results').replaceChildren();get('live-delete').disabled=true;get('live-cancel').disabled=true;setText('live-source-count','选择任务后显示各来源状态');setText('live-task-meta','只显示当前用户的检索任务');get('live-task-status').replaceChildren();get('live-progress-fill').style.transform='scaleX(0)';setText('live-result-count','');navigate('progress');message('任务及保存的结果已删除。');loadList();}).catch(function(e){message(e.message,true);});};
    get('live-source-filter').onchange=render;get('live-type-filter').onchange=render;
    if(get('live-refresh'))get('live-refresh').onclick=function(){loadList();if(taskId)loadTask(taskId);};
    request('/liveavailability').then(function(data){availability=data;get('live-install').replaceChildren();data.forEach(function(source){get('live-install').appendChild(el('p',(sourceNames[source.source]||source.source)+'：'+(!source.installed?'未安装':!source.configured?'未配置':'已安装')+' · '+source.limitations+' · 重建：'+source.rebuild));});choices();}).catch(function(){get('live-install').textContent='安装状态暂不可用。';});
    choices();loadList();route();global.addEventListener('hashchange',route);
  });
})(typeof window!=='undefined'?window:globalThis);

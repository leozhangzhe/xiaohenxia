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
  function sourceReports(container,task,sourceFilter){
    var sources=(task.sources||[]).filter(function(s){return !sourceFilter||s.source===sourceFilter;});
    if(!sources.length)return;
    var report=el('div');report.className='fl-execution-report';
    var heading=el('div');heading.className='fl-source-row';heading.appendChild(el('h3','检索执行报告'));heading.appendChild(el('p','执行状态与线索数量分别列出；0 条线索不等于查询成功或目标安全。'));report.appendChild(heading);
    var advice={completed:'可使用其他来源补充核验；无匹配不代表不存在相关信息。',partial:'稍后可在新建检索中只选择此来源重试；已保存的线索仍可查看。',failed:'请检查该来源的安装、配置及网络后重试；本次无法判断是否存在匹配。',timeout:'稍后重试或选择其他来源；超时不能判断为未匹配。',not_configured:'请由管理员检查依赖安装或 API 配置；配置完成后重新检索。',cancelled:'如需继续，请重新创建检索；已保存的线索不会因取消而删除。',waiting:'请等待来源开始执行。',running:'请等待该来源返回，结果会自动更新。'};
    sources.forEach(function(s){
      var count=(task.results||[]).filter(function(r){return r.source===s.source;}).length;
      var verdict={completed:count?'查询完成，返回线索':'查询完成，未发现匹配',partial:'部分查询未能完成',failed:'查询失败',timeout:'查询超时',not_configured:'未配置或未安装',cancelled:'查询已取消',waiting:'等待查询',running:'正在查询'}[s.status]||'状态无法识别';
      var row=el('div');row.className='fl-source-row';var title=el('div');title.className='fl-source-title';title.appendChild(el('strong',(sourceNames[s.source]||s.source||'数据源')+'：'+verdict));title.appendChild(pill(s.status));row.appendChild(title);
      row.appendChild(el('p',count+' 条已保存线索'));
      row.appendChild(el('p','来源反馈：'+(s.message||'这条记录未保存具体原因。')));
      if(['partial','failed'].indexOf(s.status)>=0&&(!s.message||['部分完成；部分站点不可用或受限。','数据源不可用。','数据源不可用，请检查安装或网络。'].indexOf(s.message)>=0))row.appendChild(el('p','历史记录未保存具体失败站点或错误类型，无法还原具体原因；重新检索后将保存执行统计和错误分类。'));
      row.appendChild(el('p','下一步：'+(advice[s.status]||'请刷新任务，或联系管理员核查。')));
      row.appendChild(el('p','查询时间：'+time(s.queried_at)));
      if(s.limitations)row.appendChild(el('p','覆盖范围：'+s.limitations));
      report.appendChild(row);
    });container.appendChild(report);
  }
  function renderResults(container, task, sourceFilter, typeFilter, clearFilters) {
    container.replaceChildren();
    sourceReports(container,task,sourceFilter);
    var results=(task.results||[]).filter(function(row){return (!sourceFilter||row.source===sourceFilter)&&(!typeFilter||row.result_type===typeFilter);});
    if(!results.length) {
      var relevant=(task.sources||[]).filter(function(s){return !sourceFilter||s.source===sourceFilter;});
      var unavailable=relevant.some(function(s){return ['failed','timeout','not_configured','partial'].indexOf(s.status)>=0;});
      var active=relevant.some(function(s){return ['waiting','running'].indexOf(s.status)>=0;})||(!sourceFilter&&['waiting','running'].indexOf(task.status)>=0);
      var filtered=(sourceFilter||typeFilter)&&(task.results||[]).length>0;
      var text=filtered?'当前筛选条件下没有结果。此任务共保存 '+task.results.length+' 条线索，请清除或更改筛选。':active?'正在检索，已返回的结果会逐步显示。':unavailable?'本次没有可展示的线索，且存在未能完整完成的来源；具体状态与原因见上方执行报告，不能据此判定无匹配。':task.status==='cancelled'?'任务已取消；仅保留取消前已保存的结果。':'当前数据源未发现匹配，不代表不存在相关信息。';
      // Keep the established unavailable wording for callers and assistive users.
      if(unavailable&&!filtered&&!active)text='数据源不可用或未完整完成。'+text;
      var empty=el('p',text);empty.className='fl-empty';container.appendChild(empty);
      if(filtered&&clearFilters){var reset=el('button','清除筛选');reset.type='button';reset.className='fl-btn';reset.onclick=clearFilters;container.appendChild(reset);}return;
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
    var taskId=null,task=null,timer=null,availability=[],listedTasks=null,listUnavailable=false;
    var taskPage=1,taskPageSize=5,taskPages=1,taskSearch='',taskStatus='',listSequence=0,listLoading=false,searchTimer=null;
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
      else if(view==='results'&&!bits[1]){
        // A generic result-center link must select a saved, owner-scoped task.
        // Explicit IDs (including denied/missing tasks) never fall back to another task.
        if(taskId)navigate('results',taskId);
        else if(listedTasks&&listedTasks.length)navigate('results',listedTasks[0].id);
        else get('live-results').textContent=listUnavailable?'数据不可用；无法读取任务列表，请刷新重试。':listedTasks?'暂无检索任务，请先新建检索。':'正在读取已保存的检索任务…';
      }
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
        Array.from(new Set(values)).forEach(function(value){var option=el('option',spec[1]==='source'?(sourceNames[value]||value):value);option.value=value;select.appendChild(option);});select.value=values.indexOf(old)>=0?old:'';
      });
    }
    function render(){if(task){var source=get('live-source-filter').value,type=get('live-type-filter').value;renderResults(get('live-results'),task,source,type,function(){get('live-source-filter').value='';get('live-type-filter').value='';render();});var rows=(task.results||[]).filter(function(r){return (!source||r.source===source)&&(!type||r.result_type===type);});var suffix=(source||type)?' 条当前显示 / 共 '+task.results.length+' 条已保存线索 · 需人工核验':' 条已保存线索 · 需人工核验';if(global.vaultMotion){motion('ticker',get('live-result-count'),rows.length,suffix);motion('results',get('live-results'),task);}else setText('live-result-count',rows.length+suffix);}}
    function loadTask(id){
      clearTimeout(timer);
      if(taskId!==id){
        task=null;get('live-source-filter').value='';get('live-type-filter').value='';
        get('live-results').textContent='正在读取已保存的结果…';setText('live-result-count','读取中');
        get('live-cancel').disabled=true;get('live-delete').disabled=true;
      }
      taskId=id;markTaskSelection();
      request('/liveget?id='+encodeURIComponent(id)).then(function(data){
        if(taskId!==id)return;task=data;motion('task',data);get('live-title').textContent=data.query+' · '+(labels[data.status]||data.status);
        var state=get('live-task-status');if(state){state.replaceChildren();state.appendChild(pill(data.status));}
        setText('live-task-meta','创建 '+time(data.created_at)+' · 更新 '+time(data.updated_at));get('live-sources').replaceChildren();var finished=0;
        data.sources.forEach(function(s){var row=el('div');row.className='fl-source-row';var head=el('div');head.className='fl-source-title';head.appendChild(el('strong',sourceNames[s.source]||s.source));head.appendChild(pill(s.status));row.appendChild(head);row.appendChild(el('p',s.message));row.appendChild(el('p',s.limitations));var when=el('p','查询时间：'+time(s.queried_at));when.className='fl-source-time';row.appendChild(when);get('live-sources').appendChild(row);if(['waiting','running'].indexOf(s.status)<0)finished++;});
        setText('live-source-count',finished+' / '+data.sources.length+' 个来源结束；结束不代表目标安全。');var fill=get('live-progress-fill');if(fill)fill.style.transform='scaleX('+(finished/Math.max(1,data.sources.length))+')';
        get('live-cancel').disabled=['waiting','running'].indexOf(data.status)<0;get('live-delete').disabled=false;filters();render();
        if(['waiting','running'].indexOf(data.status)>=0)timer=setTimeout(function(){loadTask(id);},1000);
        else{var complete=data.sources.filter(function(s){return s.status==='completed';}).length;message('本次检索已结束：已保存 '+data.results.length+' 条线索；'+complete+' 个来源查询完成，'+(data.sources.length-complete)+' 个来源未完整完成。具体原因见检索执行报告。');loadList();}
      }).catch(function(error){if(taskId!==id)return;task=null;motion('unavailable');message(error.message,true);get('live-results').textContent='数据不可用；请刷新任务列表后重试。';get('live-sources').textContent='数据不可用，无法读取来源进度。';get('live-cancel').disabled=true;get('live-delete').disabled=true;setText('live-result-count','数据不可用');setText('live-source-count','进度不可用');});
    }
    function markTaskSelection(){Array.from(get('live-tasks').children).forEach(function(b){if(b._liveTaskId){var selected=b._liveTaskId===taskId;b.className='fl-task-option'+(selected?' selected':'');b.ariaPressed=String(selected);}});}
    function listControls(){
      if(get('live-task-prev'))get('live-task-prev').disabled=listLoading||taskPage<=1;
      if(get('live-task-next'))get('live-task-next').disabled=listLoading||taskPage>=taskPages;
      if(get('live-task-page')){get('live-task-page').value=taskPage;get('live-task-page').max=taskPages;get('live-task-page').disabled=listLoading||taskPages<=1;}
      if(get('live-task-clear'))get('live-task-clear').disabled=!taskSearch&&!taskStatus;
      if(get('live-refresh'))get('live-refresh').disabled=listLoading;
    }
    function loadList(){
      var sequence=++listSequence;listLoading=true;listControls();setText('live-task-total','正在读取任务…');
      return write('/livelist',{page:taskPage,page_size:taskPageSize,search:taskSearch,status:taskStatus}).then(function(data){
        if(sequence!==listSequence)return;
        // Preserve compatibility with the original unpaged list response.
        if(Array.isArray(data))data={items:data.slice(0,taskPageSize),total:data.length,page:1,pages:Math.max(1,Math.ceil(data.length/taskPageSize))};
        if(!data||!Array.isArray(data.items)||!Number.isFinite(data.total))throw new Error('任务列表数据不可用，请刷新重试。');
        taskPage=data.page;taskPages=data.pages;listedTasks=data.items;listUnavailable=false;
        var container=get('live-tasks');container.replaceChildren();
        if(!data.items.length){var empty=el('p',taskSearch||taskStatus?'没有符合条件的任务，请调整或重置筛选。':'暂无检索任务，开始一次检索后会保存在这里。');empty.className='fl-empty';container.appendChild(empty);}
        data.items.forEach(function(item){
          var b=el('button');b.type='button';b._liveTaskId=item.id;b.className='fl-task-option';
          var heading=el('span');heading.className='fl-task-option-heading';heading.appendChild(el('strong',item.query));heading.appendChild(pill(item.status));b.appendChild(heading);
          var kind={domain:'域名 / IP',username:'用户名',email:'邮箱'}[item.input_type]||'检索';
          b.appendChild(el('small',kind+' · '+time(item.created_at)+' · '+item.id.slice(0,8)));b.title='任务编号：'+item.id;
          b.onclick=function(){var view=global.location&&global.location.hash.split('/')[0]==='#results'?'results':'progress';loadTask(item.id);navigate(view,item.id);};container.appendChild(b);
        });
        container.scrollTop=0;markTaskSelection();setText('live-task-total','共 '+data.total+' 项 · 第 '+taskPage+' / '+taskPages+' 页');route();
      }).catch(function(error){if(sequence!==listSequence)return;listUnavailable=true;listedTasks=null;get('live-tasks').textContent=error.message;setText('live-task-total','列表不可用，请重试');route();})
        .finally(function(){if(sequence===listSequence){listLoading=false;listControls();}});
    }
    function applyTaskFilters(){clearTimeout(searchTimer);taskSearch=get('live-task-search').value.trim();taskStatus=get('live-task-status-filter').value;taskPage=1;loadList();}
    if(get('live-task-search-form'))get('live-task-search-form').onsubmit=function(e){e.preventDefault();applyTaskFilters();};
    if(get('live-task-search'))get('live-task-search').oninput=function(){clearTimeout(searchTimer);searchTimer=setTimeout(applyTaskFilters,300);};
    if(get('live-task-status-filter'))get('live-task-status-filter').onchange=applyTaskFilters;
    if(get('live-task-page-size'))get('live-task-page-size').onchange=function(){taskPageSize=Number(this.value)||5;taskPage=1;loadList();};
    if(get('live-task-clear'))get('live-task-clear').onclick=function(){get('live-task-search').value='';get('live-task-status-filter').value='';applyTaskFilters();};
    if(get('live-task-prev'))get('live-task-prev').onclick=function(){if(!listLoading&&taskPage>1){taskPage--;loadList();}};
    if(get('live-task-next'))get('live-task-next').onclick=function(){if(!listLoading&&taskPage<taskPages){taskPage++;loadList();}};
    if(get('live-task-page'))get('live-task-page').onchange=function(){var next=Number(this.value);if(Number.isInteger(next)&&next>=1&&next<=taskPages){taskPage=next;loadList();}else this.value=taskPage;};
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

(function(global) {
  'use strict';
  var labels = {waiting:'等待',running:'运行',completed:'完成',partial:'部分完成',failed:'失败',not_configured:'未配置',timeout:'超时',cancelled:'已取消'};
  function el(tag, text) { var node=document.createElement(tag); if(text!==undefined) node.textContent=String(text); return node; }
  function allowedLink(value) {
    try { var u=new URL(value); return /^https?:$/.test(u.protocol) && !u.username && !u.password ? u.href : null; } catch (_) { return null; }
  }
  function renderResults(container, task, sourceFilter, typeFilter) {
    container.replaceChildren();
    var results=(task.results||[]).filter(function(row){return (!sourceFilter||row.source===sourceFilter)&&(!typeFilter||row.result_type===typeFilter);});
    if(!results.length) {
      var unavailable=(task.sources||[]).some(function(s){return ['failed','timeout','not_configured','partial'].indexOf(s.status)>=0;});
      container.appendChild(el('p',task.status==='running'||task.status==='waiting' ? '正在检索，已返回的结果会逐步显示。' : unavailable ? '部分数据源不可用或未配置；请查看各来源状态，不能据此判定无匹配。' : task.status==='cancelled' ? '任务已取消；仅保留取消前已保存的结果。' : '当前数据源未发现匹配，不代表不存在相关信息。'));
      return;
    }
    results.forEach(function(row) {
      var card=el('article'); card.className='pg-card'; card.style.padding='16px';
      card.appendChild(el('h3',row.title));
      [['数据源',row.source],['输入类型',row.input_type],['结果类型',row.result_type],['数据值',row.value],['结果状态',row.status],
       ['查询时间',new Date(row.queried_at*1000).toLocaleString('zh-CN')],['可信程度说明',row.confidence],['数据源限制',row.limitations],['来源摘要',row.raw_summary]]
        .forEach(function(pair){card.appendChild(el('p',pair[0]+'：'+(pair[1]||'暂无')));});
      var link=allowedLink(row.original_url);
      if(link) { var a=el('a','查看原始链接'); a.href=link; a.target='_blank'; a.rel='noopener noreferrer'; card.appendChild(a); }
      else card.appendChild(el('p','该线索未提供可用的 HTTP/HTTPS 原始链接。'));
      container.appendChild(card);
    });
  }
  global.liveSearchView={renderResults:renderResults,allowedLink:allowedLink};
  if(typeof module!=='undefined') module.exports=global.liveSearchView;
  if(!global.addEventListener) return;
  global.addEventListener('DOMContentLoaded',function() {
    var taskId=null, task=null, timer=null;
    function get(id){return document.getElementById(id);}
    function message(text){get('live-message').textContent=text;}
    function request(path,options) { return fetch(docroot+path,options).then(function(r){if(r.status===400)return r.json().then(function(body){throw new Error(body.error||'输入格式无效。');});if(!r.ok) throw new Error(r.status===403?'安全令牌或权限无效，请刷新页面后重试。':'检索服务暂不可用，请稍后重试。');return r.json();}); }
    function write(path,data){return request(path,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},body:new URLSearchParams(data)});}
    function filters() {
      [['live-source-filter','source','全部数据源'],['live-type-filter','result_type','全部结果类型']].forEach(function(spec){
        var select=get(spec[0]), old=select.value; select.replaceChildren(); var all=el('option',spec[2]); all.value='';select.appendChild(all);
        Array.from(new Set((task.results||[]).map(function(r){return r[spec[1]];}))).forEach(function(value){var option=el('option',value);option.value=value;select.appendChild(option);});
        select.value=old;
      });
    }
    function render(){if(task)renderResults(get('live-results'),task,get('live-source-filter').value,get('live-type-filter').value);}
    function loadTask(id) {
      clearTimeout(timer); taskId=id;
      request('/liveget?id='+encodeURIComponent(id)).then(function(data){
        if(taskId!==id)return; task=data;
        get('live-title').textContent=data.query+' · '+(labels[data.status]||data.status);
        get('live-sources').replaceChildren();
        data.sources.forEach(function(s){get('live-sources').appendChild(el('p',s.source+'：'+(labels[s.status]||s.status)+' · '+s.message+' · '+s.limitations));});
        get('live-cancel').disabled=['waiting','running'].indexOf(data.status)<0;
        get('live-delete').disabled=false; filters();render();
        if(['waiting','running'].indexOf(data.status)>=0)timer=setTimeout(function(){loadTask(id);},1000);
        else {message('本次检索已结束；请按各来源状态判断覆盖情况。');loadList();}
      }).catch(function(error){message(error.message);get('live-results').textContent='数据不可用；请刷新任务列表后重试。';});
    }
    function loadList(){return request('/livelist').then(function(data){
      get('live-tasks').replaceChildren();if(!data.length)get('live-tasks').textContent='暂无检索任务';
      data.forEach(function(item){var b=el('button',item.query+' · '+(labels[item.status]||item.status));b.className='pg-btn';b.onclick=function(){loadTask(item.id);};get('live-tasks').appendChild(b);});
    }).catch(function(error){get('live-tasks').textContent=error.message;});}
    get('live-start').onclick=function(){
      get('live-start').disabled=true;message('正在创建任务...');
      write('/livecreate',{input_type:get('live-kind').value,query:get('live-query').value}).then(function(data){
        get('live-query').value='';message('任务已创建，正在分别查询各来源。');loadTask(data.id);loadList();
      }).catch(function(error){message(error.message);}).finally(function(){get('live-start').disabled=false;});
    };
    get('live-cancel').onclick=function(){if(taskId)write('/livecancel',{id:taskId}).then(function(){loadTask(taskId);loadList();}).catch(function(e){message(e.message);});};
    get('live-delete').onclick=function(){if(taskId&&confirm('删除此任务及保存的结果？'))write('/livedelete',{id:taskId}).then(function(){clearTimeout(timer);taskId=null;task=null;get('live-title').textContent='请选择任务';get('live-sources').replaceChildren();get('live-results').replaceChildren();get('live-delete').disabled=true;get('live-cancel').disabled=true;loadList();}).catch(function(e){message(e.message);});};
    get('live-source-filter').onchange=render;get('live-type-filter').onchange=render;
    request('/liveavailability').then(function(data){get('live-install').replaceChildren();data.forEach(function(source){get('live-install').appendChild(el('p',source.source+'：'+(!source.installed?'未安装':!source.configured?'未配置':'已安装')+' · '+source.limitations+' · 重建：'+source.rebuild));});}).catch(function(){get('live-install').textContent='安装状态暂不可用。';});
    loadList();
  });
})(typeof window!=='undefined'?window:globalThis);

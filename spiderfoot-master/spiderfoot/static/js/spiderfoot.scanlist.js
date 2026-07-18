/**
 * SpiderFoot scanlist.js - 重写版
 * 保留模板表格结构，只填充 tbody + 绑定按钮
 */

console.log('[SpiderFoot] spiderfoot.scanlist.js loaded');

// 全局状态
var globalTypes = null;
var globalFilter = null;
var lastChecked = null;
var _currentData = []; // 缓存当前数据，用于搜索过滤

// 暴露常用函数到 window，确保 HTML onclick 属性可调用
window.switchSelectAll = function() {
    var checked = $("#checkall")[0].checked;
    $("input[id*=cb_]").prop('checked', checked);
}

// 统计卡筛选 - 暴露到 window 确保 onclick 可调用
window.filter = function(type) {
    console.log('[SpiderFoot] filter called:', type);
    // 清除搜索框（筛选和搜索二选一）
    var searchInput = document.getElementById('scan-search');
    if (searchInput && searchInput.value) {
        searchInput.value = '';
    }

    if (type === "all") {
        showlist(null, "All");
        return;
    }
    if (type === "running") {
        showlist(["RUNNING", "STARTING", "STARTED", "INITIALIZING"], "Running");
        return;
    }
    if (type === "finished") {
        showlist(["FINISHED"], "Finished");
        return;
    }
    if (type === "failed") {
        showlist(["ABORTED", "ERROR-FAILED"], "Failed/Aborted");
        return;
    }
};

// 获取选中的扫描 ID
function getSelected() {
    var ids = [];
    $("input[id*=cb_]").each(function(i, obj) {
        if (obj.checked) {
            ids.push(obj.id.replace("cb_", ""));
        }
    });
    if (ids.length == 0) return false;
    return ids;
}

// 停止单个扫描
window.stopScan = function(id) {
    alertify.confirm("确定要停止此扫描吗？",
    function(){
        sf.stopScan(id, function() { window.showlist(globalTypes, globalFilter); });
    }).set({title:"停止扫描"});
};

// 批量停止
window.stopSelected = function() {
    var ids = getSelected();
    if (!ids) {
        alertify.message("请先选择要停止的扫描任务。");
        return;
    }
    alertify.confirm("确定要停止这 " + ids.length + " 个扫描？<br/><br/>" + ids.join("<br/>"),
    function(){
        sf.stopScan(ids.join(','), function() { window.showlist(globalTypes, globalFilter); });
    }).set({title:"停止扫描"});
};

// 删除单个扫描
window.deleteScan = function(id) {
    alertify.confirm("确定要删除此扫描吗？此操作不可恢复。",
    function(){
        sf.deleteScan(id, function() { window.showlist(globalTypes, globalFilter); });
    }).set({title:"删除扫描"});
};

// 批量删除
window.deleteSelected = function() {
    var ids = getSelected();
    if (!ids) {
        alertify.message("请先选择要删除的扫描任务。");
        return;
    }
    var deleteMsg = "确定要删除这 " + ids.length + " 个扫描吗？此操作不可恢复。";
    alertify.confirm(deleteMsg, function(){
        sf.deleteScan(ids.join(','), function() { window.showlist(globalTypes, globalFilter); });
    }).set({title:"删除扫描"});
};

// 批量重新扫描
window.rerunSelected = function() {
    var ids = getSelected();
    if (!ids) {
        alertify.message("请先选择要重新扫描的任务。");
        return;
    }
    window.location.href = docroot + '/rerunscanmulti?ids=' + ids.join(',');
};

// 刷新列表
window.reload = function() {
    window.showlist(globalTypes, globalFilter);
};

// 状态映射
var sfStatusMap = {
    'RUNNING':       { text: '进行中', cls: 'pg-badge-running' },
    'STARTED':       { text: '启动中', cls: 'pg-badge-running' },
    'STARTING':      { text: '启动中', cls: 'pg-badge-running' },
    'INITIALIZING':  { text: '初始化', cls: 'pg-badge-running' },
    'CREATED':       { text: '已创建',  cls: 'pg-badge-queued'  },
    'FINISHED':      { text: '已完成',  cls: 'pg-badge-finished' },
    'ABORTED':       { text: '已中止',  cls: 'pg-badge-aborted'  },
    'ABORT-REQUESTED': { text: '中止中', cls: 'pg-badge-aborted' },
    'ERROR-FAILED':  { text: '失败',    cls: 'pg-badge-error'   },
};

// 目标类型中文
var sfTypeMap = {
    'DOMAIN_NAME': '域名',
    'INTERNET_NAME': '网站',
    'IP_ADDRESS': 'IP地址',
    'IPV6_ADDRESS': 'IPv6',
    'NETBLOCK_OWNER': '网段',
    'EMAILADDR': '邮箱',
    'PHONE_NUMBER': '手机号',
    'HUMAN_NAME': '姓名',
    'USERNAME': '用户名',
    'BGP_AS_MEMBER': 'ASN',
    'BITCOIN_ADDRESS': '比特币',
};

// 显示扫描列表 - 暴露到 window
window.showlist = function(types, filter) {
    globalTypes = types;
    globalFilter = filter || "All";
    console.log('[SpiderFoot] showlist called, types:', types, 'filter:', filter);

    // 更新统计卡 active 状态
    updateStatCardActive(filter);

    // 显示加载状态
    var loader = document.getElementById('scan-list-loader');
    if (loader) loader.style.display = 'inline-block';

    function maybeRedirectToLogin(jqXHR) {
        try {
            var ct = (jqXHR && jqXHR.getResponseHeader) ? (jqXHR.getResponseHeader('Content-Type') || '') : '';
            var text = (jqXHR && jqXHR.responseText) ? String(jqXHR.responseText) : '';
            // Session expired often returns HTML login page with 200.
            if (ct.indexOf('text/html') >= 0 || text.indexOf('<html') >= 0 || text.indexOf('<!DOCTYPE html') >= 0) {
                var nextUrl = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = docroot + '/login?next=' + nextUrl;
                return true;
            }
        } catch (e) {}
        return false;
    }

    // 使用 JSON 请求（会话过期时自动跳转登录）
    $.ajax({
        url: docroot + '/scanlist',
        method: 'GET',
        cache: false,
        dataType: 'json',
        timeout: 12000
    }).done(function(data) {
        data = data || [];
        console.log('[SpiderFoot] API returned', data.length, 'scans');
        _currentData = data; // 缓存数据
        renderScanList(types, data);

        // 搜索框同步过滤（如果有搜索内容）
        var searchInput = document.getElementById('scan-search');
        if (searchInput && searchInput.value.trim()) {
            applySearchFilter(searchInput.value.trim());
        }

        // 自动隐藏新建扫描提示 banner
        var banner = document.getElementById('pg-newscan-banner');
        if (banner) {
            setTimeout(function() {
                banner.style.transition = 'opacity 0.5s';
                banner.style.opacity = '0';
                setTimeout(function() { banner.remove(); }, 500);
            }, 3000);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        if (maybeRedirectToLogin(jqXHR)) return;
        console.error('[SpiderFoot] 加载扫描列表失败:', textStatus, errorThrown);
        alertify.error('加载扫描列表失败: ' + textStatus);
    });
};

// 搜索过滤（基于缓存数据 + 当前筛选状态）
function applySearchFilter(keyword) {
    var rows = document.querySelectorAll('#scanlist-tbody tr');
    keyword = keyword.toLowerCase();
    rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        row.style.display = text.includes(keyword) ? '' : 'none';
    });
}

function updateStatCardActive(filter) {
    // 移除所有 active
    document.querySelectorAll('.pg-stat-filter').forEach(function(el) {
        el.classList.remove('active');
    });
    // 高亮当前 filter 对应的卡片
    var cardMap = {
        'All':      'statcard-all',
        'Running':  'statcard-running',
        'Finished': 'statcard-finished',
        'Failed/Aborted': 'statcard-error'
    };
    var cardId = cardMap[filter] || 'statcard-all';
    var card = document.getElementById(cardId);
    if (card) card.classList.add('active');
}

function renderScanList(types, data) {
    var tbody = document.getElementById('scanlist-tbody');
    var loader = document.getElementById('scan-list-loader');
    var tableWrap = document.querySelector('#scancontent .pg-table-wrap');
    var emptyEl = document.getElementById('pg-list-empty');
    var emptyTitle = document.getElementById('pg-empty-title');
    var emptyDesc = document.getElementById('pg-empty-desc');
    if (!tbody) return;
    if (loader) loader.style.display = 'none';

    // API 返回: [guid, name, target, created_str, started_str, finished_str, status, elementCount, riskmatrix]
    // 过滤
    var filtered = [];
    for (var i = 0; i < data.length; i++) {
        var status = data[i][6];
        if (!types || types.length === 0 || types.indexOf(status) >= 0) {
            filtered.push(data[i]);
        }
    }

    // 统计
    var total = data.length;
    var running = 0, finished = 0, aborted = 0, failed = 0;
    for (var i = 0; i < data.length; i++) {
        var s = data[i][6];
        if (['RUNNING','STARTING','STARTED','INITIALIZING'].indexOf(s) >= 0) running++;
        else if (s === 'FINISHED') finished++;
        else if ((s || '').indexOf('ABORT') >= 0) aborted++;
        else if ((s || '').indexOf('FAILED') >= 0) failed++;
    }
    updateStatEl('stat-total', total);
    updateStatEl('stat-running', running);
    updateStatEl('stat-finished', finished);
    updateStatEl('stat-error', aborted + failed);

    if (filtered.length === 0) {
        if (tableWrap) tableWrap.style.display = 'none';
        if (emptyEl) {
            emptyEl.style.display = '';
            if (emptyTitle) emptyTitle.textContent = total === 0 ? '暂无扫描记录' : '没有符合筛选条件的扫描';
            if (emptyDesc) emptyDesc.textContent = total === 0
                ? '点击右上角"新建扫描"开始您的第一次数字痕迹检测'
                : '尝试调整筛选条件，或新建扫描任务';
        }
        return;
    }

    if (tableWrap) tableWrap.style.display = '';
    if (emptyEl) emptyEl.style.display = 'none';

    // 渲染行
    var html = '';
    for (var i = 0; i < filtered.length; i++) {
        var row = filtered[i];
        // API 返回字段: [0]guid [1]name [2]target [3]created [4]started [5]finished [6]status [7]elementCount [8]riskmatrix
        var scanId = row[0];
        var scanName = row[1] || '(无名称)';
        var target = row[2] || '';
        // row[3]=created_str, row[4]=started_str, row[5]=finished_str
        var started = row[4] || '-';
        var finished = row[5] || '-';
        var status = row[6];
        var elementCount = row[7] || 0;
        var riskmatrix = row[8] || { HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };

        var sm = sfStatusMap[status] || { text: status, cls: 'pg-badge-queued' };
        var isRunning = ['RUNNING','STARTING','STARTED','INITIALIZING'].indexOf(status) >= 0;

        // 高风险行高亮
        var rowClass = (riskmatrix.HIGH > 0) ? 'class="sf-row-high"' : '';

        html += '<tr ' + rowClass + '>';
        // 复选框
        html += '<td><input type="checkbox" id="cb_' + scanId + '" style="accent-color: var(--accent-blue);cursor:pointer;"></td>';
        // 名称（可点击）
        html += '<td><a href="' + docroot + '/scaninfo?id=' + scanId + '" style="color:var(--accent-blue);text-decoration:none;font-weight:500;">' + escHtml(scanName) + '</a></td>';
        // 目标
        html += '<td><code style="font-size:11px;background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:4px;">' + escHtml(target) + '</code></td>';
        // 发现数据
        html += '<td class="text-center"><span style="font-weight:600;color:var(--accent-cyan);">' + elementCount + '</span></td>';
        // 状态
        html += '<td class="text-center">';
        if (isRunning) {
            html += '<span class="pg-badge ' + sm.cls + '"><span class="pg-scan-pulse" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:4px;"></span>' + sm.text + '</span>';
        } else {
            html += '<span class="pg-badge ' + sm.cls + '">' + sm.text + '</span>';
        }
        html += '</td>';
        // 开始时间（已是格式化字符串）
        html += '<td style="font-size:11px;color:var(--text-secondary);white-space:nowrap;">' + escHtml(started) + '</td>';
        // 完成时间
        html += '<td style="font-size:11px;color:var(--text-secondary);white-space:nowrap;">' + escHtml(finished) + '</td>';
        // 操作
        html += '<td>';
        html += '<div style="display:flex;align-items:center;gap:8px;justify-content:center;">';
        if (isRunning) {
            html += '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="stopScan(\'' + scanId + '\')" title="停止" style="color:var(--accent-yellow);">';
            html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>';
            html += '</button>';
        }
        html += '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="deleteScan(\'' + scanId + '\')" title="删除" style="color:var(--accent-red);">';
        html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
        html += '</button>';
        if (!isRunning) {
            html += '<a href="' + docroot + '/rerunscan?id=' + scanId + '" class="pg-btn pg-btn-ghost pg-btn-sm" title="重新扫描" style="color:var(--accent-blue);">';
            html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.58"/></svg>';
            html += '</a>';
        }
        html += '<a href="' + docroot + '/clonescan?id=' + scanId + '" class="pg-btn pg-btn-ghost pg-btn-sm" title="克隆扫描">';
        html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>';
        html += '</a>';
        html += '</div></td>';
        html += '</tr>';
    }

    tbody.innerHTML = html;

    // 绑定 checkbox shift 多选
    var chkboxes = tbody.querySelectorAll('input[id*=cb_]');
    chkboxes.forEach(function(cb) {
        cb.addEventListener('click', function(e) {
            if (!lastChecked) {
                lastChecked = this;
                return;
            }
            if (e.shiftKey) {
                var start = Array.prototype.indexOf.call(chkboxes, this);
                var end = Array.prototype.indexOf.call(chkboxes, lastChecked);
                var slice = chkboxes.slice(Math.min(start, end), Math.max(start, end) + 1);
                slice.forEach(function(cbx) { cbx.checked = lastChecked.checked; });
            }
            lastChecked = this;
        });
    });

    // 绑定全选
    var selectAll = document.getElementById('select-all-scans');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            chkboxes.forEach(function(cb) { cb.checked = selectAll.checked; });
        });
    }

    // 高风险行样式
    var style = document.createElement('style');
    style.textContent = '.sf-row-high td { background: rgba(239,68,68,0.04) !important; }';
    document.head.appendChild(style);

    // 更新 filter 按钮文字
    var filterBtn = document.getElementById('btn-filter');
    if (filterBtn) filterBtn.innerHTML = '<i class="glyphicon glyphicon-filter"></i>&nbsp;Filter: ' + globalFilter;
}

function updateStatEl(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
}

function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatTime(val) {
    if (!val || val === 'Not yet' || val === 0) return '-';
    // val is like "2024-01-01 12:00:00"
    if (typeof val === 'string' && val.length > 16) {
        return val.substring(0, 16);
    }
    return val;
}

// 页面加载完成后初始化
$(document).ready(function() {
    console.log('[SpiderFoot] document ready, initializing...');

    // 绑定顶部操作栏按钮
    $('#btn-delete-selected').click(function() { window.deleteSelected(); });
    $('#btn-stop-selected').click(function() { window.stopSelected(); });
    $('#btn-rerun-selected').click(function() { window.rerunSelected(); });
    $('#btn-refresh').click(function() { window.reload(); });

    // 搜索框过滤（输入时实时过滤）
    $('#scan-search').on('input', function() {
        var val = this.value.toLowerCase().trim();
        applySearchFilter(val);
    });

    // 页面加载时自动获取扫描列表
    window.showlist();
});

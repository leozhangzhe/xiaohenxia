//-------------------------------------------------------------------------------
// spiderfoot.scaninfo.js
// 扫描详情页所有视图功能的实现
// 调用后端 API：scansummary / scancorrelations / scaneventresults / scanviz / scanopts / scanlog
//-------------------------------------------------------------------------------

'use strict';

// 风险等级映射
var riskLevelMap = { 'HIGH': '高风险', 'MEDIUM': '中风险', 'LOW': '低风险', 'INFO': '信息' };
var riskClassMap  = { 'HIGH': 'pg-badge-red', 'MEDIUM': 'pg-badge-yellow', 'LOW': 'pg-badge-blue', 'INFO': 'pg-badge-gray' };

function maybeRedirectToLoginFromXhr(jqXHR) {
    try {
        var ct = (jqXHR && jqXHR.getResponseHeader) ? (jqXHR.getResponseHeader('Content-Type') || '') : '';
        var text = (jqXHR && jqXHR.responseText) ? String(jqXHR.responseText) : '';
        if (jqXHR.status === 401 || (jqXHR.status === 200 && ct.indexOf('text/html') >= 0
                && /<form\b[^>]*action=["'][^"']*\/login["']/i.test(text)
                && /type=["']password["']/i.test(text))) {
            var nextUrl = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = docroot + '/login?next=' + nextUrl;
            return true;
        }
    } catch (e) {}
    return false;
}

//---------------------------------------------------------------------------
// 扫描概览
//---------------------------------------------------------------------------
function scanSummaryView(scanId) {
    setSection('btn-status');

    // 先显示加载中
    setContent('<div style="padding:40px;text-align:center;"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span><div style="margin-top:12px;color:var(--text-muted);font-size:13px;">正在加载扫描概览...</div></div>');

    var maxRetries = 3;
    var delayMs = 400;

    function buildSummaryHtml(status) {
        var html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px;">';
        var created = status[2] || '-';
        var started = status[3] || '-';
        var ended   = status[4] || '-';
        var state   = status[5] || 'UNKNOWN';
        var risks   = status[6] || { HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
        var total   = risks.HIGH + risks.MEDIUM + risks.LOW + risks.INFO;

        var stateText  = { 'FINISHED': '已完成', 'RUNNING': '扫描中', 'STARTING': '启动中',
                           'ABORTED': '已中止', 'ERROR-FAILED': '失败' }[state] || state;
        var stateClass = { 'FINISHED': 'pg-badge-green', 'RUNNING': 'pg-badge-blue',
                           'ABORTED': 'pg-badge-gray', 'ERROR-FAILED': 'pg-badge-red' }[state] || 'pg-badge-gray';

        html += '<div class="pg-card" style="grid-column:1/-1;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;">';
        html += '<div>';
        html += '<div style="font-size:13px;color:var(--text-muted);margin-bottom:4px;">扫描状态</div>';
        html += '<span class="pg-badge ' + stateClass + '">' + stateText + '</span>';
        html += '</div>';
        html += '<div style="text-align:right;">';
        html += '<div style="font-size:11px;color:var(--text-muted);">开始时间：' + started + '</div>';
        html += '<div style="font-size:11px;color:var(--text-muted);">结束时间：' + (ended !== '-' ? ended : '扫描中') + '</div>';
        html += '</div>';
        html += '</div></div>';

        html += '<div class="pg-card">';
        html += '<div class="pg-card-header"><div class="pg-card-title">风险概览</div></div>';
        html += '<div class="pg-card-body">';
        html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;text-align:center;">';
        html += '<div><div style="font-size:22px;font-weight:700;color:#e74c3c;">' + risks.HIGH + '</div><div style="font-size:11px;color:#e74c3c;">高风险</div></div>';
        html += '<div><div style="font-size:22px;font-weight:700;color:#f39c12;">' + risks.MEDIUM + '</div><div style="font-size:11px;color:#f39c12;">中风险</div></div>';
        html += '<div><div style="font-size:22px;font-weight:700;color:#3498db;">' + risks.LOW + '</div><div style="font-size:11px;color:#3498db;">低风险</div></div>';
        html += '<div><div style="font-size:22px;font-weight:700;color:#95a5a6;">' + risks.INFO + '</div><div style="font-size:11px;color:#95a5a6;">信息项</div></div>';
        html += '</div></div></div>';

        html += '<div class="pg-card">';
        html += '<div class="pg-card-header"><div class="pg-card-title">评估说明</div></div>';
        html += '<div class="pg-card-body" style="text-align:center;">';
        html += '<div style="font-size:18px;font-weight:700;">未提供安全评分</div>';
        html += '<div style="font-size:12px;color:var(--text-muted);">事件与关联风险需人工核验；无结果不等于安全。</div>';
        html += '</div></div>';

        html += '<div class="pg-card" style="grid-column:1/-1;">';
        html += '<div class="pg-card-header"><div class="pg-card-title">数据类型统计</div></div>';
        html += '<div id="summary-table"><span class="pg-loader" style="width:20px;height:20px;border-width:2px;"></span></div></div>';
        html += '</div>';
        return html;
    }

    function showRetryPanel() {
        setContent(
            '<div style="padding:40px;text-align:center;color:var(--text-muted);">' +
            '<div style="font-size:16px;margin-bottom:8px;">扫描概览暂时不可用</div>' +
            '<div style="font-size:12px;margin-bottom:14px;">网络抖动或接口超时，点击下方按钮重试</div>' +
            '<button class="pg-btn pg-btn-primary pg-btn-sm" onclick="scanSummaryView(\'' + scanId + '\')">重试加载</button>' +
            '</div>'
        );
    }

    function requestScanStatus(tryNo) {
        $.ajax({
            type: 'POST',
            url: docroot + '/scanstatus',
            data: { id: scanId },
            cache: false,
            dataType: 'json',
            timeout: 8000
        }).done(function(status) {
            if (!status || !status.length) {
                if (tryNo < maxRetries) {
                    setTimeout(function() { requestScanStatus(tryNo + 1); }, delayMs);
                    return;
                }
                showRetryPanel();
                return;
            }

            setContent(buildSummaryHtml(status));

            $.ajax({ type: 'POST', url: docroot + '/scansummary',
                     data: { id: scanId, by: 'type' }, cache: false, dataType: 'json' })
            .done(function(data) {
                if (!data || !data.length) {
                    $('#summary-table').text('当前数据源未发现匹配，不代表不存在相关信息。');
                    return;
                }
                var table = '<table class="pg-table"><thead><tr><th>数据类型</th><th>数量</th><th>最后发现</th></tr></thead><tbody>';
                data.forEach(function(row) {
                    table += '<tr><td>' + escapeHtml(row[0]) + '</td><td>' + escapeHtml(row[1]) + '</td><td>' + escapeHtml(row[2] || '-') + '</td></tr>';
                });
                table += '</tbody></table>';
                $('#summary-table').html(table);
            }).fail(function() {
                $('#summary-table').text('数据源不可用，请稍后重试。');
            });
        }).fail(function(jqXHR) {
            if (maybeRedirectToLoginFromXhr(jqXHR)) return;
            if (tryNo < maxRetries) {
                setTimeout(function() { requestScanStatus(tryNo + 1); }, delayMs);
            } else {
                showRetryPanel();
            }
        });
    }

    requestScanStatus(1);
}

//---------------------------------------------------------------------------
// 风险关联分析
//---------------------------------------------------------------------------
function browseCorrelations(scanId) {
    setSection('btn-correlations');
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-empty-icon"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span></div><div class="pg-empty-title" style="margin-top:12px;">正在加载关联数据...</div></div></div>');

    sf.fetchData(docroot + '/scancorrelations', { id: scanId }, function(data) {
        if (!data || !data.length) {
            setContent('<div style="padding:40px;text-align:center;color:var(--text-muted);">' +
                '<div style="font-size:48px;margin-bottom:12px;">🔍</div>' +
                '<div style="font-size:16px;">暂无关联分析数据</div>' +
                '<div style="font-size:12px;margin-top:6px;">扫描完成后将显示数据间的关联关系</div></div>');
            return;
        }
        var html = '<div style="padding:20px;">';
        html += '<table class="pg-table"><thead><tr>';
        html += '<th>关联类型</th><th>来源</th><th>目标</th><th>风险等级</th><th>说明</th>';
        html += '</tr></thead><tbody>';
        data.forEach(function(row) {
            var risk  = row[3] || 'INFO';
            var cls   = riskClassMap[risk] || 'pg-badge-gray';
            html += '<tr>';
            html += '<td>' + (row[0] || '-') + '</td>';
            html += '<td><code style="font-size:11px;">' + (row[1] || '-') + '</code></td>';
            html += '<td><code style="font-size:11px;">' + (row[2] || '-') + '</code></td>';
            html += '<td><span class="pg-badge ' + cls + '">' + (riskLevelMap[risk] || risk) + '</span></td>';
            html += '<td style="font-size:12px;color:var(--text-muted);">' + (row[4] || '-') + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        setContent(html);
    });
}

//---------------------------------------------------------------------------
// 数据浏览
//---------------------------------------------------------------------------
function browseEventList(scanId, extraParams) {
    setSection('btn-browse');
    currentType = extraParams && extraParams.eventType ? extraParams.eventType : currentType || 'ALL';
    var query = extraParams && extraParams.value ? String(extraParams.value).toLowerCase() : '';
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-empty-icon"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span></div><div class="pg-empty-title" style="margin-top:12px;">正在加载事件数据...</div></div></div>');

    fetchNormalizedScanResults(scanId).then(function(data) {
        var container = document.getElementById('scanresults-content');
        container.replaceChildren();
        if (data.status === 'partial') {
            var partial = document.createElement('p');
            partial.textContent = data.message || '部分完成：结果可能不完整。';
            container.appendChild(partial);
        }
        var toolbar = document.createElement('div');
        toolbar.className = 'pg-result-toolbar';
        var types = Array.from(new Set(data.results.map(function(item) { return item.event_type; }).filter(Boolean))).sort();
        var select = document.createElement('select');
        select.id = 'event-type-filter';
        select.className = 'pg-input';
        [['ALL', '全部数据类型']].concat(types.map(function(type) { return [type, type]; })).forEach(function(entry) {
            var option = document.createElement('option');
            option.value = entry[0];
            option.textContent = entry[1];
            select.appendChild(option);
        });
        select.value = currentType;
        select.onchange = function() { browseEventList(scanId, { eventType: select.value }); };
        toolbar.appendChild(select);
        ['csv', 'json'].forEach(function(format) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'pg-btn pg-btn-ghost pg-btn-sm';
            button.textContent = '导出 ' + format.toUpperCase();
            button.onclick = function() { exportEventData(scanId, currentType, format); };
            toolbar.appendChild(button);
        });
        container.appendChild(toolbar);
        var shown = data.results.filter(function(item) {
            return (currentType === 'ALL' || item.event_type === currentType)
                && (!query || String(item.data_value || '').toLowerCase().includes(query));
        });
        if (!shown.length) {
            var empty = document.createElement('p');
            empty.textContent = data.message || '当前数据源未发现匹配，不代表不存在相关信息。';
            container.appendChild(empty);
            return;
        }
        renderNormalizedResultTable(container, shown, true);
    }).catch(function() {
        setContent('<div class="pg-empty" style="padding:24px;">数据源不可用，请稍后重试。</div>');
    });
}

//---------------------------------------------------------------------------
// 关联图谱 — 静态 SVG 分组树状图（无闪烁、易读）
//---------------------------------------------------------------------------

/* -- 类型颜色映射 -- */
var TYPE_COLOR_MAP = {};
var TYPE_PALETTE = [
    '#4f8ef7','#e74c3c','#2ecc71','#f39c12','#9b59b6',
    '#1abc9c','#e67e22','#3498db','#e91e63','#00bcd4',
    '#8bc34a','#ff5722','#607d8b','#795548','#cddc39'
];
var _typeColorIdx = 0;
function getTypeColor(t) {
    if (!t) return '#607d8b';
    t = t.toLowerCase();
    if (TYPE_COLOR_MAP[t]) return TYPE_COLOR_MAP[t];
    var c = TYPE_PALETTE[_typeColorIdx % TYPE_PALETTE.length];
    _typeColorIdx++;
    TYPE_COLOR_MAP[t] = c;
    return c;
}

var RISK_NODE_COLOR = { 'HIGH': '#e74c3c', 'MEDIUM': '#f39c12', 'LOW': '#3498db', 'INFO': '#95a5a6' };

function graphEvents(scanId) {
    setSection('btn-graph');
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-empty-icon"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span></div><div class="pg-empty-title" style="margin-top:12px;">正在生成关联图谱...</div></div></div>');

    sf.fetchData(docroot + '/scanviz', { id: scanId, gexf: '0' }, function(data) {
        if (!data || !data.nodes || !data.nodes.length) {
            setContent('<div style="padding:40px;text-align:center;color:var(--text-muted);">' +
                '<div style="font-size:48px;margin-bottom:12px;">&#x1F578;&#xFE0E;</div>' +
                '<div style="font-size:16px;">图谱数据不足</div>' +
                '<div style="font-size:12px;margin-top:6px;">扫描结果足够多时才能生成关联图谱</div></div>');
            return;
        }

        var nodes = data.nodes;
        var edges = data.edges || [];
        var edgeCount = edges.length;

        /* -- 按类型分组 -- */
        var groups = {};
        var groupIdMap = {};
        var gIdx = 0;
        nodes.forEach(function(n) {
            var t = (n.type || n.categories || 'OTHER');
            if (typeof t === 'object' && t.length) t = t[0];
            t = String(t);
            if (!groups[t]) { groups[t] = []; groupIdMap[t] = gIdx++; }
            groups[t].push(n);
        });

        var groupKeys = Object.keys(groups).sort(function(a, b) { return groups[b].length - groups[a].length; });

        /* -- 统计 -- */
        var typeStats = groupKeys.map(function(k) { return { type: k, count: groups[k].length, color: getTypeColor(k) }; });

        /* -- 构建 HTML -- */
        var html = '<div style="padding:16px;">';

        /* 工具栏 */
        html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">';
        html += '<span style="font-size:13px;color:var(--text-muted);">节点 <strong style="color:var(--text-primary);">' + nodes.length + '</strong> 个 &middot; 关联 <strong style="color:var(--text-primary);">' + edgeCount + '</strong> 条</span>';
        html += '<div style="margin-left:8px;"><input id="graph-search" class="pg-input" placeholder="搜索节点..." style="width:180px;font-size:12px;height:30px;" oninput="filterGraphNodes(this.value)"></div>';
        html += '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="downloadGraphSvg()">保存图片</button>';
        html += '</div>';

        /* 类型图例 */
        html += '<div id="graph-legend" style="display:flex;flex-wrap:wrap;gap:8px 16px;margin-bottom:12px;padding:10px 14px;background:var(--bg-secondary,#f5f7fa);border-radius:8px;">';
        typeStats.forEach(function(s) {
            html += '<div style="display:flex;align-items:center;gap:5px;cursor:pointer;" onclick="highlightGraphGroup(\'' + escapeHtml(s.type) + '\')">' +
                '<div style="width:10px;height:10px;border-radius:50%;background:' + s.color + ';flex-shrink:0;"></div>' +
                '<span style="font-size:11px;color:var(--text-muted);">' + escapeHtml(s.type) + '</span>' +
                '<span style="font-size:11px;color:var(--text-secondary);font-weight:600;">' + s.count + '</span></div>';
        });
        html += '</div>';

        /* SVG 容器 */
        html += '<div id="graph-svg-wrap" style="position:relative;width:100%;overflow-x:auto;background:var(--bg-card,#fff);border:1px solid var(--border-color,#e8ecf0);border-radius:10px;">';
        html += '<svg id="graph-svg" xmlns="http://www.w3.org/2000/svg" style="display:block;"></svg>';
        html += '</div>';

        /* 悬浮提示 */
        html += '<div id="graph-tooltip" style="display:none;position:fixed;z-index:9999;padding:8px 12px;background:#1a1f2e;color:#e4e8f0;font-size:12px;border-radius:6px;pointer-events:none;max-width:320px;box-shadow:0 4px 20px rgba(0,0,0,0.3);line-height:1.5;"></div>';

        html += '</div>';
        setContent(html);

        /* -- 布局计算 -- */
        renderGroupedGraph(nodes, edges, groups, groupKeys, groupIdMap);
    });
}

function renderGroupedGraph(nodes, edges, groups, groupKeys, groupIdMap) {
    var NODE_R = 7;
    var GROUP_PAD = 30;
    var GROUP_GAP = 24;
    var COL_COUNT = Math.min(4, groupKeys.length);

    /* 计算每个分组的尺寸 */
    var groupCols = [];
    for (var i = 0; i < groupKeys.length; i += COL_COUNT) {
        groupCols.push(groupKeys.slice(i, i + COL_COUNT));
    }

    var GROUP_W = 280;
    var GROUP_H_BASE = 44;

    /* 给每个节点分配 x, y */
    var nodePos = {};
    var groupBounds = {};
    var totalW = 0;
    var totalH = 0;

    groupCols.forEach(function(col, colIdx) {
        var colX = totalW + colIdx * GROUP_GAP;
        var colMaxH = 0;
        col.forEach(function(gk, rowIdx) {
            var gNodes = groups[gk];
            var cols = Math.ceil(Math.sqrt(gNodes.length));
            cols = Math.max(cols, 2);
            var rows = Math.ceil(gNodes.length / cols);
            var gw = GROUP_W;
            var gh = GROUP_H_BASE + rows * (NODE_R * 2 + 14);
            var gx = colX + rowIdx * (GROUP_W + GROUP_GAP);
            var gy = 0;

            gNodes.forEach(function(n, idx) {
                var r = idx % cols;
                var c = Math.floor(idx / cols);
                var nx = gx + GROUP_PAD + r * (NODE_R * 2 + 22) + NODE_R + 10;
                var ny = gy + GROUP_PAD + 20 + c * (NODE_R * 2 + 14) + NODE_R;
                nodePos[n.id] = { x: nx, y: ny, node: n };
            });

            groupBounds[gk] = { x: gx, y: gy, w: gw, h: gh };
            if (gy + gh > colMaxH) colMaxH = gy + gh;
        });

        totalW = colX + col.length * (GROUP_W + GROUP_GAP);
        if (colMaxH > totalH) totalH = colMaxH;
    });

    totalW += 40;
    totalH += 40;

    /* -- 构建 SVG 字符串 -- */
    var svg = '';
    var svgW = totalW;
    var svgH = totalH;

    /* defs: 箭头 */
    svg += '<defs>';
    svg += '<marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#a0aec0"/></marker>';
    svg += '<marker id="arrowhead-hl" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#e74c3c"/></marker>';
    svg += '</defs>';

    /* 绘制分组背景 */
    groupKeys.forEach(function(gk) {
        var b = groupBounds[gk];
        var color = getTypeColor(gk);
        svg += '<rect x="' + b.x + '" y="' + b.y + '" width="' + b.w + '" height="' + b.h + '" rx="10" fill="' + color + '" fill-opacity="0.06" stroke="' + color + '" stroke-opacity="0.25" stroke-width="1.5"/>';
        svg += '<text x="' + (b.x + 12) + '" y="' + (b.y + 18) + '" font-size="11" font-weight="600" fill="' + color + '" font-family="Inter,sans-serif">' + escapeHtml(gk) + ' (' + groups[gk].length + ')</text>';
    });

    /* 绘制边 */
    var maxEdges = 300;
    var drawnEdges = 0;
    edges.forEach(function(e) {
        if (drawnEdges >= maxEdges) return;
        var s = nodePos[e.source];
        var t = nodePos[e.target];
        if (!s || !t) return;
        var sameGroup = (s.node.type === t.node.type) || (s.node.categories && t.node.categories && JSON.stringify(s.node.categories) === JSON.stringify(t.node.categories));
        var opacity = sameGroup ? '0.12' : '0.22';
        var sw = sameGroup ? '0.8' : '1.2';
        svg += '<line class="graph-edge" x1="' + s.x + '" y1="' + s.y + '" x2="' + t.x + '" y2="' + t.y + '" stroke="#a0aec0" stroke-opacity="' + opacity + '" stroke-width="' + sw + '" data-source="' + e.source + '" data-target="' + e.target + '"/>';
        drawnEdges++;
    });

    /* 绘制节点 */
    nodes.forEach(function(n) {
        var pos = nodePos[n.id];
        if (!pos) return;
        var t = (n.type || n.categories || 'OTHER');
        if (typeof t === 'object' && t.length) t = t[0];
        var color = getTypeColor(String(t));
        var label = (n.label || n.id || '').toString();
        if (label.length > 18) label = label.substring(0, 16) + '...';
        var size = (n.size || NODE_R);
        size = Math.max(4, Math.min(size, 14));

        svg += '<g class="graph-node" data-id="' + n.id + '" data-label="' + escapeHtml(n.label || n.id || '') + '" data-type="' + escapeHtml(String(t)) + '" style="cursor:pointer;">';
        svg += '<circle cx="' + pos.x + '" cy="' + pos.y + '" r="' + size + '" fill="' + color + '" stroke="rgba(255,255,255,0.6)" stroke-width="1.5" class="node-circle"/>';
        svg += '<text x="' + (pos.x + size + 4) + '" y="' + (pos.y + 4) + '" font-size="10" fill="var(--text-secondary,#5a6577)" font-family="Inter,sans-serif" class="node-label">' + escapeHtml(label) + '</text>';
        svg += '</g>';
    });

    /* 写入 SVG */
    var svgEl = document.getElementById('graph-svg');
    if (svgEl) {
        svgEl.setAttribute('width', svgW);
        svgEl.setAttribute('height', svgH);
        svgEl.setAttribute('viewBox', '0 0 ' + svgW + ' ' + svgH);
        svgEl.innerHTML = svg;
    }

    /* -- 绑定交互 -- */
    var tooltip = document.getElementById('graph-tooltip');

    svgEl.addEventListener('mousemove', function(ev) {
        var target = ev.target;
        if (target.classList && target.classList.contains('node-circle')) {
            var g = target.parentElement;
            var label = g.getAttribute('data-label') || '';
            var type = g.getAttribute('data-type') || '';
            tooltip.innerHTML = '<div style="font-weight:600;margin-bottom:2px;">' + escapeHtml(label) + '</div>' +
                '<div style="font-size:11px;opacity:0.7;">类型: ' + escapeHtml(type) + '</div>';
            tooltip.style.display = 'block';
            tooltip.style.left = (ev.clientX + 14) + 'px';
            tooltip.style.top = (ev.clientY - 10) + 'px';
        } else {
            tooltip.style.display = 'none';
        }
    });

    svgEl.addEventListener('mouseleave', function() {
        tooltip.style.display = 'none';
    });
}

/* 搜索过滤 */
function filterGraphNodes(query) {
    query = (query || '').trim().toLowerCase();
    var allNodes = document.querySelectorAll('#graph-svg .graph-node');
    var allEdges = document.querySelectorAll('#graph-svg .graph-edge');
    if (!query) {
        allNodes.forEach(function(g) { g.style.opacity = '1'; });
        allEdges.forEach(function(l) { l.setAttribute('stroke-opacity', ''); });
        return;
    }
    var matchIds = {};
    allNodes.forEach(function(g) {
        var label = (g.getAttribute('data-label') || '').toLowerCase();
        var type = (g.getAttribute('data-type') || '').toLowerCase();
        var match = label.indexOf(query) >= 0 || type.indexOf(query) >= 0;
        g.style.opacity = match ? '1' : '0.15';
        if (match) matchIds[g.getAttribute('data-id')] = true;
    });
    allEdges.forEach(function(l) {
        var s = l.getAttribute('data-source');
        var t = l.getAttribute('data-target');
        var both = matchIds[s] && matchIds[t];
        l.setAttribute('stroke-opacity', both ? '0.6' : '0.04');
        l.setAttribute('stroke', both ? '#e74c3c' : '#a0aec0');
    });
}

/* 点击图例高亮分组 */
function highlightGraphGroup(type) {
    var allNodes = document.querySelectorAll('#graph-svg .graph-node');
    var allEdges = document.querySelectorAll('#graph-svg .graph-edge');
    var matchIds = {};
    allNodes.forEach(function(g) {
        var match = g.getAttribute('data-type') === type;
        g.style.opacity = match ? '1' : '0.1';
        if (match) matchIds[g.getAttribute('data-id')] = true;
    });
    allEdges.forEach(function(l) {
        var s = l.getAttribute('data-source');
        var t = l.getAttribute('data-target');
        var both = matchIds[s] && matchIds[t];
        l.setAttribute('stroke-opacity', both ? '0.5' : '0.03');
    });
}

/* 保存为图片 */
function downloadGraphSvg() {
    var svgEl = document.getElementById('graph-svg');
    if (!svgEl) return;
    var svgData = new XMLSerializer().serializeToString(svgEl);
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    var img = new Image();
    var svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    var url = URL.createObjectURL(svgBlob);
    img.onload = function() {
        var w = svgEl.getAttribute('width') * 2;
        var h = svgEl.getAttribute('height') * 2;
        canvas.width = w; canvas.height = h;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        var a = document.createElement('a');
        a.href = canvas.toDataURL('image/png');
        a.download = 'privacy-graph.png';
        a.click();
    };
    img.src = url;
}

//---------------------------------------------------------------------------
// 扫描配置
//---------------------------------------------------------------------------
function viewScanConfig(scanId) {
    setSection('btn-info');
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-empty-icon"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span></div><div class="pg-empty-title" style="margin-top:12px;">正在加载配置...</div></div></div>');

    sf.fetchData(docroot + '/scanopts', { id: scanId }, function(data) {
        if (!data) { setContent('<div style="padding:40px;color:var(--text-muted);">无法加载配置</div>'); return; }
        var html = '<div style="padding:20px;">';
        html += '<div class="pg-card" style="margin-bottom:16px;">';
        html += '<div class="pg-card-header"><div class="pg-card-title">扫描配置详情</div></div>';
        html += '<div class="pg-card-body">';
        html += '<table class="pg-table"><thead><tr><th>配置项</th><th>值</th></tr></thead><tbody>';
        for (var key in data) {
            if (key.startsWith('_')) continue;
            var val = typeof data[key] === 'object' ? JSON.stringify(data[key]) : String(data[key]);
            html += '<tr><td style="font-size:12px;color:var(--accent-blue);">' + key + '</td>';
            html += '<td style="font-size:12px;"><code>' + escapeHtml(val.substring(0, 200)) + '</code></td></tr>';
        }
        html += '</tbody></table></div></div></div>';
        setContent(html);
    });
}

//---------------------------------------------------------------------------
// 运行日志
//---------------------------------------------------------------------------
function viewScanLog(scanId) {
    setSection('btn-log');
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-empty-icon"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span></div><div class="pg-empty-title" style="margin-top:12px;">正在加载日志...</div></div></div>');

    sf.fetchData(docroot + '/scanlog', { id: scanId, limit: '500', reverse: '1' }, function(data) {
        if (!data || !data.length) {
            setContent('<div style="padding:40px;text-align:center;color:var(--text-muted);">' +
                '<div style="font-size:48px;margin-bottom:12px;">📋</div><div>暂无日志</div></div>');
            return;
        }
        var html = '<div style="padding:16px;">';
        html += '<div style="margin-bottom:12px;"><button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="viewScanLog(\'' + scanId + '\')">刷新</button></div>';
        html += '<div style="background:#0d1117;border-radius:8px;padding:16px;max-height:600px;overflow:auto;font-family:\'Fira Code\',\'Consolas\',monospace;font-size:12px;line-height:1.6;">';
        data.forEach(function(row) {
            // row: [generated, level, module, message, generatedUnix]
            var level = row[1] || 'INFO';
            var color = { 'ERROR': '#e74c3c', 'WARNING': '#f39c12', 'DEBUG': '#7f8c8d' }[level] || '#c8d0dc';
            html += '<div style="color:#636e7b;">' + (row[0] || '') + '</div>';
            html += '<div style="color:' + color + ';">[' + level + '] <span style="color:#4f8ef7;">' + (row[2] || '') + '</span> ' + (row[3] || '') + '</div>';
        });
        html += '</div></div>';
        setContent(html);
    });
}

//---------------------------------------------------------------------------
// 搜索
//---------------------------------------------------------------------------
function searchDirector(scanId) {
    var query = $('#searchvalue').val().trim();
    if (!query) { alertify.error('请输入搜索内容'); return; }
    browseEventList(scanId, { value: query, eventType: 'ALL' });
}

//---------------------------------------------------------------------------
// 导出数据
//---------------------------------------------------------------------------
function exportEventData(scanId, eventType, format) {
    eventType = eventType || 'ALL';
    if (format === 'csv') {
        window.location.href = docroot + '/scaneventresultexport?id=' + scanId + '&type=' + eventType + '&filetype=csv';
    } else {
        window.location.href = docroot + '/scaneventresultexport?id=' + scanId + '&type=' + eventType + '&filetype=json';
    }
}

//---------------------------------------------------------------------------
// 下载日志
//---------------------------------------------------------------------------
function downloadLogs(scanId) {
    window.location.href = docroot + '/scanexportlogs?id=' + scanId;
}

//---------------------------------------------------------------------------
// 全量/去重视图切换（browseUpdate）
//---------------------------------------------------------------------------
function browseUpdate(mode) {
    var scanId = window.currentScanId;
    if (!scanId) return;
    if (mode === 'full') {
        browseEventList(scanId);
    } else if (mode === 'unique') {
        browseUniqueResults(scanId);
    } else if (mode && mode.startsWith('viz-')) {
        // 可视化暂不支持，跳过
    }
}

function browseUniqueResults(scanId) {
    setContent('<div style="padding:20px;"><div class="pg-empty"><div class="pg-loader" style="width:28px;height:28px;border-width:3px;"></div></div></div>');
    sf.fetchData(docroot + '/scaneventresultsunique', { id: scanId, eventType: currentType || 'ALL', filterfp: false }, function(data) {
        if (!data || !data.length) {
            setContent('<div style="padding:40px;text-align:center;color:var(--text-muted);">暂无去重数据</div>');
            return;
        }
        var html = '<div style="padding:16px;">';
        html += '<div style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">去重后 <strong>' + data.length + '</strong> 条唯一结果</div>';
        html += '<table class="pg-table"><thead><tr><th>唯一数据</th><th>类型</th><th>出现次数</th></tr></thead><tbody>';
        data.forEach(function(row) {
            html += '<tr><td><code style="font-size:12px;">' + escapeHtml(row[0] || '-') + '</code></td>';
            html += '<td><span class="pg-badge pg-badge-gray" style="font-size:10px;">' + (row[1] || '-') + '</span></td>';
            html += '<td>' + (row[2] || 1) + '</td></tr>';
        });
        html += '</tbody></table></div>';
        setContent(html);
    });
}

//---------------------------------------------------------------------------
// 辅助函数
//---------------------------------------------------------------------------
function setSection(btnId) {
    currentSection = btnId;
    var tabs = ['btn-status', 'btn-correlations', 'btn-browse', 'btn-graph', 'btn-info', 'btn-log'];
    tabs.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.classList.remove('pg-btn-primary');
            el.classList.add('pg-btn-ghost');
        }
    });
    var active = document.getElementById(btnId);
    if (active) {
        active.classList.remove('pg-btn-ghost');
        active.classList.add('pg-btn-primary');
    }
}

function setContent(html) {
    var el = document.getElementById('scanresults-content');
    if (el) {
        el.innerHTML = '<div class="pg-card-body" style="padding:0;">' + html + '</div>';
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// 全局变量
var currentScanId = '';
var currentType   = 'ALL';

// 页面初始化
$(document).ready(function() {
    // 从 URL 读取 scanId（备用）
    var match = location.href.match(/id=([a-z0-9]+)/i);
    if (match) { window.currentScanId = match[1]; }

    // Tab 按钮高亮
    $('[id^=btn-]').on('click', function() {
        var id = this.id;
        if (['btn-status','btn-correlations','btn-browse','btn-graph','btn-info','btn-log','btn-fullview','btn-uniqueview'].indexOf(id) < 0) return;
        var tabs = ['btn-status','btn-correlations','btn-browse','btn-graph','btn-info','btn-log'];
        tabs.forEach(function(tid) {
            var el = document.getElementById(tid);
            if (el) { el.classList.remove('pg-btn-primary'); el.classList.add('pg-btn-ghost'); }
        });
        this.classList.remove('pg-btn-ghost');
        this.classList.add('pg-btn-primary');
    });

    // 视图切换按钮
    $('#btn-fullview').on('click', function() { browseUpdate('full'); });
    $('#btn-uniqueview').on('click', function() { browseUpdate('unique'); });
});

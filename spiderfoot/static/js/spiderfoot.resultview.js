'use strict';

var normalizedResultColumns = [
    { label: '输入类型', field: 'input_type' },
    { label: '数据类型', field: 'event_type' },
    { label: '数据值', field: 'data_value' },
    { label: '数据源', field: 'data_source' },
    { label: '结果标题', field: 'title' },
    { label: '原始链接', field: 'original_url' },
    { label: '扫描记录时间', field: 'query_time' },
    { label: '结果状态', field: 'status' },
    { label: '可信程度说明', field: 'confidence_note' },
    { label: '误报提示', field: 'false_positive_hint' }
];

function fetchNormalizedScanResults(scanId) {
    return fetch(docroot + '/scanresults?id=' + encodeURIComponent(scanId), {
        credentials: 'same-origin'
    }).then(function(response) {
        if (!response.ok) throw new Error('Result request failed');
        return response.json();
    }).then(function(data) {
        if (!data || !Array.isArray(data.results) || !['complete', 'partial'].includes(data.status)) {
            throw new Error('Invalid result response');
        }
        return data;
    });
}

function renderNormalizedResultTable(container, results, selectable) {
    var wrapper = document.createElement('div');
    wrapper.className = 'pg-table-wrap pg-result-table-wrap';
    var table = document.createElement('table');
    table.className = 'pg-table pg-result-table';
    var head = document.createElement('thead');
    var headerRow = document.createElement('tr');
    var checkboxes = [];
    if (selectable) {
        var selectHead = document.createElement('th');
        var selectAll = document.createElement('input');
        selectAll.type = 'checkbox';
        selectAll.id = 'checkall';
        selectAll.onchange = function() {
            checkboxes.forEach(function(box) { box.checked = selectAll.checked; });
        };
        selectHead.appendChild(selectAll);
        headerRow.appendChild(selectHead);
    }
    normalizedResultColumns.forEach(function(column) {
        var cell = document.createElement('th');
        cell.textContent = column.label;
        headerRow.appendChild(cell);
    });
    head.appendChild(headerRow);
    table.appendChild(head);
    var body = document.createElement('tbody');
    results.forEach(function(item) {
        var row = document.createElement('tr');
        if (selectable) {
            var selectCell = document.createElement('td');
            var box = document.createElement('input');
            box.type = 'checkbox';
            box.id = 'cb_' + String(item.event_hash || '');
            box.disabled = !item.event_hash;
            selectCell.appendChild(box);
            checkboxes.push(box);
            row.appendChild(selectCell);
        }
        normalizedResultColumns.forEach(function(column) {
            var cell = document.createElement('td');
            var value = item[column.field];
            if (column.field === 'original_url' && value) {
                try {
                    var linkUrl = new URL(value);
                    if ((linkUrl.protocol === 'http:' || linkUrl.protocol === 'https:') && !linkUrl.username) {
                        var link = document.createElement('a');
                        link.href = linkUrl.href;
                        link.target = '_blank';
                        link.rel = 'noopener noreferrer';
                        link.textContent = '查看原始链接';
                        cell.appendChild(link);
                    }
                } catch (_) {}
            }
            if (!cell.hasChildNodes()) {
                cell.textContent = column.field === 'original_url' && value ? '未提供有效链接'
                    : value === null || value === undefined || value === '' ? '未记录' : String(value);
            }
            row.appendChild(cell);
        });
        body.appendChild(row);
    });
    table.appendChild(body);
    wrapper.appendChild(table);
    container.appendChild(wrapper);
}

function loadNormalizedScanResults(scanId) {
    var container = document.getElementById('normalized-scan-results');
    if (!container) return Promise.resolve();
    return fetchNormalizedScanResults(scanId).then(function(data) {
        container.replaceChildren();
        if (data.status === 'partial') {
            var partial = document.createElement('p');
            partial.textContent = data.message || '部分完成：结果可能不完整。';
            container.appendChild(partial);
        }
        if (!data.results.length) {
            var empty = document.createElement('p');
            empty.textContent = data.message || '当前数据源未发现匹配，不代表不存在相关信息。';
            container.appendChild(empty);
            return;
        }
        renderNormalizedResultTable(container, data.results, false);
    }).catch(function() {
        container.textContent = '数据源不可用，请稍后重试。';
    });
}

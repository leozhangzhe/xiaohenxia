'use strict';

function loadNormalizedScanResults(scanId) {
    var container = document.getElementById('normalized-scan-results');
    if (!container) return;
    fetch(docroot + '/scanresults?id=' + encodeURIComponent(scanId), { credentials: 'same-origin' })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            container.replaceChildren();
            if (data.status === 'unavailable') {
                container.textContent = '数据源不可用，请稍后重试。';
                return;
            }
            if (data.status === 'partial') {
                var partial = document.createElement('p');
                partial.textContent = data.message || '部分完成：结果可能不完整。';
                container.appendChild(partial);
            }
            if (!data.results || !data.results.length) {
                var empty = document.createElement('p');
                empty.textContent = data.message || '当前数据源未发现匹配，不代表不存在相关信息。';
                container.appendChild(empty);
                return;
            }
            var table = document.createElement('table');
            table.className = 'pg-table';
            var head = document.createElement('thead');
            var headerRow = document.createElement('tr');
            ['输入类型', '数据源', '结果标题', '原始链接', '扫描记录时间', '结果状态', '可信程度说明', '误报提示'].forEach(function(label) {
                var cell = document.createElement('th');
                cell.textContent = label;
                headerRow.appendChild(cell);
            });
            head.appendChild(headerRow);
            table.appendChild(head);
            var body = document.createElement('tbody');
            data.results.forEach(function(item) {
                var row = document.createElement('tr');
                ['input_type', 'data_source', 'title', 'original_url', 'query_time', 'status', 'confidence_note', 'false_positive_hint'].forEach(function(field) {
                    var cell = document.createElement('td');
                    if (field === 'original_url' && item[field]) {
                        try {
                            var linkUrl = new URL(item[field]);
                            if (linkUrl.protocol === 'http:' || linkUrl.protocol === 'https:') {
                                var link = document.createElement('a');
                                link.href = linkUrl.href;
                                link.target = '_blank';
                                link.rel = 'noopener noreferrer';
                                link.textContent = '查看原始链接';
                                cell.appendChild(link);
                            }
                        } catch (_) {}
                    }
                    if (!cell.hasChildNodes()) cell.textContent = item[field] || '未记录';
                    row.appendChild(cell);
                });
                body.appendChild(row);
            });
            table.appendChild(body);
            container.appendChild(table);
        })
        .catch(function() { container.textContent = '数据源不可用，请稍后重试。'; });
}

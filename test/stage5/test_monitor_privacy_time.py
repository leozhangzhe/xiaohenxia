"""Execute the actual monitor privacy callback against the API timestamp types."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('value', [1700000000, 1700000000000, '2026-10-21T12:00:00Z', None])
def test_monitor_renders_privacy_time_without_false_service_failure(value):
    template = Path('spiderfoot/templates/servicemonitor.tmpl').read_text(encoding='utf-8')
    callback = template.split('// 3. 隐私保护模块', 1)[1].split('\n}\n', 1)[0]
    runner = r'''
const vm = require('vm');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const elements = {}, logs = [], statuses = [];
const context = {Date, Number, docroot: '/review',
 document: {getElementById(id) {return elements[id] ||= {textContent: ''};}},
 fetch: async () => ({ok: true, json: async () => ({total: 7, items: [{created_at: input.value}]})}),
 setStatus: (...args) => statuses.push(args), addLog: (...args) => logs.push(args)};
vm.runInNewContext(input.callback, context);
setImmediate(() => setImmediate(() => process.stdout.write(JSON.stringify({elements, logs, statuses}))));
'''
    result = subprocess.run([shutil.which('node'), '-e', runner],
                            input=json.dumps({'value': value, 'callback': callback}),
                            encoding='utf-8', text=True, capture_output=True, check=True, timeout=10)
    shown = json.loads(result.stdout)
    assert shown['logs'] == []
    assert not any(row[-1] == 'error' for row in shown['statuses'])
    assert shown['elements']['sm-priv-total']['textContent'] == 7
    rendered = shown['elements']['sm-priv-last']['textContent']
    if value is None:
        assert rendered == '--'
    else:
        assert len(rendered) >= 10
        assert 'Invalid' not in rendered
        assert rendered != str(value)

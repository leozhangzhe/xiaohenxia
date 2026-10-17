// Exercise the browser-facing result renderer without adding a DOM package.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const scenario = JSON.parse(fs.readFileSync(0, 'utf8'));
let htmlWrites = 0;
class Element {
    constructor(tagName) {
        this.tagName = tagName.toLowerCase();
        this.children = [];
        this._text = '';
        this.className = '';
    }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    set innerHTML(_) { htmlWrites += 1; }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren(...children) { this._text = ''; this.children = children; }
    hasChildNodes() { return this.children.length > 0; }
}
const container = new Element('div');
container.textContent = '正在读取已保存结果...';
const requested = [];
const document = {
    getElementById: id => id === 'normalized-scan-results' ? container : null,
    createElement: tag => new Element(tag)
};
const fetch = url => {
    requested.push(url);
    if (scenario.reject) return Promise.reject(new Error('network unavailable'));
    return Promise.resolve({
        ok: scenario.httpStatus >= 200 && scenario.httpStatus < 300,
        status: scenario.httpStatus,
        json: () => scenario.badJson ? Promise.reject(new Error('invalid JSON')) : Promise.resolve(scenario.body)
    });
};
const context = { document, fetch, docroot: '', URL, console };
vm.createContext(context);
const source = fs.readFileSync(path.resolve(__dirname, '../../spiderfoot/static/js/spiderfoot.resultview.js'), 'utf8');
vm.runInContext(source, context);
if (scenario.selectable) {
    context.fetchNormalizedScanResults('a'.repeat(32)).then(data => {
        container.replaceChildren();
        context.renderNormalizedResultTable(container, data.results, true);
    });
} else {
    context.loadNormalizedScanResults('a'.repeat(32));
}

function descendants(element, tag) {
    return element.children.flatMap(child => [
        ...(child.tagName === tag ? [child] : []), ...descendants(child, tag)
    ]);
}
setImmediate(() => {
    const table = descendants(container, 'table')[0];
    const headers = table ? descendants(table, 'th').map(cell => cell.textContent) : [];
    const rows = table ? descendants(table, 'tbody').flatMap(body => body.children.map(
        row => row.children.map(cell => cell.textContent))) : [];
    const links = descendants(container, 'a').map(link => ({href: link.href, text: link.textContent}));
    const checkboxIds = descendants(container, 'input').map(input => input.id);
    console.log(JSON.stringify({
        text: container.textContent,
        loaderGone: !container.textContent.includes('正在读取已保存结果'),
        headers, rows, links, checkboxIds, htmlWrites, requested
    }));
});

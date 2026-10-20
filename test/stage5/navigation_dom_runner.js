'use strict';
// Execute the real page controller with deterministic, user-scoped API responses.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor() { this.children = []; this._text = ''; this.style = {}; this.value = ''; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren() { this.children = []; this._text = ''; }
}
const elements = {}, events = {}, requests = [];
// These nodes exist in livesearch.tmpl even when the controller never loads a task.
['live-results', 'live-title', 'live-tasks', 'live-source-filter', 'live-type-filter'].forEach(id => { elements[id] = new Element(); });
elements['live-results'].textContent = '请选择任务以读取结果。';
const location = { get hash() { return this._hash; }, set hash(value) { this._hash = '#' + value.replace(/^#/, ''); } };
location.hash = input.hash || '#results';
const task = (id, source, title) => ({id, query: 'sy***', status: 'completed',
  created_at: 1700000000, updated_at: 1700000001,
  sources: [{source, status: 'completed', message: 'done', limitations: 'limited'}],
  results: [{source, result_type: source + '_profile', title, value: 'synthetic evidence',
    original_url: 'https://example.invalid/profile', queried_at: 1700000000}]});
const tasks = input.empty ? [] : [task('a'.repeat(32), 'sherlock', 'Saved A'), task('b'.repeat(32), 'maigret', 'Saved B')];
const context = {
  console, URL, URLSearchParams, clearTimeout, setTimeout,
  docroot: '', location,
  document: {createElement: () => new Element(), getElementById: id => elements[id] || (elements[id] = new Element())},
  addEventListener: (name, handler) => { events[name] = handler; },
  fetch: async url => {
    requests.push(url);
    let status = 200, body;
    if (url === '/liveavailability') body = [];
    else if (url === '/livelist') { status = input.listFailure ? 503 : 200; body = tasks; }
    else {
      body = tasks.find(item => url === '/liveget?id=' + item.id);
      if (!body) { status = input.deniedStatus || 404; body = {}; }
    }
    return {status, ok: status === 200, json: async () => JSON.parse(JSON.stringify(body))};
  }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../spiderfoot/static/js/live-search.js'), 'utf8'), context);
const flush = async () => { for (let i = 0; i < 12; i++) await new Promise(setImmediate); };
(async () => {
  events.DOMContentLoaded(); await flush();
  const snapshot = () => ({hash: context.location.hash, text: elements['live-results'].textContent,
    title: elements['live-title'].textContent, list: elements['live-tasks'].textContent,
    source: elements['live-source-filter'].value, type: elements['live-type-filter'].value});
  const before = snapshot();
  if (input.click !== undefined) {
    elements['live-source-filter'].value = 'sherlock'; elements['live-type-filter'].value = 'sherlock_profile';
    elements['live-tasks'].children[input.click].onclick(); await flush();
  }
  if (input.reenter) {
    context.location.hash = '#new'; events.hashchange();
    context.location.hash = '#results'; events.hashchange(); await flush();
  }
  console.log(JSON.stringify({before, after: snapshot(), requests}));
})().catch(error => { console.error(error); process.exitCode = 1; });

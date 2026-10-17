'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
if (input.kind === 'dashboard') {
    const scripts = [...input.html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
    const code = scripts.find(script => script.includes('function renderStats('));
    const elements = new Map();
    const document = {
        getElementById(id) {
            if (!elements.has(id)) elements.set(id, {textContent: '0', innerHTML: ''});
            return elements.get(id);
        },
        addEventListener() {}, createElement: () => ({textContent: '', innerHTML: ''})
    };
    const fetch = url => {
        if (url.endsWith(input.failed)) {
            if (input.failure === 'network') return Promise.reject(new Error('offline'));
            return Promise.resolve({ok: input.failure !== 'http', status: 503,
                headers: {get: () => 'application/json'},
                json: () => input.failure === 'json' ? Promise.reject(new Error('invalid JSON'))
                    : Promise.resolve({status: 'unavailable'})});
        }
        return Promise.resolve({ok: true, status: 200, headers: {get: () => 'application/json'}, json: () => Promise.resolve([])});
    };
    const context = {document, fetch, docroot: '', setInterval() {}};
    vm.createContext(context);
    vm.runInContext(code, context);
    context.loadDashboard();
    setImmediate(() => console.log(JSON.stringify(Object.fromEntries(
        [...elements].map(([id, value]) => [id, value.textContent + value.innerHTML])))));
} else {
const errors = [];
const document = {getElementById: () => null, querySelectorAll: () => []};
function $() { return {ready: () => {}}; }
$.ajax = () => ({
    done() { return this; },
    fail(callback) {
        callback({status: input.status, responseText: '<html><title>Not Found</title></html>',
                  getResponseHeader: () => 'text/html'}, 'error', 'Not Found');
        return this;
    }
});
const location = {pathname: '/', search: '', href: 'unchanged'};
const context = {window: {location}, document, $, docroot: '',
    alertify: {error: text => errors.push(text)}, console: {log() {}, error() {}}};
vm.createContext(context);
const filename = input.kind === 'scaninfo' ? 'spiderfoot.scaninfo.js' : 'spiderfoot.scanlist.js';
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../spiderfoot/static/js/' + filename), 'utf8'), context);
if (input.kind === 'scaninfo') {
    context.maybeRedirectToLoginFromXhr({status: input.status,
        responseText: '<html><title>Not Found</title></html>', getResponseHeader: () => 'text/html'});
} else {
    context.window.showlist();
}
console.log(JSON.stringify({href: location.href, errors}));
}

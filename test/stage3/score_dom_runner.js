// Execute the dashboard's rendered script against its visible score elements.
'use strict';
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(0, 'utf8');
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
const code = scripts.find(script => script.includes('function renderStats('));
if (!code) throw new Error('Dashboard rendering script is missing');
const elements = new Map();
const document = {
    getElementById: id => {
        if (!elements.has(id)) elements.set(id, {textContent: '', innerHTML: ''});
        return elements.get(id);
    },
    addEventListener: () => {},
    createElement: () => ({textContent: '', innerHTML: ''})
};
const context = {document, setInterval: () => {}, fetch: () => Promise.reject(new Error('unused'))};
vm.createContext(context);
vm.runInContext(code, context);
context.renderStats([], []);
const empty = elements.get('dv-privacy-score').textContent;
context.renderStats([{id: 'synthetic'}], [{risk: 'LOW', actionStatus: 'todo'}]);
const lowOnly = elements.get('dv-privacy-score').textContent;
console.log(JSON.stringify({empty, lowOnly}));

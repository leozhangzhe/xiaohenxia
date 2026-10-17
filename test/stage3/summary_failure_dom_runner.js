// Reproduce a successful scan status followed by a failed summary request.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let section = '';
let summaryText = '';
const content = {innerHTML: ''};
const document = {getElementById: id => id === 'scanresults-content' ? content : null};
function $(selector) {
    if (selector === document) return {ready: () => {}};
    if (selector === '#summary-table') return {
        text: value => {summaryText = value;},
        html: value => {summaryText = value;}
    };
    return {on: () => {}};
}
$.ajax = options => ({
    done(callback) {
        if (options.url.endsWith('/scanstatus')) {
            callback(['scan', '', '', '', '', 'FINISHED', {HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0}]);
        }
        return this;
    },
    fail(callback) {
        if (options.url.endsWith('/scansummary')) callback({status: 500});
        return this;
    }
});
const context = {document, $, sf: {fetchData: () => {}}, docroot: '', console, setTimeout};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../spiderfoot/static/js/spiderfoot.scaninfo.js'), 'utf8'), context);
context.setSection = id => {section = id;};
context.scanSummaryView('a'.repeat(32));
console.log(JSON.stringify({section, summaryText, statusLoaded: content.innerHTML.includes('扫描状态')}));

/* Native adapter for the supplied LiquidButton. No click/submit interception. */
(function (win, doc) {
  'use strict';
  const selector = 'button.fl-btn,a.fl-btn,button.pg-btn,a.pg-btn,button.btn,a.btn,'+
    'button.sm-btn,a.sm-btn,button.risk-btn,a.risk-btn,button.ajs-button,'+
    'input.btn,input.pg-btn';
  const filterId = 'workspace-liquid-glass-refraction';
  let observer = null;
  let filter = null;
  function svgElement(name, attributes) {
    const element = doc.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes).forEach(([key,value]) => element.setAttribute(key,value));
    return element;
  }
  function addFilter() {
    if (doc.getElementById(filterId)) return;
    filter = svgElement('svg', {'aria-hidden':'true',focusable:'false',width:'0',height:'0'});
    filter.style.cssText='position:absolute;width:0;height:0;pointer-events:none;overflow:hidden';
    const defs = svgElement('defs', {});
    const glass = svgElement('filter', {id:filterId,x:'0%',y:'0%',width:'100%',height:'100%','color-interpolation-filters':'sRGB'});
    // Exact filter stages/parameters from GlassFilter in the supplied component.
    [
      ['feTurbulence',{type:'fractalNoise',baseFrequency:'0.05 0.05',numOctaves:'1',seed:'1',result:'turbulence'}],
      ['feGaussianBlur',{in:'turbulence',stdDeviation:'2',result:'blurredNoise'}],
      ['feDisplacementMap',{in:'SourceGraphic',in2:'blurredNoise',scale:'70',xChannelSelector:'R',yChannelSelector:'B',result:'displaced'}],
      ['feGaussianBlur',{in:'displaced',stdDeviation:'4',result:'finalBlur'}],
      ['feComposite',{in:'finalBlur',in2:'finalBlur',operator:'over'}]
    ].forEach(([name,attrs]) => glass.appendChild(svgElement(name,attrs)));
    defs.appendChild(glass);filter.appendChild(defs);doc.body.appendChild(filter);
  }
  function decorate(button) {
    if (!button.matches(selector) || button.hasAttribute('data-liquid-skip')) return;
    if (!button.classList.contains('workspace-liquid-button')) button.classList.add('workspace-liquid-button');
    if (button.tagName === 'INPUT') return;
    let label = Array.from(button.children).find(child => child.classList.contains('workspace-liquid-label'));
    if (label && button.childNodes.length === 1) return;
    if (!label) {
      label = doc.createElement('span');
      label.className='workspace-liquid-label';
      // Move the ORIGINAL children. Their IDs and listeners remain intact.
      while (button.firstChild) label.appendChild(button.firstChild);
      button.appendChild(label);
    } else {
      Array.from(button.childNodes).filter(child => child!==label).forEach(child => label.appendChild(child));
    }
  }
  function scan(root) {
    if (root.nodeType !== 1) return;
    if (root.matches(selector)) decorate(root);
    root.querySelectorAll(selector).forEach(decorate);
  }
  function start() {
    if (observer || !doc.body.classList.contains('fluent-body')) return;
    addFilter();scan(doc.body);
    observer = new MutationObserver(records => {
      const buttons = new Set();
      for (const record of records) {
        const target=record.target.nodeType===1 ? record.target : record.target.parentElement;
        const owner=target && target.closest(selector);
        if (owner) buttons.add(owner);
        if (record.type==='attributes') scan(target);
        record.addedNodes.forEach(node => scan(node));
      }
      buttons.forEach(decorate);
    });
    // Dynamic task controls, table rows and changed loading labels use the same material.
    observer.observe(doc.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
  }
  function stop(event) {
    if (observer) observer.disconnect();observer=null;
    if (filter) filter.remove();filter=null;
    if (!event.persisted) {
      win.removeEventListener('pagehide',stop);win.removeEventListener('pageshow',restore);
    }
  }
  function restore(event) {if (event.persisted) start();}
  if (doc.readyState==='loading') doc.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
  win.addEventListener('pagehide',stop);win.addEventListener('pageshow',restore);
})(window,document);

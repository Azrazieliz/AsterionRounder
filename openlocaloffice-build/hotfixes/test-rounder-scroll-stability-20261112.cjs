#!/usr/bin/env node
'use strict';
// Source-level regression for Rounder's infinite downward-scroll feedback.
// Runs after all UI/theme overrides, before version stamping and signing.
const fs=require('node:fs');
const assert=require('node:assert/strict');
const ui=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const from=ui.indexOf('function showVirtualItems(items,mode,key)');
const to=ui.indexOf('function handleContinuousScroll()',from);
assert(from>=0&&to>from,'Current virtual scroll implementation missing');
const virtual=ui.slice(from,to);
assert(virtual.includes('Math.max(0,totalRows-windowRows)'),
  'The virtual window may drop all cards at the end of a list');
assert(virtual.includes("+'|'+columns+'|'+rowHeight+'|'"),
  'A layout change must invalidate the recycled card window');
assert(virtual.includes('virtualTop.style.height='));
assert(virtual.includes('virtualBottom.style.height='));
assert(ui.includes("body.addEventListener('scroll',handleContinuousScroll,{passive:true});"),
  'Native passive scrolling must remain enabled');
assert(css.includes('.fg-library-root .fg-lib-body{overflow-anchor:none!important}'),
  'WebView scroll-anchoring on the changing library content is not disabled');
assert(css.includes('.fg-library-root .fg-lib-grid,.fg-library-root .fg-vault-spacer{overflow-anchor:none!important}'),
  'WebView must not anchor recycled card or spacer nodes');
assert(css.includes('.fg-lib-body{')&&css.includes('overflow-y:auto'),
  'The real vertical scroll container must remain scrollable');
assert(!virtual.includes('scrollIntoView('),
  'Recycled tiles must not programmatically fling the viewport');

// Exercise the exact window-bound arithmetic for extreme lists and tiny drags.
// The final row must always remain reachable without an empty virtual window.
function windowFor(totalRows,rowHeight,clientHeight,relative){
  const windowRows=Math.max(10,Math.ceil(clientHeight/rowHeight)+12);
  const firstRow=Math.max(0,Math.min(Math.max(0,totalRows-windowRows),
    Math.floor(relative/rowHeight)-4));
  const endRow=Math.min(totalRows,firstRow+windowRows);
  return {firstRow,endRow,windowRows};
}
for(const rows of [0,1,2,9,10,11,25,180,500000]){
  for(const rh of [124,276,413]){
    for(const view of [360,900]){
      for(const rel of [-100,0,1,2,3,4,rh,rh*5,rh*500000]){
        const w=windowFor(rows,rh,view,rel);
        assert(w.firstRow>=0&&w.firstRow<=Math.max(0,rows-w.windowRows));
        assert(w.endRow<=rows&&w.endRow>=w.firstRow);
        if(rows>0)assert(w.endRow>w.firstRow,'No visible cards at scroll edge');
        if(rel>=0&&rel<rh*4)assert(w.firstRow===0,'Tiny drag moved the card window');
      }
    }
  }
}
console.log('ROUNDER_SCROLL_STABILITY_SOURCE_PASS: passive scroll, anchor disabled, bounded windows across 486 scenarios');

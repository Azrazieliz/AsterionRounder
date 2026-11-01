'use strict';
const fs=require('fs'),assert=require('assert');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const start=css.lastIndexOf('/* Seamless webtoon reading.');
assert(start>=0,'Seamless webtoon override missing');
const overrides=css.slice(start);
for(const expected of ['.fg-comic-stack .fg-pdf-container','gap:0!important','.fg-comic-stack .fg-comic-section','min-height:0!important','box-shadow:none!important','margin:0!important','padding:0!important','border:0!important','line-height:0!important']){
  assert(overrides.includes(expected),'Missing mandatory seamless CSS: '+expected);
}
assert(!overrides.includes('.fg-pdf-section{'),'PDF-specific page borders must not be modified');
console.log('PASS: edge-to-edge comic pages have no visual separators and retain PDF layout');

/* Behavioral WebView reader regression tests. No emulator/network required. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const reader=fs.readFileSync('app/src/main/assets/universal-reader.js','utf8');
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};
  this.style={setProperty:(k,v)=>{this.style[k]=v;}};this.className='';
  this.classList={add:()=>{},remove:()=>{},toggle:()=>{}};
  this.textContent='';this.clientWidth=720;this.clientHeight=1280;
  this.scrollTop=0;this.scrollLeft=0;this.listeners={};this.attributes={};this.isConnected=true;}
 append(...nodes){this.children.push(...nodes);}
 appendChild(node){this.children.push(node);return node;}
 prepend(node){this.children.unshift(node);}
 replaceChildren(...nodes){this.children=[...nodes];}
 setAttribute(k,v){this.attributes[k]=v;}
 removeAttribute(k){delete this.attributes[k];}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
 emit(name,event){for(const fn of this.listeners[name]||[])fn(event||{});}
 getBoundingClientRect(){return {top:0,bottom:900,height:900};}
 querySelector(){return null;}
 querySelectorAll(){return [];}
 remove(){}
}
const ids=new Map();
for(const id of ['editor','sheetBar','spreadsheetTools','textFormat','notice',
                 'saveBtn','copyBtn'])
 ids.set(id,new Element(id));
const document={
 body:new Element('body'),
 createElement:tag=>new Element(tag),
 createDocumentFragment:()=>new Element('fragment'),
 getElementById:id=>ids.get(id)||null,
 querySelector:selector=>selector==='.actions'?new Element('actions'):null
};
const pending=[];
const calls=[];
let currentText='';let currentArchive='[]';
const bridge={
 getPdfPageMetrics:()=>JSON.stringify(Array.from({length:27},()=>[1920,1080])),
 getPdfPage:(index,w)=>{calls.push([index,w]);return 'AA==';},
 getText:()=>currentText,
 getArchiveEntries:()=>currentArchive,
 getArchiveEntryBase64:()=> 'AA=='
};
class Observer{constructor(cb,options){this.cb=cb;this.options=options;this.observed=[];}
 observe(e){this.observed.push(e);}
 disconnect(){}
}
const win={loadDocument:()=>{},AndroidBridge:bridge,devicePixelRatio:2,
 IntersectionObserver:Observer};
const context={window:win,document,console,TextDecoder,TextEncoder,Uint8Array,
 IntersectionObserver:Observer,
 requestAnimationFrame:fn=>{pending.push(fn);return pending.length;},
 cancelAnimationFrame:()=>{},atob:()=>'\0',
 URL:{createObjectURL:()=>'',revokeObjectURL:()=>{}},
 Blob:class{},setTimeout:()=>{},clearTimeout:()=>{}};
vm.runInNewContext(reader,context,{filename:'universal-reader.js'});
function visit(root,predicate,out=[]){
 if(predicate(root))out.push(root);
 for(const child of root.children||[])visit(child,predicate,out);
 return out;
}
function buttons(){
 return visit(ids.get('editor'),x=>x.tagName==='button').map(x=>x.textContent);
}
function flush(max=8){for(let i=0;i<max&&pending.length;i++)pending.shift()();}
win.loadDocument({type:'pdf',format:'pdf',name:'Wide NoWorld PDF',pages:27,readOnly:true});
const root=ids.get('editor');
let pages=visit(root,x=>x.className.includes('fg-pdf-section'));
assert.strictEqual(pages.length,27,'All 27 PDF pages must exist in the scroll stack');
assert.strictEqual(pages[1].style.aspectRatio,String(1920/1080),
                   'Landscape aspect must be retained');
assert(!buttons().includes('‹')&&!buttons().includes('›'),
       'PDF must not have previous/next slide navigation');
flush();
assert(calls.length<=2,'Initial PDF load may only rasterize visible-near pages');
const stack=visit(root,x=>x.className==='fg-pdf-stack')[0];
const pdfBody=visit(root,x=>x.className.includes('fg-pdf-scroll'))[0];
assert(stack&&pdfBody,'The reader must provide a zoomable scroll surface');
assert(!buttons().includes('Fit')&&!buttons().includes('100%')&&!buttons().includes('+')&&!buttons().includes('−'),
  'Reader must not expose manual Fit, percentage or zoom buttons');
const finger=(x,y)=>({clientX:x,clientY:y});
pdfBody.emit('touchstart',{touches:[finger(100,200),finger(200,200)]});
let prevented=false;
pdfBody.emit('touchmove',{touches:[finger(65,200),finger(235,200)],
 preventDefault:()=>{prevented=true;}});
assert(prevented,'Two-finger gesture must block native scrolling while actively pinching');
assert(parseInt(stack.style.width)>100,'Pinch apart must increase actual page size');
pdfBody.emit('touchend',{touches:[],changedTouches:[]});
assert(pdfBody.listeners.wheel?.length,'Ctrl+wheel zoom is supported');

assert(visit(root,x=>x.className.includes('fg-pdf-scroll')).length===1,
       'PDF needs a single vertical scroll element');
currentText=('Paragraph one.\n\nParagraph two.\n\n').repeat(350);
win.loadDocument({type:'reader',name:'Text source',format:'txt',readOnly:true});
assert(!buttons().includes('‹')&&!buttons().includes('›'),
       'Text documents must never use previous/next page buttons');
assert(visit(root,x=>x.className.includes('fg-continuous-text')).length===1,
       'Text should be one continuous document');
currentArchive=JSON.stringify(Array.from({length:8},(_,i)=>({
 name:'page'+String(i).padStart(3,'0')+'.png',size:1000,preview:true
})));
win.loadDocument({type:'archive',name:'Comic',format:'cbz',readOnly:true});
assert.strictEqual(visit(root,x=>x.className.includes('fg-comic-section')).length,8,
                   'All comic images belong to one scrollable surface');
assert(!buttons().includes('‹')&&!buttons().includes('›'),
       'Comics must not use slide navigation');
currentArchive=JSON.stringify([
 {name:'Book/10.webp',size:300,preview:true,streamed:true},
 {name:'Book/2.webp',size:280,preview:true,streamed:true},
 {name:'Book/1.webp',size:245,preview:true,streamed:true}
]);
win.loadDocument({type:'archive',name:'Comics.zip',format:'zip',comicMode:true,streamed:true});
const images=visit(root,x=>x.className.includes('fg-comic-section'));
assert.strictEqual(images.length,3,'An image-heavy ZIP must render as a continuous comic');
assert.strictEqual(images[0].attributes['aria-label'],'Comic image 1 Book/1.webp',
  'Comic ZIP pages must be numerically ordered, 1 then 2 then 10');
assert.strictEqual(images[1].attributes['aria-label'],'Comic image 2 Book/2.webp');
assert(!buttons().includes('‹')&&!buttons().includes('›'),
  'Image ZIP must not use slideshow controls');
assert(buttons().includes('Files'),'ZIP comic has a non-default file-list option');
currentArchive=JSON.stringify([{name:'notes.txt',size:500,preview:true}]);
win.loadDocument({type:'archive',name:'ZIP',format:'zip',readOnly:true});
assert.strictEqual(visit(root,x=>x.tagName==='details').length,1,
       'ZIP reader must show inline expandable entries');
console.log('Continuous reader behavior OK: landscape PDF 27 pages, lazy PDF, text, CBZ, ZIP');

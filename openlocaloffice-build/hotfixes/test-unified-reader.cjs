/* Regression simulation of unified reader controls (without Android runtime). */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync('app/src/main/assets/unified-viewer-controls.js','utf8');
const instances=[];
class Fake {
  constructor(cls=''){
    this.className=cls;this.children=[];this.listeners={};
    this.style={setProperty:(k,v)=>{this.style[k]=v;}};
    const state=new Set(cls.split(' '));
    this.classList={contains:x=>state.has(x),add:(...xs)=>xs.forEach(x=>state.add(x)),
      remove:(...xs)=>xs.forEach(x=>state.delete(x))};
    this.clientWidth=400;this.clientHeight=650;this.scrollLeft=0;this.scrollTop=0;
  }
  appendChild(el){this.children.push(el);return el;}
  append(...xs){this.children.push(...xs);}
  setAttribute(){}
  addEventListener(key,fn){(this.listeners[key]??=[]).push(fn);}
  removeEventListener(key,fn){this.listeners[key]=(this.listeners[key]||[]).filter(f=>f!==fn);}
  remove(){}
  getBoundingClientRect(){return {top:0,left:0,bottom:650,right:400};}
  emit(key,arg){for(const fn of this.listeners[key]||[])fn(arg);}
  closest(){return null;}
}
const editor=new Fake(),work=new Fake();
const body=new Fake(''),mockDoc={body,createElement:t=>new Fake(t)};
const nodes={editor,work};
mockDoc.getElementById=id=>{
  if(id==='fg-unified-dock')return work.children.find(x=>x.id===id)||null;
  return nodes[id]||null;
};
let current={};
editor.querySelector=selector=>current[selector]||null;
const mockWindow={
  loadDocument:d=>{
    current={};
    const scroll=new Fake('scroll'),target=new Fake('content');
    switch(d.type){
      case 'spreadsheet':current['.editorGridWrap']=scroll;current['table.sheet']=target;break;
      case 'sdocx':current['#sdocxEditor']=target;break;
      case 'docx':target.className='fg-docx-sheet';target.classList.add('fg-docx-sheet');current['.fg-docx-scroll']=scroll;current['.fg-docx-sheet']=target;break;
      case 'reader':current['.fg-text-scroll']=scroll;current['.fg-continuous-text']=target;break;
      case 'image':current['.fg-image-surface']=scroll;current['.fg-display-image']=target;break;
      case 'archive':
        current['.fg-archive-scroll']=scroll;
        current[(d.format==='cbz'||d.comicMode===true)&&!d.forceArchiveList?
          '.fg-comic-stack':'.fg-archive-list']=target;break;
      case 'binary':current['.fg-reader-scroll']=scroll;current['.fg-document-sheet']=target;break;
    }
  }
};
const callbacks=[];
const ctx={
 window:mockWindow,document:mockDoc,console,Date,Math,
 requestAnimationFrame:fn=>{callbacks.push(fn);return callbacks.length;}
};
vm.runInNewContext(code,ctx,{filename:'unified-viewer-controls.js'});
function flush(){while(callbacks.length)callbacks.shift()();}
for(const d of [
 {type:'reader',format:'txt'}, {type:'reader',format:'epub'},
 {type:'docx',format:'docx'},{type:'image',format:'png'},
 {type:'archive',format:'cbz'},{type:'archive',format:'zip',comicMode:true},
 {type:'archive',format:'zip'},
 {type:'binary',format:'bin'},{type:'spreadsheet',format:'xlsx'},
 {type:'sdocx',format:'sdocx'}
]){
 mockWindow.loadDocument(d);flush();
 const active=mockWindow.FileGestionerUnifiedReader.current();
 assert(active,'Missing controller for '+d.type+' '+d.format);
 assert(!work.children.some(x=>x.id==='fg-unified-dock'),
  'Zoom dock must not be mounted for '+d.type);
 assert.strictEqual(active.target.style.width||'','',
  'Initial zoom must remain fitted, no premature width expansion');
 let blocked=false;
 const finger=(x,y)=>({clientX:x,clientY:y});
 active.scroller.emit('touchstart',{touches:[finger(100,100),finger(200,100)]});
 active.scroller.emit('touchmove',{touches:[finger(60,100),finger(240,100)],
   preventDefault:()=>{blocked=true;}});
 assert(blocked,'Pinch must prevent native multi-touch scroll for '+d.type);
 assert(active.kind&&active.zoomTo,'Pinch controller must remain active');
 if(d.type==='image'||d.format==='cbz'||d.comicMode===true)
   assert(Number.parseInt(active.target.style.width)>100,'Pinch must enlarge visual content');
 active.zoomTo(1);
 if(d.type==='image'||d.format==='cbz'||d.comicMode===true)
   assert.strictEqual(active.target.style.width,'100%','Fit width reset must restore base');
}
for(const type of ['pdf','model3d']){
 mockWindow.loadDocument({type});
 assert(!mockWindow.FileGestionerUnifiedReader.current(),
  'PDF and 3D must use their own format-native pinch/zoom without duplicate dock');
}
console.log('PASS: unified professional zoom across TXT, EPUB, DOCX, PNG, CBZ, ZIP, binary, XLSX, SDOCX, plus PDF/3D delegation.');

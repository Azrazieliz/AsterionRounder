/* File Gestioner universal offline reader */
(()=>{'use strict';
const $=id=>document.getElementById(id), original=window.loadDocument;
let doc=null, page=0, zoom=1, archiveIndex=0, assetUrl=null, editing=false;
const bridge=()=>window.AndroidBridge||null;
const ro=d=>['pdf','image','reader','archive','binary'].includes(d?.type)||d?.readOnly===true;
function E(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function button(label,click){const b=E('button','fg-reader-button',label);b.onclick=click;return b;}
function toolbar(description){
 const t=E('div','fg-reader-toolbar');
 t.append(E('span','fg-reader-kind',(doc.format||doc.type||'file').toUpperCase()),
  E('span','fg-reader-title',doc.name||'Document'),E('span','fg-reader-desc',description));
 const tools=E('div','fg-reader-tools');t.appendChild(tools);return [t,tools];
}
function paper(tag){const p=E('article','fg-page '+(tag||''));p.style.setProperty('--fg-size',String(zoom));return p;}
function stage(t,content,hasTextSearch=false){
 const host=$('editor');host.classList.add('fg-reader-host');host.replaceChildren(t,content);
 for(const id of ['sheetBar','spreadsheetTools','textFormat','notice'])$(id)?.classList.add('hidden');
 document.querySelector('.searchbar')?.classList.toggle('hidden',!hasTextSearch);
 if(ro(doc)){$('saveBtn').disabled=true;$('copyBtn').disabled=true;}
}
function decode(encoded){
 const bin=atob(encoded),out=new Uint8Array(bin.length);
 for(let i=0;i<bin.length;i++)out[i]=bin.charCodeAt(i);
 return out;
}
function localBytes(){
 const b=bridge(),length=Number(b?.getRawDocumentSize?.()||0);
 if(!length||length>80*1024*1024)throw Error('File exceeds safe preview size.');
 const chunks=[],size=120*1024;
 for(let off=0;off<length;off+=size)chunks.push(decode(b.getRawDocumentChunk(off,Math.min(size,length-off))));
 const out=new Uint8Array(length);let pos=0;
 for(const c of chunks){out.set(c,pos);pos+=c.length;}
 return out;
}
/* File Gestioner mobile PDF reading surface.
   One natural scrolling document; actual layout zoom, pinch gestures and
   anchored two-dimensional panning, never a PDF-as-slideshow carousel. */
let activeReaderCleanup=null;
function pdf(){
 const b=bridge(),count=Math.max(0,Number(doc.pages)||0);
 const [bar,tools]=toolbar('');bar.classList.add('fg-pdf-toolbar');
 const body=E('div','fg-reader-scroll fg-pdf-scroll');
 body.setAttribute('role','document');
 body.setAttribute('aria-label',(doc.name||'PDF')+' — '+count+' pages');
 body.setAttribute('tabindex','0');
 const stack=E('div','fg-pdf-stack'),pages=E('div','fg-pdf-container');
 stack.appendChild(pages);body.appendChild(stack);
 const cells=[],loaded=new Map(),queued=new Set();
 let metrics=[],observer=null,disposed=false,renderScheduled=false,scrollFrame=0;
 let readingPage=0,scale=1,qualityTimer=0,pinch=null;
 const zoomKey='fg.pdf.zoom.v1.'+String(doc.name||'');
 let savedZoom=1;
 try {
   const v=Number(localStorage.getItem(zoomKey));
   if(Number.isFinite(v)&&v>=.65&&v<=4)savedZoom=v;
 }catch(_){} 
 try{metrics=JSON.parse(b?.getPdfPageMetrics?.()||'[]');}
 catch(_){metrics=[];}
 if(!Array.isArray(metrics))metrics=[];
 const progress=E('span','fg-reader-counter fg-pdf-progress',count?'1 / '+count:'0 pages');
 progress.setAttribute('aria-label','Current PDF page');
 const percent=button('100%',()=>changeZoom(1));
 percent.classList.add('fg-pdf-percent');
 percent.setAttribute('aria-label','Reset zoom to fit width');
 const minus=button('−',()=>changeZoom(scale/1.25));
 const plus=button('+',()=>changeZoom(scale*1.25));
 const fit=button('Fit',()=>changeZoom(1));
 minus.setAttribute('aria-label','Zoom out');
 plus.setAttribute('aria-label','Zoom in');
 fit.setAttribute('aria-label','Fit PDF to screen width');
 const pageLabel=E('span','fg-pdf-page-label','Page');
 tools.append(pageLabel,progress,minus,percent,plus,fit);
 function targetWidth(){
   return Math.max(400,Math.min(2400,
     Math.round(Math.max(body.clientWidth,320)*(window.devicePixelRatio||1)*scale)));
 }
 function skeleton(i){
   return E('div','fg-pdf-skeleton','Page '+(i+1));
 }
 function release(i){
   const old=loaded.get(i);
   if(old?.img)old.img.removeAttribute('src');
   loaded.delete(i);
   cells[i]?.replaceChildren(skeleton(i));
 }
 function request(i,force=false){
   if(disposed||i<0||i>=count||queued.has(i))return;
   const item=loaded.get(i);
   const target=targetWidth();
   if(!force&&item&&item.pixels>=target*.82&&item.pixels<=target*1.8)return;
   queued.add(i);
   if(!renderScheduled){renderScheduled=true;requestAnimationFrame(renderNext);}
 }
 function renderNext(){
   renderScheduled=false;
   if(disposed)return;
   const item=queued.values().next();
   if(item.done)return;
   queued.delete(item.value);
   const i=item.value,cell=cells[i];if(!cell)return;
   const view=body.getBoundingClientRect(),rect=cell.getBoundingClientRect();
   if(rect.bottom>=view.top-1.6*body.clientHeight &&
      rect.top<=view.bottom+1.6*body.clientHeight){
     try{
       const pixels=targetWidth();
       const jpg=b?.getPdfPage?.(i,pixels);
       if(!jpg)throw Error('PDF renderer returned no image');
       const im=E('img','fg-pdf-img');
       im.alt='Page '+(i+1)+' of '+count;im.decoding='async';im.draggable=false;
       im.src='data:image/jpeg;base64,'+jpg;
       im.onerror=()=>{if(!disposed&&loaded.get(i)?.img===im){
         loaded.delete(i);
         cell.replaceChildren(E('p','fg-reader-empty','Unable to display page '+(i+1)));
       }};
       const previous=loaded.get(i);
       cell.replaceChildren(im);
       loaded.set(i,{img:im,pixels});
       if(previous?.img&&previous.img!==im)previous.img.removeAttribute('src');
     }catch(err){
       if(!loaded.has(i))cell.replaceChildren(E('p','fg-reader-empty',
         'Page '+(i+1)+' could not be rendered: '+String(err.message||err)));
     }
   }
   trim();
   if(queued.size){renderScheduled=true;requestAnimationFrame(renderNext);}
 }
 function trim(){
   if(disposed)return;
   const view=body.getBoundingClientRect();
   for(const [i] of loaded){
     const rect=cells[i].getBoundingClientRect();
     if(rect.bottom<view.top-2.2*body.clientHeight ||
        rect.top>view.bottom+2.2*body.clientHeight)release(i);
   }
 }
 function updatePage(){
   if(disposed||!count)return;
   const rect=body.getBoundingClientRect(),line=rect.top+body.clientHeight*.34;
   let match=readingPage,min=Infinity;
   for(let i=0;i<count;i++){
     const r=cells[i].getBoundingClientRect();
     const d=line<r.top?r.top-line:line>r.bottom?line-r.bottom:0;
     if(d<min){min=d;match=i;if(!d)break;}
   }
   readingPage=match;progress.textContent=(match+1)+' / '+count;
   trim();
   if(!observer){
     for(let i=Math.max(0,match-1);i<=Math.min(count-1,match+2);i++)request(i);
   }
 }
 function sharpen(){
   if(disposed)return;
   const i=readingPage;
   for(let n=Math.max(0,i-1);n<=Math.min(count-1,i+1);n++)request(n);
 }
 function queueSharpen(){
   if(qualityTimer)clearTimeout(qualityTimer);
   qualityTimer=setTimeout(()=>{qualityTimer=0;sharpen();},165);
 }
 function changeZoom(requested,fx=body.clientWidth/2,fy=body.clientHeight/2,interactive=false){
   if(disposed)return;
   const next=Math.min(4,Math.max(.65,Math.round(Number(requested)*1000)/1000));
   if(!Number.isFinite(next)||Math.abs(next-scale)<.003)return;
   const previous=scale;
   // Preserve the document point under the user's fingers or the control focus.
   const anchorX=(body.scrollLeft+fx)/previous;
   const anchorY=(body.scrollTop+fy)/previous;
   scale=next;
   stack.style.width=(scale*100)+'%';
   percent.textContent=Math.round(scale*100)+'%';
   body.scrollLeft=Math.max(0,anchorX*scale-fx);
   body.scrollTop=Math.max(0,anchorY*scale-fy);
   updatePage();
   if(!interactive){
     try{localStorage.setItem(zoomKey,String(scale));}catch(_){}
     queueSharpen();
   }
 }
 for(let i=0;i<count;i++){
   const data=metrics[i],w=Number(data?.[0]),h=Number(data?.[1]);
   const aspect=Number.isFinite(w/h)&&w>0&&h>0?w/h:.707106;
   const cell=E('section','fg-pdf-section');
   cell.dataset.page=String(i+1);
   cell.style.aspectRatio=String(aspect);
   cell.setAttribute('aria-label','PDF page '+(i+1));
   cell.appendChild(skeleton(i));
   pages.appendChild(cell);cells.push(cell);
 }
 if(!count)pages.appendChild(E('p','fg-reader-empty','This PDF is empty.'));
 stage(bar,body);
 document.body.classList.add('fg-pdf-reading');
 if(Math.abs(savedZoom-1)>.005)changeZoom(savedZoom);
 // Gesture scale never invokes the native renderer inside touchmove.
 const distance=(a,b)=>Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
 const focal=(a,b)=>{
   const rect=body.getBoundingClientRect();
   return [(a.clientX+b.clientX)/2-rect.left,(a.clientY+b.clientY)/2-rect.top];
 };
 const onTouchStart=e=>{
   if(e.touches.length===2){
     const [x,y]=focal(e.touches[0],e.touches[1]);
     pinch={span:Math.max(1,distance(e.touches[0],e.touches[1])),
       initial:scale,x,y,moved:false};
   }
 };
 const onTouchMove=e=>{
   if(!pinch||e.touches.length!==2)return;
   e.preventDefault();pinch.moved=true;
   const [x,y]=focal(e.touches[0],e.touches[1]);
   changeZoom(pinch.initial*distance(e.touches[0],e.touches[1])/pinch.span,
     x,y,true);
 };
 let lastTouchTime=0,lastTouchPoint=null,suppressTap=false;
 const onTouchEnd=e=>{
   if(pinch){
     if(e.touches.length<2){
       suppressTap=pinch.moved;pinch=null;
       try{localStorage.setItem(zoomKey,String(scale));}catch(_){}
       queueSharpen();
     }
     return;
   }
   if(e.touches.length||e.changedTouches.length!==1)return;
   if(suppressTap){suppressTap=false;return;}
   const t=Date.now(),v=e.changedTouches[0],rect=body.getBoundingClientRect();
   if(t-lastTouchTime<320&&lastTouchPoint&&
      Math.hypot(v.clientX-lastTouchPoint[0],v.clientY-lastTouchPoint[1])<32){
     e.preventDefault();
     changeZoom(scale>=1.8?1:2,v.clientX-rect.left,v.clientY-rect.top);
     lastTouchTime=0;lastTouchPoint=null;
   }else{lastTouchTime=t;lastTouchPoint=[v.clientX,v.clientY];}
 };
 body.addEventListener('touchstart',onTouchStart,{passive:true});
 body.addEventListener('touchmove',onTouchMove,{passive:false});
 body.addEventListener('touchend',onTouchEnd,{passive:false});
 body.addEventListener('touchcancel',()=>{pinch=null;queueSharpen();},{passive:true});
 // Desktop/test accessibility: Ctrl+wheel zoom, double click, keyboard.
 body.addEventListener('wheel',e=>{
   if(!e.ctrlKey&&!e.metaKey)return;
   e.preventDefault();
   const rect=body.getBoundingClientRect();
   changeZoom(scale*Math.exp(-e.deltaY*.008),e.clientX-rect.left,e.clientY-rect.top);
 },{passive:false});
 body.addEventListener('dblclick',e=>{
   const rect=body.getBoundingClientRect();
   changeZoom(scale>=1.8?1:2,e.clientX-rect.left,e.clientY-rect.top);
 });
 body.addEventListener('keydown',e=>{
   if(e.key==='+'||e.key==='='){e.preventDefault();changeZoom(scale*1.25);}
   if(e.key==='-'){e.preventDefault();changeZoom(scale/1.25);}
   if(e.key==='0'){e.preventDefault();changeZoom(1);}
 });
 if(window.IntersectionObserver){
   observer=new IntersectionObserver(items=>{
     if(disposed)return;
     for(const item of items)if(item.isIntersecting)
       request(Number(item.target.dataset.page)-1);
   },{root:body,rootMargin:'80% 0px',threshold:0});
   cells.forEach(cell=>observer.observe(cell));
 }
 body.addEventListener('scroll',()=>{
   if(scrollFrame)return;
   scrollFrame=requestAnimationFrame(()=>{scrollFrame=0;updatePage();});
 },{passive:true});
 if(count){request(0);if(count>1)request(1);}
 activeReaderCleanup=()=>{
   disposed=true;
   observer?.disconnect();queued.clear();
   if(qualityTimer)clearTimeout(qualityTimer);
   if(scrollFrame)cancelAnimationFrame(scrollFrame);
   for(const [i] of loaded)release(i);
   loaded.clear();
 };
}
function imageView(){
 const [bar,tools]=toolbar('Image preview · pinch/scroll to inspect');
 const body=E('div','fg-reader-scroll fg-image-surface'),img=E('img','fg-display-image');
 const formats={jpg:'jpeg',jpeg:'jpeg',png:'png',webp:'webp',gif:'gif',avif:'avif',bmp:'bmp',heic:'heic',heif:'heif'};
 try{
  if(!assetUrl)assetUrl=doc.streamed&&doc.url?doc.url:
    URL.createObjectURL(new Blob([localBytes()],{type:'image/'+(formats[doc.format]||'jpeg')}));
  img.src=assetUrl;img.alt=doc.name;img.style.width='100%';
  img.onerror=()=>{body.replaceChildren(E('p','fg-reader-empty','This image codec is unsupported by the installed Android WebView.'));};
  body.appendChild(img);
 }catch(e){body.appendChild(E('p','fg-reader-empty',String(e.message||e)));}
 stage(bar,body);
}
function addLines(host,raw,format){
 const code=/^(json|xml|yaml|yml|toml|log|sql|tsv|java|kt|kts|js|ts|css|scss|py|sh|ini|conf|svg|gradle|c|cpp|h|hpp|go|rs|php|gitignore)$/.test(format||'');
 if(code){host.appendChild(E('pre','fg-document-code',raw));return;}
 const markdown=['md','markdown'].includes(format);
 const lines=String(raw).replace(/\r\n?/g,'\n').split('\n');
 let buffer=[],codeBlock=null;
 function flush(){
   if(!buffer.length)return;
   const p=E('p','fg-document-p',buffer.join('\n'));
   host.appendChild(p);buffer=[];
 }
 for(const line of lines){
   const trimmed=line.trim();
   if(markdown&&/^ {0,3}~~~/.test(line)){
     flush();
     if(codeBlock){host.appendChild(E('pre','fg-document-code',codeBlock.join('\n')));codeBlock=null;}
     else codeBlock=[];
     continue;
   }
   if(markdown&&line.trimStart().startsWith(String.fromCharCode(96,96,96))){
     flush();
     if(codeBlock){host.appendChild(E('pre','fg-document-code',codeBlock.join('\n')));codeBlock=null;}
     else codeBlock=[];
     continue;
   }
   if(codeBlock){codeBlock.push(line);continue;}
   if(!trimmed){flush();continue;}
   const md=markdown?/^(#{1,6})\s+(.+)$/.exec(trimmed):null;
   if(md){flush();host.appendChild(E(md[1].length<=1?'h1':'h2',md[1].length<=1?'fg-document-h1':'fg-document-h2',md[2]));continue;}
   if(markdown&&/^[-*+]\s+/.test(trimmed)){flush();host.appendChild(E('p','fg-document-bullet','• '+trimmed.slice(2)));continue;}
   if(markdown&&/^\d+[.)]\s+/.test(trimmed)){flush();host.appendChild(E('p','fg-document-bullet',trimmed));continue;}
   if(markdown&&/^>\s*/.test(trimmed)){flush();host.appendChild(E('blockquote','fg-docx-quote',trimmed.replace(/^>\s*/,'')));continue;}
   // Plain-text line breaks remain in the same logical paragraph; separate
   // only at blank lines, not at every wrapped or hard-broken source line.
   buffer.push(line);
 }
 flush();
 if(codeBlock)host.appendChild(E('pre','fg-document-code',codeBlock.join('\n')));
}
/* TXT, Markdown, EPUB, ODT/ODS text and code all scroll in ONE document.
   Large sources append source-preserving blocks rather than artificial pages. */
function textView(){
 const text=String(bridge()?.getText?.()||'');
 const [bar,tools]=toolbar('Continuous document · vertical scrolling');
 const body=E('div','fg-reader-scroll fg-text-scroll');
 const sheet=paper('fg-document-sheet fg-continuous-text');
 sheet.setAttribute('role','document');
 sheet.setAttribute('aria-label',doc.name||'Document');
 if(text.length<=2_000_000) {
   addLines(sheet,text,doc.format);
 } else {
   // Very large files: preserve every character, including whitespace and
   // original line breaks, while avoiding a monolithic UI-thread DOM build.
   let offset=0,loading=false;
   function append(){
     if(loading||offset>=text.length)return;
     loading=true;
     const frag=document.createDocumentFragment();
     for(let n=0;n<3&&offset<text.length;n++){
       let end=Math.min(text.length,offset+64_000);
       if(end<text.length){
         const cut=text.lastIndexOf('\n',end);
         if(cut>offset+32_000)end=cut+1;
       }
       const part=E('pre','fg-document-code fg-raw-text',text.slice(offset,end));
       frag.appendChild(part);offset=end;
     }
     sheet.appendChild(frag);loading=false;
   }
   append();
   let ticking=false;
   body.addEventListener('scroll',()=>{
     if(ticking)return;ticking=true;
     requestAnimationFrame(()=>{
       ticking=false;
       if(body.scrollTop+body.clientHeight>body.scrollHeight-1000)append();
     });
   },{passive:true});
 }
 body.appendChild(sheet);stage(bar,body);
}
/* DOCX reads body blocks in order, keeps tables together, and scrolls without
   manufacturing pages every 150 paragraphs. Windows are lazily appended. */
function docx(){
 const b=bridge();
 let count=0;
 try{count=Number(b?.getDocxRichBlockCount?.()||0);}catch(_){}
 const [bar,tools]=toolbar('Faithful document flow · original tables, headings and lists');
 const body=E('div','fg-reader-scroll fg-docx-scroll');
 const sheet=paper('fg-document-sheet fg-docx-sheet');
 sheet.setAttribute('role','document');
 sheet.setAttribute('aria-label',doc.name||'Word document');
 const progress=E('span','fg-reader-counter','');
 const message=E('div','fg-docx-message','');
 const foot=E('div','fg-docx-foot');
 foot.append(progress);
 body.append(sheet,foot);
 let next=0,start=0,loading=false,lastSearch=0;
 const chunk=24;
 function updateProgress(){
   const done=Math.min(count,next);
   progress.textContent=count?done+' / '+count+' blocks':'Empty document';
 }
 function appendNext(){
   if(loading||next>=count)return;
   loading=true;
   try{
     const rows=JSON.parse(b?.getDocxRichWindow?.(next,chunk)||'[]');
     if(!Array.isArray(rows)||!rows.length)throw Error('Reader returned no document blocks.');
     const f=document.createDocumentFragment();
     for(const item of rows){
       if(!Array.isArray(item)||item.length!==2)continue;
       const n=E('div','fg-docx-flow-block');
       n.dataset.index=String(item[0]);
       // Only our native parser produces HTML, with escaped user text.
       n.innerHTML=item[1];
       f.appendChild(n);
     }
     sheet.appendChild(f);
     next=Math.min(count,next+rows.length);
     message.textContent=start?'Showing from document block '+(start+1):'';
   }catch(e){
     message.textContent='Cannot render this section: '+String(e.message||e);
   }finally{loading=false;updateProgress();}
 }
 function showFrom(index){
   start=Math.max(0,Math.min(count-1,index));next=start;
   sheet.replaceChildren();body.scrollTop=0;
   appendNext();
 }
 const begin=button('↑ Start',()=>{lastSearch=0;showFrom(0);});
 begin.title='Return to the beginning of the document';
 tools.appendChild(begin);
 const searchInput=E('input','fg-reader-find');
 searchInput.type='search';searchInput.placeholder='Find in document';
 searchInput.setAttribute('aria-label','Find in entire Word document');
 const findAction=()=>{
   const term=searchInput.value.trim();
   if(!term)return;
   const target=Number(b?.findDocxBlock?.(term,lastSearch)??-1);
   if(target<0){message.textContent='No matching text found';return;}
   lastSearch=target+1;
   let node=sheet.querySelector('[data-index="'+target+'"]');
   if(!node){showFrom(target);node=sheet.querySelector('[data-index="'+target+'"]');}
   if(node)node.scrollIntoView({block:'start',behavior:'auto'});
   message.textContent='Match at block '+(target+1)+' of '+count;
 };
 searchInput.addEventListener('keydown',event=>{
   if(event.key==='Enter'){event.preventDefault();findAction();}
 });
 tools.append(searchInput,button('Find',findAction));
 tools.appendChild(button('Edit text',()=>{
   editing=true;original(doc);
   $('editor').classList.remove('fg-reader-host');
   $('fgBackToReader').classList.remove('hidden');
 }));
 foot.prepend(message);
 updateProgress();
 if(count)appendNext();
 else sheet.appendChild(E('p','fg-reader-empty','No Word body content was found.'));
 let scheduled=false;
 body.addEventListener('scroll',()=>{
   if(scheduled)return;
   scheduled=true;
   requestAnimationFrame(()=>{
     scheduled=false;
     if(body.scrollTop+body.clientHeight>=body.scrollHeight-850){
       appendNext();
       requestAnimationFrame(fillViewport);
     }
   });
 },{passive:true});
 stage(bar,body);
 // DOCX editing exists, but accidental Save in reader mode is not offered.
 if($('saveBtn'))$('saveBtn').disabled=true;
 if($('copyBtn'))$('copyBtn').disabled=true;
 function fillViewport(){
   if(next>=count||loading)return;
   if(body.scrollHeight<=body.clientHeight+400){
     const before=next;
     appendNext();
     if(next>before)requestAnimationFrame(fillViewport);
   }
 }
 requestAnimationFrame(fillViewport);
}
/* Comics and archives are content streams, not one-entry slide decks. */
function archive(){
 let entries=[];
 try{entries=JSON.parse(bridge()?.getArchiveEntries?.()||'[]');}catch(_){}
 const isComic=(doc.format==='cbz'||doc.comicMode===true)&&!doc.forceArchiveList;
 const remoteArchive=doc.cloudSource===true;
 if(isComic){
   entries=entries.filter(e=>/\.(png|jpe?g|gif|webp|bmp|avif|heic|heif)$/i.test(e.name));
   entries.sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
 }
 const [bar,tools]=toolbar('');
 const changeMode=mode=>window.loadDocument({
   ...doc,comicMode:mode,forceArchiveList:!mode
 });
 // Each image-first ZIP opens in uninterrupted comic mode; the file list
 // is available on demand, never imposed as the default reading surface.
 if(doc.format==='zip'||doc.comicMode===true||doc.forceArchiveList){
   tools.appendChild(button(isComic?'Files':'Read images',
     ()=>changeMode(!isComic)));
 }
 const body=E('div','fg-reader-scroll fg-archive-scroll');
 body.setAttribute('role','document');
 const position=E('span','fg-reader-counter',isComic?
   '1 / '+entries.length:entries.length+' files');
 tools.appendChild(position);
 if(!entries.length){
   body.appendChild(E('p','fg-reader-empty','Archive has no previewable entries.'));
   stage(bar,body);return;
 }
 function content(entry,dest,onSettled){
   dest.replaceChildren();
   let completed=false;
   const settle=()=>{if(completed)return;completed=true;onSettled?.();};
   if(!entry.preview){
     dest.appendChild(E('p','fg-reader-empty','This entry cannot be previewed safely.'));
     settle();return;
   }
   try{
     const data=entry.streamed?'':(bridge()?.getArchiveEntryBase64?.(entry.name)||'');
     if(!data&&!entry.streamed)throw Error('This archive entry cannot be displayed inline.');
     if(/\.(png|jpe?g|gif|webp|bmp|avif)$/i.test(entry.name)){
       const ext=entry.name.split('.').pop().toLowerCase();
       const im=E('img','fg-archive-img');im.alt=entry.name;
       im.loading='lazy';
       let watchdog=0;
       im.addEventListener('load',()=>{
         clearTimeout(watchdog);settle();
         if(isComic)bridge()?.readerDiagnostic?.('COMIC_IMAGE_LOADED');
       });
       im.addEventListener('error',()=>{
         clearTimeout(watchdog);
         im.removeAttribute('src');
         const retry=button('Retry image',()=>{
            retry.remove();
            im.src=entry.streamed?(bridge()?.getArchiveImageUrl?.(entry.name)||''):
              'data:image/jpeg;base64,'+data;
         });
         retry.classList.add('fg-image-retry');
         dest.appendChild(retry);
         settle();
         bridge()?.readerDiagnostic?.('ARCHIVE_IMAGE_FAILED');
       });
       im.src=entry.streamed?(bridge()?.getArchiveImageUrl?.(entry.name)||''):
         'data:image/'+(ext==='jpg'?'jpeg':ext)+';base64,'+data;
       dest.appendChild(im);
       watchdog=setTimeout(()=>{
         if(im.isConnected && !(im.complete&&im.naturalWidth>0)){
           // Timeout exposes a retry of the same original cloud range stream.
           // It MUST NOT activate a different URL, image preview, or sample.
           im.removeAttribute('src');
           im.dispatchEvent(new Event('error'));
           bridge()?.readerDiagnostic?.('ARCHIVE_ORIGINAL_STREAM_TIMEOUT');
         }
       },remoteArchive?30000:12000);
     }else{
       dest.appendChild(E('pre','fg-document-code',
         new TextDecoder().decode(decode(data))));
       settle();
     }
   }catch(error){
     dest.appendChild(E('p','fg-reader-empty',
       'Cannot preview '+entry.name+': '+String(error.message||error)));
     settle();
   }
 }
 if(isComic){
   const stack=E('div','fg-pdf-stack fg-comic-stack'),cells=[],loaded=new Map();
   let disposed=false,observer=null,scheduled=false,inFlight=0;
   const MAX_IMAGE_FETCHES=remoteArchive?2:4;
   const queue=new Set();
   const root=E('div','fg-pdf-container');
   function enqueue(i){
     if(disposed||loaded.has(i)||queue.has(i))return;
     queue.add(i);
     if(!scheduled){scheduled=true;requestAnimationFrame(draw);}
   }
   function draw(){
     scheduled=false;
     if(disposed||!queue.size||inFlight>=MAX_IMAGE_FETCHES)return;
     const i=queue.values().next().value;queue.delete(i);
     const frame=cells[i],rect=frame.getBoundingClientRect(),view=body.getBoundingClientRect();
     if(rect.bottom>=view.top-body.clientHeight&&rect.top<=view.bottom+body.clientHeight){
       const target=E('div','fg-comic-page');
       // Once the placeholder is replaced, the IMG still has no intrinsic
       // size until its network bytes arrive. Preserve the viewport slot,
       // otherwise every subsequent page collapses into view at once.
       if(remoteArchive)target.style.minHeight='85vh';
       inFlight++;
       let released=false;
       const release=()=>{
         if(released)return;released=true;
         const ready=target.querySelector('img');
         if(ready?.naturalWidth>0&&ready?.naturalHeight>0)
           target.style.minHeight='';
         inFlight=Math.max(0,inFlight-1);
         if(!disposed&&queue.size&&!scheduled){
           scheduled=true;requestAnimationFrame(draw);
         }
       };
       target.rounderRelease=release;
       content(entries[i],target,release);
       frame.replaceChildren(target);loaded.set(i,target);
     }
     trim();
     if(queue.size&&inFlight<MAX_IMAGE_FETCHES){
       scheduled=true;requestAnimationFrame(draw);
     }
   }
   function trim(){
     const view=body.getBoundingClientRect();
     for(const [i,target] of loaded){
       const rect=cells[i].getBoundingClientRect();
       if(rect.bottom<view.top-3*body.clientHeight||
          rect.top>view.bottom+3*body.clientHeight){
         target.rounderRelease?.();
         target.querySelectorAll('img').forEach(img=>img.removeAttribute('src'));
         loaded.delete(i);
         cells[i].replaceChildren(E('div','fg-pdf-skeleton','Image '+(i+1)));
       }
     }
   }
   entries.forEach((entry,i)=>{
     const frame=E('section','fg-comic-section');
     frame.dataset.page=String(i+1);
     frame.setAttribute('aria-label','Comic image '+(i+1)+' '+entry.name);
     frame.appendChild(E('div','fg-pdf-skeleton','Image '+(i+1)));
     root.appendChild(frame);cells.push(frame);
   });
   stack.appendChild(root);body.appendChild(stack);stage(bar,body);
   if(window.IntersectionObserver){
     observer=new IntersectionObserver(items=>{
       for(const item of items)if(item.isIntersecting)
         enqueue(Number(item.target.dataset.page)-1);
     },{root:body,rootMargin:'30% 0px'});
     cells.forEach(c=>observer.observe(c));
   }
   let raf=0;
   body.addEventListener('scroll',()=>{
     if(raf)return;
     raf=requestAnimationFrame(()=>{
       raf=0;trim();
       const center=body.getBoundingClientRect().top+body.clientHeight*.35;
       let best=0,minimum=Infinity;
       for(let i=0;i<cells.length;i++){
         const rect=cells[i].getBoundingClientRect();
         const distance=center<rect.top?rect.top-center:center>rect.bottom?
           center-rect.bottom:0;
         if(distance<minimum){minimum=distance;best=i;if(!distance)break;}
       }
       position.textContent=(best+1)+' / '+entries.length;
       if(!observer){
         const top=body.getBoundingClientRect().top;
         cells.forEach((c,i)=>{
           const rect=c.getBoundingClientRect();
           if(rect.bottom>=top-body.clientHeight&&rect.top<=top+2*body.clientHeight)enqueue(i);
         });
       }
     });
   },{passive:true});
   enqueue(0);if(entries.length>1)enqueue(1);
   activeReaderCleanup=()=>{
     disposed=true;observer?.disconnect();queue.clear();
     if(raf)cancelAnimationFrame(raf);
     for(const cell of loaded.values()){
       cell.rounderRelease?.();
       cell.querySelectorAll('img').forEach(img=>img.removeAttribute('src'));
     }
     loaded.clear();
   };
 }else{
   const list=E('div','fg-archive-list');
   entries.forEach((entry,i)=>{
     const row=E('details','fg-archive-entry');
     const summary=E('summary','fg-archive-summary',
       (entry.name||'Entry '+(i+1))+
       (entry.size>=0?' · '+(Math.round(entry.size/1024))+' KiB':''));
     const dest=E('div','fg-archive-preview');
     row.append(summary,dest);
     row.addEventListener('toggle',()=>{
       if(row.open)content(entry,dest);
       else {dest.querySelectorAll('img').forEach(im=>im.removeAttribute('src'));dest.replaceChildren();}
     });
     list.appendChild(row);
   });
   body.appendChild(list);stage(bar,body);
 }
}
/* Multi-gigabyte plain text is streamed in small forward windows. The UI
   keeps only a bounded number of text nodes to avoid memory exhaustion. */
function streamText(){
 const [bar,tools]=toolbar('Continuous text');
 const body=E('div','fg-reader-scroll fg-text-scroll');
 const sheet=paper('fg-document-sheet fg-continuous-text');
 const spacer=E('div','fg-streamed-spacer');
 const stream=E('div','fg-streamed-content');
 sheet.append(spacer,stream);body.appendChild(sheet);
 const status=E('span','fg-reader-counter','Reading');
 tools.append(status);
 let done=false,pending=false,removedHeight=0,chunks=0;
 function append(){
   if(done||pending)return;
   pending=true;
   try {
     const response=JSON.parse(bridge()?.nextTextChunk?.(65536)||'{}');
     if(response.text){
       const item=E('pre','fg-document-code fg-raw-text',response.text);
       item.style.whiteSpace='pre-wrap';item.style.wordBreak='break-word';
       stream.appendChild(item);chunks++;
     }
     if(response.end||!response.text)done=true;
     if(chunks>100){
       const old=Array.from(stream.children).slice(0,25);
       removedHeight+=old.reduce((n,node)=>n+node.offsetHeight,0);
       old.forEach(n=>n.remove());
       chunks-=old.length;
       spacer.style.height=removedHeight+'px';
     }
     if(done)status.textContent='End';
   }catch(error){done=true;status.textContent='Read error';}
   finally{pending=false;}
 }
 function fill(){
   if(done)return;
   for(let i=0;i<3;i++)append();
   if(body.scrollHeight<=body.clientHeight+500&&!done)
     requestAnimationFrame(fill);
 }
 stage(bar,body);
 body.addEventListener('scroll',()=>{
   if(!done&&body.scrollTop+body.clientHeight>body.scrollHeight-1000)
     requestAnimationFrame(fill);
 },{passive:true});
 requestAnimationFrame(fill);
}
function binary(){
 const [bar]=toolbar('Unknown or legacy binary document · inspection only');
 const body=E('div','fg-reader-scroll'),p=paper('fg-document-sheet');
 p.appendChild(E('h2','fg-document-h2','A dedicated renderer is required'));
 p.appendChild(E('p','fg-document-p','The original bytes are untouched. This is not a faithful document preview. Legacy DOC, XLS and PPT need specific decoders.'));
 try{
  const size=Math.min(1024,Number(bridge()?.getRawDocumentSize?.()||0)),data=decode(bridge()?.getRawDocumentChunk?.(0,size)||''),rows=[];
  for(let i=0;i<data.length;i+=16){
   const a=data.slice(i,i+16);
   rows.push(i.toString(16).padStart(6,'0')+'  '+[...a].map(v=>v.toString(16).padStart(2,'0')).join(' ').padEnd(47,' ')+'  '+[...a].map(v=>v>=32&&v<127?String.fromCharCode(v):'.').join(''));
  }
  p.appendChild(E('pre','fg-document-code',rows.join('\n')));
 }catch(e){p.appendChild(E('p','fg-reader-empty',String(e)));}
 body.appendChild(p);stage(bar,body);
}
function backButton(){
 let b=$('fgBackToReader');if(!b){b=button('Read',()=>{editing=false;page=0;docx();b.classList.add('hidden');});b.id='fgBackToReader';b.classList.add('hidden');document.querySelector('.actions')?.prepend(b);}
 return b;
}
window.loadDocument=function(d){
 if(assetUrl){URL.revokeObjectURL(assetUrl);assetUrl=null;}
 if(activeReaderCleanup){activeReaderCleanup();activeReaderCleanup=null;}
 document.body.classList.remove('fg-pdf-reading');
 doc=d;page=0;zoom=1;archiveIndex=0;editing=false;
 $('editor')?.classList.remove('fg-reader-host');backButton().classList.add('hidden');
 original(d);
 if(d.type==='pdf')pdf();
 else if(d.type==='image')imageView();
 else if(d.type==='reader')textView();
 else if(d.type==='streamText')streamText();
 else if(d.type==='archive')archive();
 else if(d.type==='binary')binary();
 else if(d.type==='docx')docx();
 if(ro(d)){$('saveBtn').disabled=true;$('copyBtn').disabled=true;}
};
})();
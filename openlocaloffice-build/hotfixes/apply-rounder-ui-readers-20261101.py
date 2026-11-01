#!/usr/bin/env python3
"""Asterion Rounder v0.15.11: concise file grid, correct reading modes, compact archives."""
from pathlib import Path
import re
root=Path("app/src/main")
assets=root/"assets"
def patch(file,fn):
    p=assets/file; a=p.read_text(encoding="utf-8");b=fn(a)
    if a==b:raise RuntimeError("No change "+file)
    p.write_text(b,encoding="utf-8")
    print("PATCHED",file)
def one(text,before,after,label):
    n=text.count(before)
    if n!=1:raise RuntimeError(label+" expected one found "+str(n))
    return text.replace(before,after,1)
def library(s):
    s=one(s,"search.placeholder='Search your books';","search.placeholder='Search files';","search term")
    s=one(s,"body.append(welcome,dashboard,toolbar,filters,loading,deck,empty,footer);",
      "body.append(toolbar,filters,loading,deck,empty,footer);\nwelcome.hidden=true;dashboard.hidden=true;","home removal")
    s=one(s,"function drawDashboard(){\n if(stack.length||currentFolder){dashboard.hidden=true;return;}",
      "function drawDashboard(){\n dashboard.hidden=true;return;\n if(stack.length||currentFolder){dashboard.hidden=true;return;}","dashboard disable")
    s=one(s," tile.setAttribute('role','button');tile.setAttribute('tabindex','0');",
      " tile.setAttribute('role','button');tile.setAttribute('tabindex','0');\n tile.setAttribute('aria-label',item.name+'. Hold to open file actions');","file longpress label")
    s=one(s," tile.addEventListener('click',e=>{",
      " tile.addEventListener('contextmenu',e=>{e.preventDefault();showFileActions(item);});\n tile.addEventListener('click',e=>{","context action")
    s=one(s," const visiblePage=shown.slice(pageStart,pageStart+PAGE);",
      """ // Document-heavy directories get readable, compact rows; previews are
 // preserved for image/video/archive collections instead of giant placeholders.
 const visualCount=shown.filter(x=>['image','video','comic','book','pdf'].includes(classify(x))).length;
 deck.classList.toggle('fg-lib-compact-files',
   !list&&shown.length>0&&visualCount<shown.length*.45);
 const visiblePage=shown.slice(pageStart,pageStart+PAGE);""","compact adaptive file collection")
    return s
patch("premium-library.js",library)
def nav(s):
    # The image-folder and document readers previously used unrelated modes.
    s=one(s,"const modeButton=btn('Horizontal','Switch image reading layout',()=>switchMode());",
      "const modeButton=btn('Pages','Cycle Pages, V-scroll and H-scroll',()=>switchMode());","image mode name")
    old="""   imageMode=imageMode==='pages'?'horizontal':imageMode==='horizontal'?'scroll':'pages';"""
    s=one(s,old,"   imageMode=imageMode==='pages'?'scroll':imageMode==='scroll'?'horizontal':'pages';","image cycle")
    s=one(s,"modeButton.textContent=imageMode==='pages'?'Horizontal':imageMode==='horizontal'?'Scroll':'Pages';",
      "modeButton.textContent=imageMode==='pages'?'Pages':imageMode==='horizontal'?'H-scroll':'V-scroll';","mode labels")
    s=one(s,"modeButton.title='Switch to '+(imageMode==='pages'?'horizontal swipe scrolling':imageMode==='horizontal'?'vertical continuous scrolling':'discrete pages');",
      "modeButton.title='Current mode: '+modeButton.textContent+'. Tap to change';","active mode title")
    # Archive, PDF and EPUB use one shared navigation that currently calls vertical
    # scroller.scrollTo even in Pages mode. Replace with actual page index navigation.
    old="""function move(delta){
 if(!scroller)return;
 const limit=Math.max(0,scroller.scrollHeight-scroller.clientHeight);"""
    new="""let readerPage=0;
const pageNodes=()=>scroller?[...scroller.querySelectorAll('.fg-comic-section,.fg-progressive-page,.fg-pdf-section,.fg-book-chapter')]:[];
function setReaderPage(i){
 const pages=pageNodes();if(!pages.length)return;
 readerPage=Math.max(0,Math.min(pages.length-1,i));
 if(mode==='pages'){
  pages.forEach((node,j)=>node.classList.toggle('fg-current-reader-page',j===readerPage));
  scroller.scrollTo({top:0,left:0,behavior:'instant'});
 }else if(mode==='hscroll'){
  scroller.scrollTo({left:pages[readerPage].offsetLeft,top:0,behavior:'auto'});
 }else{
  scroller.scrollTo({top:pages[readerPage].offsetTop,behavior:'auto'});
 }
 schedule();
}
function move(delta){
 if(!scroller)return;
 if(mode==='pages'||mode==='hscroll'){
  const pages=pageNodes();
  if(pages.length){
   const target=readerPage+delta;
   if(target>=0&&target<pages.length)setReaderPage(target);
   else window.FileGestionerLibrary?.openSibling?.(delta);
   return;
  }
 }
 const limit=Math.max(0,scroller.scrollHeight-scroller.clientHeight);"""
    s=one(s,old,new,"discrete page navigation")
    s=one(s,"function progress(){return !scroller?0:Math.min(1,Math.max(0,scroller.scrollTop/Math.max(1,scroller.scrollHeight-scroller.clientHeight)));}",
      """function progress(){if(!scroller)return 0;
 if(mode==='pages'){const nodes=pageNodes();return nodes.length>1?readerPage/(nodes.length-1):0;}
 const axis=mode==='hscroll';
 return Math.min(1,Math.max(0,axis?scroller.scrollLeft/Math.max(1,scroller.scrollWidth-scroller.clientWidth):
   scroller.scrollTop/Math.max(1,scroller.scrollHeight-scroller.clientHeight)));}""","mode-aware progress")
    s=one(s," const p=progress(),bar=controls.querySelector('.fg-control-progress'),label=controls.querySelector('.fg-control-position');",
      """ const p=progress(),bar=controls.querySelector('.fg-control-progress'),label=controls.querySelector('.fg-control-position');
 if(mode==='pages'){
   const nodes=pageNodes();label.textContent=nodes.length?(readerPage+1)+' / '+nodes.length:'0%';return;
 }
 if(mode==='hscroll'){
   const nodes=pageNodes();
   if(nodes.length)readerPage=Math.max(0,Math.min(nodes.length-1,
     Math.round(scroller.scrollLeft/Math.max(1,scroller.clientWidth))));
 }""","mode-aware label")
    old="""function pageMode(next){
 mode=next;const type=by('.fg-book-scroll')?'epub':by('.fg-pdf-scroll')?'pdf':by('.fg-archive-scroll')||by('.fg-progressive-scroll')?'comic':'text';
 save('mode:'+type,mode);
 scroller?.classList.toggle('fg-control-pages',mode==='pages');
 const toggle=controls?.querySelector('.fg-control-mode');
 if(toggle)toggle.textContent=mode==='pages'?'Pages':'Scroll';
}"""
    new="""function pageMode(next){
 const currentNodes=pageNodes();
 if(mode!=='pages' && currentNodes.length){
  const fromHorizontal=mode==='hscroll';
  const focus=(fromHorizontal?scroller.scrollLeft:scroller.scrollTop)+
    (fromHorizontal?scroller.clientWidth:scroller.clientHeight)*.4;
  let closest=0,distance=Infinity;
  currentNodes.forEach((node,i)=>{
    const start=fromHorizontal?node.offsetLeft:node.offsetTop;
    const n=Math.abs(start-focus);if(n<distance){distance=n;closest=i;}
  });
  readerPage=closest;
 }
 mode=next;
 const type=by('.fg-book-scroll')?'epub':by('.fg-pdf-scroll')?'pdf':
   by('.fg-archive-scroll')||by('.fg-progressive-scroll')?'comic':'text';
 save('mode:'+type,mode);
 scroller?.classList.toggle('fg-control-pages',mode==='pages');
 scroller?.classList.toggle('fg-control-horizontal',mode==='hscroll');
 const toggle=controls?.querySelector('.fg-control-mode');
 if(toggle){toggle.textContent=mode==='pages'?'Pages':mode==='hscroll'?'H-scroll':'V-scroll';
   toggle.title='Current mode '+toggle.textContent+'; tap to change';}
 if(currentNodes.length)setReaderPage(readerPage);
 schedule();
}"""
    s=one(s,old,new,"three-mode document navigation")
    s=one(s,"   const toggle=btn('Scroll','Switch scrolling/page mode',\n     ()=>pageMode(mode==='pages'?'scroll':'pages'));",
      """   const toggle=btn('V-scroll','Cycle Pages, V-scroll, H-scroll',
     ()=>pageMode(mode==='pages'?'scroll':mode==='scroll'?'hscroll':'pages'));""","mode cycle button")
    s=one(s,"  scroller.scrollTo({top:limit*Number(slider.value)/1000,behavior:'auto'});update();};",
      """  if(mode==='pages'){
    const nodes=pageNodes();
    if(nodes.length)setReaderPage(Math.round((nodes.length-1)*Number(slider.value)/1000));
  }else if(mode==='hscroll'){
    const end=Math.max(0,scroller.scrollWidth-scroller.clientWidth);
    scroller.scrollTo({left:end*Number(slider.value)/1000,behavior:'auto'});
  }else scroller.scrollTo({top:limit*Number(slider.value)/1000,behavior:'auto'});
  update();};""","slider modes")
    s=one(s," pageMode(saved('mode:'+(book?'epub':pdf?'pdf':comic?'comic':'text'),'scroll'));useStyle();update();",
      """ const stored=saved('mode:'+(book?'epub':pdf?'pdf':comic?'comic':'text'),'scroll');
 pageMode(['pages','scroll','hscroll'].includes(stored)?stored:'scroll');
 useStyle();update();""","saved mode consistency")
    s=one(s,"if(mode!=='pages'||e.target?.closest?.('button,input,a,textarea,[contenteditable]'))return;",
      "if(mode!=='pages'||e.target?.closest?.('button,input,a,textarea,[contenteditable]'))return;","tap unchanged") if False else s
    # A page mode also handles deliberate horizontal swipe on archives.
    s=one(s," scroller.addEventListener('click',e=>{",
      """ let pageTouch=null;
 scroller.addEventListener('touchstart',e=>{
   if(mode==='pages'&&e.touches.length===1)
     pageTouch={x:e.touches[0].clientX,y:e.touches[0].clientY};
 },{passive:true});
 scroller.addEventListener('touchend',e=>{
   if(mode!=='pages'||!pageTouch||e.changedTouches.length!==1)return;
   const dx=e.changedTouches[0].clientX-pageTouch.x;
   const dy=e.changedTouches[0].clientY-pageTouch.y;
   pageTouch=null;
   if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.3){
     move(dx<0?1:-1);
   }
 },{passive:true});
 scroller.addEventListener('click',e=>{""","archive swipe navigation")
    return s
patch("reader-controls.js",nav)
def archive(s):
    # An archive contains files, not 192 full-height disclosure cards.
    begin=s.index(" }else{\n   const list=E('div','fg-archive-list');\n   entries.forEach((entry,i)=>{")
    end=s.index("\n }\n}\n/* Multi-gigabyte plain text",begin)
    replacement=""" }else{
   const list=E('div','fg-archive-list fg-archive-compact');
   const readable=name=>{
     try{return decodeURIComponent(name);}catch(_){return name.replace(/%20/ig,' ');}
   };
   entries.forEach((entry,i)=>{
     const supported=entry.preview===true;
     const row=E(supported?'details':'div','fg-archive-entry'+
       (supported?' fg-archive-expandable':' fg-archive-static'));
     const clean=readable(entry.name||'Entry '+(i+1));
     const size=entry.size>=0?Math.max(0,Math.round(entry.size/1024))+' KiB':'';
     const summary=E(supported?'summary':'div','fg-archive-summary');
     const name=E('span','fg-archive-filename',clean);
     const detail=E('span','fg-archive-filesize',size);
     summary.append(name,detail);row.append(summary);
     if(supported){
       const dest=E('div','fg-archive-preview');
       row.append(dest);
       row.addEventListener('toggle',()=>{
         if(row.open)content(entry,dest);
         else{dest.querySelectorAll('img').forEach(im=>im.removeAttribute('src'));
           dest.replaceChildren();}
       });
     }
     list.appendChild(row);
   });
   body.appendChild(list);stage(bar,body);
 }"""
    s=s[:begin]+replacement+s[end+3:]
    s=one(s,"   function trim(){\n     const view=body.getBoundingClientRect();",
      """   function trim(){
     // Preserve already decoded pages and their DOM image sources. Recreating
     // them on reverse scrolling caused flashing and repeat cloud downloads.
     return;
     const view=body.getBoundingClientRect();""","image page persistence")
    return s
patch("universal-reader.js",archive)
def epub(s):
    s=one(s,"if(disposed||!queue.size||requested.size>=2)return;",
        "if(disposed||!queue.size||requested.size>=4)return;","EPUB four chapter requests")
    s=one(s,"function trim(){\n    const view=scroll.getBoundingClientRect();",
        """function trim(){
    // Never erase previously rendered illustrations just because a chapter
    // left the viewport; scrolling backwards must not re-fetch cloud images.
    return;
    const view=scroll.getBoundingClientRect();""","EPUB persistent images")
    return s
patch("epub-reader.js",epub)
css=r'''
/* v0.15.11: clean collection; videos always two across on phones. */
.fg-library-root .fg-lib-welcome,.fg-library-root .fg-lib-dashboard{display:none!important}
.fg-library-root .fg-lib-more,.fg-library-root .fg-lib-type{display:none!important}
.fg-library-root .fg-lib-cover-loading{font-size:10px!important}
.fg-library-root .fg-lib-item-title{font-size:14px!important;line-height:1.3!important}
.fg-library-root .fg-lib-item-detail{font-size:12px!important}
@media (max-width:699px){
 .fg-library-root .fg-lib-grid:not(.fg-lib-list):not(.fg-lib-compact-files){
   grid-template-columns:repeat(2,minmax(0,1fr))!important;
   gap:18px 12px!important;
 }
 .fg-library-root .fg-lib-grid:not(.fg-lib-list) .fg-lib-video .fg-lib-cover{
   aspect-ratio:16/9!important;min-height:100px!important;
 }
 .fg-library-root .fg-lib-body{padding-left:12px!important;padding-right:12px!important}
}
.fg-library-root .fg-lib-compact-files:not(.fg-lib-list){
 display:flex!important;flex-direction:column!important;gap:7px!important
}
.fg-library-root .fg-lib-compact-files .fg-lib-tile{
 display:flex!important;align-items:center!important;gap:11px!important;
 padding:9px!important;border-radius:12px!important;
 border:1px solid #2d3a50!important;min-height:62px!important;
 background:#151e2d!important
}
.fg-library-root .fg-lib-compact-files .fg-lib-cover{
 width:46px!important;height:46px!important;flex:0 0 46px!important;
 min-height:0!important;aspect-ratio:1!important;border-radius:9px!important
}
.fg-library-root .fg-lib-compact-files .fg-lib-item-title{font-size:14px!important}
.fg-library-root .fg-lib-compact-files .fg-lib-tile-meta{min-width:0!important;flex:1!important}
.fg-archive-compact{display:flex!important;flex-direction:column!important;
 gap:1px!important;padding:8px 10px!important;max-width:100%!important}
.fg-archive-compact .fg-archive-entry{
 min-height:44px!important;padding:0!important;margin:0!important;
 border-radius:0!important;border:0!important;border-bottom:1px solid #293447!important;
 background:transparent!important;
}
.fg-archive-compact .fg-archive-summary{display:flex!important;align-items:center!important;
 justify-content:space-between!important;gap:14px!important;padding:10px!important;
 min-height:44px!important;font-size:13px!important;line-height:1.35!important;
 overflow-wrap:anywhere!important
}
.fg-archive-compact .fg-archive-summary::marker{font-size:10px!important}
.fg-archive-compact .fg-archive-filename{flex:1!important;min-width:0!important;
 color:#e8edf6!important;font-size:13px!important}
.fg-archive-compact .fg-archive-filesize{flex:0 0 auto!important;
 color:#9babc6!important;font-size:12px!important}
.fg-archive-compact .fg-archive-preview{padding:4px 10px 12px!important;min-height:0!important}
.fg-archive-compact .fg-archive-static .fg-archive-summary{cursor:default!important}
/* Page: one at a time. V-scroll: normal. H-scroll: continuous, never snapping. */
.fg-reader-scroll.fg-control-pages{
 overflow-x:hidden!important;overflow-y:hidden!important;scroll-snap-type:none!important;
}
.fg-reader-scroll.fg-control-pages .fg-comic-section,
.fg-reader-scroll.fg-control-pages .fg-progressive-page,
.fg-reader-scroll.fg-control-pages .fg-pdf-section,
.fg-reader-scroll.fg-control-pages .fg-book-chapter{
 display:none!important
}
.fg-reader-scroll.fg-control-pages .fg-current-reader-page{
 display:flex!important;flex-direction:column!important;justify-content:center!important;
 align-items:center!important;max-height:100%!important;min-height:0!important;
 height:100%!important;overflow:auto!important;width:100%!important
}
.fg-reader-scroll.fg-control-pages .fg-comic-stack,
.fg-reader-scroll.fg-control-pages .fg-pdf-stack,
.fg-reader-scroll.fg-control-pages .fg-pdf-container{
 height:100%!important;min-height:0!important
}
.fg-reader-scroll.fg-control-pages .fg-comic-section img,
.fg-reader-scroll.fg-control-pages .fg-pdf-section img{
 width:auto!important;max-width:100%!important;max-height:100%!important;object-fit:contain!important;
}
.fg-reader-scroll.fg-control-horizontal{
 overflow-x:auto!important;overflow-y:hidden!important;scroll-snap-type:none!important;
 overscroll-behavior-x:contain!important;touch-action:pan-x!important
}
.fg-reader-scroll.fg-control-horizontal .fg-pdf-container,
.fg-reader-scroll.fg-control-horizontal .fg-book-stack,
.fg-reader-scroll.fg-control-horizontal .fg-progressive-stack{
 display:flex!important;flex-direction:row!important;width:max-content!important;
 max-width:none!important;height:100%!important;align-items:stretch!important
}
.fg-reader-scroll.fg-control-horizontal .fg-comic-section,
.fg-reader-scroll.fg-control-horizontal .fg-pdf-section,
.fg-reader-scroll.fg-control-horizontal .fg-book-chapter,
.fg-reader-scroll.fg-control-horizontal .fg-progressive-page{
 display:flex!important;flex:0 0 100vw!important;width:100vw!important;
 height:100%!important;min-height:0!important;overflow:hidden!important;
 align-items:center!important;justify-content:center!important;
 scroll-snap-align:none!important
}
.fg-reader-scroll.fg-control-horizontal img{
 object-fit:contain!important;max-width:100%!important;max-height:100%!important
}
.fg-image-reader .fg-folder-scroll.fg-image-horizontal{scroll-snap-type:none!important}
.fg-image-reader .fg-image-horizontal .fg-folder-page{
 scroll-snap-align:none!important;scroll-snap-stop:normal!important
}
.fg-image-reader .fg-image-paged .fg-folder-page:not(.fg-image-current){display:none!important}
'''
p=assets/"style.css"
p.write_text(p.read_text(encoding="utf-8")+"\n"+css,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)32\b',r'\g<1>33',g,count=1)
if n!=1:raise RuntimeError("version code expected 32")
g,n=re.subn(r'(\bversionName\s*(?:=\s*)?)"0\.15\.10"',r'\g<1>"0.15.11"',g,count=1)
if n!=1:raise RuntimeError("version name expected 0.15.10")
gradle.write_text(g,encoding="utf-8")
print("ROUNDERVER_0.15.11_UI_READERS_ARCHIVE_READY")

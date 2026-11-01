#!/usr/bin/env python3
"""Asterion Rounder 0.15.9: screenshot-driven video controls, discrete image pages, sort consistency."""
from pathlib import Path
import re
root=Path("app/src/main")
assets=root/"assets"
def patch(name,fn):
    path=assets/name
    source=path.read_text(encoding="utf-8")
    result=fn(source)
    if result==source:raise RuntimeError("No modifications to "+name)
    path.write_text(result,encoding="utf-8")
    print("PATCHED",name)
def replace(s,old,new,label):
    count=s.count(old)
    if count!=1:raise RuntimeError(label+" expected once, got "+str(count))
    return s.replace(old,new,1)
def library(s):
    insertion="""function sortReadingSequence(items){
 return items.sort((a,b)=>{
   let difference=sortBy==='size'?(Number(a.size)||0)-(Number(b.size)||0):
     sortBy==='modified'?(Number(a.modified)||0)-(Number(b.modified)||0):
     sortBy==='type'?classify(a).localeCompare(classify(b)):
     naturalCollator.compare(a.name,b.name);
   return (sortDescending?-1:1)*(difference||naturalCollator.compare(a.name,b.name));
 });
}
"""
    s=replace(s,"function openBook(item){",insertion+"function openBook(item){","library comparator")
    # The reader's siblings, videos and previous/next must follow the same order
    # selected on the library toolbar, not the hard-coded default name order.
    s=replace(s,"const candidates=entries.filter(x=>!x.folder&&classify(x)==='video')\n     .sort((a,b)=>naturalCollator.compare(a.name,b.name))",
        "const candidates=sortReadingSequence(entries.filter(x=>!x.folder&&classify(x)==='video'))","video queue sort")
    s=s.replace(".sort((a,b)=>naturalCollator.compare(a.name,b.name));\n     state.known=",";\n     state.known=") if False else s
    s=replace(s,"state.siblings=entries.filter(x=>!x.folder&&x.terabox&&classify(x)==='image')\n       .sort((a,b)=>naturalCollator.compare(a.name,b.name));",
        "state.siblings=sortReadingSequence(entries.filter(x=>!x.folder&&x.terabox&&classify(x)==='image'));","cloud image sort")
    s=replace(s,"state.siblings=entries.filter(x=>!x.folder&&classify(x)==='image')\n       .sort((a,b)=>naturalCollator.compare(a.name,b.name));",
        "state.siblings=sortReadingSequence(entries.filter(x=>!x.folder&&classify(x)==='image'));","local image sort")
    s=replace(s,"const sorted=entries.filter(e=>!e.folder&&\n   /\\.(epub|pdf|zip|cbz|cbr|jpe?g|png|webp|gif|avif)$/i.test(e.name||''))\n   .sort((a,b)=>naturalCollator.compare(a.name,b.name));",
        "const sorted=sortReadingSequence(entries.filter(e=>!e.folder&&\n   /\\.(epub|pdf|zip|cbz|cbr|jpe?g|png|webp|gif|avif)$/i.test(e.name||'')));","file sibling sort")
    s=replace(s,"const MAX_CLOUD_COVERS=8;","const MAX_CLOUD_COVERS=12;","bounded cover parallelism")
    s=replace(s,"{root:body,rootMargin:'320px 0px'}","{root:body,rootMargin:'640px 0px'}","cover prefetch")
    return s
patch("premium-library.js",library)
def reader(s):
    s=replace(s,"let imageMode='pages'; // Horizontal page navigation; scroll mode remains available.",
      "let imageMode='pages'; // A page replaces the previous page; horizontal/vertical scroll are alternatives.","image page initial")
    s=replace(s,"const modeButton=btn('Pages','Switch to page-by-page images',()=>switchMode());",
      "const modeButton=btn('Horizontal','Switch image reading layout',()=>switchMode());","mode label")
    s=replace(s,"function setPosition(i){\n   const prior=current;\n   current=Math.max(0,Math.min(Math.max(0,pages.length-1),i));",
      """function setPosition(i){
   const prior=current;
   current=Math.max(0,Math.min(Math.max(0,pages.length-1),i));
   if(imageMode==='pages'){
     const all=pageSections();
     if(all[prior]&&prior!==current)all[prior].classList.remove('fg-image-current');
     const visible=all[current];
     if(visible){
       visible.classList.add('fg-image-current');
       const img=visible.querySelector('img[data-src]');
       if(img&&!img.getAttribute('src'))img.src=img.dataset.src;
     }
   }""","visible page selection")
    s=replace(s,"if(imageMode==='pages')view.scrollTo({left:section.offsetLeft,top:0,behavior:'auto'});\n   else view.scrollTo({top:section.offsetTop-stack.offsetTop,left:0,behavior:'auto'});",
      """if(imageMode==='pages')view.scrollTo({left:0,top:0,behavior:'auto'});
   else if(imageMode==='horizontal')view.scrollTo({left:section.offsetLeft,top:0,behavior:'auto'});
   else view.scrollTo({top:section.offsetTop-stack.offsetTop,left:0,behavior:'auto'});""","jump page")
    s=replace(s,"imageMode=imageMode==='pages'?'scroll':'pages';\n   view.classList.toggle('fg-image-paged',imageMode==='pages');\n   modeButton.textContent=imageMode==='pages'?'Scroll':'Pages';\n   modeButton.title=imageMode==='pages'?'Switch to continuous images':'Switch to page-by-page images';",
      """const previousMode=imageMode;
   imageMode=imageMode==='pages'?'horizontal':imageMode==='horizontal'?'scroll':'pages';
   view.classList.toggle('fg-image-paged',imageMode==='pages');
   view.classList.toggle('fg-image-horizontal',imageMode==='horizontal');
   if(previousMode==='pages'){
     pageSections().forEach(node=>node.classList.remove('fg-image-current'));
   }
   modeButton.textContent=imageMode==='pages'?'Horizontal':imageMode==='horizontal'?'Scroll':'Pages';
   modeButton.title='Switch to '+(imageMode==='pages'?'horizontal swipe scrolling':imageMode==='horizontal'?'vertical continuous scrolling':'discrete pages');""","mode cycle")
    s=replace(s,"if(imageMode==='pages'){\n     setPosition(Math.round(view.scrollLeft/Math.max(1,view.clientWidth)));return;\n   }",
      """if(imageMode==='pages')return;
   if(imageMode==='horizontal'){
     setPosition(Math.round(view.scrollLeft/Math.max(1,view.clientWidth)));return;
   }""","current position")
    # Initial page must be active before it is decoded, even with lazy observer.
    s=replace(s,"view.classList.toggle('fg-image-paged',imageMode==='pages');\n setPosition(0);appendBatch();",
      "view.classList.toggle('fg-image-paged',imageMode==='pages');\n setPosition(0);appendBatch();setPosition(0);","first page")
    return s
patch("reader-controls.js",reader)
css=assets/"style.css"
css.write_text(css.read_text(encoding="utf-8")+"""
/* 2026-11-01: Pages means ONE image, not snap-scrolling past images.
   Horizontal and continuous vertical reading remain explicit alternatives. */
.fg-image-reader .fg-folder-scroll.fg-image-paged{
 overflow:hidden!important;scroll-snap-type:none!important;touch-action:pan-y!important;
}
.fg-image-reader .fg-image-paged .fg-folder-stack{
 display:block!important;width:100%!important;height:100%!important;min-width:0!important;
}
.fg-image-reader .fg-image-paged .fg-folder-page{
 display:none!important;width:100%!important;height:100%!important;min-width:0!important;
 min-height:0!important;position:relative!important;overflow:hidden!important;
}
.fg-image-reader .fg-image-paged .fg-folder-page.fg-image-current{
 display:flex!important;align-items:center!important;justify-content:center!important;
}
.fg-image-reader .fg-image-paged .fg-folder-image{
 width:auto!important;max-width:100%!important;height:auto!important;
 max-height:100%!important;object-fit:contain!important;
}
.fg-image-reader .fg-folder-scroll.fg-image-horizontal{
 overflow-x:auto!important;overflow-y:hidden!important;scroll-snap-type:x mandatory!important;
 touch-action:pan-x!important;
}
.fg-image-reader .fg-image-horizontal .fg-folder-stack{
 display:flex!important;flex-direction:row!important;width:max-content!important;
 height:100%!important;padding:0!important;
}
.fg-image-reader .fg-image-horizontal .fg-folder-page{
 display:flex!important;flex:0 0 100vw!important;width:100vw!important;
 min-width:100vw!important;height:100%!important;align-items:center;justify-content:center;
 scroll-snap-align:start;scroll-snap-stop:always;overflow:hidden!important;
}
.fg-image-reader .fg-image-horizontal .fg-folder-image{
 width:auto!important;max-width:100%!important;max-height:100%!important;
 height:auto!important;object-fit:contain!important;
}
""",encoding="utf-8")
gradle=Path("app/build.gradle.kts")
if not gradle.exists():gradle=Path("app/build.gradle")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)30\b',r'\g<1>31',g,count=1)
if n!=1:raise RuntimeError("Expected versionCode 30")
g,n=re.subn(r'(\bversionName\s*(?:=\s*)?)"0\.15\.8"',r'\g<1>"0.15.9"',g,count=1)
if n!=1:raise RuntimeError("Expected v0.15.8")
gradle.write_text(g,encoding="utf-8")
print("0.15.9 sorting and true paging patch complete")

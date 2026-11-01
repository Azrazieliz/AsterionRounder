#!/usr/bin/env python3
"""Rounder v0.15.14: native video FIT; two wide videos; reliable ZIP/EPUB image paths."""
from pathlib import Path
import re
root=Path("app")
src=root/"src/main"
def change(file,old,new,label):
 p=src/file
 s=p.read_text(encoding="utf-8")
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{label}: expected 1 occurrence, got {n}")
 p.write_text(s.replace(old,new,1),encoding="utf-8")
 print("PATCHED",label)
change("java/com/openlocal/office/core/FgMediaPlayer.java",
    "display.setResizeMode(androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM);",
    "display.setResizeMode(androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_FIT);",
    "Native aspect-ratio FIT default")
change("assets/premium-library.js",
    " const visiblePage=shown.slice(pageStart,pageStart+PAGE);",
    """ const visiblePage=shown.slice(pageStart,pageStart+PAGE);
 // A mixed folder with videos gets the same two-wide large thumbnails
 // as the dedicated Video filter. Other collections retain their layout.
 deck.classList.toggle('fg-lib-video-grid',
   !list&&visiblePage.some(item=>classify(item)==='video'));""",
    "mixed video folders two columns")
change("assets/premium-library.js",
    """ const more=b('⋮','fg-lib-more',e=>{e.stopPropagation();showFileActions(item);});
 more.title='File actions';more.setAttribute('aria-label','Actions for '+item.name);
 tile.append(more);""",
    """ // No three-dot overlays on the owner's thumbnails.
 // File actions remain available by long press and right-click.
 tile.addEventListener('contextmenu',event=>{
   event.preventDefault();showFileActions(item);
 });""",
    "remove redundant tile menus")
change("assets/premium-library.js",
    " const badge=E('span','fg-lib-type',label(item));\n cover.appendChild(badge);",
    " // Keep covers unobstructed by redundant VIDEO / EBOOK / ZIP badges.",
    "remove redundant badges")
style=src/"assets/style.css"
css=style.read_text(encoding="utf-8")
add=r"""
/* Asterion Rounder v0.15.14: large two-across video tiles, with no overlays. */
.fg-library-root .fg-lib-more,
.fg-library-root .fg-lib-type{display:none!important}
@media (min-width:345px) and (max-width:699px){
  .fg-library-root .fg-lib-grid.fg-lib-video-grid:not(.fg-lib-list){
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:17px 12px!important
  }
  .fg-library-root .fg-lib-video .fg-lib-cover{
    aspect-ratio:16/9!important;
    min-height:104px!important
  }
  .fg-library-root .fg-lib-video .fg-lib-item-title{
    font-size:13px!important;line-height:1.35!important
  }
}
"""
assert "Asterion Rounder v0.15.14:" not in css
style.write_text(css+"\n"+add,encoding="utf-8")
change("java/com/openlocal/office/MainActivity.java",
    "try{return active.responseSampled(assetPath);}",
    """try{return active.responseSampled(u.getEncodedPath());}""",
    "sampled EPUB/ZIP fallback uses encoded path")
change("assets/universal-reader.js",
    """       let watchdog=0;
       im.addEventListener('load',()=>{
         clearTimeout(watchdog);settle();
         if(isComic)bridge()?.readerDiagnostic?.('COMIC_IMAGE_LOADED');
       });
       im.addEventListener('error',()=>{
         clearTimeout(watchdog);
         if(entry.streamed&&!im.dataset.fgSampled){
           const regular=bridge()?.getArchiveImageUrl?.(entry.name)||'';
           if(regular.includes('/book/')){
             im.dataset.fgSampled='yes';
             im.src=regular.replace('/book/','/book-fallback/');
             return;
           }
         }
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
       },remoteArchive?30000:12000);""",
    """       // Do not forcibly abort an image merely because a cloud range
       // takes over 12 or 30 seconds. That self-generated error caused blank
       // pages while the original member was still downloading.
       const originalUrl=entry.streamed?
         (bridge()?.getArchiveImageUrl?.(entry.name)||''):
         'data:image/'+(ext==='jpg'?'jpeg':ext)+';base64,'+data;
       let retryTimer=0,progressTimer=0,attempt=0;
       const stopTimer=()=>{clearTimeout(retryTimer);clearTimeout(progressTimer);};
       im.addEventListener('load',()=>{
         stopTimer();settle();
         if(isComic)bridge()?.readerDiagnostic?.('COMIC_IMAGE_LOADED');
       });
       im.addEventListener('error',()=>{
         stopTimer();
         // Retry one transient provider interruption, then use a native
         // decoded JPEG for valid images unsupported by Chromium.
         if(entry.streamed&&attempt++===0){
           retryTimer=setTimeout(()=>{if(im.isConnected)im.src=originalUrl+'?fgRetry=1';},500);
           return;
         }
         if(entry.streamed&&!im.dataset.fgSampled&&originalUrl.includes('/book/')){
           im.dataset.fgSampled='yes';
           im.src=originalUrl.replace('/book/','/book-fallback/');
           return;
         }
         im.removeAttribute('src');
         im.remove();
         const failure=E('p','fg-reader-empty','Image failed to load: '+entry.name);
         const retry=button('Retry image',()=>{
           failure.remove();retry.remove();attempt=0;
           delete im.dataset.fgSampled;
           dest.appendChild(im);im.src=originalUrl;
         });
         retry.classList.add('fg-image-retry');
         dest.append(failure,retry);
         settle();
         bridge()?.readerDiagnostic?.('ARCHIVE_IMAGE_FAILED');
       });
       im.src=originalUrl;
       dest.appendChild(im);
       progressTimer=setTimeout(()=>{
         if(im.isConnected && !(im.complete&&im.naturalWidth>0)){
           // Diagnostic only. Never clear a valid in-flight response.
           bridge()?.readerDiagnostic?.('ARCHIVE_IMAGE_STILL_LOADING');
         }
       },remoteArchive?45000:25000);""",
    "never abort slow original ZIP images; bounded retry and sampled fallback")
gradle=root/"build.gradle.kts"
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)35\b',r'\g<1>36',g,count=1)
assert n==1
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.13"',r'\g<1>"0.15.14"',g,count=1)
assert n==1
gradle.write_text(g,encoding="utf-8")
print("ROUNDERVER_V0_15_14_REPAIR_COMPLETE")

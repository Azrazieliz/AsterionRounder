#!/usr/bin/env python3
"""Keep library outside Android edge-to-edge bars and make mobile bookshelf usable."""
from pathlib import Path
s=Path("app/src/main/assets/style.css")
css=s.read_text()
css+="""

/* Library must never render underneath Android clock, status or gesture bars. */
.fg-library-root{
  box-sizing:border-box!important;
  padding-top:max(27px, env(safe-area-inset-top, 0px))!important;
  padding-bottom:max(25px, env(safe-area-inset-bottom, 0px))!important;
}
.fg-library-root .fg-lib-header{
  box-sizing:border-box!important;
  padding:9px 12px!important;
  min-height:60px!important;
  column-gap:8px!important;
}
.fg-library-root .fg-lib-brand{flex:0 1 auto;min-width:0!important;}
.fg-library-root .fg-lib-brand-title{
  font-size:15px!important;white-space:nowrap!important;
  overflow:hidden!important;text-overflow:ellipsis!important;
}
.fg-library-root .fg-lib-brand-subtitle{
  font-size:8px!important;white-space:nowrap!important;
  overflow:hidden!important;
}
.fg-library-root .fg-lib-actions{flex:0 0 auto;gap:5px!important;}
.fg-library-root .fg-lib-actions button{
  font-size:11px!important;padding:7px 8px!important;
  min-height:36px!important;white-space:nowrap!important;
}
.fg-library-root .fg-lib-body{
  min-height:0!important;
  padding-bottom:max(72px, env(safe-area-inset-bottom, 0px))!important;
}
.fg-library-root .fg-lib-cover{
  contain:layout paint;transform:translateZ(0);
}
.fg-library-root .fg-lib-fallback-title{display:none!important}
.fg-library-root .fg-lib-fallback{justify-content:center!important;}
.fg-library-root .fg-lib-item-title{
  font-size:12px!important;min-height:0!important;
  display:-webkit-box;-webkit-line-clamp:2;
}
@media(max-width:399px){
 .fg-library-root .fg-lib-monogram{width:33px;height:33px;flex-basis:33px!important}
 .fg-library-root .fg-lib-brand{gap:6px!important}
 .fg-library-root .fg-lib-actions button{font-size:10px!important;padding:6px!important}
}
@media(min-width:345px) and (max-width:699px){
 .fg-library-root .fg-lib-grid:not(.fg-lib-list){
   grid-template-columns:repeat(3,minmax(0,1fr))!important;
   column-gap:10px!important;row-gap:19px!important;
 }
 .fg-library-root .fg-lib-body{padding-left:10px!important;padding-right:10px!important}
}
"""
css+="""
.fg-lib-cover-request{
 position:absolute;left:8px;right:8px;bottom:33px;z-index:2;
 padding:6px 4px;min-height:29px;border-radius:8px;
 background:#243451e8;color:#e8efff;border:1px solid #ffffff33;
 font:600 11px system-ui;cursor:pointer;touch-action:manipulation;
}
.fg-lib-cover-request:active{background:#394b73}
"""
css+="""
/* Landscape video previews, even inside a mixed file collection. */
.fg-library-root .fg-lib-video .fg-lib-cover{
 aspect-ratio:16/9!important;height:auto!important;min-height:0!important;
 overflow:hidden!important;position:relative
}
.fg-library-root .fg-lib-video .fg-lib-cover-image{
 width:100%!important;height:100%!important;object-fit:cover!important
}
.fg-library-root .fg-lib-grid.fg-lib-video-grid:not(.fg-lib-list){
 grid-template-columns:repeat(2,minmax(0,1fr))!important;
 gap:12px!important
}
.fg-library-root .fg-lib-grid:not(.fg-lib-list) .fg-lib-video{
 grid-column:span 1;min-width:0
}
.fg-library-root .fg-lib-video .fg-lib-type{font-size:10px}
.fg-lib-dashboard[hidden]{display:none!important}
.fg-lib-dashboard{display:flex;flex-direction:column;gap:13px;
 margin:4px 0 14px;padding:10px 12px 12px;border-radius:16px;
 background:linear-gradient(120deg,#1b2942,#121c30);
 border:1px solid #33465f}
.fg-home-heading{font:700 17px/1.3 system-ui;color:#f4f6ff}
.fg-home-quick{display:flex;gap:8px;flex-wrap:wrap}
.fg-home-action{border:1px solid #526888;border-radius:11px;
 background:#263a58;color:#f2f6ff;padding:9px 13px;font:600 12px system-ui}
.fg-home-section{display:flex;flex-direction:column;gap:7px;min-width:0}
.fg-home-label{font:650 12px system-ui;color:#bbc9e5}
.fg-home-strip{display:flex;gap:9px;overflow-x:auto;overscroll-behavior-x:contain;
 padding:3px 0 8px;scrollbar-width:thin}
.fg-home-recent{flex:0 0 148px;max-width:148px;min-height:56px;
 border-radius:12px;border:1px solid #425775;background:#202d46;
 color:#f4f5fa;font:500 12px/1.4 system-ui;text-align:left;
 padding:10px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;
 overflow-wrap:anywhere}
.fg-image-reader .fg-folder-scroll.fg-image-paged{
 overflow-x:auto!important;overflow-y:hidden!important;
 overscroll-behavior-x:contain;scroll-snap-type:x mandatory;
 touch-action:pan-x;scrollbar-width:none
}
.fg-image-reader .fg-image-paged .fg-folder-stack{
 display:flex!important;flex-direction:row!important;
 align-items:stretch!important;width:max-content;min-width:100%;height:100%;
 padding:0!important;margin:0!important
}
.fg-image-reader .fg-image-paged .fg-folder-page{
 box-sizing:border-box!important;flex:0 0 100vw!important;
 width:100vw!important;min-width:100vw!important;height:100%!important;
 min-height:0!important;max-height:100%!important;
 display:flex;align-items:center;justify-content:center;
 scroll-snap-align:start;scroll-snap-stop:always;
 padding:0!important;margin:0!important;overflow:hidden!important
}
.fg-image-reader .fg-image-paged .fg-folder-image{
 display:block;max-width:100%!important;max-height:100%!important;
 width:auto!important;height:auto!important;object-fit:contain!important
}
.fg-image-reader .fg-image-paged .fg-folder-sentinel{
 flex:0 0 40vw;min-height:0;display:flex;align-items:center;justify-content:center
}
"""
s.write_text(css)
print("Library uses safe system insets, compact uncluttered header and compact mobile covers")

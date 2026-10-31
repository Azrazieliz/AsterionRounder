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
s.write_text(css)
print("Library uses safe system insets, compact uncluttered header and compact mobile covers")

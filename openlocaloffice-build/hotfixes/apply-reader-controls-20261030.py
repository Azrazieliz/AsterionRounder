#!/usr/bin/env python3
"""Add shared reader controls without replacing PDF, EPUB or ZIP readers."""
from pathlib import Path
root=Path("app/src/main")
html=root/"assets/index.html"
s=html.read_text()
assert "</body>" in s and "reader-controls.js" not in s
s=s.replace("</body>",'<script src="reader-controls.js"></script>\n</body>')
html.write_text(s)
css=root/"assets/style.css"
style=css.read_text()
style+="""

/* One compact reader control dock; system bars remain immersive during reading. */
.fg-controls{position:fixed;bottom:max(3px,env(safe-area-inset-bottom,0px));
 left:50%;transform:translateX(-50%);width:min(calc(100% - 12px),700px);
 z-index:9950;background:#111a2be8;color:#e8eefd;border:1px solid #405376b0;
 border-radius:12px;box-shadow:0 4px 20px #0008;padding:4px;
 font:12px/1.25 system-ui;backdrop-filter:blur(12px);}
.fg-control-row{display:flex;gap:3px;align-items:center;justify-content:space-between;min-height:35px;}
.fg-control-row>.fg-control-button{flex:1 1 auto;min-width:0;}
.fg-control-button{border:0;background:#263753bf;color:#eef3ff;border-radius:8px;
 font:600 12px/1.2 system-ui;min-height:34px;padding:7px 4px;touch-action:manipulation;}
.fg-control-button:active{background:#526db8}
.fg-control-progress{flex:1;min-width:20px;accent-color:#8da3fa;height:20px;touch-action:pan-x}
.fg-control-position{flex:0 0 55px;text-align:center;font-size:10px;white-space:nowrap;}
.fg-controls-mini .fg-control-scrub,.fg-controls-mini .fg-control-row>.fg-control-button:not(:last-child){display:none}
.fg-controls-mini{width:46px;left:auto;right:7px;transform:none}
.fg-controls-mini .fg-control-row{min-height:30px}
.fg-control-settings{position:fixed;z-index:11000;right:8px;bottom:95px;
 width:min(360px,calc(100vw - 16px));max-height:65dvh;overflow:auto;
 padding:14px;background:#1d2638;color:#f1f4fc;border:1px solid #637493;
 border-radius:16px;box-shadow:0 0 40px #0008;font:14px/1.4 system-ui;}
.fg-control-settings-row{display:flex;align-items:center;gap:7px;justify-content:space-between;margin:8px 0;}
.fg-control-field{display:flex;align-items:center;justify-content:space-between;
 gap:12px;margin:10px 0;padding:4px 0;}
.fg-control-field>*:last-child{min-width:40px;max-width:60%;color:inherit}
.fg-control-field select{background:#303c55;border:1px solid #607396;padding:9px;
 border-radius:8px;min-width:130px!important}
.fg-control-field input[type=range]{width:50%}
.fg-control-field input[type=color]{width:72px;height:40px;background:transparent;border:0}
.fg-control-lightbox{position:fixed;inset:0;z-index:13000;
 background:#070b11;display:flex;align-items:center;justify-content:center;
 overflow:hidden;touch-action:none}
.fg-control-big-image{display:block;max-width:100%;max-height:100%;
 object-fit:contain;touch-action:none;will-change:transform}
.fg-control-image-close{position:absolute;top:max(12px,env(safe-area-inset-top));
 right:12px;padding:8px 18px;font-size:23px}
.fg-folder-reader{width:100%;height:100%;min-height:0;display:flex;flex-direction:column;
 background:var(--fg-reader-paper,#101114);color:var(--fg-reader-ink,#e3e0dc)}
.fg-folder-scroll{width:100%;height:100%;flex:1;overflow:auto;overscroll-behavior:contain;
 -webkit-overflow-scrolling:touch;touch-action:pan-y;box-sizing:border-box;padding:0!important}
.fg-folder-stack{width:100%;max-width:none!important;padding:0!important;margin:0!important;
 display:flex;flex-direction:column;gap:0!important}
.fg-folder-page{margin:0!important;border:0!important;padding:0!important;line-height:0!important;
 width:100%;min-height:0;scroll-snap-align:start}
.fg-folder-image{width:100%!important;height:auto!important;display:block!important;max-width:none!important;
 border:0!important;margin:0!important;padding:0!important;object-fit:contain}
body.fg-folder-reading #editor{padding:0!important;margin:0!important;width:100%!important;
 max-width:none!important;display:block!important;height:100%!important;min-height:0!important;overflow:hidden!important}
body.fg-folder-reading #work{height:100dvh!important;overflow:hidden!important}
body.fg-folder-reading .bar{display:none!important}
.fg-control-pages{scroll-snap-type:y proximity}
.fg-control-pages .fg-comic-section,.fg-control-pages .fg-pdf-section,
.fg-control-pages .fg-book-chapter,.fg-control-pages .fg-progressive-page{scroll-snap-align:start}
.fg-book,.fg-book-scroll,.fg-book-article{background:var(--fg-book-bg,#101114)!important;
 color:var(--fg-book-text,#e3e0dc)!important}
.fg-book-article{font-family:var(--fg-book-font,Georgia,serif)!important;
 font-size:var(--fg-book-font-size,19px)!important}
.fg-book-content:has(img){max-width:100%!important}
.fg-book-illustration,.fg-book-illustration img,.fg-book-chapter img{max-width:100%!important;
 object-fit:contain}
.fg-reader-scroll{background:var(--fg-reader-paper,#101114)!important}
.fg-continuous-text,.fg-document-p,.fg-document-sheet{color:var(--fg-reader-ink,#e3e0dc)!important;
 font-family:var(--fg-reader-font,Georgia,serif)!important;
 font-size:var(--fg-reader-size,19px)!important}
"""
style+="""
/* Large folders: only 96 document tiles render at a time. */
.fg-lib-pager{display:flex;align-items:center;justify-content:center;
 gap:7px;margin:12px 0 24px;grid-column:1/-1;font:600 12px system-ui;
 color:#b7c7dd;flex-wrap:wrap}
.fg-lib-page-control{background:#283a58;color:#eef5ff;
 border:1px solid #455b7d;border-radius:9px;min-height:38px;
 padding:7px 13px;font:600 12px system-ui}
.fg-lib-page-control:disabled{opacity:.32}
.fg-lib-page-number{background:#19253a;color:#eef5ff;
 border:1px solid #50658a;border-radius:8px;width:56px;min-height:35px;
 text-align:center;font:600 13px system-ui}
.fg-folder-sentinel{display:flex;justify-content:center;align-items:center;
 padding:12px 4px;color:#aebed8;background:#111722;
 font:12px system-ui;min-height:32px;line-height:1.3}
"""
style+="""

/* Android 17 draws edge-to-edge; use fixed viewport controls and leave
   clearance for transient navigation bars, not the auto-sized editor bottom. */
body.fg-image-reader-active .fg-image-toolbar{
 position:fixed!important;bottom:max(94px,calc(env(safe-area-inset-bottom,0px) + 74px))!important;
 left:50%!important;right:auto!important;z-index:2147483000!important;
 width:min(calc(100vw - 18px),500px)!important;
 transform:translateX(-50%)!important;
 pointer-events:auto!important;touch-action:manipulation!important;
}
body.fg-image-reader-active .fg-image-toolbar-small{
 opacity:.3!important;transform:translateX(-50%)!important;
}
body.fg-image-reader-active .fg-control-button{
 min-height:44px!important;min-width:40px!important;
}
body.fg-image-reader-active .fg-koikatsu-float{
 position:fixed!important;right:12px!important;left:auto!important;
 top:max(32px,calc(env(safe-area-inset-top,0px) + 22px))!important;
 bottom:auto!important;z-index:2147483001!important;
 min-height:50px!important;padding:10px 17px!important;
 background:#5270ee!important;color:white!important;
 border:1px solid #a4b3ff!important;border-radius:13px!important;
 box-shadow:0 4px 20px #000a;touch-action:manipulation!important;
 font:700 15px/1.25 system-ui!important;
}
body.fg-image-reader-active .fg-koikatsu-float[hidden]{display:none!important}
/* Separate image-reading surface: no EPUB dock, no section bars or wasted
   document canvas. Continuous mode is edge-to-edge and naturally sized. */
body.fg-folder-reading{margin:0!important;overflow:hidden!important;background:#000!important}
body.fg-folder-reading #work{height:100dvh!important;padding:0!important;margin:0!important}
body.fg-folder-reading #editor{height:100dvh!important;min-height:0!important;
 overflow:hidden!important;padding:0!important;max-width:none!important}
.fg-image-reader{position:relative!important;width:100%!important;
 height:100dvh!important;overflow:hidden!important;background:#000}
.fg-image-reader .fg-folder-scroll{width:100%!important;height:100%!important;
 overflow:auto!important;scroll-behavior:auto!important;padding:0!important;
 background:#000;overscroll-behavior:contain}
.fg-image-reader .fg-folder-stack{width:100%!important;display:flex!important;
 flex-direction:column!important;gap:0!important;margin:0!important;padding:0!important}
.fg-image-reader .fg-folder-page{position:relative!important;width:100%!important;
 display:block;margin:0!important;padding:0!important;border:0!important;
 background:#000;line-height:0!important}
.fg-image-reader .fg-folder-image{display:block!important;width:100%!important;
 height:auto!important;max-height:none!important;max-width:none!important;
 margin:0!important;padding:0!important;object-fit:contain!important}
.fg-image-reader .fg-image-paged{scroll-snap-type:y mandatory!important}
.fg-image-reader .fg-image-paged .fg-folder-page{height:100dvh!important;
 min-height:100dvh!important;flex:0 0 100dvh!important;scroll-snap-align:start;
 display:flex!important;align-items:center!important;justify-content:center!important;
 overflow:hidden!important}
.fg-image-reader .fg-image-paged .fg-folder-image{width:auto!important;
 height:auto!important;max-width:100%!important;max-height:100%!important;
 margin:auto!important;object-fit:contain!important}
.fg-image-reader .fg-image-paged .fg-image-rotated .fg-folder-image{
 position:absolute!important;left:50%;top:50%;margin:0!important;
 width:100dvh!important;height:100vw!important;max-width:none!important;
 max-height:none!important;transform:translate(-50%,-50%) rotate(90deg)!important;
 object-fit:contain!important}
.fg-image-toolbar{position:absolute;z-index:9990;bottom:max(46px,env(safe-area-inset-bottom,0px));
 left:50%;transform:translateX(-50%);width:min(98%,480px);
 display:flex;gap:4px;align-items:center;padding:5px 7px;border-radius:11px;
 background:#0b1029d9;border:1px solid #59668388;color:#fff;
 box-sizing:border-box;font:500 13px system-ui;backdrop-filter:blur(14px)}
.fg-image-toolbar .fg-control-button{flex:0 1 auto;min-width:36px;min-height:36px;
 border:0;background:#273650b0;color:white;padding:6px 9px}
.fg-image-toolbar .fg-image-position{flex:1;text-align:center;
 white-space:nowrap;font:600 12px system-ui}
.fg-image-toolbar-small{opacity:.12;transform:translateX(-50%) translateY(80%);transition:opacity .15s}
.fg-image-toolbar-small:active,.fg-image-toolbar-small:focus-within{opacity:1;
 transform:translateX(-50%)}
.fg-image-reader .fg-image-retry{position:absolute;top:50%;left:50%;
 transform:translate(-50%,-50%);z-index:3;white-space:nowrap}
.fg-image-reader .fg-image-error{padding:14px!important;background:#411c2b!important}
.fg-image-reader .fg-folder-sentinel{border:0;background:#000;color:#b6bdcc;
 padding:4px 0;min-height:10px;line-height:1.2}
"""

style+=r"""
/* File-specific professional control sheet and responsive library controls. */
.fg-library-root .fg-lib-toolbar{flex-wrap:wrap;row-gap:9px;column-gap:8px}
.fg-library-root .fg-lib-sort{padding:8px 9px;min-height:38px;max-width:116px;
 white-space:nowrap;text-overflow:ellipsis;overflow:hidden;
 border-radius:10px;background:#242d41;border:1px solid #445471;color:#e8eeff;
 font:650 11px system-ui;touch-action:manipulation}
.fg-library-root .fg-lib-search{min-width:0;flex:0 1 180px}
.fg-library-root .fg-lib-tile{position:relative}
.fg-library-root .fg-lib-more{position:absolute;right:5px;top:5px;z-index:7;
 display:grid;place-items:center;width:34px;height:34px;min-width:34px;
 background:#10182bdd;color:#eef4ff;border:1px solid #65728b99;
 border-radius:11px;backdrop-filter:blur(14px);font:800 23px/1 system-ui;
 touch-action:manipulation}
.fg-library-root .fg-lib-more:active{background:#485d88}
.fg-library-root .fg-lib-tile:focus-within .fg-lib-cover{
 outline:1px solid #849bff88;outline-offset:2px}
.fg-library-root .fg-lib-list .fg-lib-more{position:static;flex:0 0 36px}
.fg-file-sheet-overlay{position:fixed;inset:0;z-index:20000;background:#030811ad;
 display:flex;align-items:flex-end;justify-content:center;padding:0 0 env(safe-area-inset-bottom,0px);
 backdrop-filter:blur(5px)}
.fg-file-sheet{box-sizing:border-box;width:min(100%,520px);max-height:88dvh;
 overflow-y:auto;overscroll-behavior:contain;padding:16px 16px 22px;
 background:linear-gradient(155deg,#202b40,#121a2a 76%);
 color:#eff4ff;border:1px solid #5e73964d;border-radius:22px 22px 0 0;
 box-shadow:0 -18px 70px #0009;font-family:system-ui}
.fg-file-sheet-head{display:flex;align-items:center;gap:14px;
 justify-content:space-between;padding-bottom:13px;border-bottom:1px solid #ffffff20}
.fg-file-sheet-head strong{font:750 17px/1.4 system-ui;
 overflow-wrap:anywhere;max-height:3.5em;overflow:hidden}
.fg-file-sheet-close{flex:0 0 40px;width:40px;height:40px;background:#304058;
 border:1px solid #546784;color:#fff;border-radius:11px;font-size:25px}
.fg-file-sheet-subtitle{font:13px/1.5 system-ui;color:#a9bad4;margin:12px 0}
.fg-file-action{width:100%;display:flex;flex-direction:column;gap:4px;
 align-items:flex-start;justify-content:center;text-align:left;
 padding:13px 14px;margin:6px 0;border-radius:13px;border:1px solid #42516b87;
 color:#f0f5ff;background:#28354b;font:650 14px/1.3 system-ui;
 min-height:52px;touch-action:manipulation}
.fg-file-action:active{background:#425775}
.fg-file-action:disabled{opacity:.38;cursor:not-allowed}
.fg-file-action-description{color:#a8b8d1;font:400 11px/1.4 system-ui}
.fg-file-danger{border-color:#a25d6888;color:#ffc5c9;background:#442b38}
.fg-file-danger .fg-file-action-description{color:#e6a6b0}
.fg-file-name-input{box-sizing:border-box;width:100%;font:500 16px system-ui;
 background:#121d2e;color:#fff;border:1px solid #7284a5;border-radius:10px;
 padding:12px;margin:13px 0}
.fg-file-details{display:grid;grid-template-columns:95px 1fr;gap:10px 12px;
 padding:13px 0;line-height:1.4;font-size:13px}
.fg-file-details dt{color:#91a4c2}.fg-file-details dd{margin:0;overflow-wrap:anywhere}
.fg-file-write-note{font:12px/1.5 system-ui;color:#b2c0d6;margin:13px 3px}
.fg-file-delete-name{font:650 14px/1.5 system-ui;overflow-wrap:anywhere}
.fg-file-toast{position:fixed;bottom:max(24px,env(safe-area-inset-bottom,0px));
 left:50%;transform:translateX(-50%);width:min(92vw,480px);
 z-index:24000;background:#344665;color:#fff;border:1px solid #7084b0;
 border-radius:12px;padding:13px 16px;box-shadow:0 12px 28px #0007;
 font:600 13px system-ui;text-align:center}
@media(max-width:560px){
 .fg-library-root .fg-lib-toolbar{display:grid;grid-template-columns:34px 1fr 92px 38px;
  align-items:center;padding-top:13px}
 .fg-library-root .fg-lib-head-info{grid-column:2/4;grid-row:1;min-width:0}
 .fg-library-root .fg-lib-nav-back{grid-row:1;grid-column:1}
 .fg-library-root .fg-lib-search{grid-row:2;grid-column:1/3;width:100%;max-width:none}
 .fg-library-root .fg-lib-sort{grid-row:2;grid-column:3;max-width:92px}
 .fg-library-root .fg-lib-icon{grid-column:4;grid-row:2}
 .fg-file-sheet{border-radius:19px 19px 0 0}
}
"""

css.write_text(style)
print("Shared reader dock + paged mode + colors/fonts + zoomable EPUB illustrations + image-folder layout enabled")

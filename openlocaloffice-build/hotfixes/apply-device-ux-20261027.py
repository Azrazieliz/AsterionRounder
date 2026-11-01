#!/usr/bin/env python3
"""Android-first reader fixes: true comic pinch, fitted minimum, immersive bars and spreadsheet controls."""
from pathlib import Path
root=Path("app/src/main")
assets=root/"assets"
u=assets/"unified-viewer-controls.js"
s=u.read_text()
assert "const minScale=.65,maxScale=4;" in s
s=s.replace("const minScale=.65,maxScale=4;","const minScale=1,maxScale=4;")
# Native WebView must own single-finger scroll and fling; never intercept it.
# The existing unified viewer only calls preventDefault for two-finger pinch.
s=s.replace("target.style.width=Math.round(value*100)+'%';",
            "target.style.setProperty('width',Math.round(value*100)+'%','important');")
u.write_text(s)

p=assets/"universal-reader.js"
s=p.read_text()
assert "Math.max(.65,Math.round(Number(requested)*1000)/1000)" in s
s=s.replace("Math.max(.65,Math.round(Number(requested)*1000)/1000)",
            "Math.max(1,Math.round(Number(requested)*1000)/1000)")
p.write_text(s)

n=root/"java/com/openlocal/office/MainActivity.java"
s=n.read_text()
anchor='        @JavascriptInterface public void readerDiagnostic(String event){'
assert s.count(anchor)==1
method=r'''        @JavascriptInterface public void setReadingImmersive(boolean enabled){
            runOnUiThread(()->{
                android.view.View decor=getWindow().getDecorView();
                if(android.os.Build.VERSION.SDK_INT>=30){
                    android.view.WindowInsetsController controller=decor.getWindowInsetsController();
                    if(controller!=null){
                        controller.setSystemBarsBehavior(
                            android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                        if(enabled)controller.hide(android.view.WindowInsets.Type.navigationBars());
                        else controller.show(android.view.WindowInsets.Type.navigationBars());
                    }
                }else{
                    int before=decor.getSystemUiVisibility();
                    int bits=android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                        android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
                        android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION;
                    decor.setSystemUiVisibility(enabled?(before|bits):(before&~bits));
                }
            });
        }
'''
s=s.replace(anchor,method+anchor)
n.write_text(s)

p=assets/"premium-library.js"
s=p.read_text()
assert "function show(){" in s
s=s.replace("function show(){",
            "function show(){\n bridge()?.setReadingImmersive?.(false);\n document.body.classList.remove('fg-reader-fullscreen','fg-reader-chrome-open');",1)
old="window.loadDocument=function(payload){\n visible=false;"
assert old in s
s=s.replace(old,"""window.loadDocument=function(payload){
 bridge()?.setReadingImmersive?.(true);
 document.body.classList.add('fg-reader-fullscreen');
 document.body.classList.remove('fg-reader-chrome-open');
 visible=false;""")
anchor="function handleAndroidBack(){"
assert anchor in s
s=s.replace(anchor,"""// The hidden header can always be reopened without covering the reading surface.
const chromeToggle=E('button','fg-reader-chrome-toggle','☰');
chromeToggle.type='button';
chromeToggle.setAttribute('aria-label','Show or hide reader controls');
chromeToggle.addEventListener('click',()=>{
  document.body.classList.toggle('fg-reader-chrome-open');
});
document.body.appendChild(chromeToggle);
"""+anchor)
p.write_text(s)

# The spreadsheet mutation observer must never flip an actively edited cell
# back to contentEditable=false while typing. This was the reason edits stopped.
app=assets/"app.js"
s=app.read_text()
# Fix a malformed comma-expression that made visible() throw whenever a sheet
# contained cells, aborting selection, tap-to-edit and formula interaction.
bad="if(!x.length)return null,rs=x.map(e=>+e.dataset.r),cs=x.map(e=>+e.dataset.c);return{"
good="if(!x.length)return null;const rs=x.map(e=>+e.dataset.r),cs=x.map(e=>+e.dataset.c);return{"
assert bad in s,"Spreadsheet visible-range parser bug anchor missing"
s=s.replace(bad,good)

old="cells().forEach(prep);let sh=sheet();"
assert old in s,"Spreadsheet input synchronization anchor missing"
s=s.replace(old,"cells().forEach(td=>{if(td.contentEditable==='true'&&document.activeElement===td)return;prep(td)});let sh=sheet();")
old="$('sheetUndo').onclick=undo;"
assert old in s
extra="""// Explicit phone edit/save affordances; never rely on difficult double-tap.
const quick=T.querySelector('.sheetQuickActions');
if(quick){
 const editButton=document.createElement('button');
 editButton.type='button';editButton.textContent='Edit';
 editButton.title='Edit selected cell';
 editButton.id='sheetEditAction';
 editButton.onclick=()=>edit(at(S.active)||cells()[0]);
 quick.prepend(editButton);
 const saveCopyButton=document.createElement('button');
 saveCopyButton.type='button';saveCopyButton.textContent='Save copy';
 saveCopyButton.title='Save changed spreadsheet as a new document';
 saveCopyButton.id='sheetSaveCopyAction';
 saveCopyButton.onclick=()=>document.getElementById('copyBtn')?.click();
 quick.appendChild(saveCopyButton);
}
"""
s=s.replace(old,extra+old)
# Rebuilding a single cell must not reinitialize the entire grid.
old="new MutationObserver(sync).observe(E,{childList:true,subtree:true});"
assert old in s
s=s.replace(old,"new MutationObserver(sync).observe(E,{childList:true,subtree:false});")
app.write_text(s)

css=assets/"style.css"
css.write_text(css.read_text()+r'''
/* Native Android WebView handles single-finger scroll/fling for comics and images.
   Pinch zoom is handled separately by two-finger touch listeners. */
.fg-archive-scroll.fg-unified-scroll:has(.fg-comic-stack),
.fg-unified-image-scroll.fg-unified-scroll{
 touch-action:pan-x pan-y!important;
 -webkit-overflow-scrolling:touch;
 overscroll-behavior:contain;
}
.fg-comic-stack .fg-comic-section{margin:0!important;padding:0!important;box-shadow:none!important;border:0!important}
.fg-comic-stack .fg-pdf-container{gap:0!important}
body.fg-reader-fullscreen:not(.fg-reader-chrome-open) .bar,
body.fg-reader-fullscreen:not(.fg-reader-chrome-open) .fg-reader-toolbar{
 display:none!important;
}
body.fg-reader-fullscreen .fg-reader-chrome-toggle{
 display:grid!important;position:fixed;z-index:120;
 top:calc(max(6px,env(safe-area-inset-top)) + 3px);right:9px;
 width:34px;height:34px;padding:0;place-items:center;
 border:1px solid #ffffff42;border-radius:11px;
 background:#141b28c7;color:#fff;font-size:17px;
 opacity:.75;touch-action:manipulation;
}
body.fg-reader-fullscreen.fg-reader-chrome-open .fg-reader-chrome-toggle{
 background:#586edf;opacity:1;
}
.fg-reader-chrome-toggle{display:none!important}
body.fg-reader-fullscreen:not(.fg-reader-chrome-open) .fg-reader-scroll{padding-bottom:0!important}
body.fg-reader-fullscreen .fg-comic-stack .fg-pdf-container{
 margin:0!important;padding:0!important;gap:0!important;
}
body.fg-reader-fullscreen .fg-comic-stack img{margin:0!important;padding:0!important;display:block}
/* Spreadsheet: prioritize the cells and an actually usable formula input. */
body.fg-reader-fullscreen .sheetbar{padding:4px 6px!important}
body.fg-reader-fullscreen .rangeNav{gap:3px!important}
body.fg-reader-fullscreen .rangeNav button{min-height:30px!important;font-size:11px!important}
body.fg-reader-fullscreen #rangeInfo{font-size:10px!important}
body.fg-reader-fullscreen .spreadsheetTools{
 display:grid;grid-template-columns:54px minmax(0,1fr);gap:5px;
 padding:5px 7px!important;
}
body.fg-reader-fullscreen #selectedCellRef{height:35px;min-width:51px}
body.fg-reader-fullscreen .formulaBox{height:35px}
body.fg-reader-fullscreen .sheetQuickActions{
 display:flex!important;grid-column:1/-1;overflow-x:auto;
 gap:5px;padding:0 0 2px;scrollbar-width:none;
}
body.fg-reader-fullscreen .sheetQuickActions button{
 flex:0 0 35px!important;width:35px!important;height:32px!important;
 min-width:35px!important;font-size:15px!important;
}
body.fg-reader-fullscreen #editor{padding-bottom:0!important}
''')
print("Device fixes: gesture-owned comic pinch and pan, >=fit clamp, navigation insets, collapsible chrome")

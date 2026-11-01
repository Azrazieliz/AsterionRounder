#!/usr/bin/env python3
from pathlib import Path
js=Path("app/src/main/assets/app.js")
s=js.read_text()
anchor="    pageRows:100, pageCols:24, docStart:0, docPageSize:200,"
assert s.count(anchor)==1
s=s.replace(anchor,"    pageRows:48, pageCols:12, docStart:0, docPageSize:200,",1)
window='    const totalRows=Math.max(20,s.rows||0), totalCols=Math.max(12,s.cols||0);'
assert s.count(window)==1
s=s.replace(window,"    const totalRows=Math.max(doc.format==='xlsx'?1048576:100000,s.rows||0), totalCols=Math.max(doc.format==='xlsx'?16384:256,s.cols||0);",1)
s+="""
;(()=>{
 'use strict';
 const bar=document.getElementById('sheetBar');
 const tools=document.getElementById('spreadsheetTools');
 const actions=tools?.querySelector('.sheetQuickActions');
 if(!bar||!tools||!actions)return;
 const make=(title,fn)=>{
   const n=document.createElement('button');n.type='button';
   n.textContent=title;n.setAttribute('aria-label',title);n.onclick=fn;return n;
 };
 const expand=make('Tools',()=>{
   document.body.classList.toggle('fg-sheet-tools-open');
   expand.textContent=document.body.classList.contains('fg-sheet-tools-open')?'Less':'Tools';
 });
 expand.id='fgSheetToggle';tools.insertBefore(expand,actions);
 const back=make('‹',()=>{
   document.activeElement?.blur?.();
   window.FileGestionerLibrary?.show?.();
 });
 back.id='fgSheetBack';
 back.title='Back to library';
 back.setAttribute('aria-label','Back to library');
 tools.insertBefore(back,tools.firstChild);
 const save=make('Save',()=>{
   document.activeElement?.blur?.();
   document.getElementById('saveBtn')?.click();
 });
 save.id='fgSheetSave';actions.append(save);
 const sync=()=>{
   const enabled=!bar.classList.contains('hidden');
   document.body.classList.toggle('fg-spreadsheet-reading',enabled);
   if(enabled)document.getElementById('notice')?.classList.add('hidden');
   save.disabled=Boolean(document.getElementById('saveBtn')?.disabled);
 };
 new MutationObserver(sync).observe(bar,{attributes:true,attributeFilter:['class']});
 const nativeSave=document.getElementById('saveBtn');
 if(nativeSave)new MutationObserver(sync).observe(nativeSave,
   {attributes:true,attributeFilter:['disabled']});
 sync();
})();
"""
js.write_text(s)
css=Path("app/src/main/assets/style.css")
css.write_text(css.read_text()+"""
/* A spreadsheet has its own Back, formula and Save controls.
   Hide the redundant general-purpose bar, which otherwise sits behind the
   Android status icons on edge-to-edge Samsung devices. */
body.fg-spreadsheet-reading>.bar{display:none!important}
body.fg-spreadsheet-reading #work{height:100dvh!important;max-height:100dvh!important;
 padding-top:max(33px,env(safe-area-inset-top,0px))!important;
 padding-bottom:env(safe-area-inset-bottom,0px)!important}
body.fg-spreadsheet-reading #spreadsheetTools{
 grid-template-columns:35px 52px minmax(0,1fr) 55px!important}
body.fg-spreadsheet-reading #fgSheetBack{grid-column:1;grid-row:1;
 border:1px solid #526685;background:#263c5c;color:#eff5ff;
 border-radius:10px;min-height:34px;min-width:34px;padding:0 6px!important;
 font:700 25px/1 system-ui}
body.fg-spreadsheet-reading #selectedCellRef{grid-column:2;grid-row:1}
body.fg-spreadsheet-reading #spreadsheetTools .formulaBox{grid-column:3;grid-row:1}
body.fg-spreadsheet-reading #fgSheetToggle{grid-column:4;grid-row:1}
body.fg-spreadsheet-reading .sheetQuickActions{grid-row:2}
@media(max-width:550px){body.fg-spreadsheet-reading #spreadsheetTools{
 grid-template-columns:34px 50px minmax(0,1fr) 55px!important}}
/* File-specific spreadsheet canvas: no bottom black overlay. */
body.fg-spreadsheet-reading{overflow:hidden!important}
body.fg-spreadsheet-reading .bar{padding-top:max(28px,env(safe-area-inset-top,0px))!important;
 min-height:80px!important}
body.fg-spreadsheet-reading #work{display:flex!important;flex-direction:column!important;
 height:100dvh!important;max-height:100dvh!important;min-height:0!important;
 padding-top:max(33px,env(safe-area-inset-top,0px))!important;
 overflow:hidden!important;padding-bottom:env(safe-area-inset-bottom,0px)!important}
body.fg-spreadsheet-reading #sheetBar{flex:0 0 auto!important;overflow-x:auto!important;
 max-height:100px;padding:5px!important}
body.fg-spreadsheet-reading #spreadsheetTools{display:grid!important;flex:0 0 auto!important;
 grid-template-columns:35px 52px minmax(0,1fr) 55px!important;gap:4px!important;
 padding:5px!important;background:var(--surface)!important;min-height:44px!important}
body.fg-spreadsheet-reading #selectedCellRef{grid-column:2;grid-row:1}
body.fg-spreadsheet-reading #spreadsheetTools .formulaBox{grid-column:3;grid-row:1;min-width:0!important}
body.fg-spreadsheet-reading #formulaInput{font-size:16px!important}
body.fg-spreadsheet-reading #fgSheetToggle{grid-column:4;grid-row:1;min-height:35px;padding:5px!important;
 border:1px solid #4e6182;background:#314664;color:#fff;border-radius:9px;font:650 12px system-ui}
body.fg-spreadsheet-reading .sheetQuickActions{display:none!important;grid-column:1/-1!important;
 overflow-x:auto!important;white-space:nowrap;gap:4px!important}
body.fg-spreadsheet-reading.fg-sheet-tools-open .sheetQuickActions{display:flex!important}
body.fg-spreadsheet-reading .sheetQuickActions button{flex:0 0 40px!important;
 width:40px!important;min-width:40px!important;height:34px!important;padding:3px!important}
body.fg-spreadsheet-reading #fgSheetSave{flex-basis:56px!important;width:56px!important}
body.fg-spreadsheet-reading #notice{display:none!important}
body.fg-spreadsheet-reading #editor{flex:1 1 0!important;height:auto!important;
 min-height:0!important;overflow:hidden!important;padding:0!important;margin:0!important}
body.fg-spreadsheet-reading .editorGridWrap{height:100%!important;max-height:none!important;
 width:100%!important;overflow:auto!important;touch-action:pan-x pan-y!important;
 margin:0!important;padding:0!important}
body.fg-spreadsheet-reading #editor table.sheet td[contenteditable=true]{
 touch-action:auto!important;-webkit-user-select:text!important;user-select:text!important}
@media(max-width:560px){body.fg-spreadsheet-reading #work>.searchbar{display:none!important}
 body.fg-spreadsheet-reading #sheetBar{max-height:75px!important}}
""")
print("CSV/XLSX mobile grid and editable controls upgraded")

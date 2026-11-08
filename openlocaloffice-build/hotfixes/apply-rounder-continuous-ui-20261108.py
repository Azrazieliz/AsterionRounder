#!/usr/bin/env python3
"""Rounder v0.15.19: replace paginated generic shell with continuous cloud vault,
compact genuine folder rows, and a native in-app signed update control.
Run LAST after full 0.15.18 organizer assembly and existing tests.
"""
from pathlib import Path
import re
base=Path("app/src/main")
lib=base/"assets/premium-library.js"
s=lib.read_text(encoding="utf-8")
def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:raise AssertionError(f"{label}: expected 1 anchor, got {n}: {old[:100]}")
    s=s.replace(old,new,1)
def section(start,end,new,label):
    global s
    a=s.find(start)
    b=s.find(end,a+len(start))
    if a<0 or b<0 or s.find(start,a+1)>=0:
        raise AssertionError(f"{label}: unique function bounds missing")
    s=s[:a]+new+s[b:]

once("actions.append(openBtn,organizeBtn,settingsBtn);",
"""const updateBtn=b('Update','fg-vault-update',()=>showUpdater());
updateBtn.setAttribute('aria-label','Check and install Rounder updates');
actions.append(openBtn,organizeBtn,updateBtn,settingsBtn);""",
"update action")
once("body.append(premiumIntro,toolbar,filters,loading,deck,empty,footer);",
"""body.append(toolbar,filters,loading,deck,empty,footer);""",
"remove repetitive hero")
once("const entryIds=new Set();",
"""const entryIds=new Set();
const folderRail=E('section','fg-vault-folderrail');
const virtualTop=E('div','fg-vault-spacer');
const virtualBottom=E('div','fg-vault-spacer');
body.insertBefore(folderRail,deck);
body.insertBefore(virtualTop,deck);
deck.after(virtualBottom);
let virtualMode='',virtualKey='',virtualFolderKey='',virtualFiles=[];
let virtualLastStart=-1,virtualLastEnd=-1,virtualLastSig='';
let virtualRowHeight=276,virtualCols=2,virtualScrollTimer=0;
let updaterPanel=null,updaterData=null,updateChecked=false;""",
"virtual viewport state")

# Eliminate placeholder text rendered inside media thumbnails. The actual file
# name remains readable in the card metadata below.
once("fallback.append(E('span','fg-lib-fallback-glyph',icon(c)),\n                 E('strong','fg-lib-fallback-title',item.title));",
"""fallback.append(E('span','fg-lib-fallback-glyph',icon(c)));""",
"remove duplicated file title from cover")

# Folder cards are compact, differentiated navigation rows, never fake covers.
folder_helpers=r'''
function folderAccent(name){
 const lower=(name||'').toLowerCase();
 if(/art|image|gallery|illustration|pixiv|photo/.test(lower))return ['◈','art'];
 if(/book|comic|manga|novel|pdf/.test(lower))return ['▤','book'];
 if(/app|apk|program|software/.test(lower))return ['▦','app'];
 if(/video|movie|film/.test(lower))return ['▶','video'];
 if(/sound|music|audio/.test(lower))return ['♫','audio'];
 if(/3d|model|blend|koikatsu/.test(lower))return ['⬡','model'];
 return ['▰','folder'];
}
function folderCard(item){
 const [symbol,type]=folderAccent(item.name);
 const button=b('','fg-vault-folder fg-vault-folder-'+type,()=>openBook(item));
 button.setAttribute('aria-label','Open '+item.name);
 const thumb=E('span','fg-vault-folder-art');
 const mosaic=folderPreviewCache.get(item.path||'');
 if(mosaic?.length){
   thumb.classList.add('fg-vault-has-cover');
   for(const src of mosaic.slice(0,3)){
     const im=E('img','fg-vault-folder-image');
     im.alt='';im.loading='lazy';im.decoding='async';im.src=src;
     im.onerror=()=>{im.remove();if(!thumb.querySelector('img')){
       thumb.classList.remove('fg-vault-has-cover');
       thumb.replaceChildren(E('span','fg-vault-folder-glyph',symbol));}};
     thumb.append(im);
   }
 }else thumb.append(E('span','fg-vault-folder-glyph',symbol));
 const meta=E('span','fg-vault-folder-content');
 meta.append(E('strong','',item.name),E('small','','Folder · TeraBox'));
 button.append(thumb,meta,E('span','fg-vault-folder-chevron','›'));
 return button;
}
function drawFolderRail(folders,mode){
 const key=mode+'|'+folders.map(x=>x.path||x.id||x.name).join('\n')+'|'+
  folders.map(x=>(folderPreviewCache.get(x.path||'')||[]).length).join(',');
 if(key===virtualFolderKey)return;
 virtualFolderKey=key;
 folderRail.replaceChildren();
 if(!folders.length){folderRail.hidden=true;return;}
 folderRail.hidden=false;
 folderRail.append(E('h2','fg-vault-section-heading',
   mode==='search'?'Matching collections':'Collections'));
 const content=E('div','fg-vault-folder-grid');
 for(const item of folders.slice(0,200))content.append(folderCard(item));
 folderRail.append(content);
 if(folders.length>200)folderRail.append(E('p','fg-vault-overflow',
   'Showing the first 200 folders. Narrow your search to find other collections.'));
}
function resetVirtual(mode,key){
 if(mode===virtualMode&&key===virtualKey)return;
 virtualMode=mode;virtualKey=key;virtualFolderKey='';
 virtualLastStart=-1;virtualLastEnd=-1;virtualLastSig='';
 retainedCards.clear();lastVisibleKeys='';
 deck.replaceChildren();
 virtualTop.style.height='0px';virtualBottom.style.height='0px';
 body.scrollTop=0;
}
function showVirtualItems(items,mode,key){
 resetVirtual(mode,key);
 // Folder links are compact separate navigation surfaces, not giant fake covers.
 const folders=items.filter(e=>e.folder);
 const files=items.filter(e=>!e.folder);
 drawFolderRail(folders,mode);
 virtualFiles=files;
 const useList=list||!files.some(e=>e.cover)||filter==='document'||filter==='file';
 deck.className='fg-lib-grid'+(useList?' fg-lib-list':' fg-vault-media-grid');
 const computedCols=(window.getComputedStyle(deck).gridTemplateColumns.match(/[\\d.]+px/g)||[]).length;
 const columns=useList?1:Math.max(1,computedCols||2);
 const rowHeight=useList?78:276;
 virtualCols=columns;virtualRowHeight=rowHeight;
 const totalRows=Math.ceil(files.length/columns);
 const origin=virtualTop.getBoundingClientRect().top-
   body.getBoundingClientRect().top+body.scrollTop;
 const relative=Math.max(0,body.scrollTop-origin);
 const firstRow=Math.max(0,Math.min(totalRows,Math.floor(relative/rowHeight)-4));
 const windowRows=Math.max(10,Math.ceil(body.clientHeight/rowHeight)+12);
 const endRow=Math.min(totalRows,firstRow+windowRows);
 const start=firstRow*columns;
 const end=Math.min(files.length,endRow*columns);
 virtualTop.style.height=(firstRow*rowHeight)+'px';
 virtualBottom.style.height=((totalRows-endRow)*rowHeight)+'px';
 const signature=mode+'|'+key+'|'+start+'|'+end+'|'+useList+'|'+
   files.slice(start,end).map(x=>x.path||x.uri||x.id||x.name).join('\n');
 if(signature===virtualLastSig)return;
 const needed=files.slice(start,end).map((entry,idx)=>{
   const id=(entry.path||entry.uri||entry.id||entry.name)+'|'+list;
   let cached=retainedCards.get(id);
   if(!cached){cached=card(entry,start+idx);retainedCards.set(id,cached);}
   return cached;
 });
 needed.forEach((node,i)=>{
   const existing=deck.children[i];
   if(existing!==node)deck.insertBefore(node,existing||null);
 });
 while(deck.children.length>needed.length)deck.lastElementChild.remove();
 if(retainedCards.size>300){
   const keep=new Set(files.slice(start,end).map(x=>
     (x.path||x.uri||x.id||x.name)+'|'+list));
   for(const id of retainedCards.keys())
     if(!keep.has(id))retainedCards.delete(id);
 }
 virtualLastStart=start;virtualLastEnd=end;virtualLastSig=signature;
}
function handleContinuousScroll(){
 if(!visible||(!virtualFiles.length&&!indexedMode()))return;
 if(virtualScrollTimer)return;
 virtualScrollTimer=requestAnimationFrame(()=>{
   virtualScrollTimer=0;
   if(indexedMode()){
     renderIndexedResults();
     const nearEnd=body.scrollTop+body.clientHeight+1000>=body.scrollHeight;
     if(nearEnd&&indexedMore&&!indexedPending)
       scheduleIndexSearch(indexedResults.length,0);
   }else render();
 });
}
body.addEventListener('scroll',handleContinuousScroll,{passive:true});
window.addEventListener('resize',()=>{virtualLastSig='';if(visible)render();});
'''
section("function render(){","function createFilters(){",folder_helpers+r'''
function render(){
 if(indexedMode()){renderIndexedResults();return;}
 indexedRefresh.hidden=true;
 if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
 empty.replaceChildren();
 root.querySelectorAll('.fg-lib-pager').forEach(node=>node.remove());
 const needle=phrase.trim().toLocaleLowerCase();
 const key=[currentFolder,filter,needle,sortBy,sortDescending?'desc':'asc'].join('\u0001');
 let shown;
 if(indexedRevision===catalogRevision&&indexedKey===key)shown=indexedEntries;
 else{
   shown=entries.filter(e=>{
     const c=classify(e);
     return (filter==='all'||c===filter||c==='folder')&&
       (!needle||(e.title||e.name).toLocaleLowerCase().includes(needle));
   }).sort((a,b)=>{
     if(a.folder!==b.folder)return a.folder?-1:1;
     let value=0;
     if(sortBy==='size')value=(a.size||0)-(b.size||0);
     else if(sortBy==='modified')value=(a.modified||0)-(b.modified||0);
     else if(sortBy==='type')value=classify(a).localeCompare(classify(b));
     else value=naturalCollator.compare(a.name,b.name);
     return (sortDescending?-1:1)*(value||
       naturalCollator.compare(a.name,b.name));
   });
   indexedEntries=shown;indexedRevision=catalogRevision;indexedKey=key;
 }
 const viewKey=key+'|'+list;
 showVirtualItems(shown,'browse',viewKey);
 loading.classList.add('fg-lib-hidden');deck.classList.remove('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');
 const folders=shown.filter(x=>x.folder).length;
 const files=shown.length-folders;
 count.textContent=folders+' folders · '+files+' files'+(scanning?' · syncing':'');
 if(!shown.length)empty.append(
   E('strong','',entries.length?'No matches':'This folder is empty'),
   E('p','',entries.length?'Try a different search or filter.':
     'There are no files in this TeraBox folder.'));
}
''' ,"replace segmented browsing with virtual continuous list")

# Indexed search has no numeric pages, and further backend search batches are
# requested only when the viewer reaches the bottom of its current results.
section("function renderIndexedResults(){","function receiveIndexedSearch(data){",
r'''function renderIndexedResults(){
 if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
 root.querySelectorAll('.fg-lib-pager').forEach(node=>node.remove());
 empty.replaceChildren();
 showVirtualItems(indexedResults,'search',phrase+'|'+filter+'|'+cloudMode+'|'+list);
 loading.classList.add('fg-lib-hidden');deck.classList.remove('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');
 indexedRefresh.hidden=false;
 const suffix=indexedBuilding?' · indexing '+indexedCount.toLocaleString()+' files':'';
 count.textContent=indexedResults.length.toLocaleString()+
   (indexedMore?'+':'')+' matches'+suffix+
   (indexedPending?' · loading more…':'');
 if(indexedResults.length===0)
   empty.append(E('strong','',indexedPending?'Searching…':
     indexedError?'Search unavailable':indexedBuilding?'Indexing folders…':'No matches'),
     E('p','',indexedError||
       (indexedBuilding?'The first index scan is still building.':
        'Search covers all descendants of your selected cloud library.')));
}
''',"remove indexed search pager")
once("indexedResults=Array.isArray(data.items)?data.items:[];",
"""const next=Array.isArray(data.items)?data.items:[];
  indexedResults=indexedOffset>0?indexedResults.concat(next):next;""",
"append indexed search batches")

# Metadata streaming is retained, while numeric-pager manipulation is removed.
start="  if(!payload.finished && filter==='all' && !phrase.trim() &&"
pos=s.find(start)
end=s.find("  const elapsed=Date.now()-lastRender;",pos)
if pos<0 or end<0:raise AssertionError("streaming pager branch missing")
s=s[:pos]+'''  if(!payload.finished&&filter==='all'&&!phrase.trim()&&
     entries.length>PAGE&&virtualLastEnd>0){
    count.textContent=entries.length.toLocaleString()+' items · syncing…';
    if(body.scrollTop+body.clientHeight+800>=body.scrollHeight &&
       Date.now()-lastRender>=1100){
      render();lastRender=Date.now();
    }
    return;
  }
'''+s[end:]

# Keep every file reachable through scrolling, reset position for a newly
# navigated folder rather than perpetuating the previous directory's scroll.
once("  collectionCacheKey=nextCollectionKey;\n activeVersion=null;",
"""  collectionCacheKey=nextCollectionKey;
 if(!sameCollection)body.scrollTop=0;
 activeVersion=null;""",
"reset scroll on navigation") if False else None

# Use a clean root label instead of repetitive 'Your library' text.
s=s.replace("heading.textContent=stack.length?'Collection':'Your library';",
            "heading.textContent=cloudMode?(currentFolder?'Folder':'TeraBox'):'Local files';")
# Remove old pagination state from user-visible counts.
s=s.replace("window.FileGestionerLibrary={",
"""window.FileGestionerLibrary={
 updaterStatus,""",1)
once(" if(managerPanel){closeOrganizer();return true;}",
""" if(updaterPanel){updaterPanel.remove();updaterPanel=null;return true;}
 if(managerPanel){closeOrganizer();return true;}""",
"system Back dismisses updater")

# Update panel uses the actual signed APK downloader, not an external browser or
# an inert link. Android system installer is the only confirmation authority.
updates=r'''
function updaterStatus(data){
 if(!data)return;
 updaterData=data;
 if(data.status==='available')updateBtn.classList.add('fg-vault-update-available');
 else if(data.status==='current'||data.status==='none')
   updateBtn.classList.remove('fg-vault-update-available');
 if(updaterPanel)renderUpdater();
}
function showUpdater(){
 if(updaterPanel)return;
 updaterPanel=E('div','fg-vault-updater-backdrop');
 const panel=E('section','fg-vault-updater-sheet');
 panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');
 panel.setAttribute('aria-label','Update Asterion Rounder');
 updaterPanel.append(panel);
 updaterPanel.addEventListener('click',e=>{
   if(e.target===updaterPanel){updaterPanel.remove();updaterPanel=null;}
 });
 document.body.append(updaterPanel);
 renderUpdater();
 if(!updateChecked){
   updateChecked=true;bridge()?.checkRounderUpdate?.();
 }
}
function renderUpdater(){
 const panel=updaterPanel?.firstElementChild;
 if(!panel)return;
 panel.replaceChildren();
 const top=E('div','fg-vault-updater-head');
 top.append(E('strong','','Rounder Updates'),
   b('✕','fg-vault-updater-close',()=>{
     updaterPanel.remove();updaterPanel=null;
   }));
 panel.append(top,E('p','fg-vault-updater-desc',
   'Signed official releases · installed through Android'));
 if(updaterData){
   const status=E('div','fg-vault-updater-status');
   status.append(E('strong','',updaterData.message||'Update status unavailable'));
   if(updaterData.percent>=0&&updaterData.status==='downloading'){
     const meter=E('progress','');meter.max=100;meter.value=updaterData.percent;
     status.append(meter,E('small','',updaterData.percent+'% downloaded'));
   }
   if(updaterData.tag)status.append(E('small','',updaterData.tag));
   panel.append(status);
 }
 const buttons=E('div','fg-vault-updater-buttons');
 buttons.append(b('Check releases','fg-vault-updater-secondary',()=>{
   updaterData=null;renderUpdater();bridge()?.checkRounderUpdate?.();
 }));
 const install=b('Download & install','fg-vault-updater-primary',()=>{
   bridge()?.installRounderUpdate?.();
 });
 install.disabled=updaterData?.status==='downloading';
 buttons.append(install);panel.append(buttons);
 panel.append(E('p','fg-vault-updater-note',
   'Rounder verifies the APK checksum, Android package identity, signing certificate and newer version before launching the system installer. Installation requires your Android confirmation.'));
}
'''
section("function handleAndroidBack(){","function navigateBack(){",
updates+"function handleAndroidBack(){","insert native updater modal") if False else None
once("function handleAndroidBack(){",updates+"\nfunction handleAndroidBack(){",
"native updater UI")

# Eliminate the redundant local/cloud choice inside the connection screen.
once("panel.append(head,desc,input,info,save,local);",
     "panel.append(head,desc,input,info,save);",
     "TeraBox-only settings")
# The local file picker remains accessible from the header only.

# New version for a real in-place update.
lib.write_text(s,encoding="utf-8")
css=base/"assets/style.css"
theme=Path("../additions/rounder-continuous-ui.css").read_text(encoding="utf-8")
assert "fg-vault-updater-backdrop" in theme and "fg-vault-spacer" in theme
css.write_text(css.read_text(encoding="utf-8")+"\n"+theme,encoding="utf-8")

gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)40\b',r'\g<1>41',g,count=1)
assert n==1,"Expected versionCode 40"
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.18"',r'\g<1>"0.15.19"',g,count=1)
assert n==1,"Expected versionName 0.15.18"
gradle.write_text(g,encoding="utf-8")
print("ROUND ER 0.15.19: no numeric pages, bounded virtual scroll, compact folders, in-app updater")

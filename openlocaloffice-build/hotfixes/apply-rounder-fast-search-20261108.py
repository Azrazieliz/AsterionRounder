#!/usr/bin/env python3
"""Asterion Rounder: global recursive local SAF search, persistent metadata index.
Run LAST, after all existing reader/appearance hotfixes. No viewer redesign.
"""
from pathlib import Path
import re

base=Path("app/src/main")
java=base/"java/com/openlocal/office/MainActivity.java"
s=java.read_text(encoding="utf-8")

def one(source,needle,replacement,label):
    count=source.count(needle)
    if count!=1:
        raise AssertionError(f"{label}: expected 1 anchor, found {count}: {needle[:110]}")
    return source.replace(needle,replacement,1)

s=one(s,"    private volatile Uri libraryTree;",
"""    private volatile Uri libraryTree;
    private com.openlocal.office.core.FgSearchIndex fgSearchIndex;
    private synchronized com.openlocal.office.core.FgSearchIndex fgSearch(){
        if(fgSearchIndex==null)
            fgSearchIndex=new com.openlocal.office.core.FgSearchIndex(this,
                new com.openlocal.office.core.FgSearchIndex.Listener(){
                    @Override public void onResult(String json){
                        runOnUiThread(()->js("window.FileGestionerLibrary?.receiveIndexedSearch("+json+")"));
                    }
                    @Override public void onProgress(String json){
                        runOnUiThread(()->js("window.FileGestionerLibrary?.indexProgress("+json+")"));
                    }
                });
        return fgSearchIndex;
    }
""","search index field")

s=one(s,'js("window.FileGestionerLibrary?.openCollection()");',
'''fgSearch().ensure(uri,false);
                js("window.FileGestionerLibrary?.openCollection()");''',"start index on collection selection")

anchor="        @JavascriptInterface public void openKoikatsu3d(){"
bridge=r'''        @JavascriptInterface public void searchLibraryIndex(
                String needle,String category,int offset,int token){
            final Uri root=libraryTree;
            if(root==null)return;
            fgSearch().search(root,needle,category,offset,token);
        }
        @JavascriptInterface public void refreshLibraryIndex(){
            final Uri root=libraryTree;
            if(root!=null)fgSearch().ensure(root,true);
        }
        @JavascriptInterface public void stopLibraryListing(){
            fgDirectoryVersion.incrementAndGet();
        }
        @JavascriptInterface public void openIndexedFile(String documentId){
            final Uri root=libraryTree;
            if(root==null||documentId==null)return;
            fgDirectoryExecutor.execute(()->{
                try{
                    boolean authorized=false;
                    for(android.content.UriPermission p:
                            getContentResolver().getPersistedUriPermissions()){
                        if(root.equals(p.getUri())&&p.isReadPermission()){
                            authorized=true;break;
                        }
                    }
                    if(!authorized||!fgSearch().contains(root,documentId))
                        throw new java.io.IOException("Indexed file is no longer accessible. Reauthorize the folder or refresh its index.");
                    Uri file=android.provider.DocumentsContract.buildDocumentUriUsingTree(
                        root,documentId);
                    runOnUiThread(()->openUri(file));
                }catch(Exception e){
                    runOnUiThread(()->js("window.showError("+q(message(e))+")"));
                }
            });
        }
'''
s=one(s,anchor,bridge+anchor,"native JS search bridge")
java.write_text(s,encoding="utf-8")

lib=base/"assets/premium-library.js"
js=lib.read_text(encoding="utf-8")
js=one(js,"search.type='search';search.placeholder='Search your books';",
       "search.type='search';search.placeholder='Search all folders';",
       "search placeholder")

js=one(js,"let cloudMode=false;",
r'''let cloudMode=false;
// Search local SAF metadata using persistent native SQLite, never the current
// folder's streamed in-memory list. Cloud browsing is left unchanged.
let indexedResults=[],indexedMore=false,indexedOffset=0,indexedPending=false;
let indexedCount=0,indexedBuilding=false,indexedError='';
let indexedToken=0,indexedTimer=0,indexedRefreshTimer=0;
const indexedRefresh=b('↻','fg-lib-icon',()=>{
  if(cloudMode)return;
  indexedPending=true;indexedError='';
  bridge()?.refreshLibraryIndex?.();
  render();
});
indexedRefresh.title='Refresh the saved file index';
indexedRefresh.setAttribute('aria-label','Refresh search index');
indexedRefresh.hidden=true;
toolbar.append(indexedRefresh);
function localIndexedMode(){return !cloudMode&&!!phrase.trim();}
function scheduleIndexSearch(offset=0,delay=140){
  if(indexedTimer)clearTimeout(indexedTimer);
  indexedOffset=Math.max(0,offset);
  indexedPending=true;
  const token=++indexedToken;
  indexedTimer=setTimeout(()=>{
    indexedTimer=0;
    if(!localIndexedMode()||token!==indexedToken)return;
    bridge()?.searchLibraryIndex?.(phrase,filter,indexedOffset,token);
  },delay);
}
function renderIndexedResults(){
  if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
  root.querySelectorAll('.fg-lib-pager').forEach(n=>n.remove());
  deck.className='fg-lib-grid'+(list?' fg-lib-list':'')+
      (filter==='video'?' fg-lib-video-grid':'');
  retainedCards.clear();lastVisibleKeys='';
  // Search-result pages are separate from the cached, image-rich folder grid.
  deck.replaceChildren();
  empty.replaceChildren();
  indexedResults.forEach((item,i)=>deck.appendChild(card(item,indexedOffset+i)));
  loading.classList.add('fg-lib-hidden');
  deck.classList.remove('fg-lib-hidden');
  empty.classList.remove('fg-lib-hidden');
  indexedRefresh.hidden=false;
  const state=indexedBuilding?
    ' · indexing '+indexedCount.toLocaleString()+' items (partial results)':
    '';
  count.textContent=indexedResults.length?
    'Matches '+(indexedOffset+1)+'–'+(indexedOffset+indexedResults.length)+
      (indexedMore?'+':'')+state:
    (indexedPending?'Searching indexed files…':
     indexedBuilding?'Indexing '+indexedCount.toLocaleString()+' items…':
     'No indexed matches');
  if(indexedResults.length===0){
    empty.append(E('strong','',indexedPending?'Searching…':
      indexedError?'Search unavailable':
      indexedBuilding?'Indexing folders…':'No matching files'),
      E('p','',indexedError||(
        indexedBuilding?'The first scan runs once. Results appear as folders are indexed.':
        'Search includes all subfolders of the selected collection.')));
  }
  if(indexedResults.length && (indexedOffset>0||indexedMore)){
    const nav=E('nav','fg-lib-pager');
    const prev=b('‹ Previous','fg-lib-page-control',()=>{
      scheduleIndexSearch(Math.max(0,indexedOffset-96),0);body.scrollTop=0;
    });
    prev.disabled=indexedOffset===0;
    const next=b('Next ›','fg-lib-page-control',()=>{
      scheduleIndexSearch(indexedOffset+96,0);body.scrollTop=0;
    });
    next.disabled=!indexedMore;
    nav.append(prev,E('span','','Page '+(Math.floor(indexedOffset/96)+1)),next);
    deck.after(nav);
  }
}
function receiveIndexedSearch(data){
  if(!data||data.token!==indexedToken||!localIndexedMode())return;
  indexedPending=false;
  indexedResults=Array.isArray(data.items)?data.items:[];
  indexedMore=!!data.hasMore;
  indexedCount=Number(data.indexed)||0;
  indexedBuilding=!!data.building;
  indexedError=data.error||'';
  renderIndexedResults();
}
function indexProgress(data){
  if(!data||data.root!==bridge()?.getLibraryRoot?.())return;
  indexedCount=Number(data.indexed)||0;
  indexedBuilding=!!data.building;
  indexedError=data.error||'';
  if(!localIndexedMode()||!visible)return;
  if(indexedRefreshTimer)clearTimeout(indexedRefreshTimer);
  indexedRefreshTimer=setTimeout(()=>{
    indexedRefreshTimer=0;
    scheduleIndexSearch(indexedOffset,0);
  },900);
}
''',"indexed state/functions")

js=one(js,"function openBook(item){\n if(item.folder){",
r'''function openBook(item){
 if(item.indexedSearch&&!cloudMode){
   if(item.folder){
     stack.push(currentFolder);currentFolder=item.id;
     phrase='';search.value='';indexedToken++;
     indexedResults=[];indexedRefresh.hidden=true;
     request();return;
   }
   recordRecent(item);
   activeUri=item.uri;
   root.classList.add('fg-lib-hidden');visible=false;
   document.getElementById('home')?.classList.add('hidden');
   document.getElementById('work')?.classList.remove('hidden');
   bridge()?.openIndexedFile?.(item.id);
   return;
 }
 if(item.folder){''',"open indexed item")

js=one(js,"E('span','fg-lib-item-detail',formatSize(item.size)||",
       "E('span','fg-lib-item-detail',item.indexedSearch?(item.searchPath||'Collection root'):(formatSize(item.size)||",
       "search path metadata")
js=one(js,"(item.folder?'Open collection':'')));",
       "(item.folder?'Open collection':''))));",
       "close metadata ternary")

js=one(js,"""tile.addEventListener('contextmenu',event=>{
   event.preventDefault();showFileActions(item);
 });""",
       """tile.addEventListener('contextmenu',event=>{
   if(item.indexedSearch)return;
   event.preventDefault();showFileActions(item);
 });""",
       "disable indexed result context actions")
js=one(js,"if(e.pointerType==='touch' && !e.target.closest('.fg-lib-more')){",
       "if(!item.indexedSearch && e.pointerType==='touch' && !e.target.closest('.fg-lib-more')){",
       "disable indexed long press")

js=one(js,"function render(){\n if(renderTimer)",
       "function render(){\n if(localIndexedMode()){renderIndexedResults();return;}\n indexedRefresh.hidden=true;\n if(renderTimer)",
       "render search path")

js=one(js,"""const control=b(name,'fg-lib-filter'+(filter===key?' fg-lib-selected':''),
     ()=>{filter=key;pageStart=0;createFilters();render();});""",
       """const control=b(name,'fg-lib-filter'+(filter===key?' fg-lib-selected':''),
     ()=>{filter=key;pageStart=0;createFilters();
       if(localIndexedMode()){indexedResults=[];scheduleIndexSearch(0,0);}
       render();});""",
       "native category filters")

js=one(js,"function append(payload){\n if(!payload||!Array.isArray(payload.items))return;",
       """function append(payload){
 if(!payload||!Array.isArray(payload.items))return;
 if(localIndexedMode())return;""",
       "no per-batch filtering during indexed search")

js=one(js,"search.addEventListener('input',()=>{phrase=search.value;pageStart=0;render();});",
       """search.addEventListener('input',()=>{
 const old=localIndexedMode();
 phrase=search.value;pageStart=0;
 if(localIndexedMode()){
   if(!old){
     bridge()?.stopLibraryListing?.();
     entries=[];entryIds.clear();retainedCards.clear();lastVisibleKeys='';
   }
   indexedResults=[];indexedMore=false;indexedError='';
   scheduleIndexSearch(0,130);
 }else{
   indexedToken++;
   if(indexedTimer)clearTimeout(indexedTimer);
   indexedResults=[];indexedPending=false;
   if(old)request();else render();
 }
 render();
});""",
       "debounced indexed search handler")

js=one(js," openCollection:()=>{\n   currentFolder='';stack=[];show();",
       """  receiveIndexedSearch,indexProgress,
  openCollection:()=>{
    currentFolder='';stack=[];phrase='';search.value='';
    indexedToken++;indexedResults=[];indexedRefresh.hidden=true;show();""",
       "search response bridge")

# Set the correct caption depending on local or cloud browsing.
js=one(js," heading.textContent=cloudMode?'TeraBox':'Your library';",
       """  heading.textContent=cloudMode?'TeraBox':'Your library';
  search.placeholder=cloudMode?'Search current TeraBox folder':'Search all subfolders';""",
       "contextual search caption")

lib.write_text(js,encoding="utf-8")

css=base/"assets/style.css"
style=css.read_text(encoding="utf-8")
style+="""

/* v0.15.15 local indexed search: preserve existing library card/grid design. */
.fg-library-root .fg-lib-toolbar .fg-lib-icon[hidden]{display:none!important}
.fg-library-root .fg-lib-grid .fg-lib-tile .fg-lib-item-detail{
  overflow-wrap:anywhere;word-break:break-word
}
.fg-library-root .fg-lib-tile .fg-lib-more[hidden]{display:none!important}
"""
css.write_text(style,encoding="utf-8")

gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)36\b',r'\g<1>37',g,count=1)
assert n==1, "Expected last approved versionCode 36"
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.14"',r'\g<1>"0.15.15"',g,count=1)
assert n==1, "Expected last approved version 0.15.14"
gradle.write_text(g,encoding="utf-8")
print("Rounder v0.15.15: recursive indexed local search, resumable metadata, no query-time scans")

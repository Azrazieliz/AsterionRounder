#!/usr/bin/env python3
"""Scope v0.15.15 recursive search to TeraBox as well, without changing chosen UI.
TeraBox's existing folder-only filter must not masquerade as global search.
"""
from pathlib import Path
import re
base=Path("app/src/main")
java=base/"java/com/openlocal/office/MainActivity.java"
s=java.read_text(encoding="utf-8")
def once(src,old,new,label):
    n=src.count(old)
    if n!=1:raise AssertionError(f"{label}: expected 1 occurrence, found {n}: {old[:100]}")
    return src.replace(old,new,1)
s=once(s,"    private com.openlocal.office.core.FgSearchIndex fgSearchIndex;",
"""    private com.openlocal.office.core.FgTeraboxSearchIndex fgCloudIndex;
    private synchronized com.openlocal.office.core.FgTeraboxSearchIndex fgCloudIndex(){
        if(fgCloudIndex==null)
            fgCloudIndex=new com.openlocal.office.core.FgTeraboxSearchIndex(
                this,tb(),new com.openlocal.office.core.FgTeraboxSearchIndex.Listener(){
                    @Override public void onSearch(String json){
                        runOnUiThread(()->js(
                            "window.FileGestionerLibrary?.receiveIndexedSearch("+json+")"));
                    }
                    @Override public void onProgress(String json){
                        runOnUiThread(()->js(
                            "window.FileGestionerLibrary?.indexProgress("+json+")"));
                    }
                });
        return fgCloudIndex;
    }
    private com.openlocal.office.core.FgSearchIndex fgSearchIndex;""",
    "native TeraBox index field")
s=once(s,"        @JavascriptInterface public void searchLibraryIndex(",
"""        @JavascriptInterface public void startTeraboxIndex(){
            if(tb().configured())fgCloudIndex().ensure(false);
        }
        @JavascriptInterface public void searchTeraboxIndex(
                String needle,String category,int offset,int token){
            fgCloudIndex().search(needle,category,offset,token);
        }
        @JavascriptInterface public void refreshTeraboxIndex(){
            if(tb().configured())fgCloudIndex().ensure(true);
        }
        @JavascriptInterface public String getTeraboxSearchScope(){
            return tb().configured()?tb().metadataScope():"";
        }
        @JavascriptInterface public void stopTeraboxListing(){
            fgTbVersion.incrementAndGet();
        }
        @JavascriptInterface public void searchLibraryIndex(""",
    "native search API")
s=once(s,"        @JavascriptInterface public void disconnectTerabox(){\n             fgTbVersion.incrementAndGet();",
"""        @JavascriptInterface public void disconnectTerabox(){
             fgTbVersion.incrementAndGet();""",
    "disconnect API anchor") if False else s
s=once(s,"            tb().disconnect();",
        "            tb().disconnect();\n            fgCloudIndex().clear();",
        "clear stale account metadata on disconnect")
java.write_text(s,encoding="utf-8")
lib=base/"assets/premium-library.js"
j=lib.read_text(encoding="utf-8")
j=once(j,"function localIndexedMode(){return !cloudMode&&!!phrase.trim();}",
"""function localIndexedMode(){return !cloudMode&&!!phrase.trim();}
function cloudIndexedMode(){return cloudMode&&!!phrase.trim();}
function indexedMode(){return localIndexedMode()||cloudIndexedMode();}""",
    "cloud search scope")
j=once(j,"  if(cloudMode)return;\n  indexedPending=true;indexedError='';\n  bridge()?.refreshLibraryIndex?.();",
"""  indexedPending=true;indexedError='';
  if(cloudMode)bridge()?.refreshTeraboxIndex?.();
  else bridge()?.refreshLibraryIndex?.();""",
    "refresh button supports cloud")
j=once(j,"    if(!localIndexedMode()||token!==indexedToken)return;\n    bridge()?.searchLibraryIndex?.(phrase,filter,indexedOffset,token);",
"""    if(!indexedMode()||token!==indexedToken)return;
    if(cloudMode)bridge()?.searchTeraboxIndex?.(phrase,filter,indexedOffset,token);
    else bridge()?.searchLibraryIndex?.(phrase,filter,indexedOffset,token);""",
    "indexed query routing")
j=once(j,"  if(!data||data.token!==indexedToken||!localIndexedMode())return;",
"""  if(!data||data.token!==indexedToken||!indexedMode())return;
  if(cloudMode&&data.scope!==bridge()?.getTeraboxSearchScope?.())return;
  if(!cloudMode&&data.scope)return;""",
    "reject crossed account/search results")
j=once(j,"  if(!data||data.root!==bridge()?.getLibraryRoot?.())return;",
"""  if(!data)return;
  if(cloudMode){
    if(data.scope!==bridge()?.getTeraboxSearchScope?.())return;
  }else if(data.root!==bridge()?.getLibraryRoot?.())return;""",
    "cloud index progress")
j=once(j,"  if(!localIndexedMode()||!visible)return;",
        "  if(!indexedMode()||!visible)return;",
        "progress route")
j=once(j,"function openBook(item){\n if(item.indexedSearch&&!cloudMode){",
"""function openBook(item){
 if(item.indexedSearch&&cloudMode){
   if(item.folder){
     stack.push(currentFolder);currentFolder=item.path;
     phrase='';search.value='';indexedToken++;
     indexedResults=[];indexedRefresh.hidden=true;
     request();return;
   }
   recordRecent(item);activeUri=item.uri;
   root.classList.add('fg-lib-hidden');visible=false;
   document.getElementById('home')?.classList.add('hidden');
   document.getElementById('work')?.classList.remove('hidden');
   // Search can return a file in any subfolder. Do not use the current
   // folder's image-sibling array when opening it.
   bridge()?.openTeraboxFile?.(item.path,item.name);
   return;
 }
 if(item.indexedSearch&&!cloudMode){""",
    "open cloud indexed files/directories")
j=once(j,"function render(){\n if(localIndexedMode()){renderIndexedResults();return;}",
        "function render(){\n if(indexedMode()){renderIndexedResults();return;}",
        "render cloud search")
j=once(j,"       if(localIndexedMode()){indexedResults=[];scheduleIndexSearch(0,0);}",
        "       if(indexedMode()){indexedResults=[];scheduleIndexSearch(0,0);}",
        "filtered cloud search")
j=once(j,"  if(cloudMode)bridge()?.listTerabox?.(currentFolder||'');",
"""  if(cloudMode){
    bridge()?.startTeraboxIndex?.();
    bridge()?.listTerabox?.(currentFolder||'');
  }""",
    "warm index outside search input")
j=once(j," if(localIndexedMode())return;",
        " if(indexedMode())return;",
        "no folder enumeration while indexed search")
j=once(j," const old=localIndexedMode();",
        " const old=indexedMode();",
        "search typing route")
j=once(j," if(localIndexedMode()){\n   if(!old){\n     bridge()?.stopLibraryListing?.();",
""" if(indexedMode()){
   if(!old){
     if(cloudMode)bridge()?.stopTeraboxListing?.();
     else bridge()?.stopLibraryListing?.();""",
    "cancel full current-folder scan")
j=once(j,"search.placeholder=cloudMode?'Search current TeraBox folder':'Search all subfolders';",
        "search.placeholder=cloudMode?'Search all TeraBox folders':'Search all subfolders';",
        "honest search scope")
lib.write_text(j,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)37\b',r'\g<1>38',g,count=1)
assert n==1,"Expected v0.15.15 code 37"
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.15"',r'\g<1>"0.15.16"',g,count=1)
assert n==1,"Expected v0.15.15 release string"
gradle.write_text(g,encoding="utf-8")
print("Rounder 0.15.16: persistent TeraBox account-scoped recursive search, local search preserved")

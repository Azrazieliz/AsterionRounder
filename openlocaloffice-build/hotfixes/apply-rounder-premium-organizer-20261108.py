#!/usr/bin/env python3
"""Rounder 0.15.17 — Atlas x Obsidian cloud vault and deterministic organizer.
Run after all 0.15.16 hotfixes. Existing player/reader/native storage untouched.
"""
from pathlib import Path
import re
base=Path("app/src/main")
def replace_once(src,old,new,reason):
    n=src.count(old)
    if n!=1:
        raise AssertionError(f"{reason}: expected 1 occurrence, found {n}: {old[:100]}")
    return src.replace(old,new,1)

# Native: review, duplicates, incoming refresh, preview, apply, and opt-in jobs.
main=base/"java/com/openlocal/office/MainActivity.java"
s=main.read_text(encoding="utf-8")
s=replace_once(s,"    private com.openlocal.office.core.FgSearchIndex fgSearchIndex;",
r'''    private volatile com.openlocal.office.core.FgRounderOrganizer fgOrganizer;
    private synchronized com.openlocal.office.core.FgRounderOrganizer fgOrganizer(){
        if(fgOrganizer==null)
            fgOrganizer=new com.openlocal.office.core.FgRounderOrganizer(
                this,tb(),fgCloudIndex());
        return fgOrganizer;
    }
    private com.openlocal.office.core.FgSearchIndex fgSearchIndex;''',
"organizer backend")
s=replace_once(s,"        @JavascriptInterface public void searchTeraboxIndex(",
r'''        @JavascriptInterface public void fetchTeraboxFolderPreviews(String folders){
            if(!tb().configured()||folders==null||folders.length()>3000)return;
            fgDirectoryExecutor.execute(()->{
                try{
                    org.json.JSONObject previews=fgCloudIndex().folderPreviews(
                        new org.json.JSONArray(folders));
                    String json=previews.toString();
                    runOnUiThread(()->js("window.FileGestionerLibrary?.folderPreviews("+json+")"));
                }catch(Exception e){
                    android.util.Log.w("FG_PREVIEW","Collection preview unavailable");
                }
            });
        }
        @JavascriptInterface public void organizerReview(){
            fgDirectoryExecutor.execute(()->{
                try{
                    String data=fgOrganizer().review().toString();
                    runOnUiThread(()->js("window.FileGestionerLibrary?.managerReview("+data+")"));
                }catch(Exception e){fgOrganizerFailure("review",e);}
            });
        }
        @JavascriptInterface public void organizerDuplicates(){
            fgDirectoryExecutor.execute(()->{
                try{
                    String data=fgOrganizer().duplicates().toString();
                    runOnUiThread(()->js("window.FileGestionerLibrary?.managerDuplicates("+data+")"));
                }catch(Exception e){fgOrganizerFailure("duplicates",e);}
            });
        }
        @JavascriptInterface public void organizerScan(){
            fgDirectoryExecutor.execute(()->{
                try{
                    String status=fgOrganizer().scanIncoming().toString();
                    runOnUiThread(()->{
                        js("window.FileGestionerLibrary?.managerScan("+status+")");
                        js("window.FileGestionerLibrary?.managerRefreshReview()");
                    });
                }catch(Exception e){fgOrganizerFailure("scan",e);}
            });
        }
        @JavascriptInterface public void organizerApply(String json){
            if(json==null||json.length()>16000)return;
            fgDirectoryExecutor.execute(()->{
                try{
                    fgOrganizer().apply(new org.json.JSONArray(json),event->
                        runOnUiThread(()->js("window.FileGestionerLibrary?.managerProgress("+event+")")));
                }catch(Exception e){fgOrganizerFailure("apply",e);}
            });
        }
        @JavascriptInterface public void organizerCleanupDuplicates(String json){
            if(json==null||json.length()>24000)return;
            fgDirectoryExecutor.execute(()->{
                try{
                    fgOrganizer().cleanupDuplicates(new org.json.JSONObject(json),event->
                        runOnUiThread(()->js(
                            "window.FileGestionerLibrary?.managerCleanupProgress("+event+")")));
                }catch(Exception e){fgOrganizerFailure("duplicates-cleanup",e);}
            });
        }
        @JavascriptInterface public void organizerStop(){
            fgOrganizer().stop();
        }
        @JavascriptInterface public void organizerConfigureSource(
                String id,String folder,boolean automatic){
            fgDirectoryExecutor.execute(()->{
                try{
                    fgOrganizer().configureSource(id,folder,automatic);
                    String data=fgOrganizer().review().toString();
                    runOnUiThread(()->{
                        js("window.FileGestionerLibrary?.managerReview("+data+")");
                        js("window.FileGestionerLibrary?.managerSourceSaved()");
                    });
                }catch(Exception e){fgOrganizerFailure("source",e);}
            });
        }
        @JavascriptInterface public void organizerAuto(boolean enable){
            if(!tb().configured())return;
            fgOrganizer().setAutoEnabled(enable);
            com.openlocal.office.core.FgRounderOrganizeJob.schedule(
                MainActivity.this,enable);
            final String reply=Boolean.toString(fgOrganizer().autoEnabled());
            runOnUiThread(()->js("window.FileGestionerLibrary?.managerAuto("+reply+")"));
        }
        private void fgOrganizerFailure(String phase,Exception error){
            android.util.Log.w("FG_ORGANIZER","Organizer "+phase+" unavailable",error);
            try{
                String data=new org.json.JSONObject().put("phase",phase)
                    .put("error",message(error)).toString();
                runOnUiThread(()->js("window.FileGestionerLibrary?.managerError("+data+")"));
            }catch(Exception ignored){}
        }
        @JavascriptInterface public void searchTeraboxIndex(''',"JS organizer APIs")
s=replace_once(s,"            fgCloudIndex().clear();",
'''            fgCloudIndex().clear();
            com.openlocal.office.core.FgRounderOrganizeJob.schedule(MainActivity.this,false);''',
"disable auto on cloud disconnect")
s=replace_once(s,'''        @JavascriptInterface public void startTeraboxIndex(){
            if(tb().configured())fgCloudIndex().ensure(false);
        }''',
'''        @JavascriptInterface public void startTeraboxIndex(){
            if(tb().configured()){
                fgCloudIndex().ensure(false);
                com.openlocal.office.core.FgRounderOrganizeJob.schedule(
                    MainActivity.this,fgOrganizer().autoEnabled());
            }
        }''',"restore opt-in jobs on app entry")
main.write_text(s,encoding="utf-8")

manifest=base/"AndroidManifest.xml"
m=manifest.read_text(encoding="utf-8")
assert "FgRounderOrganizeJob" not in m
m=replace_once(m,"</application>",
'''    <service android:name="com.openlocal.office.core.FgRounderOrganizeJob"
        android:exported="false"
        android:permission="android.permission.BIND_JOB_SERVICE" />
  </application>''',"jobservice manifest")
manifest.write_text(m,encoding="utf-8")

# Premium UI: cloud-first, compact legitimate folders, actual source previews.
lib=base/"assets/premium-library.js"
j=lib.read_text(encoding="utf-8")
j=replace_once(j,"actions.append(openBtn,collectionBtn,tbBtn);header.append(brand,actions);",
'''const organizeBtn=b('Organize','fg-lib-secondary fg-premium-organize',()=>showOrganizer());
const settingsBtn=b('⋯','fg-lib-icon fg-premium-settings',()=>showTeraboxSettings());
settingsBtn.setAttribute('aria-label','TeraBox connection settings');
actions.append(openBtn,organizeBtn,settingsBtn);
header.append(brand,actions);''',"cloud-only header actions")
j=replace_once(j,"let cloudMode=false;","let cloudMode=true;","cloud mode as default")
premium_intro="""const premiumIntro=E('section','fg-premium-intro');
const premiumEyebrow=E('span','fg-premium-eyebrow','ASTERION CLOUD');
const premiumTitle=E('h1','fg-premium-title','Your collection');
const premiumSummary=E('p','fg-premium-summary',
  'Browse your TeraBox library, keep reading, and discover your files.');
premiumIntro.append(premiumEyebrow,premiumTitle,premiumSummary);
"""
j=replace_once(j,"const footer=E('div','fg-lib-footer',",
  premium_intro+"const footer=E('div','fg-lib-footer',","premium hero declare")
j=replace_once(j,"body.append(toolbar,filters,loading,deck,empty,footer);",
'''body.append(premiumIntro,toolbar,filters,loading,deck,empty,footer);''',"premium home placement")
j=replace_once(j,"const entryIds=new Set();",
'''const entryIds=new Set();
const folderPreviewCache=new Map();
const requestedFolderPreviews=new Set();
let managerPanel=null,managerView='moves',managerData=null,managerDupeData=null;
const managerSelected=new Set();
let managerRunning=false,managerMessage='';''',
"manager and mosaic state")
j=replace_once(j," const c=classify(item),tile=E('article','fg-lib-tile fg-lib-'+c);",
''' const c=classify(item),tile=E('article','fg-lib-tile fg-lib-'+c+
   (item.folder?' fg-premium-folder':' fg-premium-media'));
 if(item.folder&&item.path)tile.dataset.folderPath=item.path;''',"content-aware cards")
j=replace_once(j," cover.appendChild(fallback);",
''' cover.appendChild(fallback);
 if(item.folder&&item.path){
   const mosaic=folderPreviewCache.get(item.path);
   if(mosaic?.length){
     const rail=E('div','fg-premium-mosaic');
     for(const src of mosaic.slice(0,3)){
       const im=E('img','fg-premium-mosaic-image');
       im.alt='';im.loading='lazy';im.decoding='async';
       im.src=src;rail.append(im);
     }
     cover.append(rail);
     cover.classList.add('fg-premium-cover-ready');
   }
 }''',"actual thumbnail mosaic")
j=replace_once(j," tile.append(cover,meta);",
''' tile.append(cover,meta);
 if(item.folder){
   const detail=meta.querySelector('.fg-lib-item-detail');
   if(detail)detail.textContent='Open collection';
 }''',"no misleading folder size")
j=replace_once(j,"function render(){\n if(indexedMode())",
'''function render(){
 premiumIntro.hidden=!!currentFolder||!!phrase.trim()||!cloudMode;
 if(indexedMode())''',"premium root visibility")
j=replace_once(j,"function append(payload){\n if(!payload||!Array.isArray(payload.items))return;",
'''function append(payload){
 if(!payload||!Array.isArray(payload.items))return;
 if(cloudMode&&!currentFolder&&!phrase.trim()){
   const pending=payload.items.filter(x=>x.folder&&x.path&&!requestedFolderPreviews.has(x.path))
     .slice(0,24).map(x=>x.path);
   if(pending.length){
     pending.forEach(p=>requestedFolderPreviews.add(p));
     bridge()?.fetchTeraboxFolderPreviews?.(JSON.stringify(pending));
   }
 }''',"query preview images for actual indexed folders")
j=replace_once(j,"function indexProgress(data){",
'''function indexProgress(data){
 if(data&&!data.building&&cloudMode&&!currentFolder&&visible){
   const folders=entries.filter(x=>x.folder&&x.path).slice(0,24).map(x=>x.path);
   if(folders.length)bridge()?.fetchTeraboxFolderPreviews?.(JSON.stringify(folders));
 }''',"refresh thumbnails after initial index")
# Display preview only from actual native cover proxy. Do not synthesize imagery.
j=replace_once(j,"function handleAndroidBack(){",
'''function folderPreviews(data){
 if(!data||typeof data!=='object')return;
 let changed=false;
 for(const [path,images] of Object.entries(data)){
   if(!Array.isArray(images))continue;
   const valid=images.filter(v=>typeof v==='string'&&
     v.startsWith('https://fg-assets.invalid/tb-cover/')).slice(0,3);
   if(valid.length){folderPreviewCache.set(path,valid);changed=true;}
 }
 if(changed&&visible&&!phrase.trim())render();
}
function handleAndroidBack(){''',"real preview callback")
j=replace_once(j," if(operationDialog){closeFileActions();return true;}",
''' if(managerPanel){closeOrganizer();return true;}
 if(operationDialog){closeFileActions();return true;}''',"back dismisses manager")
j=replace_once(j,"window.FileGestionerLibrary={",
'''window.FileGestionerLibrary={
 folderPreviews,managerReview,managerDuplicates,managerProgress,managerScan,
 managerAuto,managerError,managerRefreshReview,managerSourceSaved,managerCleanupProgress,''',"manager callback exports")
# Because manager body declared later as hoisted functions, safe to expose.
j=replace_once(j," if(bridge()?.getTeraboxConfigured?.())show();",
                 " if(bridge()?.getTeraboxConfigured?.())show();",
                 "preserve connection condition") if False else j
j=replace_once(j,"  heading.textContent=cloudMode?'TeraBox':'Your library';",
'''  heading.textContent=cloudMode?(currentFolder?'Collection':'TeraBox'):'Your library';''',
"cloud title")

lib.write_text(j,encoding="utf-8")
print("ROUNDER_PREMIUM_CORE_UI_PATCHED")

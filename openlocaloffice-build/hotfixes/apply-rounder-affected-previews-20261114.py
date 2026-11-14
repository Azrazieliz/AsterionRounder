#!/usr/bin/env python3
"""Add an evidence-based affected-preview filter after the original-image
thumbnail stage. Never fetch a prohibited TeraBox preview to display a card.
Keep approved cards, scroll virtualization, identity, readers and files intact.
"""
from pathlib import Path

root=Path("app/src/main")
native=root/"java/com/openlocal/office/MainActivity.java"
s=native.read_text(encoding="utf-8")

def once(text,old,new,reason):
    n=text.count(old)
    if n!=1:
        raise AssertionError(f"{reason}: expected one anchor, found {n}")
    return text.replace(old,new,1)

# Existing TeraBox listing keeps provider metadata and enriches it with the
# user's private, account-scoped review flags in one SQLite lookup per page.
start=s.index("    private void listTeraboxNative(")
stop=s.index("    private void ",start+15)
listing=s[start:stop]
listing=once(listing,
    "org.json.JSONArray batch=new org.json.JSONArray();",
    """org.json.JSONArray batch=new org.json.JSONArray();
                    java.util.Set<String> reviewed=fgCloudIndex().markedForPage(cloud);""",
    "batch preview-flag query")
listing=once(listing,
    'String path=mapped.optString("path","");',
    """String path=mapped.optString("path","");
                            mapped.put("previewManuallyMarked",reviewed.contains(path));""",
    "annotate original image entries")
s=s[:start]+listing+s[stop:]

anchor="        @JavascriptInterface public void searchTeraboxIndex("
assert s.count(anchor)==1, "Expected live cloud search bridge"
s=s.replace(anchor,'''        @JavascriptInterface public void markTeraboxPreview(String path,boolean affected){
            if(path==null||path.length()>8192||!path.startsWith("/")||
               !com.openlocal.office.core.FgTeraboxClient.image(path))return;
            final String requestedScope=tb().metadataScope();
            fgDirectoryExecutor.execute(()->{
                boolean ok=false;
                String error="";
                try{
                    if(requestedScope.isEmpty()||
                       !requestedScope.equals(tb().metadataScope()))
                        throw new IOException("TeraBox account changed");
                    fgCloudIndex().markPreview(path,affected);
                    ok=true;
                }catch(Exception failure){
                    error=failure.getClass().getSimpleName();
                    android.util.Log.w("FG_PREVIEW_FILTER","Flag update rejected",failure);
                }
                try{
                    org.json.JSONObject response=new org.json.JSONObject()
                        .put("scope",requestedScope).put("path",path)
                        .put("marked",affected).put("ok",ok).put("error",error);
                    String json=response.toString();
                    runOnUiThread(()->js(
                        "window.FileGestionerLibrary?.previewMarkResult("+json+")"));
                }catch(Exception ignored){}
            });
        }
'''+anchor,1)
native.write_text(s,encoding="utf-8")

# The TeraBox filter is global over the *persisted metadata index*. A file
# qualifies only when the provider supplies no HTTPS thumbnail OR the owner
# explicitly marked its server preview as a restricted/placeholder result.
lib=root/"assets/premium-library.js"
j=lib.read_text(encoding="utf-8")
j=once(j,"['all','All files'],['image','Images'],",
       "['all','All files'],['image','Images'],['affected','Affected previews'],",
       "category chip")
j=once(j,"function cloudIndexedMode(){return cloudMode&&!!phrase.trim();}",
       "function cloudIndexedMode(){return cloudMode&&(!!phrase.trim()||filter==='affected');}",
       "affected global index routing")
j=once(j,"for(const [key,name] of categories){",
       "for(const [key,name] of categories){\n    if(key==='affected'&&!cloudMode)continue;",
       "TeraBox-only category")
# Keep the approved filter row, and use one indexed-result path for both
# normal search and the newly added affected-preview category.
start=j.index("function createFilters(){")
end=j.index("function request(){",start)
original=j[start:end]
assert "filters.replaceChildren();" in original
assert "const control=b(name,'fg-lib-filter'" in original
assert "filters.append(control);" in original
j=j[:start]+"""function createFilters(){
 filters.replaceChildren();
 for(const [key,name] of categories){
   if(key==='affected'&&!cloudMode)continue;
   const control=b(name,'fg-lib-filter'+(filter===key?' fg-lib-selected':''),
     ()=>{
       const wasAffected=filter==='affected';
       filter=key;pageStart=0;createFilters();
       if(indexedMode()){
         if(cloudMode&&!wasAffected&&filter==='affected')
           bridge()?.stopTeraboxListing?.();
         indexedResults=[];indexedMore=false;indexedError='';
         scheduleIndexSearch(0,0);
         render();
       }else if(cloudMode&&wasAffected&&!phrase.trim()){
         indexedToken++;
         request();
       }else render();
     });
   filters.append(control);
 }
}
""" + j[end:]
# A narrow non-obstructing indicator: approved original tiles and covers stay
# unmodified. Details explain what evidence was observed.
j=once(j,
    "tile.setAttribute('role','button');tile.setAttribute('tabindex','0');",
    """tile.setAttribute('role','button');tile.setAttribute('tabindex','0');
 if(cloudMode&&c==='image'&&(item.previewUnavailable||item.previewManuallyMarked)){
   tile.classList.add('fg-preview-affected');
   tile.title=item.previewUnavailable?
     'TeraBox supplied no usable preview; Rounder displays the original':
     'Preview flagged by owner; Rounder displays the original';
 }""",
    "visible item issue status")
# No cloud file is altered; only a private account/path marker changes.
start=j.index("function showFileActions(item){")
terabox=j.index("if(item.terabox){",start)
close=j.index("fileAction(sheet,'Close','',closeFileActions);",terabox)
# Place the reviewed flag beside the existing native cloud-file actions.
# Do not rebuild the sheet, modify its other commands, or touch local files.
j=j[:close]+"""if(!item.folder&&classify(item)==='image')
      fileAction(sheet,item.previewManuallyMarked?
          'Remove affected-preview flag':'Flag affected preview',
        'Use when TeraBox substitutes a placeholder despite providing a preview URL. Only private Rounder metadata changes.',
        ()=>{closeFileActions();bridge()?.markTeraboxPreview?.(
            item.path,!item.previewManuallyMarked);});
    """+j[close:]
# Native acknowledgement, not optimistic UI state: on failure show an error,
# on success reconcile the current folder and global indexed results.
j=once(j,"function handleAndroidBack(){",'''function previewMarkResult(data){
 if(!data||data.scope!==bridge()?.getTeraboxSearchScope?.())return;
 const ok=!!data.ok;
 if(ok){
   for(const item of entries.concat(indexedResults||[]))
     if(item.path===data.path)item.previewManuallyMarked=!!data.marked;
   catalogRevision++;indexedRevision=-1;virtualLastSig='';
   if(indexedMode()){
     indexedResults=[];scheduleIndexSearch(0,0);
   }else render();
 }
 const toast=E('div','fg-file-toast',ok?
    (data.marked?'Affected preview flagged':'Preview flag removed'):
    ('Could not save preview flag: '+(data.error||'unknown error')));
 toast.setAttribute('role','status');
 document.body.append(toast);
 setTimeout(()=>toast.remove(),4500);
}
function handleAndroidBack(){''',
    "real acknowledgment callback")
j=once(j,"window.FileGestionerLibrary={",
       "window.FileGestionerLibrary={\n previewMarkResult,",
       "expose callback")
lib.write_text(j,encoding="utf-8")
css=root/"assets/style.css"
css.write_text(css.read_text(encoding="utf-8")+"""
/* One unobtrusive status dot; preserve existing card geometry and cover art. */
.fg-library-root .fg-preview-affected .fg-lib-item-title::after {
  content:" ●";color:#d5ad7e;font-size:11px;
}
""",encoding="utf-8")
print("ROUNDER_AFFECTED_PREVIEWS_READY: global filter, provider evidence, reviewed placeholders, no cloud mutation")

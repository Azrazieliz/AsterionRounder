#!/usr/bin/env python3
"""Fix first-page reader handoff discovered by physical Android 17 testing."""
from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
old='''        fgFolderPageMap.clear();
        fgImageCollectionCount.set(0);
        fgSelectedCollectionImage=startUri;
        fgImageCollectionActive=true;
        fgVerifiedKoikatsuCard=null;
        checkCollectionKoikatsu(Uri.parse(startUri));
        runOnUiThread(()->js("window.loadDocument({\\\"type\\\":\\\"folderImages\\\","+
            "\\\"name\\\":\\\"Image collection\\\",\\\"pages\\\":[]})"));'''
if s.count(old)!=1:raise RuntimeError("Missing native initial page anchor: "+str(s.count(old)))
new='''        fgFolderPageMap.clear();
        // The selected image must appear immediately, independently of
        // expensive sibling enumeration, sorting, or JS callback scheduling.
        Uri first=Uri.parse(startUri);
        String firstName=displayName(first);
        if(firstName==null||firstName.isBlank())firstName="Image";
        fgFolderPageMap.put(0,new FolderPage(first,firstName));
        fgImageCollectionCount.set(1);
        fgSelectedCollectionImage=startUri;
        fgImageCollectionActive=true;
        fgVerifiedKoikatsuCard=null;
        checkCollectionKoikatsu(first);
        try{
            String initial=new org.json.JSONObject()
                .put("type","folderImages").put("name","Image collection")
                .put("pages",new org.json.JSONArray().put(new org.json.JSONObject()
                    .put("name",firstName).put("selected",true)
                    .put("url","https://fg-assets.invalid/folder-img/"+fgFolderToken+"/0")))
                .toString();
            android.util.Log.i("FG_IMAGE","INITIAL_LOCAL_PAGE_READY");
            runOnUiThread(()->js("window.loadDocument("+initial+")"));
        }catch(org.json.JSONException error){
            android.util.Log.e("FG_IMAGE","Cannot initialize image reader",error);
        }'''
s=s.replace(old,new,1)
old='''                if(value.isEmpty()||name.isEmpty()||!allowedLibraryUris.contains(value))
                    continue;'''
assert s.count(old)==1
s=s.replace(old,'''                if(value.isEmpty()||name.isEmpty()||!allowedLibraryUris.contains(value))
                    continue;
                // Initial selected page is already in the view at index zero.
                if(value.equals(fgSelectedCollectionImage))continue;''',1)
main.write_text(s)
css=Path("app/src/main/assets/style.css")
c=css.read_text()
c+="""
/* Actual 360dp Android testing: prevent Asterion brand/header controls overlap. */
@media(max-width:600px){
  .fg-lib-header{flex-direction:column!important;align-items:stretch!important;
    gap:9px!important;padding:12px 13px!important;
    padding-top:calc(12px + env(safe-area-inset-top))!important}
  .fg-lib-brand{min-width:0;width:100%;flex-shrink:0}
  .fg-lib-brand-title{font-size:18px;line-height:1.14}
  .fg-lib-brand-subtitle{font-size:9px;white-space:normal}
  .fg-lib-actions{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;
    width:100%;min-width:0;gap:8px}
  .fg-lib-actions button{min-width:0;max-width:100%;padding:10px 3px!important;
    font-size:12px!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .fg-lib-monogram{width:38px;height:38px;flex:0 0 38px}
}
"""
css.write_text(c)
gradle=Path("app/build.gradle.kts")
if not gradle.exists():gradle=Path("app/build.gradle")
g=gradle.read_text()
assert "versionCode = 14" in g or "versionCode 14" in g
assert "0.14.2" in g
import re
g=re.sub(r'(\bversionCode\s*(?:=\s*)?)14\b',r'\g<1>15',g,count=1)
g=g.replace("0.14.2","0.14.3",1)
gradle.write_text(g)
print("Asterion v0.14.3: immediate local page + no duplicate + responsive header")

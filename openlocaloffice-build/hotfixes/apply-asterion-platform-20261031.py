#!/usr/bin/env python3
"""Asterion Files: SAF TeraBox provider, true open-in-place and premium branding.
Applied after existing File Gestioner reader patches; no package/certificate changes.
"""
from pathlib import Path
import re
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text(encoding="utf-8")
anchor='        @JavascriptInterface public void saveTeraboxFile(String path,String name){'
assert s.count(anchor)==1, "Expected direct-TeraBox bridge"
s=s.replace(anchor,'''        @JavascriptInterface public void openTeraboxFile(String path,String name){
            if(path==null||!path.startsWith("/")||name==null||name.isBlank())return;
            // The native reader receives a seekable SAF content URI, never a
            // download destination or an export into the app's cache.
            final Uri document=com.openlocal.office.core.FgTeraboxDocumentsProvider.uriFor(path);
            runOnUiThread(()->openUri(document));
        }
'''+anchor,1)
# Cloud covers first use server-provided small thumbnails. For office/archives
# that lack thumbnails, use the same bounded native ReaderCovers pipeline.
needle='''        try{return new WebResourceResponse("image/jpeg",null,tb().openThumbnail(path));}
        catch(Exception problem){'''
assert s.count(needle)==1
s=s.replace(needle,'''        try{return new WebResourceResponse("image/jpeg",null,tb().openThumbnail(path));}
        catch(Exception noServerPreview){
            try{
                String lower=path.toLowerCase(java.util.Locale.ROOT);
                if(lower.endsWith(".pdf")||lower.endsWith(".epub")||
                   lower.endsWith(".cbz")||lower.endsWith(".zip")){
                    org.json.JSONObject meta=tb().fileDetails(path);
                    Uri cloud=com.openlocal.office.core.FgTeraboxDocumentsProvider.uriFor(path);
                    return new WebResourceResponse("image/jpeg",null,
                        ReaderCovers.open(this,cloud,path,meta.optLong("size",-1),
                            meta.optLong("server_mtime",0)*1000L));
                }
            }catch(Exception notSeekable){
                android.util.Log.i("FG_TERA","Cover range access unavailable");
            }
            // Do not download a whole cloud book just to make a cover.
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
        /* dead-code guard removed with dedicated preview fallback */ /*
        catch(Exception problem){''',1)
# Remove obsolete catch body after replacing with new branch.
start=s.index('        /* dead-code guard removed with dedicated preview fallback */ /*')
stop=s.index('    private WebResourceResponse fgTbImage(', start)
s=s[:start]+'''    }
'''+s[stop:]
# Supply thumbnail URLs for all formats the server might preview.
old='''if(!mapped.optBoolean("folder")&&
                               com.openlocal.office.core.FgTeraboxClient.image(mapped.optString("name",""))){'''
assert s.count(old)==1
s=s.replace(old,'''if(!mapped.optBoolean("folder")){''',1)
main.write_text(s,encoding="utf-8")
# Export provider through Android DocumentsUI without exposing credentials.
manifest=Path("app/src/main/AndroidManifest.xml")
m=manifest.read_text(encoding="utf-8")
assert 'com.openlocal.office.core.FgTeraboxDocumentsProvider' not in m
anchor='</application>'
assert m.count(anchor)==1
m=m.replace(anchor,'''    <provider
        android:name="com.openlocal.office.core.FgTeraboxDocumentsProvider"
        android:authorities="com.openlocal.office.terabox.documents"
        android:exported="true"
        android:grantUriPermissions="true"
        android:permission="android.permission.MANAGE_DOCUMENTS">
        <intent-filter>
            <action android:name="android.content.action.DOCUMENTS_PROVIDER" />
        </intent-filter>
    </provider>
'''+anchor,1)
manifest.write_text(m,encoding="utf-8")
# Open TeraBox files in their reader rather than invoking Save Document.
js=Path("app/src/main/assets/premium-library.js")
j=js.read_text(encoding="utf-8")
old='''    bridge()?.saveTeraboxFile?.(item.path,item.name);'''
assert j.count(old)==1,("Cloud open anchor changed",j.count(old))
j=j.replace(old,'''    bridge()?.openTeraboxFile?.(item.path,item.name);''',1)
# Use efficient first-frame opening for huge image collections:
# build/sort the sibling index after the viewer is already shown.
for cloud in (True,False):
    if cloud:
        old='''    const siblings=entries.filter(x=>!x.folder&&x.terabox&&classify(x)==='image')
      .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
    const version=++imagePumpVersion;
    imagePumpState={version,siblings,offset:0,started:false,live:scanning,
      folder:currentFolder,paused:false,feed:null,terabox:true};
    bridge().beginTeraboxImageCollection(item.path,item.name);'''
        new='''    const version=++imagePumpVersion;
    const state={version,siblings:[],offset:0,started:false,live:scanning,
      folder:currentFolder,paused:false,feed:null,terabox:true,preparing:true};
    imagePumpState=state;
    bridge().beginTeraboxImageCollection(item.path,item.name);
    setTimeout(()=>{
      if(imagePumpState!==state)return;
      state.siblings=entries.filter(x=>!x.folder&&x.terabox&&classify(x)==='image')
        .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
      state.preparing=false;
      state.feed?.();
    },16);'''
    else:
        old='''    const siblings=entries.filter(x=>!x.folder&&classify(x)==='image')
      .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
    const version=++imagePumpVersion;
    imagePumpState={version,siblings,offset:0,started:false,live:scanning,folder:currentFolder,paused:false,feed:null};
    // Native loads the viewer first. It notifies us after installing the
    // image-reader callback, so no early Round Sync batch can be lost.
    bridge().beginImageCollection(item.uri);'''
        new='''    const version=++imagePumpVersion;
    const state={version,siblings:[],offset:0,started:false,live:scanning,
      folder:currentFolder,paused:false,feed:null,preparing:true};
    imagePumpState=state;
    bridge().beginImageCollection(item.uri);
    setTimeout(()=>{
      if(imagePumpState!==state)return;
      state.siblings=entries.filter(x=>!x.folder&&classify(x)==='image')
        .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
      state.preparing=false;
      state.feed?.();
    },16);'''
    assert j.count(old)==1, ("Image opening anchor",cloud,j.count(old))
    j=j.replace(old,new,1)
old='''     if(imagePumpState!==state||imagePumpVersion!==state.version)return;
     if(state.offset>=state.siblings.length){'''
new='''     if(imagePumpState!==state||imagePumpVersion!==state.version)return;
     if(state.preparing)return;
     if(state.offset>=state.siblings.length){'''
assert j.count(old)==1
j=j.replace(old,new,1)
# Asterion identity throughout the file-management UI.
j=j.replace("'File Gestioner'","'Asterion Files'")
j=j.replace("'YOUR PRIVATE LIBRARY'","'ASTERION · FILE PLATFORM'")
j=j.replace("'FG'","'✦'")
j=j.replace("'OFFLINE READING'","'LOCAL · CLOUD · CONNECTED'")
j=j.replace("'Your files. Your control.'","'Everything in one place.'")
j=j.replace("'Browse local and connected storage. Files remain on their original provider.'",
            "'Open and explore your local and TeraBox files without importing them first.'")
j=j.replace("'YOUR FILES · LOCAL & CONNECTED STORAGE'","'ASTERION FILES · LOCAL & TERABOX'")
j=j.replace("tbBtn.title='Native cloud browsing — no RoundSync required';",
            "tbBtn.title='Secure native TeraBox storage';")
js.write_text(j,encoding="utf-8")
# Preserve installed certificate and package ID, advance version for update-in-place.
gradle=Path("app/build.gradle.kts")
if not gradle.exists():gradle=Path("app/build.gradle")
g=gradle.read_text()
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)13\b',r'\g<1>14',g,count=1)
assert n==1
g,n=re.subn(r'\bversionName\s*(?:=\s*)?["\']0\.14\.1["\']',
            'versionName = "0.14.2"' if gradle.suffix==".kts" else 'versionName "0.14.2"',g,count=1)
assert n==1
gradle.write_text(g)
strings=Path("app/src/main/res/values/strings.xml")
v=strings.read_text()
v,n=re.subn(r'<string name="app_name">.*?</string>',
            '<string name="app_name">Asterion Files</string>',v,count=1)
assert n==1
strings.write_text(v)
index=Path("app/src/main/assets/index.html")
html=index.read_text(encoding="utf-8")
html=html.replace("File Gestioner","Asterion Files").replace("OpenLocal Office","Asterion Files")
index.write_text(html,encoding="utf-8")
print("Asterion SAF platform, cloud open, fast image setup, UI name and versionCode 14 applied")

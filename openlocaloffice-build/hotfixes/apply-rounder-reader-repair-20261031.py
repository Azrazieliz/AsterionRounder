#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('app/src/main')
main=root/'java/com/openlocal/office/MainActivity.java'
s=main.read_text()
anchor='''        @JavascriptInterface public void openTeraboxFile(String path,String name){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        // Video playlists are metadata from the currently visible folder only.
        // Credentials and signed cloud links are never passed through JS.
        @JavascriptInterface public void setVideoQueue(String json){
            if(json==null||json.length()>280000)return;
            try{
                org.json.JSONObject object=new org.json.JSONObject(json);
                org.json.JSONArray entries=object.optJSONArray("entries");
                if(entries==null)return;
                java.util.ArrayList<RounderVideo> parsed=new java.util.ArrayList<>();
                for(int i=0;i<entries.length()&&parsed.size()<1500;i++){
                    org.json.JSONObject item=entries.optJSONObject(i);
                    if(item==null)continue;
                    String name=item.optString("name","");
                    String uriText=item.optString("uri","");
                    String path=item.optString("path","");
                    Uri uri;
                    String key;
                    if(path.startsWith("/")){
                        long size=item.optLong("size",-1);
                        uri=com.openlocal.office.core.FgTeraboxDocumentsProvider.uriFor(path,size);
                        key=path;
                    }else{
                        if(!allowedLibraryUris.contains(uriText))continue;
                        uri=Uri.parse(uriText);key=uriText;
                    }
                    if(!name.toLowerCase(java.util.Locale.ROOT).matches(
                        ".*\\\\.(mp4|webm|mkv|mov|avi)$"))continue;
                    parsed.add(new RounderVideo(uri,name,key));
                }
                fgVideoQueue=java.util.Collections.unmodifiableList(parsed);
            }catch(Exception ex){
                android.util.Log.w("FG_MEDIA","Video playlist metadata rejected");
            }
        }
'''+anchor,1)
anchor='''    private com.openlocal.office.core.FgMediaPlayer fgMediaSession;
    private void showFgMedia(Uri uri,String name,boolean video){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''    private static final class RounderVideo {
        final Uri uri;
        final String name,key;
        RounderVideo(Uri uri,String name,String key){
        this.uri=uri;this.name=name;this.key=key;
        }
    }
    private volatile java.util.List<RounderVideo> fgVideoQueue=
        java.util.Collections.emptyList();
    private com.openlocal.office.core.FgMediaPlayer fgMediaSession;
    private String fgVideoKey(Uri uri){
        if(uri==null)return "";
        try{
            if(com.openlocal.office.core.FgTeraboxDocumentsProvider.AUTHORITY
                .equals(uri.getAuthority()))
                return com.openlocal.office.core.FgTeraboxDocumentsProvider.cloudPath(uri);
        }catch(Exception ignored){}
        return uri.toString();
    }
    private void navigateFgVideo(int direction,boolean random){
        final java.util.List<RounderVideo> queue=fgVideoQueue;
        if(queue.size()<2||fgMediaSession==null)return;
        String current=fgVideoKey(fgMediaCurrentUri);
        int at=-1;
        for(int i=0;i<queue.size();i++)
            if(queue.get(i).key.equals(current)){at=i;break;}
        if(at<0)return;
        int next;
        if(random){
            next=java.util.concurrent.ThreadLocalRandom.current().nextInt(queue.size()-1);
            if(next>=at)next++;
        }else next=Math.floorMod(at+direction,queue.size());
        RounderVideo item=queue.get(next);
        runOnUiThread(()->showFgMedia(item.uri,item.name,true));
    }
    private volatile Uri fgMediaCurrentUri;
    private void showFgMedia(Uri uri,String name,boolean video){''',1)
anchor='''        fgMediaSession=new com.openlocal.office.core.FgMediaPlayer(
            this,uri,name,video,this::hideFgMedia);'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        fgMediaCurrentUri=uri;
        fgMediaSession=new com.openlocal.office.core.FgMediaPlayer(
            this,uri,name,video,this::hideFgMedia,this::navigateFgVideo);''',1)
# Cloud TeraBox URI knows file length already, avoids a synchronous
# filemetas request before even showing the selected file.
needle='''        @JavascriptInterface public void openTeraboxFile(String path,String name){
            if(path==null||!path.startsWith("/")||name==null||name.isBlank())return;'''
assert s.count(needle)==1
s=s.replace(needle,'''        @JavascriptInterface public void openTeraboxFile(String path,String name,long size){
            if(path==null||!path.startsWith("/")||name==null||name.isBlank())return;''',1)
needle='''            final Uri document=com.openlocal.office.core.FgTeraboxDocumentsProvider.uriFor(path);
            runOnUiThread(()->openUri(document));'''
assert s.count(needle)==1
s=s.replace(needle,'''            final Uri document=com.openlocal.office.core.FgTeraboxDocumentsProvider.uriFor(path,size);
            runOnUiThread(()->openUri(document));''',1)
# EPUB chapter IO must not block WebView's JavaScript thread.
anchor='''        @JavascriptInterface public String getBookChapter(int index){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        @JavascriptInterface public void requestBookChapter(int index,String token){
            if(index<0||token==null||token.length()>100)return;
            final BookArchive active=bookArchive;
            if(active==null||!token.equals(active.token()))return;
            io.execute(()->{
                String result;
                try{result=active.chapter(index).toString();}
                catch(Exception error){
                    try{result=new org.json.JSONObject()
                        .put("error",message(error)).toString();}
                    catch(Exception ignored){result="{\\\"error\\\":\\\"Chapter unavailable\\\"}";}
                }
                final String response=result;
                runOnUiThread(()->{
                    if(bookArchive!=active)return;
                    js("window.FileGestionerBookReader?.receiveChapter("+
                        q(token)+","+index+","+q(response)+")");
                });
            });
        }
'''+anchor,1)
# Prefer quick sampled view for large standalone images. Original untouched.
anchor='''                    String url="https://fg-assets.invalid/raw/"+imageStreamToken+"/image";'''
assert s.count(anchor)==1
s=s.replace(anchor,'''                    long imageBytes=displaySize(uri);
                    String url="https://fg-assets.invalid/"+
                        (imageBytes>=12L*1024*1024?"fallback/":"raw/")+
                        imageStreamToken+"/image";''',1)
# Cloud fallback route after full image stream errors, including errors
# happening asynchronously in WebView rather than at HTTP connect.
anchor='''    private WebResourceResponse fgTbImage(Uri source){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''    private WebResourceResponse fgTbPreview(Uri source){
        String[] parts=source.getPath().split("/");
        if(parts.length!=4||!parts[2].equals(fgTbToken))
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        try{
            TbPage item=fgTbPages.get(Integer.parseInt(parts[3]));
            if(item==null)throw new IOException("Image not in current collection");
            return new WebResourceResponse("image/jpeg",null,
                tb().openThumbnail(item.path));
        }catch(Exception error){
            android.util.Log.w("FG_IMAGE","Cloud image preview failed: "+
                error.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
'''+anchor,1)
anchor='''                    if(assetPath!=null&&assetPath.startsWith("/terabox-image/"))
                        return fgTbImage(u);'''
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
                    if(assetPath!=null&&assetPath.startsWith("/terabox-preview/"))
                        return fgTbPreview(u);''',1)
# Archive fallback when WebView rejects original compression/decoder stream.
anchor='''                    BookArchive active=bookArchive;
                    try {'''
assert s.count(anchor)==1
s=s.replace(anchor,'''                    BookArchive active=bookArchive;
                    if(active!=null&&assetPath!=null&&
                       assetPath.startsWith("/book-fallback/")){
                        try{return active.responseSampled(assetPath);}
                        catch(Exception issue){android.util.Log.w("FG_IMAGE",
                            "Archive sampled fallback failed: "+issue.getClass().getSimpleName());}
                    }
                    try {''',1)
main.write_text(s)
# Protects reader after source stream errors; selected page stays visible.
reader=root/'assets/reader-controls.js'
j=reader.read_text()
# Native appendImageCollectionChunk and appendTeraboxImageCollectionChunk
# deliver a JSON ARRAY. Earlier UI silently discarded both because it
# expected {pages:[...]}, so every folder stopped at the first image.
assert "append:payload=>add(payload?.pages)" in j
j=j.replace("append:payload=>add(payload?.pages)",
            "append:payload=>add(Array.isArray(payload)?payload:payload?.pages)",1)
needle='''         const nativeUrl=page.url.startsWith('https://fg-assets.invalid/raw/')?'''
assert j.count(needle)==1
j=j.replace(needle,'''         const nativeUrl=page.url.startsWith('https://fg-assets.invalid/book/')?
           page.url.replace('/book/','/book-fallback/'):
           page.url.startsWith('https://fg-assets.invalid/terabox-image/')?
           page.url.replace('/terabox-image/','/terabox-preview/'):
           page.url.startsWith('https://fg-assets.invalid/raw/')?''',1)
reader.write_text(j)
js=root/'assets/premium-library.js'
t=js.read_text()
# During ongoing folder enumeration, cloud files do not have a local SAF
# URI. Deduplication must use path, not undefined URI for every item.
assert 'new Set(state.siblings.map(e=>e.uri))' in t
assert 'known.has(entry.uri)' in t
t=t.replace('new Set(state.siblings.map(e=>e.uri))',
            'new Set(state.siblings.map(e=>e.path||e.uri))',1)
t=t.replace('known.has(entry.uri)','known.has(entry.path||entry.uri)',1)
t=t.replace('known.add(entry.uri)','known.add(entry.path||entry.uri)',1)
anchor=''' activeUri=item.uri;
 root.classList.add('fg-lib-hidden');'''
assert t.count(anchor)==1
t=t.replace(anchor,''' // Playlist follows the currently visible folder and never requests
 // a full-file transfer to navigate between movies.
 if(classify(item)==='video'){
   const candidates=entries.filter(x=>!x.folder&&classify(x)==='video')
     .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}))
     .slice(0,1500);
   bridge()?.setVideoQueue?.(JSON.stringify({entries:candidates.map(x=>({
     name:x.name,uri:x.terabox?'':x.uri,path:x.terabox?x.path:'',size:x.size
   }))}));
 }
 activeUri=item.uri;
 root.classList.add('fg-lib-hidden');''',1)
t=t.replace('bridge()?.openTeraboxFile?.(item.path,item.name);',
            'bridge()?.openTeraboxFile?.(item.path,item.name,Number(item.size)||-1);',1)
js.write_text(t)
# Version for new private candidate, same package and certificate.
gradle=Path("app/build.gradle.kts")
s=gradle.read_text()
assert '0.14.6' in s
s,n=re.subn(r'(\\bversionCode\\s*(?:=\\s*)?)18\\b',r'\\g<1>19',s,count=1)
if n!=1:
    s,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)18\b',r'\g<1>19',s,count=1)
assert n==1
s=s.replace('0.14.6','0.14.7',1)
gradle.write_text(s)
print("MainActivity, image fallback, async EPUB, video playlist and 0.14.7 wired")

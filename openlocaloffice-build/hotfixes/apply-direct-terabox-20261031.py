#!/usr/bin/env python3
"""Native, Keystore-backed TeraBox cloud browsing, file downloads and image paging.

No dependency on RoundSync, desktop rclone, or ADB. Keep original SAF library,
production package, and its signing identity untouched.
"""
from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
anchor='    private void loadLibrary(String folder){'
assert s.count(anchor)==1
impl=r'''    private static final int FG_TERA_SAVE_REQUEST=2027;
    private volatile com.openlocal.office.core.FgTeraboxClient fgTerabox;
    private synchronized com.openlocal.office.core.FgTeraboxClient tb(){
        if(fgTerabox==null)
            fgTerabox=new com.openlocal.office.core.FgTeraboxClient(this);
        return fgTerabox;
    }
    private final java.util.concurrent.atomic.AtomicLong fgTbVersion=
        new java.util.concurrent.atomic.AtomicLong();
    private volatile String fgTbToken=java.util.UUID.randomUUID().toString();
    private volatile String fgTbSavePending=null;
    private static final class TbPage {
        final String path,name;
        TbPage(String path,String name){this.path=path;this.name=name;}
    }
    private final java.util.concurrent.ConcurrentHashMap<Integer,TbPage> fgTbPages=
        new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.Set<String> fgTbKnown=
        java.util.concurrent.ConcurrentHashMap.newKeySet();
    private final java.util.concurrent.atomic.AtomicInteger fgTbNextIndex=
        new java.util.concurrent.atomic.AtomicInteger();
    private volatile String fgTbSelectedPath=null;
    // Stateless, stable cover URLs prevent hundreds of thousands of duplicated
    // native map entries and let the WebView reuse existing cached thumbnails.
    private static String fgTbCoverId(String path,int page){
        return android.util.Base64.encodeToString(
            path.getBytes(java.nio.charset.StandardCharsets.UTF_8),
            android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
            android.util.Base64.NO_PADDING)+"."+page;
    }

    private void listTeraboxNative(String folder){
        final String requested=folder==null?"":folder;
        if(!requested.isEmpty()&&!requested.startsWith("/"))return;
        final long version=fgTbVersion.incrementAndGet();
        fgDirectoryExecutor.execute(()->{
            final long start=android.os.SystemClock.elapsedRealtime();
            // Four metadata requests in flight maximum. Images themselves
            // never download during folder discovery.
            final java.util.concurrent.ExecutorService listPool=
                java.util.concurrent.Executors.newFixedThreadPool(4);
            final java.util.Map<Integer,java.util.concurrent.Future<org.json.JSONArray>>
                listingFutures=new java.util.HashMap<>();
            try{
                if(!tb().configured())throw new IOException("Connect a TeraBox ndus cookie first");
                int total=0;
                for(int page=1;page<=10000;page++){
                    if(version!=fgTbVersion.get())return;
                    org.json.JSONArray cloud;
                    if(page==1){
                        // Prioritize first visible rows before parallel paging.
                        cloud=tb().listPageCached(requested,1);
                    }else{
                        for(int candidate=page;candidate<page+4&&candidate<=10000;candidate++){
                            if(!listingFutures.containsKey(candidate)){
                                final int requestedPage=candidate;
                                listingFutures.put(candidate,listPool.submit(
                                    ()->tb().listPageCached(requested,requestedPage)));
                            }
                        }
                        cloud=listingFutures.remove(page).get(65,
                            java.util.concurrent.TimeUnit.SECONDS);
                    }
                    if(version!=fgTbVersion.get())return;
                    org.json.JSONArray batch=new org.json.JSONArray();
                    for(int i=0;i<cloud.length();i++){
                        org.json.JSONObject row=cloud.optJSONObject(i);
                        if(row==null)continue;
                        try{
                            org.json.JSONObject mapped=
                                com.openlocal.office.core.FgTeraboxClient.mapEntry(row);
                            String path=mapped.optString("path","");
                            if(!mapped.optBoolean("folder")&&
                               com.openlocal.office.core.FgTeraboxClient.image(mapped.optString("name",""))){
                                mapped.put("cover","https://fg-assets.invalid/tb-cover/"+
                                    fgTbCoverId(path,page));
                                mapped.put("remoteCover",true);
                            }
                            batch.put(mapped);
                        }catch(Exception ignored){android.util.Log.w("FG_TERA","Skipping malformed cloud item");}
                    }
                    total+=batch.length();
                    final boolean done=cloud.length()<com.openlocal.office.core.FgTeraboxClient.pageSize();
                    final String response=new org.json.JSONObject()
                        .put("version",version).put("folder",requested)
                        .put("requestedFolder",requested).put("finished",done)
                        .put("items",batch).toString();
                    if(version==fgTbVersion.get())runOnUiThread(()->{
                        if(version==fgTbVersion.get())
                            js("window.FileGestionerLibrary?.append("+response+")");
                    });
                    if(page==1)android.util.Log.i("FG_TERA","FIRST_PAGE_ms="+
                        (android.os.SystemClock.elapsedRealtime()-start)+" count="+batch.length());
                    if(done)break;
                }
                android.util.Log.i("FG_TERA","LIST_COMPLETE entries="+total);
            }catch(Exception problem){
                android.util.Log.w("FG_TERA","Cloud folder request failed: "+
                    problem.getClass().getSimpleName());
                if(version==fgTbVersion.get()){
                    final String message=problem.getMessage()==null?"Cloud request failed":problem.getMessage();
                    runOnUiThread(()->{
                        if(version==fgTbVersion.get())js("window.FileGestionerLibrary?.error("+
                            q(message)+")");
                    });
                }
            }finally{
                for(java.util.concurrent.Future<?> future:listingFutures.values())
                    future.cancel(true);
                listPool.shutdownNow();
            }
        });
    }
    private void beginTbImages(String path,String name){
        if(path==null||!path.startsWith("/")||
            !com.openlocal.office.core.FgTeraboxClient.image(name))return;
        final String token=java.util.UUID.randomUUID().toString();
        fgTbToken=token;
        fgImageCollectionActive=false;
        fgSelectedCollectionImage=null;
        fgTbSelectedPath=path;
        fgTbPages.clear();fgTbKnown.clear();fgTbNextIndex.set(1);
        fgTbKnown.add(path);fgTbPages.put(0,new TbPage(path,name));
        fgVerifiedKoikatsuCard=null;
        currentUri=null;
        final String url="https://fg-assets.invalid/terabox-image/"+token+"/0";
        final String payload;
        try{
            payload=new org.json.JSONObject().put("type","folderImages")
                .put("standalone",false)
                .put("pages",new org.json.JSONArray().put(new org.json.JSONObject()
                    .put("name",name).put("url",url).put("selected",true)))
                .toString();
        }catch(Exception e){return;}
        runOnUiThread(()->js("window.loadDocument("+payload+")"));
        // Card classification is asynchronous; displaying the image never
        // depends on downloading/inspecting its appended PNG payload.
        if(name.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))
            fgDirectoryExecutor.execute(()->{
                java.io.File cached=null;
                try{
                    cached=java.io.File.createTempFile("tb-card-", ".png",getCacheDir());
                    final java.io.File target=cached;
                    try(OutputStream out=new java.io.BufferedOutputStream(new FileOutputStream(target))){
                        tb().save(path,out);
                    }
                    if(!token.equals(fgTbToken)||!path.equals(fgTbSelectedPath))return;
                    final Uri uri=Uri.fromFile(target);
                    final boolean verified=KoikatsuCards.isCharacterCard(this,uri);
                    if(verified){
                        currentUri=uri;fgVerifiedKoikatsuCard=uri;
                        runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard(true)"));
                    }else target.delete();
                }catch(Exception e){
                    if(cached!=null)cached.delete();
                    android.util.Log.w("FG_TERA","Cloud 3D check unavailable: "+
                        e.getClass().getSimpleName());
                }
            });
    }
    private void appendTbImages(String chunk){
        final String token=fgTbToken;
        try{
            org.json.JSONArray items=new org.json.JSONArray(chunk);
            org.json.JSONArray pages=new org.json.JSONArray();
            for(int i=0;i<items.length()&&i<96;i++){
                org.json.JSONObject item=items.optJSONObject(i);
                if(item==null)continue;
                String path=item.optString("path","");
                String name=item.optString("name","");
                if(!path.startsWith("/")||!com.openlocal.office.core.FgTeraboxClient.image(name))
                    continue;
                if(!fgTbKnown.add(path))continue;
                int idx=fgTbNextIndex.getAndIncrement();
                fgTbPages.put(idx,new TbPage(path,name));
                pages.put(new org.json.JSONObject().put("name",name)
                    .put("url","https://fg-assets.invalid/terabox-image/"+token+"/"+idx));
            }
            if(pages.length()>0&&token.equals(fgTbToken)){
                final String json=pages.toString();
                runOnUiThread(()->{
                    if(token.equals(fgTbToken))
                        js("window.FileGestionerFolder?.append("+json+")");
                });
            }
        }catch(Exception problem){
            android.util.Log.w("FG_TERA","Invalid image chunk");
        }
    }
    private WebResourceResponse fgTbCover(Uri source){
        String id=source.getLastPathSegment();
        if(id==null||id.length()>8192)return new WebResourceResponse("image/jpeg",null,
            new ByteArrayInputStream(new byte[0]));
        String path=null;
        try{
            int split=id.lastIndexOf('.');
            if(split<1)throw new IOException("Missing thumbnail page");
            int page=Integer.parseInt(id.substring(split+1));
            if(page<1||page>10000)throw new IOException("Invalid thumbnail page");
            path=new String(android.util.Base64.decode(id.substring(0,split),
                android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
                android.util.Base64.NO_PADDING),java.nio.charset.StandardCharsets.UTF_8);
            if(!path.startsWith("/"))throw new IOException("Invalid cloud cover path");
            int slash=path.lastIndexOf('/');
            String folder=path.substring(0,slash);
            return new WebResourceResponse("image/jpeg",null,
                tb().openThumbnail(path,folder,page));
        }
        catch(Exception problem){
            android.util.Log.w("FG_TERA","Thumbnail error: "+
                problem.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
    private WebResourceResponse fgTbImage(Uri source){
        String[] parts=source.getPath().split("/");
        if(parts.length!=4||!parts[2].equals(fgTbToken))
            return new WebResourceResponse("image/jpeg",null,new ByteArrayInputStream(new byte[0]));
        try{
            int index=Integer.parseInt(parts[3]);
            TbPage item=fgTbPages.get(index);
            if(item==null)throw new IOException("Image is not in this collection");
            InputStream stream=tb().open(item.path);
            return new WebResourceResponse(
                com.openlocal.office.core.FgTeraboxClient.mime(item.name),null,stream);
        }catch(Exception problem){
            android.util.Log.w("FG_TERA","Image stream error: "+
                problem.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,new ByteArrayInputStream(new byte[0]));
        }
    }
    private void saveTbFile(String path,String name){
        if(path==null||!path.startsWith("/")||name==null||name.isBlank())return;
        fgTbSavePending=path;
        Intent chooser=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        chooser.setType(com.openlocal.office.core.FgTeraboxClient.mime(name));
        chooser.addCategory(Intent.CATEGORY_OPENABLE);
        chooser.putExtra(Intent.EXTRA_TITLE,name);
        chooser.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        startActivityForResult(chooser,FG_TERA_SAVE_REQUEST);
    }
    private void finishTbSave(Uri outputUri){
        final String path=fgTbSavePending;fgTbSavePending=null;
        if(path==null||outputUri==null)return;
        fgDirectoryExecutor.execute(()->{
            try(OutputStream target=getContentResolver().openOutputStream(outputUri,"wt")){
                if(target==null)throw new IOException("Save location refused output stream");
                tb().save(path,target);
                runOnUiThread(()->js("window.FileGestionerLibrary?.loadingStatus("+
                    q("Cloud file saved successfully.")+")"));
            }catch(Exception error){
                final String message=error.getMessage();
                runOnUiThread(()->js("window.FileGestionerLibrary?.error("+
                    q("Cloud download failed: "+message)+")"));
            }
        });
    }
'''
s=s.replace(anchor,impl+anchor,1)
anchor='                    if(assetPath!=null&&assetPath.startsWith("/folder-img/")){'
assert s.count(anchor)==1
s=s.replace(anchor,'''                    if(assetPath!=null&&assetPath.startsWith("/tb-cover/"))
                        return fgTbCover(u);
                    if(assetPath!=null&&assetPath.startsWith("/terabox-image/"))
                        return fgTbImage(u);
'''+anchor,1)
anchor='        if(requestCode==REQ_FG_CONVERT){'
assert s.count(anchor)==1
s=s.replace(anchor,'''        if(requestCode==FG_TERA_SAVE_REQUEST){
            finishTbSave(uri);
            return;
        }
'''+anchor,1)
anchor='        @JavascriptInterface public void listLibrary(String folder){loadLibrary(folder);}'
assert s.count(anchor)==1
s=s.replace(anchor,'''        @JavascriptInterface public void selectImageCollectionPage(int index){
            if(index<0)return;
            if(fgTbSelectedPath!=null){
                TbPage page=fgTbPages.get(index);
                if(page==null||page.path.equals(fgTbSelectedPath))return;
                fgTbSelectedPath=page.path;
                currentUri=null;
                fgVerifiedKoikatsuCard=null;
                android.util.Log.i("FG_3D","SELECTED_CLOUD_PAGE="+index);
                return;
            }
            if(fgImageCollectionActive){
                FolderPage page=fgFolderPageMap.get(index);
                if(page==null)return;
                String next=page.uri.toString();
                if(next.equals(fgSelectedCollectionImage))return;
                fgSelectedCollectionImage=next;
                fgVerifiedKoikatsuCard=null;
                currentUri=null;
                android.util.Log.i("FG_3D","SELECTED_SAF_PAGE="+index);
            }
        }
        @JavascriptInterface public void verifyCurrentKoikatsuCard(){
            // Image collections keep their selected SAF URI independently of
            // currentUri; using currentUri here inspected the preceding file
            // (or null), leaving genuine Koikatsu PNGs without 3D controls.
            final String selected=fgSelectedCollectionImage;
            if(selected!=null&&fgImageCollectionActive){
                checkCollectionKoikatsu(Uri.parse(selected));
                return;
            }
            final Uri local=currentUri;
            if(local!=null&&"content".equals(local.getScheme())){
                final Uri selectedUri=local;
                io.execute(()->{
                    boolean verified=KoikatsuCards.isCharacterCard(MainActivity.this,selectedUri);
                    fgVerifiedKoikatsuCard=verified?selectedUri:null;
                    final boolean ok=verified;
                    runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard("+ok+")"));
                });
                return;
            }
            final String cloud=fgTbSelectedPath;
            if(cloud==null||!cloud.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))return;
            final String token=fgTbToken;
            fgDirectoryExecutor.execute(()->{
                java.io.File file=null;
                try{
                    file=java.io.File.createTempFile("fg-verified-card-", ".png",getCacheDir());
                    try(OutputStream output=new BufferedOutputStream(new FileOutputStream(file))){
                        tb().save(cloud,output);
                    }
                    if(!token.equals(fgTbToken)||!cloud.equals(fgTbSelectedPath))return;
                    final Uri candidate=Uri.fromFile(file);
                    final boolean verified=KoikatsuCards.isCharacterCard(MainActivity.this,candidate);
                    if(verified){
                        currentUri=candidate;fgVerifiedKoikatsuCard=candidate;
                    }else file.delete();
                    runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard("+verified+")"));
                    android.util.Log.i("FG_KOIKATSU","USER_CARD_CHECK verified="+verified);
                }catch(Exception problem){
                    if(file!=null)file.delete();
                    runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard(false)"));
                    android.util.Log.w("FG_KOIKATSU","Manual card verification unavailable");
                }
            });
        }
        @JavascriptInterface public boolean getTeraboxConfigured(){
            return tb().configured();
        }
        @JavascriptInterface public boolean setTeraboxCookie(String token){
            return tb().setCookie(token);
        }
        @JavascriptInterface public void disconnectTerabox(){
            fgTbVersion.incrementAndGet();
            tb().disconnect();
            fgTbToken=java.util.UUID.randomUUID().toString();
        }
        @JavascriptInterface public void listTerabox(String folder){
            listTeraboxNative(folder);
        }
        @JavascriptInterface public void beginTeraboxImageCollection(String path,String name){
            beginTbImages(path,name);
        }
        @JavascriptInterface public void appendTeraboxImageCollectionChunk(String json){
            appendTbImages(json);
        }
        @JavascriptInterface public void saveTeraboxFile(String path,String name){
            runOnUiThread(()->saveTbFile(path,name));
        }
'''+anchor,1)
# Prevent a local folder session from inheriting a cloud 3D verification target.
needle='        fgSelectedCollectionImage=startUri;'
assert needle in s
s=s.replace(needle,'        fgTbSelectedPath=null;\n'+needle,1)
main.write_text(s)
print("Native direct TeraBox API: Keystore ndus, on-demand cloud pages, images, download SAF")

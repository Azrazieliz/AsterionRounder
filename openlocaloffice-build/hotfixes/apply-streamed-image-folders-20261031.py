#!/usr/bin/env python3
"""Open massive SAF image directories progressively, without a 20k cap."""
from pathlib import Path
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text()
start=s.index("    private void openFolderImages(String uriText){")
end=s.index("    private void openUri(Uri uri) {",start)
assert 2800<end-start<11000
replacement=r'''    private final java.util.concurrent.ConcurrentHashMap<Integer,FolderPage>
        fgFolderPageMap=new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.concurrent.atomic.AtomicLong fgFolderVersion=
        new java.util.concurrent.atomic.AtomicLong();
    private void openFolderImages(String uriText){
        openFolderImages(uriText,null);
    }
    private volatile String fgSelectedCollectionImage;
    private volatile boolean fgImageCollectionActive;
    private final java.util.concurrent.atomic.AtomicInteger fgImageCollectionCount=
        new java.util.concurrent.atomic.AtomicInteger();

    private void checkCollectionKoikatsu(Uri image){
        if(image==null||!"content".equals(image.getScheme()))return;
        final String name=displayName(image);
        if(name==null||!name.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))return;
        io.execute(()->{
            boolean genuine=KoikatsuCards.isCharacterCard(this,image);
            if(!image.toString().equals(fgSelectedCollectionImage))return;
            if(genuine){
                fgVerifiedKoikatsuCard=image;
                currentUri=image;
                android.util.Log.i("FG_KOIKATSU","NATIVE_CARD_VERIFIED");
            }
            final boolean verified=genuine;
            runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard("+verified+")"));
        });
    }
    // Image tiles already have SAF URIs from the library scanner. Reuse those
    // entries for local storage AND Round Sync; never enumerate a cloud folder
    // a second time just to display its already-listed pictures.
    private void beginImageCollection(String startUri){
        if(startUri==null||!allowedLibraryUris.contains(startUri))return;
        fgFolderVersion.incrementAndGet();
        fgFolderToken=java.util.UUID.randomUUID().toString();
        fgFolderPageMap.clear();
        fgImageCollectionCount.set(0);
        fgSelectedCollectionImage=startUri;
        fgImageCollectionActive=true;
        fgVerifiedKoikatsuCard=null;
        checkCollectionKoikatsu(Uri.parse(startUri));
        runOnUiThread(()->js("window.loadDocument({\"type\":\"folderImages\","+
            "\"name\":\"Image collection\",\"pages\":[]})"));
    }
    private void appendImageCollectionChunk(String json){
        if(!fgImageCollectionActive||json==null||json.length()>60000)return;
        try{
            org.json.JSONArray files=new org.json.JSONArray(json);
            if(files.length()>96)return;
            org.json.JSONArray pages=new org.json.JSONArray();
            for(int i=0;i<files.length();i++){
                org.json.JSONObject file=files.getJSONObject(i);
                String value=file.optString("uri"),name=file.optString("name");
                if(value.isEmpty()||name.isEmpty()||!allowedLibraryUris.contains(value))
                    continue;
                Uri uri=Uri.parse(value);
                if(libraryTree==null||!libraryTree.getAuthority().equals(uri.getAuthority()))
                    continue;
                int id=fgImageCollectionCount.getAndIncrement();
                fgFolderPageMap.put(id,new FolderPage(uri,name));
                pages.put(new org.json.JSONObject()
                    .put("name",name)
                    .put("url","https://fg-assets.invalid/folder-img/"+fgFolderToken+"/"+id)
                    .put("selected",value.equals(fgSelectedCollectionImage)));
            }
            if(pages.length()>0){
                String payload=new org.json.JSONObject().put("pages",pages).toString();
                runOnUiThread(()->js("window.FileGestionerFolder?.append("+payload+")"));
            }
        }catch(Exception e){
            android.util.Log.w("FG_FOLDER","IMAGE_COLLECTION_CHUNK_ERROR",e);
        }
    }
    private void finishImageCollection(){
        if(!fgImageCollectionActive)return;
        fgImageCollectionActive=false;
        final int count=fgImageCollectionCount.get();
        runOnUiThread(()->js("window.FileGestionerFolder?.done("+count+")"));
        android.util.Log.i("FG_FOLDER","IMAGE_COLLECTION_READY count="+count);
    }
    private void openImageInFolder(String folderId,String selectedUri){
        if(libraryTree==null||selectedUri==null)return;
        // File URI must have been exposed by our selected collection.
        if(!allowedLibraryUris.contains(selectedUri)){
            runOnUiThread(()->js("window.FileGestionerLibrary?.error("+
                q("This image is no longer in the current collection")+")"));
            return;
        }
        String id=(folderId==null||folderId.isEmpty())?
            android.provider.DocumentsContract.getTreeDocumentId(libraryTree):folderId;
        Uri parent=android.provider.DocumentsContract.buildDocumentUriUsingTree(libraryTree,id);
        openFolderImages(parent.toString(),selectedUri);
    }
    private void openFolderImages(String uriText,String selectedUri){
        if(uriText==null||libraryTree==null)return;
        final Uri directory=Uri.parse(uriText);
        // Opening a subfolder must not depend on the current scan's transient
        // allowedLibraryUris set: it is cleared when the library refreshes.
        // Validate against the persistently granted SAF tree instead.
        try{
            if(!"content".equals(directory.getScheme())||
               !libraryTree.getAuthority().equals(directory.getAuthority())||
               !android.provider.DocumentsContract.getTreeDocumentId(libraryTree)
                   .equals(android.provider.DocumentsContract.getTreeDocumentId(directory)))
                throw new SecurityException("Folder is outside the selected library");
        }catch(Exception invalid){
            runOnUiThread(()->js("window.FileGestionerLibrary?.error("+
                q("Cannot open image folder: "+message(invalid))+")"));
            return;
        }
        final long request=fgFolderVersion.incrementAndGet();
        final String token=java.util.UUID.randomUUID().toString();
        fgFolderToken=token;
        // Track the requested image and scroll to it as its page arrives.
        final Uri selected=selectedUri==null?null:Uri.parse(selectedUri);
        fgFolderPageMap.clear();
        fgDirectoryExecutor.execute(()->{
            final java.util.concurrent.atomic.AtomicInteger pageIndex=
                new java.util.concurrent.atomic.AtomicInteger();
            final java.util.concurrent.atomic.AtomicBoolean started=
                new java.util.concurrent.atomic.AtomicBoolean();
            final java.util.function.Consumer<java.util.List<FolderPage>> flush=(batch)->{
                if(request!=fgFolderVersion.get()||batch.isEmpty())return;
                try{
                    batch.sort((x,y)->com.openlocal.office.core.ReaderLibrary.naturalCompare(
                        x.name,y.name));
                    org.json.JSONArray images=new org.json.JSONArray();
                    for(FolderPage page:batch){
                        int i=pageIndex.getAndIncrement();
                        fgFolderPageMap.put(i,page);
                        images.put(new org.json.JSONObject().put("name",page.name)
                            .put("url","https://fg-assets.invalid/folder-img/"+
                                token+"/"+i)
                            .put("selected",selected!=null&&selected.equals(page.uri)));
                    }
                    if(!started.getAndSet(true)){
                        final String payload=new org.json.JSONObject()
                            .put("type","folderImages").put("name","Image folder")
                            .put("pages",images).toString();
                        runOnUiThread(()->{
                            if(request==fgFolderVersion.get())
                                js("window.loadDocument("+payload+")");
                        });
                    }else{
                        final String payload=new org.json.JSONObject()
                            .put("pages",images).toString();
                        runOnUiThread(()->{
                            if(request==fgFolderVersion.get())
                                js("window.FileGestionerFolder?.append("+payload+")");
                        });
                    }
                }catch(Exception e){android.util.Log.w("FG_FOLDER","Batch failed",e);}
            };
            try{
                final String folderId=android.provider.DocumentsContract.getDocumentId(directory);
                final long startMillis=android.os.SystemClock.elapsedRealtime();
                // Reuse the same adaptive SAF listing strategy as the library.
                // Round Sync may refuse tree-scoped queries or optional columns.
                final java.util.List<FolderPage> batch=new java.util.ArrayList<>(48);
                ReaderLibrary.stream(this,libraryTree,folderId,(foundFolder,items,done)->{
                    if(request!=fgFolderVersion.get())
                        throw new java.util.concurrent.CancellationException();
                    for(int at=0;at<items.length();at++){
                        org.json.JSONObject file=items.getJSONObject(at);
                        if(file.optBoolean("folder"))continue;
                        String name=file.optString("name","");
                        String lower=name.toLowerCase(java.util.Locale.ROOT);
                        if(name.startsWith(".")||
                           !(lower.endsWith(".png")||lower.endsWith(".jpg")||
                             lower.endsWith(".jpeg")||lower.endsWith(".webp")||
                             lower.endsWith(".gif")||lower.endsWith(".avif")||
                             lower.endsWith(".bmp")))continue;
                        batch.add(new FolderPage(Uri.parse(file.getString("uri")),name));
                        if(batch.size()>=(started.get()?48:1)){
                            flush.accept(batch);
                            batch.clear();
                        }
                    }
                    if(done)flush.accept(batch);
                });
                if(!started.get()){
                    runOnUiThread(()->{
                        if(request==fgFolderVersion.get())
                            js("window.FileGestionerLibrary?.enterFolder("+
                                q(android.provider.DocumentsContract.getDocumentId(directory))+")");
                    });
                }else{
                    final int total=pageIndex.get();
                    runOnUiThread(()->{
                        if(request==fgFolderVersion.get())
                            js("window.FileGestionerFolder?.done("+total+")");
                    });
                }
                android.util.Log.i("FG_FOLDER","FOLDER_STREAM_COMPLETE pages="+
                    pageIndex.get()+" millis="+
                    (android.os.SystemClock.elapsedRealtime()-startMillis));
            }catch(Exception e){
                android.util.Log.e("FG_FOLDER","FOLDER_STREAM_FAILED provider="+
                    directory.getAuthority(),e);
                if(request==fgFolderVersion.get())
                    runOnUiThread(()->{
                        js("window.FileGestionerFolder?.failed("+q(message(e))+")");
                        js("window.FileGestionerLibrary?.error("+
                            q("Cannot browse image folder: "+message(e))+")");
                    });
            }
        });
    }
'''
s=s[:start]+replacement+s[end:]
start=s.index('                    if(assetPath!=null&&assetPath.startsWith("/folder-img/")){')
end=s.index('                    if(assetPath!=null&&assetPath.startsWith("/cover/")){',start)
old=s[start:end]
assert 'fgFolderUris' in old
new=r'''                    if(assetPath!=null&&assetPath.startsWith("/folder-img/")){
                        String[] part=assetPath.split("/");
                        if(part.length==4&&part[2].equals(fgFolderToken)){
                            try{
                                int index=Integer.parseInt(part[3]);
                                FolderPage page=fgFolderPageMap.get(index);
                                if(page!=null){
                                    String lower=page.name.toLowerCase(java.util.Locale.ROOT);
                                    String mime=lower.endsWith(".png")?"image/png":
                                        lower.endsWith(".webp")?"image/webp":
                                        lower.endsWith(".gif")?"image/gif":
                                        lower.endsWith(".avif")?"image/avif":"image/jpeg";
                                    InputStream input=null;
                                    try{
                                        input=getContentResolver().openInputStream(page.uri);
                                    }catch(Exception first){
                                        android.util.Log.w("FG_FOLDER",
                                            "SAF openInputStream failed; retrying file descriptor",first);
                                        android.os.ParcelFileDescriptor descriptor=
                                            getContentResolver().openFileDescriptor(page.uri,"r");
                                        if(descriptor!=null)
                                            input=new android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor);
                                    }
                                    if(input!=null)return new WebResourceResponse(mime,null,input);
                                }
                            }catch(Exception e){
                                android.util.Log.w("FG_FOLDER","Failed image fetch",e);
                            }
                        }
                        return new WebResourceResponse("image/jpeg",null,
                            new ByteArrayInputStream(new byte[0]));
                    }
'''
s=s[:start]+new+s[end:]
# The pre-existing bridge method is inserted by apply-reading-platform.
anchor='''        @JavascriptInterface public void openKoikatsu3d(){'''
assert s.count(anchor)==1, "3D bridge insertion point missing"
s=s.replace(anchor,'''        @JavascriptInterface public void beginImageCollection(String image){
            MainActivity.this.beginImageCollection(image);
        }
        @JavascriptInterface public void appendImageCollectionChunk(String json){
            MainActivity.this.appendImageCollectionChunk(json);
        }
        @JavascriptInterface public void finishImageCollection(){
            MainActivity.this.finishImageCollection();
        }
        @JavascriptInterface public void openImageInFolder(String folder,String selected){
            MainActivity.this.openImageInFolder(folder,selected);
        }
'''+anchor,1)
main.write_text(s)
print("SAF image folders: Round Sync tree access, sequential navigation and resilient image streams")

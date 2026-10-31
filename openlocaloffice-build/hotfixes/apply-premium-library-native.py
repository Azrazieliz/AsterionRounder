from pathlib import Path

main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
def once(old,new):
    global s
    assert s.count(old)==1,("Expected one anchor:",old[:80],s.count(old))
    s=s.replace(old,new,1)
once('    private static final int REQ_SAVE_COPY = 1002;',
'''    private static final int REQ_SAVE_COPY = 1002;
    private static final int REQ_LIBRARY_TREE = 2010;
    private static final int REQ_KOIKATSU_PREVIEW = 2011;''')
once('    private String imageStreamToken;', '''
    private String imageStreamToken;
    private volatile Uri libraryTree;
    private final java.util.concurrent.ExecutorService collectionIo=
        java.util.concurrent.Executors.newSingleThreadExecutor();
    private final java.util.concurrent.ConcurrentHashMap<String,LibraryCover> libraryCovers=
        new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.Set<String> allowedLibraryUris=
        java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static final class LibraryCover {
        final Uri uri; final String name; final long size,modified; final boolean folder;
        LibraryCover(Uri uri,String name,long size,long modified,boolean folder){
            this.uri=uri;this.name=name;this.size=size;this.modified=modified;this.folder=folder;
        }
    }
''')
once('''        web = new WebView(this);
        setContentView(web);''','''        web = new WebView(this);
        setContentView(web);
        String libraryValue=getSharedPreferences("library",MODE_PRIVATE).getString("tree",null);
        if(libraryValue!=null)try{libraryTree=Uri.parse(libraryValue);}catch(Exception ignored){}''')
once('''                    String assetPath=u.getPath();
                    if(assetPath!=null&&imageStreamToken!=null&&''','''                    String assetPath=u.getPath();
                    if(assetPath!=null&&assetPath.startsWith("/cover/")){
                        LibraryCover ref=libraryCovers.get(assetPath.substring("/cover/".length()));
                        if(ref==null)return new WebResourceResponse("image/jpeg",null,
                            new ByteArrayInputStream(new byte[0]));
                        try{
                            ReaderLibrary.CoverCandidate first=ref.folder?
                                ReaderLibrary.firstCover(MainActivity.this,ref.uri):null;
                            if(ref.folder&&first==null)
                                throw new java.io.IOException("No supported first book or image");
                            Uri coverSource=ref.folder?first.uri:ref.uri;
                            String coverName=ref.folder?first.name:ref.name;
                            long coverSize=ref.folder?first.size:ref.size;
                            long coverModified=ref.folder?first.modified:ref.modified;
                            return new WebResourceResponse("image/jpeg",null,
                                ReaderCovers.open(MainActivity.this,coverSource,
                                    coverName,coverSize,coverModified));
                        }catch(Exception ignored){
                            return new WebResourceResponse("image/jpeg",null,
                                new ByteArrayInputStream(new byte[0]));
                        }
                    }
                    if(assetPath!=null&&imageStreamToken!=null&&''')
once('''        if (requestCode == REQ_OPEN) {''','''        if(requestCode==REQ_LIBRARY_TREE){
            try{
                int granted=Intent.FLAG_GRANT_READ_URI_PERMISSION|
                    (data==null?0:(data.getFlags()&Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
                getContentResolver().takePersistableUriPermission(uri,granted);
                libraryTree=uri;
                getSharedPreferences("library",MODE_PRIVATE).edit()
                    .putString("tree",uri.toString()).apply();
                js("window.FileGestionerLibrary?.openCollection()");
            }catch(Exception e){
                js("window.showError("+q("The chosen folder cannot be retained: "+message(e))+")");
            }
            return;
        }
        if(requestCode==REQ_KOIKATSU_PREVIEW){
            try{
                int flags=data.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION;
                getContentResolver().takePersistableUriPermission(uri,flags);
                if(currentUri!=null){
                    getSharedPreferences("koikatsu",MODE_PRIVATE).edit()
                        .putString("preview:"+currentUri.toString(),uri.toString()).apply();
                }
                openUri(uri);
            }catch(Exception e){js("window.showError("+q(message(e))+")");}
            return;
        }
        if (requestCode == REQ_OPEN) {''')
once('''    private void openUri(Uri uri) {''','''    private void selectLibraryFolder(){
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|
            Intent.FLAG_GRANT_WRITE_URI_PERMISSION|
            Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent,REQ_LIBRARY_TREE);
    }
    private void selectKoikatsuPreview(){
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("*/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|
            Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent,REQ_KOIKATSU_PREVIEW);
    }
    private String savedCharacterPreview(){
        if(currentUri==null)return null;
        String value=getSharedPreferences("koikatsu",MODE_PRIVATE).getString(
            "preview:"+currentUri.toString(),null);
        if(value==null)return null;
        Uri paired=Uri.parse(value);
        return hasDurableReadGrant(paired)?value:null;
    }
    private void loadLibrary(String folder){
        final Uri root=libraryTree;
        if(root==null){runOnUiThread(()->
            js("window.FileGestionerLibrary?.missingCollection()"));return;}
        // Do not queue a document open behind a slow Round Sync cloud query.
        collectionIo.execute(()->{
            try{
                long started=android.os.SystemClock.elapsedRealtime();
                ReaderLibrary.Listing listing=ReaderLibrary.list(this,root,folder);
                android.util.Log.i("FG_PERF","COLLECTION_LIST_ms="+
                    (android.os.SystemClock.elapsedRealtime()-started)+
                    " items="+listing.items.length());
                libraryCovers.clear();allowedLibraryUris.clear();
                org.json.JSONArray items=listing.items;
                for(int i=0;i<items.length();i++){
                    org.json.JSONObject item=items.getJSONObject(i);
                    // Folder covers resolved only when their thumbnails are requested.
                    String id=java.util.UUID.randomUUID().toString().replace("-","");
                    Uri file=Uri.parse(item.getString("uri"));
                    allowedLibraryUris.add(file.toString());
                    libraryCovers.put(id,new LibraryCover(
                        file,item.optString("name"),item.optLong("size",-1),
                        item.optLong("modified",0),item.optBoolean("folder")));
                    // Prevent background downloads of cloud archives for thumbnails.
                    String coverName=item.optBoolean("folder")?
                        "folder-cover.jpg":item.optString("name");
                    // WebView lazy-loads only on-screen covers. Cloud archive
                    // requests now scan a bounded ZIP prefix, never spool whole
                    // remote books. Cached complete books are served locally.
                    String lower=coverName.toLowerCase(java.util.Locale.ROOT);
                    boolean safeCover=item.optBoolean("folder")||
                        lower.endsWith(".epub")||lower.endsWith(".cbz")||
                        lower.endsWith(".zip")||lower.endsWith(".pdf")||
                        lower.endsWith(".jpg")||lower.endsWith(".jpeg")||
                        lower.endsWith(".png")||lower.endsWith(".webp");
                    if(safeCover){
                        item.put("cover","https://fg-assets.invalid/cover/"+id);
                        // Remote folders and compressed books require network
                        // transfers: only fetch covers after an explicit tap.
                        boolean cloud="de.felixnuesse.extract.vcp".equals(file.getAuthority());
                        boolean knownCached=ReaderCovers.hasCached(MainActivity.this,file,
                            item.optLong("size",-1),item.optLong("modified",0))||
                            RemoteBookSpool.hasCompleted(MainActivity.this,file,
                                item.optLong("size",-1));
                        // No network thumbnail requests during any cloud listing.
                        // Even a JPEG/PDF may be several megabytes on TeraBox.
                        item.put("remoteCover",cloud&&!knownCached);
                    }
                }
                String json=new org.json.JSONObject()
                    .put("folder",listing.folder).put("items",items).toString();
                runOnUiThread(()->js("window.FileGestionerLibrary?.receive("+json+")"));
            }catch(Throwable error){
                runOnUiThread(()->js("window.FileGestionerLibrary?.error("+q(message(error))+")"));
            }
        });
    }
    private void openUri(Uri uri) {''')
once('''                    BookArchive candidate=new BookArchive(this,uri,false);
                    bookArchive=candidate;''','''                    long indexedAt=android.os.SystemClock.elapsedRealtime();
                    BookArchive candidate=new BookArchive(this,uri,false);
                    android.util.Log.i("FG_ARCHIVE","ZIP_READY count="+candidate.imageCount()+
                        " comic="+candidate.comicLike()+" elapsed_ms="+
                        (android.os.SystemClock.elapsedRealtime()-indexedAt));
                    bookArchive=candidate;''')
once('''                    imageStreamToken=java.util.UUID.randomUUID().toString();
                    remember(uri,name,currentMime);
                    String url="https://fg-assets.invalid/raw/"+imageStreamToken+"/image";
                    String payload="{\\"type\\":\\"image\\",\\"name\\":"+q(name)+''','''                    imageStreamToken=java.util.UUID.randomUUID().toString();
                    boolean character=false; // Nonblocking: show image before validating Koikatsu payload
                    remember(uri,name,currentMime);
                    String url="https://fg-assets.invalid/raw/"+imageStreamToken+"/image";
                    String payload="{\\"type\\":\\"image\\",\\"name\\":"+q(name)+
                        ",\\"koikatsuCard\\":"+character+
                        ",\\"linked3d\\":"+(character&&savedCharacterPreview()!=null)+''')
once('''        @JavascriptInterface public void pickFile(){ runOnUiThread(MainActivity.this::openPicker); }''','''        @JavascriptInterface public void pickFile(){ runOnUiThread(MainActivity.this::openPicker); }
        @JavascriptInterface public void readerDiagnostic(String event){
            if(event!=null&&event.length()<100)
                android.util.Log.i("FG_READER_UI",event);
        }
        @JavascriptInterface public void pickLibraryFolder(){
            runOnUiThread(MainActivity.this::selectLibraryFolder);
        }
        @JavascriptInterface public String getLibraryRoot(){
            return libraryTree==null?"":libraryTree.toString();
        }
        @JavascriptInterface public void listLibrary(String folder){loadLibrary(folder);}
        @JavascriptInterface public void openLibraryFile(String value){
            if(!allowedLibraryUris.contains(value))return;
            runOnUiThread(()->openUri(Uri.parse(value)));
        }
        @JavascriptInterface public void openKoikatsu3d(){
            runOnUiThread(()->{
                String preview=savedCharacterPreview();
                if(preview!=null)openUri(Uri.parse(preview));
                else selectKoikatsuPreview();
            });
        }
''')
main.write_text(s)
print("Native premium bookshelf, lazy cover URLs and Koikatsu 3D preview pairing connected.")

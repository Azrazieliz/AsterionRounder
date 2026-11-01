package com.openlocal.office.core;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.ParcelFileDescriptor;
import android.os.ProxyFileDescriptorCallback;
import android.os.storage.StorageManager;
import android.provider.DocumentsContract;
import android.provider.DocumentsProvider;
import android.net.Uri;
import java.io.IOException;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import android.content.ContentResolver;
import java.util.Locale;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Android Storage Access Framework gateway for Asterion apps.
 * The user chooses TeraBox in the system file picker and grants individual
 * documents or folders. The ndus session stays in this app's private Keystore;
 * consumers receive ordinary content:// URIs, never login material or CDN URLs.
 *
 * Reads are HTTP byte ranges, not file downloads to local storage.
 */
public final class FgTeraboxDocumentsProvider extends DocumentsProvider {
    public static final String AUTHORITY = "com.openlocal.office.terabox.documents";
    private static final String ROOT = "asterion-terabox";
    private static final String ROOT_DOC = "tb:/";
    private static final String[] ROOT_COLUMNS = {
        DocumentsContract.Root.COLUMN_ROOT_ID, DocumentsContract.Root.COLUMN_DOCUMENT_ID,
        DocumentsContract.Root.COLUMN_TITLE, DocumentsContract.Root.COLUMN_SUMMARY,
        DocumentsContract.Root.COLUMN_FLAGS, DocumentsContract.Root.COLUMN_ICON
    };
    private static final String[] DOC_COLUMNS = {
        DocumentsContract.Document.COLUMN_DOCUMENT_ID, DocumentsContract.Document.COLUMN_DISPLAY_NAME,
        DocumentsContract.Document.COLUMN_MIME_TYPE, DocumentsContract.Document.COLUMN_SIZE,
        DocumentsContract.Document.COLUMN_LAST_MODIFIED, DocumentsContract.Document.COLUMN_FLAGS
    };
    private FgTeraboxClient client;
    private HandlerThread workerThread;
    private final ExecutorService listingWorker=Executors.newSingleThreadExecutor(r->{
        Thread t=new Thread(r,"asterion-saf-list");
        t.setDaemon(true);
        return t;
    });
    private final Object foldersLock=new Object();
    // Keep only recently browsed picker groups; a 300K-file library must not
    // retain every discovered SAF cursor and metadata row on the Java heap.
    private final Map<String,ArrayList<JSONObject>> folderRows=
        new LinkedHashMap<String,ArrayList<JSONObject>>(32,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,ArrayList<JSONObject>> eldest){
                if(size()<=24)return false;
                listed.remove(eldest.getKey());
                folderHasNext.remove(eldest.getKey());
                retryAfter.remove(eldest.getKey());
                return true;
            }
        };
    private final Map<String,JSONObject> knownItems=
        new LinkedHashMap<String,JSONObject>(5120,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,JSONObject> eldest){
                return size()>6000;
            }
        };
    private final Set<String> folderHasNext=new HashSet<>();
    private final Set<String> listingInProgress=new HashSet<>();
    private final Set<String> listed=new HashSet<>();
    private final Map<String,Long> retryAfter=new HashMap<>();
    // Android Files uses non-paged cursors; expose bounded continuation folders
    // instead of silently truncating after 450 entries.
    private static final int SAF_PAGES_PER_GROUP=4;
    private static final int SAF_MAX_VISIBLE=SAF_PAGES_PER_GROUP*100;
    // Custom queryArgs understood by AsterionCore, not by the system picker.
    public static final String PAGE_OFFSET="asterion.page.offset";
    public static final String PAGE_LIMIT="asterion.page.limit";
    private static final int INDEX_PAGE_SIZE=100;
    private static final long METADATA_FRESH_MS=15*60*1000L;
    private final ExecutorService pageWorkers=Executors.newFixedThreadPool(4,r->{
        Thread thread=new Thread(r,"asterion-metadata-page");
        thread.setDaemon(true);return thread;
    });
    private final Set<String> pageFlights=ConcurrentHashMap.newKeySet();
    private final Map<String,Long> failedPages=new ConcurrentHashMap<>();


    public static Uri uriFor(String path) {
        if (path == null || !path.startsWith("/")) throw new IllegalArgumentException("Invalid cloud path");
        return DocumentsContract.buildDocumentUri(AUTHORITY, "tb:" + path);
    }
    // Private fast opening: the library already received this file's size
    // during listing. Pass it to the provider via a harmless document-ID hint
    // to avoid a redundant synchronous network lookup on openDocument().
    // The signed CDN URL and the ndus credential are NOT encoded in the URI.
    public static Uri uriFor(String path,long size){
        if(path==null||!path.startsWith("/")||size<0)return uriFor(path);
        String encoded=android.util.Base64.encodeToString(
            path.getBytes(java.nio.charset.StandardCharsets.UTF_8),
            android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
            android.util.Base64.NO_PADDING);
        return DocumentsContract.buildDocumentUri(AUTHORITY,"tb2:"+encoded+"."+size);
    }
    private static boolean isContinuation(String documentId){
        return documentId!=null&&documentId.startsWith("tbmore:");
    }
    private static int firstPage(String documentId)throws IOException{
        if(!isContinuation(documentId))return 1;
        try{
            int stop=documentId.indexOf(':',"tbmore:".length());
            int page=Integer.parseInt(documentId.substring("tbmore:".length(),stop));
            if(page<2||page>100000||((page-1)%SAF_PAGES_PER_GROUP)!=0)
                throw new IOException("Invalid continuation page");
            return page;
        }catch(IndexOutOfBoundsException|NumberFormatException error){
            throw new IOException("Invalid continuation identifier",error);
        }
    }
    private static String continuationId(String path,int page){
        String encoded=android.util.Base64.encodeToString(
            path.getBytes(StandardCharsets.UTF_8),
            android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
            android.util.Base64.NO_PADDING);
        return "tbmore:"+page+":"+encoded;
    }
    private static String path(String docId) throws IOException {
        if(docId==null)throw new IOException("Missing TeraBox document ID");
        String p;
        if(isContinuation(docId)){
            firstPage(docId);
            int split=docId.indexOf(':',"tbmore:".length());
            try{
                p=new String(android.util.Base64.decode(docId.substring(split+1),
                    android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP),
                    StandardCharsets.UTF_8);
            }catch(IllegalArgumentException ex){
                throw new IOException("Invalid continuation folder",ex);
            }
        }else if(docId.startsWith("tb2:")){
            int split=docId.lastIndexOf('.');
            if(split<=4)throw new IOException("Malformed TeraBox document ID");
            try{
                p=new String(android.util.Base64.decode(docId.substring(4,split),
                    android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP),
                    java.nio.charset.StandardCharsets.UTF_8);
                long size=Long.parseLong(docId.substring(split+1));
                if(size<0)throw new IOException("Invalid cloud size");
            }catch(IllegalArgumentException ex){
                throw new IOException("Malformed cloud document ID",ex);
            }
        }else if(docId.startsWith("tb:/"))p=docId.substring(3);
        else throw new IOException("Invalid cloud document ID");
        if(!p.startsWith("/")||p.contains("/../")||p.endsWith("/..")||
           p.contains("\n")||p.contains("\r"))throw new IOException("Unsafe cloud path");
        return p;
    }
    public static String cloudPath(Uri uri)throws IOException{
        if(uri==null||!AUTHORITY.equals(uri.getAuthority()))
            throw new IOException("Not an Asterion TeraBox document");
        return path(DocumentsContract.getDocumentId(uri));
    }
    public static long sizeHint(Uri uri){
        if(uri==null||!AUTHORITY.equals(uri.getAuthority()))return -1;
        try{return hintedLength(DocumentsContract.getDocumentId(uri));}
        catch(Exception ignored){return -1;}
    }
    private static long hintedLength(String docId){
        if(docId==null||!docId.startsWith("tb2:"))return -1;
        try{return Long.parseLong(docId.substring(docId.lastIndexOf('.')+1));}
        catch(Exception ignored){return -1;}
    }
    @Override public boolean onCreate() {
        client = new FgTeraboxClient(getContext());
        workerThread = new HandlerThread("asterion-terabox-range");
        workerThread.start();
        return true;
    }
    @Override public Cursor queryRoots(String[] projection) {
        MatrixCursor result = new MatrixCursor(projection == null ? ROOT_COLUMNS : projection);
        if (!client.configured()) return result;
        MatrixCursor.RowBuilder row = result.newRow();
        add(row, result, DocumentsContract.Root.COLUMN_ROOT_ID, ROOT);
        add(row, result, DocumentsContract.Root.COLUMN_DOCUMENT_ID, ROOT_DOC);
        add(row, result, DocumentsContract.Root.COLUMN_TITLE, "Asterion TeraBox");
        add(row, result, DocumentsContract.Root.COLUMN_SUMMARY, "Cloud files · stream without download");
        add(row, result, DocumentsContract.Root.COLUMN_FLAGS,
            DocumentsContract.Root.FLAG_SUPPORTS_IS_CHILD);
        add(row, result, DocumentsContract.Root.COLUMN_ICON, android.R.drawable.ic_menu_gallery);
        return result;
    }
    private static void add(MatrixCursor.RowBuilder row, MatrixCursor cursor, String column, Object value) {
        if (cursor.getColumnIndex(column) >= 0) row.add(column, value);
    }
    private void addDocument(MatrixCursor rows, JSONObject item, String cloudPath) {
        MatrixCursor.RowBuilder row = rows.newRow();
        boolean dir = item.optInt("isdir", 0) != 0 || "/".equals(cloudPath);
        String name = item.optString("server_filename", "");
        if (name.isEmpty()) name = "/".equals(cloudPath) ? "TeraBox" : cloudPath.substring(cloudPath.lastIndexOf('/') + 1);
        long fileSize=item.optLong("size",-1L);
        String docId="tb:"+cloudPath;
        if(!dir&&fileSize>=0L){
            String encoded=android.util.Base64.encodeToString(
                cloudPath.getBytes(StandardCharsets.UTF_8),
                android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
                android.util.Base64.NO_PADDING);
            docId="tb2:"+encoded+"."+fileSize;
        }
        add(row, rows, DocumentsContract.Document.COLUMN_DOCUMENT_ID, docId);
        add(row, rows, DocumentsContract.Document.COLUMN_DISPLAY_NAME, name);
        add(row, rows, DocumentsContract.Document.COLUMN_MIME_TYPE,
            dir ? DocumentsContract.Document.MIME_TYPE_DIR : FgTeraboxClient.mime(name));
        if (!dir) add(row, rows, DocumentsContract.Document.COLUMN_SIZE, item.optLong("size", -1));
        add(row, rows, DocumentsContract.Document.COLUMN_LAST_MODIFIED,
            item.optLong("server_mtime", 0) * 1000L);
        add(row, rows, DocumentsContract.Document.COLUMN_FLAGS, 0);
    }
    private void addContinuation(MatrixCursor rows,String folder,int page){
        MatrixCursor.RowBuilder row=rows.newRow();
        add(row,rows,DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            continuationId(folder,page));
        add(row,rows,DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            "More files · "+((page-1)*FgTeraboxClient.pageSize()+1)+" onward");
        add(row,rows,DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.MIME_TYPE_DIR);
        add(row,rows,DocumentsContract.Document.COLUMN_FLAGS,0);
    }
    @Override public Cursor queryDocument(String documentId, String[] projection)
            throws java.io.FileNotFoundException {
        MatrixCursor rows = new MatrixCursor(projection == null ? DOC_COLUMNS : projection);
        try {
            String p = path(documentId);
            if(isContinuation(documentId)){
                addContinuation(rows,p,firstPage(documentId));
                return rows;
            }
            if ("/".equals(p)) {
                addDocument(rows,new JSONObject().put("isdir",1)
                    .put("server_filename","TeraBox"),"/");
            } else {
                JSONObject item;
                synchronized(foldersLock) { item=knownItems.get(p); }
                if(item==null){
                    // Never synchronously perform a network lookup from the
                    // system picker or startup Binder transaction.
                    item=new JSONObject().put("server_filename",
                        p.substring(p.lastIndexOf('/')+1)).put("path",p);
                }
                if(hintedLength(documentId)>=0){
                    // Preserve the original stored metadata fields, only patch
                    // the length hint for this intra-app document URI.
                    item=new JSONObject(item.toString());
                    item.put("size",hintedLength(documentId));
                }
                addDocument(rows,item,p);
            }
            return rows;
        }catch(Exception ex){throw unavailable(ex);}
    }
    /**
     * AsterionCore streams directory metadata 100 at a time through the
     * Android SAF permission it already owns. No image pixels are fetched.
     * Standard Android picker queries continue to use the legacy method.
     */
    @Override public Cursor queryChildDocuments(String documentId,String[] projection,Bundle args)
            throws java.io.FileNotFoundException {
        if(args==null||!args.containsKey(PAGE_OFFSET))
            return queryChildDocuments(documentId,projection,(String)null);
        final MatrixCursor rows=new MatrixCursor(projection==null?DOC_COLUMNS:projection);
        try{
            if(!client.configured())throw new IOException("TeraBox is disconnected");
            final String folder=path(documentId);
            final int offset=args.getInt(PAGE_OFFSET,-1);
            final int limit=args.getInt(PAGE_LIMIT,INDEX_PAGE_SIZE);
            // 400 rows fit comfortably in an Android Binder cursor, so
            // AsterionCore can consume four metadata pages per IPC query.
            if(offset<0||offset%INDEX_PAGE_SIZE!=0||
               (limit!=INDEX_PAGE_SIZE&&limit!=4*INDEX_PAGE_SIZE)||
               offset/INDEX_PAGE_SIZE>=100000)
                throw new IOException("Invalid paged directory query");
            final int firstPage=offset/INDEX_PAGE_SIZE+1;
            boolean ready=true;
            boolean terminal=false;
            for(int i=0;i<limit/INDEX_PAGE_SIZE;i++){
                int page=firstPage+i;
                String key=pageKey(folder,page);
                File cache=pageFile(key);
                JSONArray cached=readMetadataPage(cache);
                boolean stale=cache.isFile()&&
                    System.currentTimeMillis()-cache.lastModified()>METADATA_FRESH_MS;
                if(cached==null||stale)queuePage(folder,page,key,cache);
                if(cached==null){ready=false;continue;}
                for(int j=0;j<cached.length();j++){
                    JSONObject item=cached.optJSONObject(j);
                    if(item==null)continue;
                    String cloudPath=item.optString("path","");
                    if(cloudPath.startsWith("/"))addDocument(rows,item,cloudPath);
                }
                if(cached.length()<INDEX_PAGE_SIZE){terminal=true;break;}
            }
            if(!terminal && firstPage+limit/INDEX_PAGE_SIZE<99998){
                for(int lookahead=0;lookahead<2;lookahead++){
                    int next=firstPage+limit/INDEX_PAGE_SIZE+lookahead;
                    String key=pageKey(folder,next),name=key;
                    File file=pageFile(name);
                    if(!file.isFile()||
                       System.currentTimeMillis()-file.lastModified()>METADATA_FRESH_MS)
                        queuePage(folder,next,key,file);
                }
            }
            Bundle result=new Bundle();
            result.putBoolean(DocumentsContract.EXTRA_LOADING,!ready);
            result.putBoolean("asterion.page.ready",ready);
            result.putInt("asterion.page.number",firstPage);
            result.putInt("asterion.page.size",limit);
            rows.setExtras(result);
            rows.setNotificationUri(getContext().getContentResolver(),
                DocumentsContract.buildChildDocumentsUri(AUTHORITY,documentId));
            return rows;
        }catch(Exception e){throw unavailable(e);}
    }
    private String pageKey(String folder,int page)throws Exception{
        String scope=client.metadataScope();
        if(scope==null||scope.isEmpty())throw new IOException("No TeraBox session scope");
        byte[] digest=MessageDigest.getInstance("SHA-256").digest(
            (scope+"|"+folder+"|"+page).getBytes(StandardCharsets.UTF_8));
        StringBuilder b=new StringBuilder();
        for(byte n:digest)b.append(String.format(Locale.ROOT,"%02x",n&255));
        return b.toString();
    }
    private File pageFile(String key)throws IOException{
        File dir=new File(getContext().getFilesDir(),"terabox-metadata-v1");
        if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Cannot create private metadata index");
        return new File(dir,key+".json");
    }
    private JSONArray readMetadataPage(File cache){
        if(!cache.isFile()||cache.length()>256*1024)return null;
        try{
            byte[] bytes=new byte[(int)cache.length()];
            try(java.io.FileInputStream input=new java.io.FileInputStream(cache)){
                int pos=0;
                while(pos<bytes.length){
                    int got=input.read(bytes,pos,bytes.length-pos);
                    if(got<0)throw new IOException("Incomplete metadata page");
                    pos+=got;
                }
            }
            return new JSONArray(new String(bytes,StandardCharsets.UTF_8));
        }catch(Exception e){
            cache.delete();
            return null;
        }
    }
    private void queuePage(String folder,int page,String key,File file){
        long now=android.os.SystemClock.elapsedRealtime();
        if(now<failedPages.getOrDefault(key,0L)||!pageFlights.add(key))return;
        pageWorkers.execute(()->{
            try{
                // Reuse the SAME native TeraBox metadata cache as Rounder browsing.
                JSONArray cloud=client.listPageCached(folder,page);
                JSONArray minimal=new JSONArray();
                for(int i=0;i<cloud.length();i++){
                    JSONObject item=cloud.optJSONObject(i);
                    if(item==null)continue;
                    String full=item.optString("path","");
                    if(!full.startsWith("/"))continue;
                    JSONObject kept=new JSONObject();
                    kept.put("path",full);
                    kept.put("server_filename",item.optString("server_filename",""));
                    kept.put("isdir",item.optInt("isdir",0));
                    kept.put("size",item.optLong("size",-1L));
                    kept.put("server_mtime",item.optLong("server_mtime",0L));
                    minimal.put(kept);
                }
                // Write metadata only (no thumbnails/original bytes), atomically.
                File temp=new File(file.getParentFile(),key+".part");
                byte[] bytes=minimal.toString().getBytes(StandardCharsets.UTF_8);
                if(bytes.length>256*1024)throw new IOException("Metadata page exceeded size limit");
                try(FileOutputStream stream=new FileOutputStream(temp)){
                    stream.write(bytes);stream.getFD().sync();
                }
                if(!temp.renameTo(file)){
                    if(file.exists()&&!file.delete()||!temp.renameTo(file))
                        throw new IOException("Unable to store metadata page");
                }
                failedPages.remove(key);
            }catch(Exception ex){
                failedPages.put(key,android.os.SystemClock.elapsedRealtime()+5000L);
                android.util.Log.w("FG_TERA_PROVIDER",
                    "Metadata page temporarily unavailable "+ex.getClass().getSimpleName());
            }finally{
                pageFlights.remove(key);
                try{getContext().getContentResolver().notifyChange(
                    DocumentsContract.buildChildDocumentsUri(AUTHORITY,"tb:"+folder),null);
                }catch(Exception ignored){}
            }
        });
        // Fetch the next two pages concurrently, but only on the foreground
        // consumer's request; avoid 100K unbounded queued tasks.
        if(page==1||page%4==0) android.util.Log.d("FG_TERA_PROVIDER","Paged metadata fetch active");
    }
    @Override public Cursor queryChildDocuments(String parentDocumentId,String[] projection,String sortOrder)
            throws java.io.FileNotFoundException {
        MatrixCursor rows=new MatrixCursor(projection==null?DOC_COLUMNS:projection);
        try{
            String folder=path(parentDocumentId);
            int page=firstPage(parentDocumentId);
            String group=folder+"#"+page;
            ArrayList<JSONObject> snapshot;
            boolean loading;
            boolean hasNext;
            synchronized(foldersLock){
                ArrayList<JSONObject> existing=folderRows.get(group);
                snapshot=existing==null?new ArrayList<>():new ArrayList<>(existing);
                loading=!listed.contains(group);
                hasNext=folderHasNext.contains(group);
                long retry=retryAfter.getOrDefault(group,0L);
                if(loading && android.os.SystemClock.elapsedRealtime()>=retry &&
                   listingInProgress.add(group))
                    listingWorker.execute(()->fetchChildren(folder,page,parentDocumentId,group));
            }
            for(JSONObject item:snapshot){
                String p=item.optString("path","");
                if(p.startsWith("/"))addDocument(rows,item,p);
            }
            // SAF cursors cannot contain 300K rows. The next group appears
            // as a real, navigable folder once the current group completes.
            if(hasNext)addContinuation(rows,folder,page+SAF_PAGES_PER_GROUP);
            Bundle extras=new Bundle();
            extras.putBoolean(DocumentsContract.EXTRA_LOADING,loading);
            rows.setExtras(extras);
            rows.setNotificationUri(getContext().getContentResolver(),
                DocumentsContract.buildChildDocumentsUri(AUTHORITY,parentDocumentId));
            return rows;
        }catch(Exception ex){throw unavailable(ex);}
    }
    private void fetchChildren(String folder,int firstPage,String documentId,String group){
        final Uri uri=DocumentsContract.buildChildDocumentsUri(AUTHORITY,documentId);
        boolean success=false;
        boolean continuation=false;
        try{
            // Four 100-item metadata pages per group, asynchronously
            // notifying the Android picker after every successful page.
            for(int page=firstPage;page<firstPage+SAF_PAGES_PER_GROUP;page++){
                JSONArray batch=client.listPageCached(folder,page);
                synchronized(foldersLock){
                    ArrayList<JSONObject> rows=folderRows.computeIfAbsent(group,k->new ArrayList<>());
                    for(int i=0;i<batch.length() && rows.size()<SAF_MAX_VISIBLE;i++){
                        JSONObject item=batch.optJSONObject(i);
                        if(item==null)continue;
                        String p=item.optString("path","");
                        if(!p.startsWith("/"))continue;
                        rows.add(item);
                        knownItems.put(p,item);
                    }
                }
                getContext().getContentResolver().notifyChange(uri,null);
                if(batch.length()<FgTeraboxClient.pageSize())break;
                if(page==firstPage+SAF_PAGES_PER_GROUP-1)continuation=true;
            }
            success=true;
        }catch(Exception ex){
            android.util.Log.w("FG_TERA_PROVIDER","Cloud listing deferred: "+ex.getClass().getSimpleName());
        }finally{
            synchronized(foldersLock){
                listingInProgress.remove(group);
                if(success){
                    listed.add(group);
                    if(continuation)folderHasNext.add(group);
                    else folderHasNext.remove(group);
                    retryAfter.remove(group);
                }else{
                    listed.remove(group);
                    retryAfter.put(group,
                        android.os.SystemClock.elapsedRealtime()+5000L);
                }
            }
            getContext().getContentResolver().notifyChange(uri,null);
        }
    }
    @Override public boolean isChildDocument(String parentDocumentId, String documentId) {
        try {
            String parent = path(parentDocumentId), child = path(documentId);
            if(isContinuation(documentId))
                return parent.equals(child)&&firstPage(documentId)>firstPage(parentDocumentId);
            return child.startsWith(parent.equals("/") ? "/" : parent + "/") && !child.equals(parent);
        } catch (IOException ignored) { return false; }
    }
    @Override public String getDocumentType(String documentId) throws java.io.FileNotFoundException {
        try{
            String p=path(documentId);
            if("/".equals(p)||isContinuation(documentId))
                return DocumentsContract.Document.MIME_TYPE_DIR;
            JSONObject item;
            synchronized(foldersLock){item=knownItems.get(p);}
            if(item!=null && item.optInt("isdir",0)!=0)
                return DocumentsContract.Document.MIME_TYPE_DIR;
            return FgTeraboxClient.mime(p);
        }catch(Exception ex){throw unavailable(ex);}
    }
    @Override public ParcelFileDescriptor openDocument(String documentId, String mode, CancellationSignal signal)
            throws java.io.FileNotFoundException {
        if (!"r".equals(mode)) throw new java.io.FileNotFoundException("Cloud provider is read-only");
        try {
            if(isContinuation(documentId))throw new IOException("Cannot open a pagination folder as a file");
            String cloudPath = path(documentId);
            long size=hintedLength(documentId);
            if(size<0){
                JSONObject details=client.fileDetails(cloudPath);
                if(details.optInt("isdir",0)!=0)throw new IOException("Cannot open a cloud folder");
                size=details.optLong("size",-1);
            }
            if(size<0)throw new IOException("TeraBox did not supply a valid file length");
            final long fileSize=size;
            StorageManager storage = (StorageManager)getContext().getSystemService(Context.STORAGE_SERVICE);
            return storage.openProxyFileDescriptor(ParcelFileDescriptor.MODE_READ_ONLY,
                new ProxyFileDescriptorCallback() {
                    private long blockOffset = -1;
                    private byte[] block;
                    @Override public long onGetSize() { return fileSize; }
                    @Override public synchronized int onRead(long offset, int request, byte[] data)
                            throws android.system.ErrnoException {
                        try {
                            if (signal != null && signal.isCanceled()) throw new IOException("Read cancelled");
                            if (request == 0 || offset >= fileSize) return 0;
                            if (offset < 0) throw new IOException("Negative file offset");
                            int remaining = (int)Math.min(request, fileSize - offset);
                            int done = 0;
                            while (done < remaining) {
                                long position = offset + done;
                                if (block == null || position < blockOffset ||
                                    position >= blockOffset + block.length) {
                                    blockOffset = position;
                                    // Larger image entries in ZIP64 may need many sequential
                                    // byte ranges. Cache a bounded 2 MiB cloud block
                                    // in memory only; do not write page data to disk.
                                    long blockSize=cloudPath.toLowerCase(java.util.Locale.ROOT)
                                        .matches(".*\\.(zip|cbz|epub)$")?2L*1024*1024:512L*1024;
                                    int fetch = (int)Math.min(blockSize, fileSize - position);
                                    block = client.readRange(cloudPath, position, fetch);
                                    if (block.length == 0) throw new IOException("Unexpected end of cloud file");
                                }
                                int index = (int)(position - blockOffset);
                                int count = Math.min(remaining - done, block.length - index);
                                System.arraycopy(block, index, data, done, count);
                                done += count;
                            }
                            return done;
                        } catch (Exception ex) {
                            android.util.Log.w("FG_TERA_PROVIDER", "Range read unavailable: " + ex.getClass().getSimpleName());
                            throw new android.system.ErrnoException("TeraBox read", android.system.OsConstants.EIO);
                        }
                    }
                    @Override public void onRelease() { block = null; }
                }, new Handler(workerThread.getLooper()));
        } catch (Exception ex) { throw unavailable(ex); }
    }
    private static java.io.FileNotFoundException unavailable(Exception exception) {
        java.io.FileNotFoundException error = new java.io.FileNotFoundException(
            "TeraBox document unavailable: " + exception.getMessage());
        error.initCause(exception);
        return error;
    }
}

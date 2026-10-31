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
import java.util.Locale;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
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
    private final Map<String,ArrayList<JSONObject>> folderRows=new HashMap<>();
    private final Map<String,JSONObject> knownItems=new HashMap<>();
    private final Set<String> listingInProgress=new HashSet<>();
    private final Set<String> listed=new HashSet<>();
    private static final int SAF_MAX_VISIBLE=450;


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
    private static String path(String docId) throws IOException {
        if(docId==null)throw new IOException("Missing TeraBox document ID");
        String p;
        if(docId.startsWith("tb2:")){
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
        add(row, rows, DocumentsContract.Document.COLUMN_DOCUMENT_ID, "tb:" + cloudPath);
        add(row, rows, DocumentsContract.Document.COLUMN_DISPLAY_NAME, name);
        add(row, rows, DocumentsContract.Document.COLUMN_MIME_TYPE,
            dir ? DocumentsContract.Document.MIME_TYPE_DIR : FgTeraboxClient.mime(name));
        if (!dir) add(row, rows, DocumentsContract.Document.COLUMN_SIZE, item.optLong("size", -1));
        add(row, rows, DocumentsContract.Document.COLUMN_LAST_MODIFIED,
            item.optLong("server_mtime", 0) * 1000L);
        add(row, rows, DocumentsContract.Document.COLUMN_FLAGS, 0);
    }
    @Override public Cursor queryDocument(String documentId, String[] projection)
            throws java.io.FileNotFoundException {
        MatrixCursor rows = new MatrixCursor(projection == null ? DOC_COLUMNS : projection);
        try {
            String p = path(documentId);
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
    @Override public Cursor queryChildDocuments(String parentDocumentId,String[] projection,String sortOrder)
            throws java.io.FileNotFoundException {
        MatrixCursor rows=new MatrixCursor(projection==null?DOC_COLUMNS:projection);
        try{
            String folder=path(parentDocumentId);
            ArrayList<JSONObject> snapshot;
            boolean loading;
            synchronized(foldersLock){
                ArrayList<JSONObject> existing=folderRows.get(folder);
                snapshot=existing==null?new ArrayList<>():new ArrayList<>(existing);
                loading=!listed.contains(folder);
                if(loading && listingInProgress.add(folder))
                    listingWorker.execute(()->fetchChildren(folder));
            }
            for(JSONObject item:snapshot){
                String p=item.optString("path","");
                if(p.startsWith("/"))addDocument(rows,item,p);
            }
            Bundle extras=new Bundle();
            extras.putBoolean(DocumentsContract.EXTRA_LOADING,loading);
            rows.setExtras(extras);
            rows.setNotificationUri(getContext().getContentResolver(),
                DocumentsContract.buildChildDocumentsUri(AUTHORITY,parentDocumentId));
            return rows;
        }catch(Exception ex){throw unavailable(ex);}
    }
    private void fetchChildren(String folder){
        final Uri uri=DocumentsContract.buildChildDocumentsUri(AUTHORITY,"tb:"+folder);
        try{
            // The native library offers full pagination. This SAF adapter
            // deliberately caps a Binder cursor below Android's transaction
            // limit and never blocks a system thread for network traversal.
            for(int page=1;page<=5;page++){
                JSONArray batch=client.listPage(folder,page);
                synchronized(foldersLock){
                    ArrayList<JSONObject> rows=folderRows.computeIfAbsent(folder,k->new ArrayList<>());
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
            }
        }catch(Exception ex){
            android.util.Log.w("FG_TERA_PROVIDER","Cloud listing deferred: "+ex.getClass().getSimpleName());
        }finally{
            synchronized(foldersLock){
                listingInProgress.remove(folder);
                listed.add(folder);
            }
            getContext().getContentResolver().notifyChange(uri,null);
        }
    }
    @Override public boolean isChildDocument(String parentDocumentId, String documentId) {
        try {
            String parent = path(parentDocumentId), child = path(documentId);
            return child.startsWith(parent.equals("/") ? "/" : parent + "/") && !child.equals(parent);
        } catch (IOException ignored) { return false; }
    }
    @Override public String getDocumentType(String documentId) throws java.io.FileNotFoundException {
        try{
            String p=path(documentId);
            if("/".equals(p))return DocumentsContract.Document.MIME_TYPE_DIR;
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
                                    int fetch = (int)Math.min(512 * 1024L, fileSize - position);
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

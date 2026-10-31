package com.openlocal.office.core;

import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.provider.OpenableColumns;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Read-only SAF bookshelf: no whole-book copies, no source modifications,
 * no network/third-party service. Enumerate only the selected folder and page.
 */
public final class ReaderLibrary {
    public static final int PAGE_SIZE=500;
    public static final class Listing {
        public final JSONArray items;
        public final String folder;
        Listing(String folder,JSONArray items){this.folder=folder;this.items=items;}
    }
    private ReaderLibrary(){}
    public static final class PendingDirectoryException extends java.io.IOException {
        public final boolean loading;
        public PendingDirectoryException(boolean loading,String message){
            super(message);this.loading=loading;
        }
    }
    /** Emit bounded metadata batches while a SAF provider is still enumerating.
     * No 500-file ceiling, no up-front cover downloads, no all-files JSON.
     * Providers that yield cursor rows incrementally show the first batch early.
     */
    public interface BatchSink {
        void accept(String folderId,JSONArray batch,boolean finished) throws Exception;
    }
    public static Listing stream(Context ctx,Uri tree,String folderId,
                                 BatchSink sink) throws Exception {
        final String root=DocumentsContract.getTreeDocumentId(tree);
        final String id=folderId==null||folderId.isBlank()?root:folderId;
        final Uri treeChildren=DocumentsContract.buildChildDocumentsUriUsingTree(tree,id);
        final String[] projection={DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED};
        // RoundSync's DocumentsProvider returns an empty ExtrasMatrixCursor
        // with EXTRA_LOADING or EXTRA_ERROR when its rclone request times
        // out. It is not evidence that an image directory is empty.
        Cursor cursor=null;
        boolean isRoundSync="de.felixnuesse.extract.vcp".equals(tree.getAuthority());
        String providerError=null;
        boolean providerLoading=false;
        final long started=android.os.SystemClock.elapsedRealtime();
        try {
            cursor=ctx.getContentResolver().query(treeChildren,projection,null,null,null);
            if(cursor!=null){
                android.os.Bundle extras=cursor.getExtras();
                if(extras!=null){
                    providerLoading=extras.getBoolean(DocumentsContract.EXTRA_LOADING,false);
                    providerError=extras.getString(DocumentsContract.EXTRA_ERROR);
                }
            }
            if(cursor==null){
                throw new java.io.IOException("Storage provider did not return a cursor");
            }
            if(!cursor.moveToFirst()){
                cursor.close();cursor=null;
                String hint=providerError==null?"Provider returned no results":providerError;
                android.util.Log.w("FG_FOLDER","SAF_EMPTY status="+
                    (providerLoading?"loading":"not-loading")+" elapsed_ms="+
                    (android.os.SystemClock.elapsedRealtime()-started)+
                    " authority="+tree.getAuthority()+" providerMessage="+hint);
                if(isRoundSync && (providerLoading||providerError!=null)){
                    throw new PendingDirectoryException(providerLoading,
                        "RoundSync is still loading or could not list this cloud folder: "+hint);
                }
                sink.accept(id,new JSONArray(),true);
                return new Listing(id,new JSONArray());
            }
        }catch(Exception e){
            if(cursor!=null)cursor.close();
            throw e;
        }
        android.util.Log.i("FG_FOLDER","SAF_CHILDREN_SELECTED method=tree"+
            " elapsed_ms="+(android.os.SystemClock.elapsedRealtime()-started));
        int rows=0;
        JSONArray batch=new JSONArray();
        boolean firstBatch=true;
        try(Cursor items=cursor){
            final int ixId=items.getColumnIndex(DocumentsContract.Document.COLUMN_DOCUMENT_ID);
            final int ixName=items.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME);
            final int ixMime=items.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE);
            final int ixSize=items.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE);
            final int ixModified=items.getColumnIndex(DocumentsContract.Document.COLUMN_LAST_MODIFIED);
            if(ixId<0||ixName<0)throw new java.io.IOException(
                "Storage provider omitted file ID or name");
            do{
                if(items.isNull(ixId)||items.isNull(ixName))continue;
                final String did=items.getString(ixId),name=items.getString(ixName);
                if(name==null||name.isBlank()||did==null||did.isBlank())continue;
                final String mime=ixMime>=0&&!items.isNull(ixMime)?
                    items.getString(ixMime):"application/octet-stream";
                final boolean folder=DocumentsContract.Document.MIME_TYPE_DIR.equals(mime);
                JSONObject item=new JSONObject();
                item.put("id",did).put("title",stripExtension(name))
                    .put("name",name).put("mime",mime)
                    .put("folder",folder)
                    .put("size",ixSize>=0&&!items.isNull(ixSize)?items.getLong(ixSize):-1L)
                    .put("modified",ixModified>=0&&!items.isNull(ixModified)?
                        items.getLong(ixModified):0L)
                    .put("uri",DocumentsContract.buildDocumentUriUsingTree(tree,did).toString());
                batch.put(item);
                rows++;
                if(batch.length()>=(firstBatch?1:48)){
                    sink.accept(id,batch,false);
                    firstBatch=false;
                    batch=new JSONArray();
                }
            }while(items.moveToNext());
        }
        sink.accept(id,batch,true);
        android.util.Log.i("FG_FOLDER","SAF_METADATA_FINISHED count="+rows+
            " authority="+tree.getAuthority());
        return new Listing(id,new JSONArray());
    }

    public static Listing list(Context ctx,Uri tree,String folderId) throws Exception{
        String root=DocumentsContract.getTreeDocumentId(tree);
        String id=folderId==null||folderId.isBlank()?root:folderId;
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,id);
        String[] cols={
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED
        };
        JSONArray array=new JSONArray();
        try(Cursor cursor=ctx.getContentResolver().query(children,cols,null,null,null)){
            if(cursor==null)throw new java.io.IOException("The folder provider did not return files");
            int total=0;
            while(cursor.moveToNext()){
                String did=cursor.getString(0),name=cursor.getString(1),mime=cursor.getString(2);
                if(name==null||did==null||mime==null)continue;
                boolean folder=DocumentsContract.Document.MIME_TYPE_DIR.equals(mime);
                String lower=name.toLowerCase(Locale.ROOT);
                // Even unsupported file types must remain visible in directory listings.
                JSONObject item=new JSONObject();
                item.put("id",did).put("title",stripExtension(name))
                    .put("name",name).put("mime",mime)
                    .put("folder",folder)
                    .put("size",cursor.isNull(3)?-1L:cursor.getLong(3))
                    .put("modified",cursor.isNull(4)?0L:cursor.getLong(4));
                item.put("uri",DocumentsContract.buildDocumentUriUsingTree(tree,did).toString());
                array.put(item);
                if(++total>=PAGE_SIZE)break;
            }
        }
        return new Listing(id,array);
    }
    /** First actual image or supported book in a folder. Metadata only:
     * do not download any book while listing a collection.
     */
    public static final class CoverCandidate {
        public final Uri uri;
        public final String name;
        public final long size;
        public final long modified;
        CoverCandidate(Uri uri,String name,long size,long modified){
            this.uri=uri;this.name=name;this.size=size;this.modified=modified;
        }
    }
    public static CoverCandidate firstCover(Context ctx,Uri directory) throws Exception {
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(
            directory,DocumentsContract.getDocumentId(directory));
        String[] cols={DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED};
        String bestId=null,bestName=null;
        long bestSize=-1,bestModified=0;
        try(Cursor cursor=ctx.getContentResolver().query(children,cols,null,null,null)){
            if(cursor==null)return null;
            int scanned=0;
            while(cursor.moveToNext()&&scanned++<2000){
                String id=cursor.getString(0),name=cursor.getString(1),mime=cursor.getString(2);
                if(id==null||name==null||mime==null)continue;
                String low=name.toLowerCase(Locale.ROOT);
                if(name.startsWith(".")||low.startsWith("._")||
                   !(low.endsWith(".jpg")||low.endsWith(".jpeg")||
                     low.endsWith(".png")||low.endsWith(".webp")||
                     low.endsWith(".epub")||low.endsWith(".cbz")||
                     low.endsWith(".zip")||low.endsWith(".pdf")))continue;
                if(bestName==null||naturalCompare(name,bestName)<0){
                    bestName=name;bestId=id;
                    bestSize=cursor.isNull(3)?-1:cursor.getLong(3);
                    bestModified=cursor.isNull(4)?0:cursor.getLong(4);
                }
            }
        }
        return bestId==null?null:new CoverCandidate(
            DocumentsContract.buildDocumentUriUsingTree(directory,bestId),
            bestName,bestSize,bestModified);
    }
    public static int naturalCompare(String a,String b){
        int i=0,j=0;
        while(i<a.length()&&j<b.length()){
            char x=a.charAt(i),y=b.charAt(j);
            if(Character.isDigit(x)&&Character.isDigit(y)){
                int startI=i,startJ=j;
                while(i<a.length()&&Character.isDigit(a.charAt(i)))i++;
                while(j<b.length()&&Character.isDigit(b.charAt(j)))j++;
                String n=a.substring(startI,i).replaceFirst("^0+(?!$)","");
                String m=b.substring(startJ,j).replaceFirst("^0+(?!$)","");
                if(n.length()!=m.length())return Integer.compare(n.length(),m.length());
                int c=n.compareTo(m);if(c!=0)return c;
            }else{
                int c=Character.compare(Character.toLowerCase(x),Character.toLowerCase(y));
                if(c!=0)return c;i++;j++;
            }
        }
        return Integer.compare(a.length(),b.length());
    }
    private static boolean supported(String filename){
        for(String suffix:new String[]{
            ".zip",".cbz",".cbr",".epub",".pdf",".docx",".doc",
            ".xlsx",".xls",".csv",".txt",".md",".rtf",".odt",".ods",
            ".sdocx",".jpg",".jpeg",".png",".webp",".avif",".gif",
            ".mp3",".mp4",".m4a",".webm",".mkv",".mov",
            ".glb",".gltf",".fbx",".obj",".blend",".vrm",".pmx",".pmd"
        })if(filename.endsWith(suffix))return true;
        return false;
    }
    private static String stripExtension(String text){
        int index=text.lastIndexOf('.');
        return index>0?text.substring(0,index):text;
    }
}

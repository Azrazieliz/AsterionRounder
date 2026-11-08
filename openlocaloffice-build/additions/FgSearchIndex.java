package com.openlocal.office.core;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.database.sqlite.SQLiteStatement;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Persistent, read-only metadata index for a user-authorized SAF tree.
 * No file contents are opened. Never traverses storage during a search.
 * A resumable breadth-first scan runs once per tree (or by explicit refresh).
 */
public final class FgSearchIndex extends SQLiteOpenHelper {
    public interface Listener {
        void onResult(String json);
        void onProgress(String json);
    }
    private static final int PAGE=96;
    private static final int BATCH=128;
    private final Context app;
    private final Listener listener;
    private final ExecutorService scanner=Executors.newSingleThreadExecutor();
    private final ExecutorService queries=Executors.newSingleThreadExecutor();
    private final Set<String> scheduled=ConcurrentHashMap.newKeySet();
    private final Set<String> complete=ConcurrentHashMap.newKeySet();
    private final ConcurrentHashMap<String,Long> retryAfter=new ConcurrentHashMap<>();

    public FgSearchIndex(Context app,Listener listener){
        super(app.getApplicationContext(),"rounder-search-v1.db",null,1);
        this.app=app.getApplicationContext();
        this.listener=listener;
        setWriteAheadLoggingEnabled(true);
    }
    @Override public void onCreate(SQLiteDatabase db){
        db.execSQL("CREATE TABLE roots (root TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0, building INTEGER NOT NULL DEFAULT 0, seen INTEGER NOT NULL DEFAULT 0, error TEXT)");
        db.execSQL("CREATE TABLE files (root TEXT NOT NULL, generation INTEGER NOT NULL, doc TEXT NOT NULL, name TEXT NOT NULL, lookup TEXT NOT NULL, mime TEXT, kind TEXT NOT NULL, folder INTEGER NOT NULL, size INTEGER, modified INTEGER, parent_path TEXT NOT NULL, PRIMARY KEY(root,generation,doc))");
        db.execSQL("CREATE INDEX files_name ON files(root,generation,lookup)");
        db.execSQL("CREATE INDEX files_kind ON files(root,generation,kind,lookup)");
        db.execSQL("CREATE TABLE pending (root TEXT NOT NULL, generation INTEGER NOT NULL, doc TEXT NOT NULL, path TEXT NOT NULL, PRIMARY KEY(root,generation,doc))");
    }
    @Override public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion){
        throw new IllegalStateException("Search index migration required");
    }
    private static final class State {
        int active,building;
        long seen;
        String error="";
    }
    private static State state(SQLiteDatabase db,String root){
        State value=new State();
        try(Cursor c=db.rawQuery("SELECT active,building,seen,error FROM roots WHERE root=?",new String[]{root})){
            if(c.moveToFirst()){
                value.active=c.getInt(0);value.building=c.getInt(1);
                value.seen=c.getLong(2);value.error=c.isNull(3)?"":c.getString(3);
            }
        }
        return value;
    }
    private static void execute(SQLiteDatabase db,String sql,Object[] bindings){
        db.execSQL(sql,bindings);
    }
    private static final class Folder {
        final String id,path;
        Folder(String id,String path){this.id=id;this.path=path;}
    }
    private static Folder next(SQLiteDatabase db,String root,int generation){
        try(Cursor c=db.rawQuery("SELECT doc,path FROM pending WHERE root=? AND generation=? LIMIT 1",
                new String[]{root,Integer.toString(generation)})){
            return c.moveToFirst()?new Folder(c.getString(0),c.getString(1)):null;
        }
    }
    public void ensure(Uri tree,boolean force){
        if(tree==null)return;
        final String root=tree.toString();
        if(!force && complete.contains(root))return;
        if(!force && System.currentTimeMillis()<retryAfter.getOrDefault(root,0L))return;
        if(!scheduled.add(root))return;
        if(force)complete.remove(root);
        scanner.execute(()->{
            try{build(tree,force);}
            catch(Exception error){
                retryAfter.put(root,System.currentTimeMillis()+60000L);
                android.util.Log.e("FG_SEARCH","Persistent index paused",error);
                try{
                    execute(getWritableDatabase(),
                        "UPDATE roots SET error=? WHERE root=?",
                        new Object[]{String.valueOf(error.getMessage()),root});
                    progress(root);
                }catch(Exception ignored){}
            }finally{scheduled.remove(root);}
        });
    }
    private void build(Uri tree,boolean force) throws Exception {
        final String root=tree.toString();
        final SQLiteDatabase db=getWritableDatabase();
        State s=state(db,root);
        int generation=s.building;
        if(force || (s.active==0 && generation==0)){
            generation=Math.max(s.active,s.building)+1;
            db.beginTransactionNonExclusive();
            try{
                execute(db,"INSERT OR REPLACE INTO roots(root,active,building,seen,error) VALUES(?,?,?,?,NULL)",
                    new Object[]{root,s.active,generation,0});
                execute(db,"DELETE FROM pending WHERE root=?",new Object[]{root});
                execute(db,"INSERT INTO pending(root,generation,doc,path) VALUES(?,?,?,?)",
                    new Object[]{root,generation,DocumentsContract.getTreeDocumentId(tree),""});
                db.setTransactionSuccessful();
            }finally{db.endTransaction();}
        }else if(generation==0){
            complete.add(root);
            return;
        }
        progress(root);
        Folder folder;
        while((folder=next(db,root,generation))!=null){
            boolean success=false;
            Exception last=null;
            for(int attempt=0;attempt<3&&!success;attempt++){
                try{
                    visit(tree,root,generation,folder,db);
                    success=true;
                }catch(Exception error){
                    last=error;
                    if(attempt<2)Thread.sleep((attempt+1)*1200L);
                }
            }
            if(!success)throw last==null?new java.io.IOException("Unable to index directory"):last;
            execute(db,"DELETE FROM pending WHERE root=? AND generation=? AND doc=?",
                new Object[]{root,generation,folder.id});
            progress(root);
        }
        db.beginTransactionNonExclusive();
        try{
            execute(db,"UPDATE roots SET active=?,building=0,error=NULL WHERE root=?",
                new Object[]{generation,root});
            execute(db,"DELETE FROM files WHERE root=? AND generation<>?",
                new Object[]{root,generation});
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
        complete.add(root);
        retryAfter.remove(root);
        progress(root);
        android.util.Log.i("FG_SEARCH","Index complete root="+tree.getAuthority());
    }
    private static final String[] COLUMNS={
        DocumentsContract.Document.COLUMN_DOCUMENT_ID,
        DocumentsContract.Document.COLUMN_DISPLAY_NAME,
        DocumentsContract.Document.COLUMN_MIME_TYPE,
        DocumentsContract.Document.COLUMN_SIZE,
        DocumentsContract.Document.COLUMN_LAST_MODIFIED
    };
    private static final class Entry {
        String id,name,mime,kind,path;
        boolean folder;
        long size,modified;
    }
    private void visit(Uri tree,String root,int generation,Folder folder,SQLiteDatabase db)
            throws Exception {
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,folder.id);
        ArrayList<Entry> batch=new ArrayList<>(BATCH);
        try(Cursor cursor=app.getContentResolver().query(children,COLUMNS,null,null,null)){
            if(cursor==null)throw new java.io.IOException("Provider returned no cursor");
            final int id=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DOCUMENT_ID);
            final int name=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME);
            final int mime=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE);
            final int size=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE);
            final int modified=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_LAST_MODIFIED);
            if(id<0||name<0)throw new java.io.IOException("Provider omitted required metadata");
            while(cursor.moveToNext()){
                if(cursor.isNull(id)||cursor.isNull(name))continue;
                Entry e=new Entry();
                e.id=cursor.getString(id);e.name=cursor.getString(name);
                if(e.id==null||e.id.isEmpty()||e.name==null||e.name.isEmpty())continue;
                e.mime=mime<0||cursor.isNull(mime)?"application/octet-stream":cursor.getString(mime);
                e.folder=DocumentsContract.Document.MIME_TYPE_DIR.equals(e.mime);
                e.kind=e.folder?"folder":kind(e.name);
                e.path=folder.path;
                e.size=size<0||cursor.isNull(size)?-1:cursor.getLong(size);
                e.modified=modified<0||cursor.isNull(modified)?0:cursor.getLong(modified);
                batch.add(e);
                if(batch.size()>=BATCH){save(db,root,generation,batch);batch.clear();}
            }
            Bundle extras=cursor.getExtras();
            if(extras!=null&&(extras.getBoolean(DocumentsContract.EXTRA_LOADING,false)||
                extras.getString(DocumentsContract.EXTRA_ERROR)!=null))
                throw new java.io.IOException("Provider directory listing is still loading");
        }
        if(!batch.isEmpty())save(db,root,generation,batch);
    }
    private void save(SQLiteDatabase db,String root,int generation,ArrayList<Entry> batch){
        db.beginTransactionNonExclusive();
        try{
            SQLiteStatement insert=db.compileStatement(
                "INSERT OR REPLACE INTO files(root,generation,doc,name,lookup,mime,kind,folder,size,modified,parent_path) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
            SQLiteStatement folder=db.compileStatement(
                "INSERT OR IGNORE INTO pending(root,generation,doc,path) VALUES(?,?,?,?)");
            try{
                for(Entry e:batch){
                    insert.clearBindings();
                    insert.bindString(1,root);insert.bindLong(2,generation);
                    insert.bindString(3,e.id);insert.bindString(4,e.name);
                    insert.bindString(5,e.name.toLowerCase(Locale.ROOT));
                    insert.bindString(6,e.mime);insert.bindString(7,e.kind);
                    insert.bindLong(8,e.folder?1:0);
                    insert.bindLong(9,e.size);insert.bindLong(10,e.modified);
                    insert.bindString(11,e.path);insert.executeInsert();
                    if(e.folder){
                        folder.clearBindings();
                        folder.bindString(1,root);folder.bindLong(2,generation);
                        folder.bindString(3,e.id);
                        folder.bindString(4,e.path.isEmpty()?e.name:e.path+"/"+e.name);
                        folder.executeInsert();
                    }
                }
            }finally{insert.close();folder.close();}
            execute(db,"UPDATE roots SET seen=seen+? WHERE root=?",
                new Object[]{batch.size(),root});
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
    }
    private static String kind(String name){
        String n=name.toLowerCase(Locale.ROOT);
        if(n.matches(".*\\.(cbz|cbr)$"))return "comic";
        if(n.matches(".*\\.(zip|7z|rar|tar|gz)$"))return "archive";
        if(n.endsWith(".epub"))return "book";
        if(n.endsWith(".pdf"))return "pdf";
        if(n.matches(".*\\.(png|jpe?g|webp|avif|gif|bmp)$"))return "image";
        if(n.matches(".*\\.(mp4|webm|mkv|mov|avi)$"))return "video";
        if(n.matches(".*\\.(mp3|m4a|flac|wav|ogg|opus)$"))return "audio";
        if(n.matches(".*\\.(glb|gltf|fbx|obj|vrm|blend|pmx|pmd)$"))return "model";
        if(n.matches(".*\\.(docx?|xlsx?|csv|txt|md|rtf|odt|ods|sdocx|pptx?)$"))return "document";
        return "file";
    }
    private static String escapeLike(String s){
        return s.replace("\\","\\\\").replace("%","\\%").replace("_","\\_");
    }
    public void search(Uri tree,String phrase,String filter,int offset,int request){
        if(tree==null)return;
        ensure(tree,false);
        queries.execute(()->{
            try {
                String root=tree.toString();
                SQLiteDatabase db=getReadableDatabase();
                State state=state(db,root);
                int gen=state.active>0?state.active:state.building;
                JSONObject reply=new JSONObject();
                reply.put("token",request).put("offset",Math.max(0,offset))
                    .put("indexed",state.seen).put("building",state.building!=0)
                    .put("error",state.error);
                JSONArray rows=new JSONArray();
                boolean more=false;
                if(gen!=0 && phrase!=null && !phrase.trim().isEmpty()){
                    String sql="SELECT doc,name,mime,kind,folder,size,modified,parent_path FROM files WHERE root=? AND generation=? AND lookup LIKE ? ESCAPE '\\'";
                    ArrayList<String> args=new ArrayList<>();
                    args.add(root);args.add(Integer.toString(gen));
                    args.add("%"+escapeLike(phrase.trim().toLowerCase(Locale.ROOT))+"%");
                    if(filter!=null&&!filter.equals("all")&&!filter.isEmpty()){
                        sql+=" AND kind=?";args.add(filter);
                    }
                    sql+=" ORDER BY lookup,doc LIMIT ? OFFSET ?";
                    args.add(Integer.toString(PAGE+1));
                    args.add(Integer.toString(Math.max(0,offset)));
                    try(Cursor c=db.rawQuery(sql,args.toArray(new String[0]))){
                        int count=0;
                        while(c.moveToNext()){
                            if(++count>PAGE){more=true;break;}
                            String doc=c.getString(0),name=c.getString(1);
                            String path=c.getString(7);
                            int dot=name.lastIndexOf('.');
                            JSONObject item=new JSONObject();
                            item.put("id",doc).put("name",name)
                                .put("title",dot>0?name.substring(0,dot):name)
                                .put("mime",c.getString(2)).put("category",c.getString(3))
                                .put("folder",c.getInt(4)!=0)
                                .put("size",c.getLong(5)).put("modified",c.getLong(6))
                                .put("searchPath",path).put("indexedSearch",true)
                                .put("uri",DocumentsContract.buildDocumentUriUsingTree(tree,doc).toString());
                            rows.put(item);
                        }
                    }
                }
                reply.put("items",rows).put("hasMore",more);
                listener.onResult(reply.toString());
            }catch(Exception error){
                android.util.Log.e("FG_SEARCH","Query failed",error);
                try{listener.onResult(new JSONObject().put("token",request)
                    .put("items",new JSONArray()).put("error",
                        String.valueOf(error.getMessage())).toString());}
                catch(Exception ignored){}
            }
        });
    }
    public boolean contains(Uri tree,String id){
        if(tree==null||id==null||id.isBlank())return false;
        try{
            SQLiteDatabase db=getReadableDatabase();
            State s=state(db,tree.toString());
            int gen=s.active>0?s.active:s.building;
            if(gen==0)return false;
            try(Cursor c=db.rawQuery("SELECT 1 FROM files WHERE root=? AND generation=? AND doc=? LIMIT 1",
                    new String[]{tree.toString(),Integer.toString(gen),id})){
                return c.moveToFirst();
            }
        }catch(Exception error){return false;}
    }
    private void progress(String root){
        try{
            State s=state(getReadableDatabase(),root);
            listener.onProgress(new JSONObject().put("root",root)
                .put("indexed",s.seen).put("building",s.building!=0)
                .put("error",s.error).toString());
        }catch(Exception ignored){}
    }
}
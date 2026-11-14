package com.openlocal.office.core;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.database.sqlite.SQLiteStatement;
import android.net.Uri;
import android.os.SystemClock;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** A persistent filename/metadata index for an authenticated TeraBox account.
 * The web-cookie is owned exclusively by FgTeraboxClient. Search never contacts
 * TeraBox: a background paged scan builds an incremental, resumable local index.
 * Never downloads source media, stores credentials, or deletes cloud files.
 */
public final class FgTeraboxSearchIndex extends SQLiteOpenHelper {
    public interface Listener {
        void onSearch(String response);
        void onProgress(String response);
    }
    private static final int LIMIT=96;
    private final FgTeraboxClient cloud;
    private final Listener listener;
    private final ExecutorService scanner=Executors.newSingleThreadExecutor();
    private final ExecutorService queries=Executors.newSingleThreadExecutor();
    private final Set<String> running=ConcurrentHashMap.newKeySet();
    private final ConcurrentHashMap<String,Long> retryAfter=new ConcurrentHashMap<>();
    private volatile long lastProgressMs=0;

    public FgTeraboxSearchIndex(Context context,FgTeraboxClient cloud,Listener listener) {
        super(context.getApplicationContext(),"rounder-terabox-search-v1.db",null,3);
        this.cloud=cloud;
        this.listener=listener;
        setWriteAheadLoggingEnabled(true);
    }
    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE accounts (scope TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0, building INTEGER NOT NULL DEFAULT 0, indexed INTEGER NOT NULL DEFAULT 0, error TEXT)");
        db.execSQL("CREATE TABLE objects (scope TEXT NOT NULL, generation INTEGER NOT NULL, path TEXT NOT NULL, name TEXT NOT NULL, needle TEXT NOT NULL, kind TEXT NOT NULL, folder INTEGER NOT NULL, size INTEGER, modified INTEGER, parent TEXT NOT NULL, checksum TEXT, listing_page INTEGER NOT NULL DEFAULT 1, preview_missing INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,generation,path))");
        db.execSQL("CREATE INDEX objects_lookup ON objects(scope,generation,needle)");
        db.execSQL("CREATE INDEX objects_type ON objects(scope,generation,kind)");
        db.execSQL("CREATE INDEX objects_exact ON objects(scope,generation,checksum,size)");
        db.execSQL("CREATE INDEX objects_candidates ON objects(scope,generation,needle,size)");
        db.execSQL("CREATE TABLE pending (scope TEXT NOT NULL, generation INTEGER NOT NULL, path TEXT NOT NULL, page INTEGER NOT NULL, PRIMARY KEY(scope,generation,path))");
        db.execSQL("CREATE INDEX objects_preview ON objects(scope,generation,kind,preview_missing)");
        db.execSQL("CREATE TABLE preview_marks (scope TEXT NOT NULL, path TEXT NOT NULL, marked INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(scope,path))");
    }
    @Override public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion){
        if(oldVersion<2){
            db.execSQL("ALTER TABLE objects ADD COLUMN checksum TEXT");
            db.execSQL("ALTER TABLE objects ADD COLUMN listing_page INTEGER NOT NULL DEFAULT 1");
            db.execSQL("CREATE INDEX objects_exact ON objects(scope,generation,checksum,size)");
            db.execSQL("CREATE INDEX objects_candidates ON objects(scope,generation,needle,size)");
        }
        if(oldVersion<3){
            db.execSQL("ALTER TABLE objects ADD COLUMN preview_missing INTEGER NOT NULL DEFAULT 0");
            db.execSQL("CREATE INDEX objects_preview ON objects(scope,generation,kind,preview_missing)");
            db.execSQL("CREATE TABLE IF NOT EXISTS preview_marks (scope TEXT NOT NULL, path TEXT NOT NULL, marked INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(scope,path))");
            // Old indexed rows lack preview metadata: rebuild once from listing
            // metadata only. No cloud files are opened or modified.
            db.execSQL("DELETE FROM objects");
            db.execSQL("DELETE FROM pending");
            db.execSQL("UPDATE accounts SET active=0,building=0,indexed=0,error=NULL");
        }
    }
    private static final class State {
        int active,building;
        long indexed;
        String error="";
    }
    private static State state(SQLiteDatabase db,String scope) {
        State s=new State();
        try(Cursor c=db.rawQuery("SELECT active,building,indexed,error FROM accounts WHERE scope=?",
                new String[]{scope})){
            if(c.moveToFirst()){
                s.active=c.getInt(0);s.building=c.getInt(1);
                s.indexed=c.getLong(2);s.error=c.isNull(3)?"":c.getString(3);
            }
        }
        return s;
    }
    private static final class Task {
        final String path;
        final int page;
        Task(String path,int page){this.path=path;this.page=page;}
    }
    private static Task next(SQLiteDatabase db,String scope,int generation){
        try(Cursor c=db.rawQuery("SELECT path,page FROM pending WHERE scope=? AND generation=? LIMIT 1",
                new String[]{scope,Integer.toString(generation)})){
            return c.moveToFirst()?new Task(c.getString(0),c.getInt(1)):null;
        }
    }
    private String connectedScope(){
        if(!cloud.configured())return "";
        String scope=cloud.metadataScope();
        return scope==null?"":scope;
    }
    public void ensure(boolean force){
        String scope=connectedScope();
        if(scope.isEmpty())return;
        if(!force && System.currentTimeMillis()<retryAfter.getOrDefault(scope,0L))return;
        if(!running.add(scope))return;
        scanner.execute(()->{
            try{scan(scope,force);}
            catch(Exception e){
                android.util.Log.w("FG_CLOUD_SEARCH","Index interrupted: "+e.getClass().getSimpleName());
                retryAfter.put(scope,System.currentTimeMillis()+60000L);
                try{
                    getWritableDatabase().execSQL("UPDATE accounts SET error=? WHERE scope=?",
                        new Object[]{String.valueOf(e.getMessage()),scope});
                    progress(scope,true);
                }catch(Exception ignored){}
            }finally{running.remove(scope);}
        });
    }
    private void scan(String scope,boolean force)throws Exception {
        SQLiteDatabase db=getWritableDatabase();
        // Names of a disconnected/replaced account must not remain searchable.
        db.beginTransactionNonExclusive();
        try{
            db.execSQL("DELETE FROM objects WHERE scope<>?",new Object[]{scope});
            db.execSQL("DELETE FROM pending WHERE scope<>?",new Object[]{scope});
            db.execSQL("DELETE FROM accounts WHERE scope<>?",new Object[]{scope});
            db.execSQL("DELETE FROM preview_marks WHERE scope<>?",new Object[]{scope});
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
        State s=state(db,scope);
        if(s.building==0 && s.active>0 && !force){progress(scope,true);return;}
        int generation=s.building;
        if(force||generation==0) {
            generation=Math.max(s.active,s.building)+1;
            db.beginTransactionNonExclusive();
            try{
                db.execSQL("INSERT OR REPLACE INTO accounts(scope,active,building,indexed,error) VALUES(?,?,?,?,NULL)",
                    new Object[]{scope,s.active,generation,0});
                db.execSQL("DELETE FROM pending WHERE scope=?",new Object[]{scope});
                db.execSQL("INSERT INTO pending(scope,generation,path,page) VALUES(?,?,?,?)",
                    new Object[]{scope,generation,"/",1});
                db.setTransactionSuccessful();
            }finally{db.endTransaction();}
        }
        progress(scope,true);
        Task task;
        while((task=next(db,scope,generation))!=null) {
            if(!scope.equals(connectedScope()))
                throw new java.io.IOException("TeraBox account disconnected or changed");
            // A failed metadata page is retried on the next scan, at this exact
            // folder/page. Cursor is persisted after each committed page.
            JSONArray rows=cloud.listPageCached(task.path,task.page);
            if(rows==null)throw new java.io.IOException("Cloud directory page is unavailable");
            writePage(db,scope,generation,task,rows);
            progress(scope,false);
        }
        db.beginTransactionNonExclusive();
        try{
            db.execSQL("UPDATE accounts SET active=?,building=0,error=NULL WHERE scope=?",
                new Object[]{generation,scope});
            db.execSQL("DELETE FROM objects WHERE scope=? AND generation<>?",
                new Object[]{scope,generation});
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
        retryAfter.remove(scope);
        progress(scope,true);
        android.util.Log.i("FG_CLOUD_SEARCH","Recursive cloud metadata scan complete");
    }
    private void writePage(SQLiteDatabase db,String scope,int generation,Task task,JSONArray rows)
            throws Exception {
        db.beginTransactionNonExclusive();
        try{
            SQLiteStatement put=db.compileStatement(
                "INSERT OR REPLACE INTO objects(scope,generation,path,name,needle,kind,folder,size,modified,parent,checksum,listing_page,preview_missing) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)");
            SQLiteStatement queue=db.compileStatement(
                "INSERT OR IGNORE INTO pending(scope,generation,path,page) VALUES(?,?,?,1)");
            int admitted=0;
            try{
                for(int i=0;i<rows.length();i++){
                    JSONObject raw=rows.optJSONObject(i);
                    if(raw==null)continue;
                    JSONObject row;
                    try{row=FgTeraboxClient.mapEntry(raw);}
                    catch(Exception malformed){continue;}
                    String path=row.optString("path","");
                    String name=row.optString("name","");
                    if(!path.startsWith("/")||name.isBlank())continue;
                    boolean folder=row.optBoolean("folder",false);
                    // Reject malformed descendants to prevent cross-tree recursion.
                    String parent=task.path.equals("/")?"/":task.path;
                    String prefix=parent.equals("/")?"/":parent+"/";
                    if(!path.startsWith(prefix)||path.equals(parent))continue;
                    String kind=folder?"folder":category(name);
                    put.clearBindings();
                    put.bindString(1,scope);
                    put.bindLong(2,generation);
                    put.bindString(3,path);
                    put.bindString(4,name);
                    put.bindString(5,name.toLowerCase(Locale.ROOT));
                    put.bindString(6,kind);
                    put.bindLong(7,folder?1:0);
                    put.bindLong(8,row.optLong("size",-1));
                    put.bindLong(9,row.optLong("modified",0));
                    put.bindString(10,parent);
                    // Use only syntactically valid provider-supplied whole-file MD5.
                    String digest=raw.optString("md5","").toLowerCase(Locale.ROOT);
                    if(digest.matches("[0-9a-f]{32}"))put.bindString(11,digest);
                    else put.bindNull(11);
                    put.bindLong(12,task.page);
                    put.bindLong(13,FgTeraboxClient.previewUnavailable(raw)?1:0);
                    put.executeInsert();
                    admitted++;
                    if(folder){
                        queue.clearBindings();queue.bindString(1,scope);
                        queue.bindLong(2,generation);queue.bindString(3,path);
                        queue.executeInsert();
                    }
                }
            }finally{put.close();queue.close();}
            if(rows.length()<FgTeraboxClient.pageSize()){
                db.execSQL("DELETE FROM pending WHERE scope=? AND generation=? AND path=?",
                    new Object[]{scope,generation,task.path});
            }else{
                db.execSQL("UPDATE pending SET page=? WHERE scope=? AND generation=? AND path=?",
                    new Object[]{task.page+1,scope,generation,task.path});
            }
            db.execSQL("UPDATE accounts SET indexed=indexed+?,error=NULL WHERE scope=?",
                new Object[]{admitted,scope});
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
    }
    private static String category(String name) {
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
    private static String escapeLike(String value){
        return value.replace("\\","\\\\").replace("%","\\%").replace("_","\\_");
    }
    public void search(String text,String category,int offset,int request) {
        ensure(false);
        String scope=connectedScope();
        queries.execute(()->{
            try{
                State s=state(getReadableDatabase(),scope);
                int gen=s.active>0?s.active:s.building;
                JSONObject reply=new JSONObject()
                    .put("token",request).put("scope",scope)
                    .put("building",s.building!=0).put("indexed",s.indexed)
                    .put("error",s.error).put("offset",Math.max(0,offset));
                JSONArray results=new JSONArray();
                boolean more=false;
                boolean affected="affected".equals(category);
                if(!scope.isEmpty()&&gen>0&&text!=null&&
                   (!text.trim().isEmpty()||affected)){
                    ArrayList<String> params=new ArrayList<>();
                    String sql="SELECT o.path,o.name,o.kind,o.folder,o.size,o.modified,o.parent,o.listing_page,o.preview_missing,COALESCE(mark.marked,0) FROM objects o LEFT JOIN preview_marks mark ON mark.scope=o.scope AND mark.path=o.path WHERE o.scope=? AND o.generation=? AND o.needle LIKE ? ESCAPE '\\'";
                    params.add(scope);params.add(Integer.toString(gen));
                    params.add("%"+escapeLike(text.trim().toLowerCase(Locale.ROOT))+"%");
                    if(affected){
                        sql+=" AND o.kind='image' AND (o.preview_missing=1 OR COALESCE(mark.marked,0)=1)";
                    }else if(category!=null&&!category.isEmpty()&&!category.equals("all")){
                        sql+=" AND o.kind=?";params.add(category);
                    }
                    sql+=" ORDER BY o.needle,o.path LIMIT ? OFFSET ?";
                    params.add(Integer.toString(LIMIT+1));
                    params.add(Integer.toString(Math.max(0,offset)));
                    try(Cursor cursor=getReadableDatabase().rawQuery(sql,params.toArray(new String[0]))){
                        int added=0;
                        while(cursor.moveToNext()){
                            if(++added>LIMIT){more=true;break;}
                            String path=cursor.getString(0),name=cursor.getString(1);
                            JSONObject item=new JSONObject()
                                .put("id",path).put("path",path)
                                .put("name",name).put("title",name)
                                .put("folder",cursor.getInt(3)!=0)
                                .put("size",cursor.getLong(4))
                                .put("modified",cursor.getLong(5))
                                .put("searchPath",cursor.getString(6))
                                .put("terabox",true).put("indexedSearch",true)
                                .put("uri","fgterabox://file/"+Uri.encode(path));
                            if("image".equals(cursor.getString(2))){
                                boolean missing=cursor.getInt(8)!=0;
                                boolean manual=cursor.getInt(9)!=0;
                                item.put("cover",coverUrl(path,cursor.getInt(7)))
                                    .put("remoteCover",true)
                                    .put("previewUnavailable",missing)
                                    .put("previewManuallyMarked",manual);
                            }
                            results.put(item);
                        }
                    }
                }
                reply.put("items",results).put("hasMore",more);
                listener.onSearch(reply.toString());
            }catch(Exception e){
                android.util.Log.w("FG_CLOUD_SEARCH","Query rejected",e);
                try{listener.onSearch(new JSONObject().put("token",request)
                    .put("scope",scope).put("items",new JSONArray())
                    .put("error",String.valueOf(e.getMessage())).toString());}
                catch(Exception ignored){}
            }
        });
    }
    private void progress(String scope,boolean force) {
        long now=SystemClock.elapsedRealtime();
        if(!force&&now-lastProgressMs<1500L)return;
        lastProgressMs=now;
        try{
            State s=state(getReadableDatabase(),scope);
            listener.onProgress(new JSONObject().put("scope",scope)
                .put("indexed",s.indexed).put("building",s.building!=0)
                .put("error",s.error).toString());
        }catch(Exception ignored){}
    }

    /** Constructs only an existing authenticated native thumbnail proxy URL. */
    public static String coverUrl(String path,int page){
        String encoded=android.util.Base64.encodeToString(
            path.getBytes(java.nio.charset.StandardCharsets.UTF_8),
            android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
            android.util.Base64.NO_PADDING);
        return "https://fg-assets.invalid/tb-cover/"+encoded+"."+Math.max(1,page);
    }
    public JSONObject folderPreviews(JSONArray folders)throws Exception {
        JSONObject result=new JSONObject();
        if(folders==null||folders.length()>24)return result;
        String scope=connectedScope();
        State state=state(getReadableDatabase(),scope);
        int gen=state.active>0?state.active:state.building;
        if(gen==0)return result;
        for(int i=0;i<folders.length();i++){
            String folder=folders.optString(i,"");
            if(!folder.startsWith("/")||folder.length()>512)continue;
            JSONArray covers=new JSONArray();
            try(Cursor rows=getReadableDatabase().rawQuery(
                "SELECT path,listing_page FROM objects WHERE scope=? AND generation=? AND folder=0 AND kind='image' AND path LIKE ? ESCAPE '\\' ORDER BY modified DESC LIMIT 3",
                new String[]{scope,Integer.toString(gen),
                    (folder.endsWith("/")?folder:folder+"/").replace("\\","\\\\")
                        .replace("%","\\%").replace("_","\\_")+"%"})){
                while(rows.moveToNext())covers.put(coverUrl(rows.getString(0),rows.getInt(1)));
            }
            result.put(folder,covers);
        }
        return result;
    }

    /** Admit changed incoming metadata without a 300k-file full-account rebuild. */
    public int ingestIncoming(String directory,int page,JSONArray listing)throws Exception{
        String scope=connectedScope();
        int gen=currentGeneration();
        if(scope.isEmpty()||gen==0||listing==null)return 0;
        if(directory==null||!directory.startsWith("/"))return 0;
        SQLiteDatabase db=getWritableDatabase();
        int touched=0;
        db.beginTransactionNonExclusive();
        try{
            SQLiteStatement put=db.compileStatement(
                "INSERT OR REPLACE INTO objects(scope,generation,path,name,needle,kind,folder,size,modified,parent,checksum,listing_page,preview_missing) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)");
            try{
                for(int i=0;i<listing.length();i++){
                    JSONObject raw=listing.optJSONObject(i);
                    if(raw==null)continue;
                    JSONObject row;
                    try{row=FgTeraboxClient.mapEntry(raw);}
                    catch(Exception bad){continue;}
                    String path=row.optString("path","");
                    if(!path.startsWith(directory.endsWith("/")?directory:directory+"/"))continue;
                    String name=row.optString("name","");
                    if(name.isBlank())continue;
                    boolean isFolder=row.optBoolean("folder",false);
                    put.clearBindings();
                    put.bindString(1,scope);put.bindLong(2,gen);
                    put.bindString(3,path);put.bindString(4,name);
                    put.bindString(5,name.toLowerCase(Locale.ROOT));
                    put.bindString(6,isFolder?"folder":category(name));
                    put.bindLong(7,isFolder?1:0);
                    put.bindLong(8,row.optLong("size",-1));
                    put.bindLong(9,row.optLong("modified",0));
                    put.bindString(10,directory);
                    String checksum=raw.optString("md5","").toLowerCase(Locale.ROOT);
                    if(checksum.matches("[0-9a-f]{32}"))put.bindString(11,checksum);
                    else put.bindNull(11);
                    put.bindLong(12,page);
                    put.bindLong(13,FgTeraboxClient.previewUnavailable(raw)?1:0);
                    put.executeInsert();
                    touched++;
                }
            }finally{put.close();}
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
        return touched;
    }
    /** One private indexed lookup per page, never one SQLite query per image. */
    public java.util.Set<String> markedForPage(JSONArray page){
        java.util.Set<String> marked=new java.util.HashSet<>();
        String scope=connectedScope();
        if(scope.isEmpty()||page==null||page.length()==0)return marked;
        java.util.ArrayList<String> args=new java.util.ArrayList<>();
        args.add(scope);
        StringBuilder sql=new StringBuilder(
            "SELECT path FROM preview_marks WHERE scope=? AND path IN (");
        for(int i=0;i<page.length()&&i<100;i++){
            JSONObject row=page.optJSONObject(i);
            String path=row==null?"":row.optString("path","");
            if(!path.startsWith("/")||!FgTeraboxClient.image(path))continue;
            if(args.size()>1)sql.append(',');
            sql.append('?');args.add(path);
        }
        if(args.size()==1)return marked;
        sql.append(')');
        try(Cursor rows=getReadableDatabase().rawQuery(
                sql.toString(),args.toArray(new String[0]))){
            while(rows.moveToNext())marked.add(rows.getString(0));
        }
        return marked;
    }
    /** Keep user-reviewed placeholder flags private and scoped to this account. */
    public void markPreview(String path,boolean affected)throws Exception{
        String scope=connectedScope();
        if(scope.isEmpty()||path==null||path.length()>8192||
           !path.startsWith("/")||path.contains("\\")||
           path.contains("/../")||path.endsWith("/..")||
           !FgTeraboxClient.image(path))
            throw new java.io.IOException("Invalid preview flag target");
        SQLiteDatabase db=getWritableDatabase();
        if(affected)db.execSQL(
            "INSERT OR REPLACE INTO preview_marks(scope,path,marked) VALUES(?,?,1)",
            new Object[]{scope,path});
        else db.execSQL(
            "DELETE FROM preview_marks WHERE scope=? AND path=?",
            new Object[]{scope,path});
    }
    /** Metadata snapshot, never opens file contents. */
    public SQLiteDatabase metadata(){return getReadableDatabase();}
    public String currentScope(){return connectedScope();}
    public int currentGeneration(){
        String scope=connectedScope();
        if(scope.isEmpty())return 0;
        State state=state(getReadableDatabase(),scope);
        return state.active>0?state.active:state.building;
    }
    /** Invalidate an indexed path only after remote deletion is confirmed. */
    public void noteDeleted(String expectedScope,String oldPath){
        if(expectedScope==null||!expectedScope.equals(connectedScope()))return;
        getWritableDatabase().execSQL(
            "DELETE FROM objects WHERE scope=? AND path=?",
            new Object[]{expectedScope,oldPath});
        getWritableDatabase().execSQL(
            "DELETE FROM preview_marks WHERE scope=? AND path=?",
            new Object[]{expectedScope,oldPath});
    }
    public void noteMoved(String expectedScope,String oldPath,String newPath){
        if(expectedScope==null||!expectedScope.equals(connectedScope()))return;
        SQLiteDatabase db=getWritableDatabase();
        String parent=newPath.substring(0,newPath.lastIndexOf('/'));
        if(parent.isEmpty())parent="/";
        db.execSQL("UPDATE objects SET path=?,parent=? WHERE scope=? AND path=?",
            new Object[]{newPath,parent,expectedScope,oldPath});
        db.execSQL("INSERT OR REPLACE INTO preview_marks(scope,path,marked) SELECT scope,?,marked FROM preview_marks WHERE scope=? AND path=?",
            new Object[]{newPath,expectedScope,oldPath});
        db.execSQL("DELETE FROM preview_marks WHERE scope=? AND path=?",
            new Object[]{expectedScope,oldPath});
    }
    public void clear(){
        try{
            SQLiteDatabase db=getWritableDatabase();
            db.execSQL("DELETE FROM objects");db.execSQL("DELETE FROM pending");
            db.execSQL("DELETE FROM accounts");
            db.execSQL("DELETE FROM preview_marks");
        }catch(Exception ignored){}
    }
}
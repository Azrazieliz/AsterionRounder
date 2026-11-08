package com.openlocal.office.core;

import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Deterministic, metadata-only organizer. All writes use the existing authenticated
 * TeraBox client. No AI, cross-app credentials, hidden deletion, or silent overwrite.
 */
public final class FgRounderOrganizer {
    public interface Reporter {void send(String payload);}
    private final Context app;
    private final FgTeraboxClient cloud;
    private final FgTeraboxSearchIndex index;
    private final SharedPreferences prefs;
    private static final Object EXECUTION_LOCK=new Object();
    private volatile boolean stop;
    private static final int REVIEW_LIMIT=120;
    private static final int APPLY_LIMIT=30;
    private static final String PREFS="fg_rounder_organizer_v1";
    private static final String[] INBOXES={
        "/Nocturne/Kuroha","/Nocturne/Kyora","/Nocturne/VideoFlow",
        "/AsterionDownloader","/Incoming","/Downloads"
    };
    public FgRounderOrganizer(Context app,FgTeraboxClient cloud,FgTeraboxSearchIndex index){
        this.app=app.getApplicationContext();
        this.cloud=cloud;this.index=index;
        prefs=this.app.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
    }
    public boolean autoEnabled(){return prefs.getBoolean("auto",false);}
    public void setAutoEnabled(boolean enabled){prefs.edit().putBoolean("auto",enabled).apply();}
    public void stop(){stop=true;}
    private static boolean inside(String file,String directory) {
        return file.startsWith(directory+"/")&&!file.equals(directory+"/");
    }
    private static String filename(String path){return path.substring(path.lastIndexOf('/')+1);}
    private static String relative(String path,String prefix) {
        if(!inside(path,prefix))return "";
        return path.substring(prefix.length()+1);
    }
    private static String kind(String name) {
        String n=name.toLowerCase(Locale.ROOT);
        if(n.matches(".*\\.(png|jpe?g|webp|bmp|gif|avif|heif|heic|tiff?)$"))return "image";
        if(n.matches(".*\\.(mp4|webm|mkv|mov|avi|m4v|wmv)$"))return "video";
        if(n.matches(".*\\.(mp3|m4a|flac|wav|ogg|opus|aac)$"))return "audio";
        if(n.matches(".*\\.(epub|mobi|azw3)$"))return "book";
        if(n.matches(".*\\.(cbz|cbr|cb7)$"))return "comic";
        if(n.endsWith(".pdf"))return "pdf";
        if(n.matches(".*\\.(apk|apks|xapk|aab|exe|msi|deb|rpm)$"))return "app";
        if(n.matches(".*\\.(glb|gltf|fbx|obj|vrm|blend|pmx|pmd)$"))return "model";
        if(n.matches(".*\\.(docx?|xlsx?|pptx?|odt|ods|csv|txt|md|rtf)$"))return "document";
        if(n.matches(".*\\.(zip|7z|rar|tar|gz|bz2)$"))return "archive";
        return "other";
    }
    /** Only known, explicitly designated incoming directories may be moved. */
    public static String destination(String path) {
        if(path==null||!path.startsWith("/")||path.contains("/../")||
            path.contains("/./")||path.contains("\\")||path.endsWith("/"))
            return "";
        final String name=filename(path);
        final String kind=kind(name);
        // Source provenance wins for art downloads, never for unrelated files.
        if(inside(path,"/Nocturne/Kuroha")&&kind.equals("image"))
            return "/Art/Pixiv";
        if(inside(path,"/Nocturne/Kyora")&&kind.equals("image"))
            return "/Art/Cosplay";
        if(inside(path,"/Nocturne/VideoFlow")&&kind.equals("video"))
            return "/Videos/Downloader";
        boolean otherSource=false;
        for(String inbox:INBOXES)if(inside(path,inbox))otherSource=true;
        if(!otherSource)return "";
        switch(kind) {
            case "image":return "/Art/Downloads";
            case "book":case "comic":case "pdf":return "/Books/Downloads";
            case "app":return "/Apps/Downloads";
            case "video":return "/Videos/Downloads";
            case "audio":return "/Audio/Downloads";
            case "document":return "/Documents/Downloads";
            case "model":return "/3D/Downloads";
            case "archive":return "/Archives/Downloads";
            default:return "";
        }
    }

    /**
     * Refresh the known downloader ingress paths, not the entire cloud.
     * Round-robin nested subfolders over successive runs for bounded traffic.
     */
    public JSONObject scanIncoming()throws Exception{return scanIncoming(false);}
    public JSONObject scanIncoming(boolean quick)throws Exception{
        String scope=index.currentScope();int gen=index.currentGeneration();
        JSONObject out=new JSONObject().put("indexed",0).put("folders",0);
        if(scope.isEmpty()||gen==0)return out.put("pendingIndex",true);
        ArrayList<String> folders=new ArrayList<>();
        for(String root:INBOXES)folders.add(root);
        try(Cursor c=index.metadata().rawQuery(
            "SELECT path FROM objects WHERE scope=? AND generation=? AND folder=1"+
            " AND (path LIKE '/Nocturne/%' OR path LIKE '/AsterionDownloader/%'"+
            " OR path LIKE '/Incoming/%' OR path LIKE '/Downloads/%') ORDER BY path",
            new String[]{scope,Integer.toString(gen)})){
            while(c.moveToNext()&&folders.size()<1500)folders.add(c.getString(0));
        }
        int offset=prefs.getInt("subfolder_offset",0);
        int inspected=0,admitted=0,failed=0;
        ArrayList<String> selected=new ArrayList<>();
        // Always inspect six source roots; rotate twelve nested directories.
        for(int i=0;i<INBOXES.length;i++)selected.add(INBOXES[i]);
        int subCount=Math.max(0,folders.size()-INBOXES.length);
        for(int i=0;i<Math.min(quick?4:12,subCount);i++)
            selected.add(folders.get(INBOXES.length+(offset+i)%subCount));
        if(subCount>0)prefs.edit().putInt("subfolder_offset",
            (offset+(quick?4:12))%subCount).apply();
        for(String folder:selected){
            if(stop||!scope.equals(index.currentScope()))break;
            try{
                // Newest-first: early pages cover newly uploaded work.
                for(int page=1;page<=(quick?1:3);page++){
                    JSONArray rows=cloud.listIncomingPage(folder,page);
                    admitted+=index.ingestIncoming(folder,page,rows);
                    if(rows.length()<FgTeraboxClient.pageSize())break;
                }
                inspected++;
            }catch(Exception unavailable){
                // A missing source is normal. Do not invent a success receipt.
                failed++;
            }
        }
        return out.put("indexed",admitted).put("folders",inspected)
            .put("unavailable",failed)
            .put("partial",subCount>12);
    }
    /** Auto routing is explicit opt-in and applies only deterministic rules. */
    public JSONObject autoRun(Reporter reporter)throws Exception{
        JSONObject scan=scanIncoming(true);
        if(!autoEnabled()||index.currentGeneration()==0)
            return scan.put("automatic",false);
        JSONObject candidateReview=review();
        JSONArray proposals=candidateReview.optJSONArray("proposals");
        JSONArray batch=new JSONArray();
        if(proposals!=null){
            for(int i=0;i<proposals.length()&&batch.length()<20;i++){
                String source=proposals.getJSONObject(i).optString("source","");
                String identity=skipIdentity(index.currentScope(),source);
                if(prefs.getBoolean("skip_"+identity,false))continue;
                batch.put(source);
            }
        }
        if(batch.length()>0)applyInternal(batch,reporter,true);
        return scan.put("automatic",true).put("scheduled",batch.length());
    }
    private static String skipIdentity(String scope,String path){
        try{
            java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");
            byte[] bytes=digest.digest((scope+"|"+path).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder id=new StringBuilder();
            for(int i=0;i<16;i++)id.append(String.format(Locale.ROOT,"%02x",bytes[i]&255));
            return id.toString();
        }catch(Exception impossible){throw new IllegalStateException(impossible);}
    }
    public JSONObject review()throws Exception {
        String scope=index.currentScope();
        int gen=index.currentGeneration();
        JSONObject out=new JSONObject().put("accountReady",!scope.isEmpty())
            .put("indexReady",gen>0).put("auto",autoEnabled());
        JSONArray rules=new JSONArray();
        for(String source:INBOXES)
            rules.put(new JSONObject().put("source",source).put("rule","Extension + trusted origin"));
        out.put("rules",rules);
        JSONArray proposals=new JSONArray();
        if(gen==0)return out.put("proposals",proposals).put("hasMore",false);
        ArrayList<String> args=new ArrayList<>();
        StringBuilder sql=new StringBuilder("SELECT path,name,size,modified,checksum FROM objects WHERE scope=? AND generation=? AND folder=0 AND (");
        args.add(scope);args.add(Integer.toString(gen));
        for(int i=0;i<INBOXES.length;i++){
            if(i>0)sql.append(" OR ");
            sql.append("path LIKE ?");
            args.add(INBOXES[i]+"/%");
        }
        sql.append(") ORDER BY modified DESC,path LIMIT ?");
        args.add(Integer.toString(REVIEW_LIMIT*3+1));
        int eligible=0;
        try(Cursor c=index.metadata().rawQuery(sql.toString(),args.toArray(new String[0]))){
            while(c.moveToNext()){
                String path=c.getString(0),dest=destination(path);
                if(dest.isEmpty()||path.startsWith(dest+"/"))continue;
                eligible++;
                if(proposals.length()>=REVIEW_LIMIT)continue;
                proposals.put(new JSONObject()
                    .put("source",path).put("target",dest+"/"+filename(path))
                    .put("category",kind(filename(path)))
                    .put("reason",originReason(path))
                    .put("size",c.getLong(2)).put("modified",c.getLong(3))
                    .put("checksumKnown",!c.isNull(4)));
            }
        }
        out.put("proposals",proposals);
        out.put("hasMore",eligible>REVIEW_LIMIT);
        out.put("proposedCount",eligible);
        return out;
    }
    private static String originReason(String path){
        if(inside(path,"/Nocturne/Kuroha"))return "Kuroha / Pixiv source";
        if(inside(path,"/Nocturne/Kyora"))return "Kyora / cosplay source";
        if(inside(path,"/Nocturne/VideoFlow"))return "VideoFlow source";
        return "File extension in an incoming/download folder";
    }
    /** Hash-based groups are strong metadata evidence, not a freshly recomputed SHA-256. */
    public JSONObject duplicates()throws Exception{
        JSONObject output=new JSONObject();
        JSONArray exact=new JSONArray(),possible=new JSONArray();
        String scope=index.currentScope();int gen=index.currentGeneration();
        if(gen==0)return output.put("exact",exact).put("possible",possible)
            .put("indexReady",false);
        SQLiteDatabase db=index.metadata();
        String query="SELECT checksum,size,COUNT(*) FROM objects WHERE scope=? AND generation=?"+
          " AND folder=0 AND checksum IS NOT NULL AND size>=0"+
          " GROUP BY checksum,size HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 40";
        try(Cursor groups=db.rawQuery(query,new String[]{scope,String.valueOf(gen)})){
            while(groups.moveToNext()){
                JSONArray paths=new JSONArray();
                String hash=groups.getString(0),size=String.valueOf(groups.getLong(1));
                try(Cursor files=db.rawQuery(
                    "SELECT path FROM objects WHERE scope=? AND generation=? AND checksum=? AND size=? ORDER BY path LIMIT 24",
                    new String[]{scope,String.valueOf(gen),hash,size})){
                    while(files.moveToNext())paths.put(files.getString(0));
                }
                exact.put(new JSONObject().put("basis","matching cloud MD5 and size")
                    .put("size",groups.getLong(1)).put("count",groups.getInt(2))
                    .put("paths",paths));
            }
        }
        String q2="SELECT needle,size,COUNT(*) FROM objects WHERE scope=? AND generation=?"+
          " AND folder=0 AND checksum IS NULL AND size>=0"+
          " GROUP BY needle,size HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 40";
        try(Cursor groups=db.rawQuery(q2,new String[]{scope,String.valueOf(gen)})){
            while(groups.moveToNext()){
                JSONArray paths=new JSONArray();
                String name=groups.getString(0),size=String.valueOf(groups.getLong(1));
                try(Cursor files=db.rawQuery(
                    "SELECT path FROM objects WHERE scope=? AND generation=? AND needle=? AND size=? AND checksum IS NULL ORDER BY path LIMIT 24",
                    new String[]{scope,String.valueOf(gen),name,size})){
                    while(files.moveToNext())paths.put(files.getString(0));
                }
                possible.put(new JSONObject().put("basis","same filename and size (unverified)")
                    .put("size",groups.getLong(1)).put("count",groups.getInt(2))
                    .put("paths",paths));
            }
        }
        output.put("exact",exact).put("possible",possible)
              .put("indexReady",true);
        return output;
    }
    private JSONObject indexedFile(String scope,int gen,String path)throws Exception {
        try(Cursor c=index.metadata().rawQuery(
            "SELECT size FROM objects WHERE scope=? AND generation=? AND path=? AND folder=0 LIMIT 1",
            new String[]{scope,String.valueOf(gen),path})){
            if(!c.moveToFirst())return null;
            return new JSONObject().put("size",c.getLong(0));
        }
    }
    private void mkdirs(String dest)throws Exception{
        String[] segments=dest.split("/");
        if(segments.length>6)throw new java.io.IOException("Folder depth exceeds organizer limit");
        String parent="";
        for(String part:segments){
            if(part.isEmpty())continue;
            if(!part.matches("[\\p{L}\\p{N} _-]{1,60}"))
                throw new java.io.IOException("Invalid organizer destination");
            parent+="/"+part;
            boolean existing=false;
            try{
                JSONObject info=cloud.fileDetails(parent);
                if(info.optInt("isdir",0)!=1)
                    throw new java.io.IOException("Destination is not a folder");
                existing=true;
            }catch(java.io.IOException notFound){
                // Cloud write is safe only if provider can create and verify.
                cloud.createDirectory(parent);
            }
            JSONObject verified=cloud.fileDetails(parent);
            if(verified.optInt("isdir",0)!=1)
                throw new java.io.IOException("Destination folder not verified");
        }
    }
    public void apply(JSONArray paths,Reporter callback)throws Exception{
        applyInternal(paths,callback,false);
    }
    private void applyInternal(JSONArray paths,Reporter callback,boolean automatic)throws Exception{
        if(paths==null||paths.length()<1||paths.length()>APPLY_LIMIT)
            throw new IllegalArgumentException("Select 1–30 proposed files");
        synchronized(EXECUTION_LOCK) {
            stop=false;
            String scope=index.currentScope();
            int gen=index.currentGeneration();
            if(scope.isEmpty()||gen==0)throw new java.io.IOException("Connect TeraBox and build its index first");
            Set<String> unique=new HashSet<>();
            int moved=0,failed=0;
            for(int i=0;i<paths.length();i++){
                if(stop)break;
                String source=paths.optString(i,"");
                String dest=destination(source);
                JSONObject event=new JSONObject().put("source",source)
                    .put("completed",i).put("total",paths.length());
                try{
                    if(!scope.equals(index.currentScope()))
                        throw new java.io.IOException("TeraBox account changed");
                    if(dest.isEmpty()||!unique.add(source))
                        throw new java.io.IOException("No trusted route or duplicate request");
                    JSONObject indexed=indexedFile(scope,gen,source);
                    if(indexed==null)throw new java.io.IOException("File no longer in search index");
                    String name=filename(source);
                    long size=indexed.optLong("size",-1);
                    if(size<0)throw new java.io.IOException("Unknown file size — review required");
                    // Before moving, verify the original still exists with its
                    // indexed size. Server handles collision with ondup=fail.
                    JSONObject original=cloud.fileDetails(source);
                    if(size!=original.optLong("size",-1))
                        throw new java.io.IOException("Original changed; refresh index");
                    mkdirs(dest);
                    cloud.moveFileChecked(source,dest,name,size);
                    index.noteMoved(scope,source,dest+"/"+name);
                    moved++;
                    event.put("status","moved").put("target",dest+"/"+name);
                }catch(Exception error){
                    failed++;
                    // Automated failure cannot be retried blindly if the
                    // server may have moved the original already.
                    if(automatic) prefs.edit().putBoolean(
                        "skip_"+skipIdentity(scope,source),true).apply();
                    event.put("status","review")
                         .put("error",String.valueOf(error.getMessage()));
                }
                callback.send(event.toString());
            }
            callback.send(new JSONObject().put("finished",true)
                .put("moved",moved).put("review",failed)
                .put("stopped",stop).put("total",paths.length()).toString());
        }
    }
}

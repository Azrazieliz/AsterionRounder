package com.openlocal.office.core;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.Bundle;
import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * Read-only, explicitly authorized TeraBox inventory for the installed Asterion Control.
 * Never exposes cloud credentials, file bytes, streaming URLs or unrelated directories.
 * The existing account-scoped FgTeraboxSearchIndex owns recursive traversal and pagination.
 */
public final class FgRounderInventoryBridge extends ContentProvider {
    public static final String AUTHORITY = "com.openlocal.office.asterion.bridge";
    private static final String CONTROL = "com.asterion.control";
    // Installed original Asterion Control production signer, not Rounder's signer.
    private static final String CONTROL_CERT = "9bc439712a0a460cc4703ebf254aaaf9bf3cc6e67b0ced6fc12162ed3ca3b9ad";
    private static final String SETTINGS = "rounder_control_inventory_v1";
    private static final long ACCESS_MS = 30L * 60L * 1000L;
    private static final int MAX_RESPONSE_BYTES = 7000;
    private static final int PAGE_QUERY_LIMIT = 80;
    private static final String ACCOUNT_DB = "rounder-terabox-search-v1.db";
    private static final Object LOCK = new Object();
    private static volatile FgTeraboxSearchIndex index;

    public static void grant(Context context, FgTeraboxClient cloud, String folder)
            throws Exception {
        String root = validFolder(folder);
        if (!cloud.configured() || cloud.metadataScope().isEmpty())
            throw new IllegalStateException("Connect TeraBox first");
        String account=cloud.metadataScope();
        // The owner has selected this folder in Rounder's authenticated browser.
        // Verify its actual cloud listing, not a possibly-incomplete global index.
        // An empty folder is valid. No file contents are opened or downloaded.
        cloud.listPage(root,1);
        if(!account.equals(cloud.metadataScope()))
            throw new IllegalStateException("TeraBox account changed during approval");
        long until = System.currentTimeMillis() + ACCESS_MS;
        if (!context.getSharedPreferences(SETTINGS, Context.MODE_PRIVATE).edit()
                .putString("scope",account).putString("root",root)
                .putLong("expiry",until).commit())
            throw new IllegalStateException("Could not save owner approval");
        // A dedicated snapshot of just this subtree uses the existing search
        // index's durable page queue; no full-account scan prerequisite.
        index(context,cloud).ensureInventory(root,true);
    }

    public static void revoke(Context context) {
        if (!context.getSharedPreferences(SETTINGS,Context.MODE_PRIVATE).edit().clear().commit())
            throw new IllegalStateException("Could not revoke inventory access");
    }

    private static String validFolder(String path) {
        if(path==null || path.length()>1024 || !path.startsWith("/") ||
                path.contains("\\") || path.contains("\n") || path.contains("\r") ||
                path.contains("/../") || path.endsWith("/..") ||
                path.contains("/./") || path.endsWith("/.") ||
                (path.length()>1 && path.endsWith("/")))
            throw new IllegalArgumentException("Invalid selected folder");
        return path;
    }

    private static void checkCaller(Context context) throws Exception {
        int uid = Binder.getCallingUid();
        String[] packages = context.getPackageManager().getPackagesForUid(uid);
        boolean found = false;
        if (packages != null) for(String pkg:packages) if(CONTROL.equals(pkg)) found = true;
        if(!found) throw new SecurityException("Only Asterion Control may read this inventory");
        PackageManager pm = context.getPackageManager();
        Signature[] signatures;
        if(Build.VERSION.SDK_INT>=28) {
            PackageInfo p=pm.getPackageInfo(CONTROL,PackageManager.GET_SIGNING_CERTIFICATES);
            if(p.signingInfo==null)throw new SecurityException("Control signature unavailable");
            signatures=p.signingInfo.getApkContentsSigners();
        } else {
            signatures=pm.getPackageInfo(CONTROL,PackageManager.GET_SIGNATURES).signatures;
        }
        if(signatures==null || signatures.length!=1)
            throw new SecurityException("Unexpected Control signature");
        byte[] digest=MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray());
        StringBuilder s=new StringBuilder();
        for(byte b:digest)s.append(String.format(Locale.US,"%02x",b&255));
        if(!CONTROL_CERT.equals(s.toString())) throw new SecurityException("Unrecognized Control signer");
    }

    private static String inventoryScope(String account,String root){
        return "inventory:"+account+"|"+root;
    }

    private static final class Approval {
        final String scope,root;
        Approval(String s,String r){scope=s;root=r;}
    }

    private static Approval approval(Context ctx,FgTeraboxClient cloud) {
        SharedPreferences p=ctx.getSharedPreferences(SETTINGS,Context.MODE_PRIVATE);
        if(!cloud.configured() || cloud.metadataScope().isEmpty() ||
           !cloud.metadataScope().equals(p.getString("scope","")) ||
           System.currentTimeMillis()>=p.getLong("expiry",0L))
            throw new SecurityException("Rounder owner must approve this account and folder locally");
        return new Approval(cloud.metadataScope(),validFolder(p.getString("root","")));
    }

    private static FgTeraboxSearchIndex index(Context ctx,FgTeraboxClient cloud) {
        if(index==null) synchronized(LOCK) {
            if(index==null) index=new FgTeraboxSearchIndex(ctx,cloud,
                new FgTeraboxSearchIndex.Listener(){
                    @Override public void onSearch(String unused){}
                    @Override public void onProgress(String unused){}
                });
        }
        return index;
    }

    private static JSONObject state(Context ctx,Approval approval) throws Exception {
        int active=0,building=0;long indexed=0;String error="";
        try(SQLiteDatabase db=SQLiteDatabase.openDatabase(
                ctx.getDatabasePath(ACCOUNT_DB).getPath(),null,SQLiteDatabase.OPEN_READONLY);
            Cursor c=db.rawQuery("SELECT active,building,indexed,error FROM accounts WHERE scope=?",
                    new String[]{inventoryScope(approval.scope,approval.root)})){
            if(c.moveToFirst()){
                active=c.getInt(0);building=c.getInt(1);indexed=c.getLong(2);
                error=c.isNull(3)?"":c.getString(3);
            }
        }catch(android.database.sqlite.SQLiteException notIndexed){
            return new JSONObject().put("status","accepted").put("indexed",0)
                .put("reason","index_initializing");
        }
        JSONObject reply=new JSONObject().put("root",approval.root)
            .put("account_fingerprint",accountFingerprint(approval.scope))
            .put("indexed",indexed).put("index_building",building!=0)
            .put("index_error",error);
        if(!error.isEmpty())
            return reply.put("status","failed").put("reason","index_error");
        if(building!=0||active==0)
            return reply.put("status","accepted").put("reason","index_not_complete");
        String like=likePrefix(approval.root);
        try(SQLiteDatabase db=SQLiteDatabase.openDatabase(
                ctx.getDatabasePath(ACCOUNT_DB).getPath(),null,SQLiteDatabase.OPEN_READONLY);
            Cursor c=db.rawQuery(
                "SELECT COUNT(*),COALESCE(SUM(folder),0),COALESCE(SUM(CASE WHEN folder=0 THEN size ELSE 0 END),0) "
                +"FROM objects WHERE scope=? AND generation=? AND path LIKE ? ESCAPE '\\'",
                new String[]{inventoryScope(approval.scope,approval.root),Integer.toString(active),like})){
            c.moveToFirst();
            return reply.put("status","completed").put("generation",active)
                .put("entries",c.getLong(0)).put("folders",c.getLong(1))
                .put("files",c.getLong(0)-c.getLong(1))
                .put("total_file_bytes",c.getLong(2))
                .put("format_options",new JSONArray().put("json").put("csv"))
                .put("complete_for_index_generation",true);
        }
    }

    /** Irreversible account marker; never return the actual private scope or cookie. */
    private static String accountFingerprint(String scope) throws Exception {
        byte[] hash=MessageDigest.getInstance("SHA-256").digest(
            scope.getBytes(StandardCharsets.UTF_8));
        StringBuilder out=new StringBuilder();
        for(int i=0;i<12;i++)out.append(String.format(Locale.US,"%02x",hash[i]&255));
        return out.toString();
    }

    private static String likePrefix(String root) {
        String prefix="/".equals(root)?"/":root+"/";
        return prefix.replace("\\","\\\\").replace("%","\\%")
            .replace("_","\\_")+"%";
    }

    private static String csvQuote(String s) {
        return "\"" + (s==null?"":s).replace("\"","\"\"") + "\"";
    }

    private static JSONObject page(Context ctx,Approval a,JSONObject payload) throws Exception {
        int generation=payload.optInt("generation",-1);
        String after=payload.optString("after","");
        String format=payload.optString("format","json");
        if(generation<1 || (!"json".equals(format)&&!"csv".equals(format)) ||
           after.length()>4096 || (!after.isEmpty() && !after.startsWith(
                "/".equals(a.root)?"/":a.root+"/")))
            throw new IllegalArgumentException("Invalid inventory page request");
        // A page must not recount the entire account (300K+ items) on every call.
        // Only the active completed generation may be exported.
        try(SQLiteDatabase check=SQLiteDatabase.openDatabase(
                ctx.getDatabasePath(ACCOUNT_DB).getPath(),null,SQLiteDatabase.OPEN_READONLY);
            Cursor ready=check.rawQuery(
                "SELECT active,building,error FROM accounts WHERE scope=?",
                new String[]{inventoryScope(a.scope,a.root)})){
            if(!ready.moveToFirst() || ready.getInt(0)!=generation ||
               ready.getInt(1)!=0 || !ready.isNull(2))
                throw new IllegalStateException("Index changed or scan is not complete; restart export");
        }
        JSONArray rows=new JSONArray(); StringBuilder csv=new StringBuilder();
        if("csv".equals(format) && after.isEmpty())
            csv.append("path,parent,name,type,folder,size,modified,md5\n");
        String next=after;
        boolean more=false;
        try(SQLiteDatabase db=SQLiteDatabase.openDatabase(
                    ctx.getDatabasePath(ACCOUNT_DB).getPath(),null,SQLiteDatabase.OPEN_READONLY);
            Cursor cursor=db.rawQuery(
                "SELECT path,parent,name,kind,folder,size,modified,checksum FROM objects "+
                "WHERE scope=? AND generation=? AND path LIKE ? ESCAPE '\\' AND path>? "+
                "ORDER BY path LIMIT "+PAGE_QUERY_LIMIT,
                new String[]{inventoryScope(a.scope,a.root),Integer.toString(generation),likePrefix(a.root),after})){
            while(cursor.moveToNext()){
                String path=cursor.getString(0);
                JSONObject item=new JSONObject().put("path",path)
                    .put("parent",cursor.getString(1)).put("name",cursor.getString(2))
                    .put("type",cursor.getString(3)).put("folder",cursor.getInt(4)!=0)
                    .put("size",cursor.getLong(5)).put("modified",cursor.getLong(6))
                    .put("md5",cursor.isNull(7)?JSONObject.NULL:cursor.getString(7));
                String record = csvQuote(path)+","+csvQuote(cursor.getString(1))+","+
                    csvQuote(cursor.getString(2))+","+csvQuote(cursor.getString(3))+","+
                    cursor.getInt(4)+","+cursor.getLong(5)+","+cursor.getLong(6)+","+
                    csvQuote(cursor.isNull(7)?"":cursor.getString(7))+"\n";
                // Account for enveloping metadata, escaping, and Controller's 8KB ceiling.
                int bytes=("csv".equals(format)?
                    csv.toString().getBytes(StandardCharsets.UTF_8).length+
                        record.getBytes(StandardCharsets.UTF_8).length:
                    rows.toString().getBytes(StandardCharsets.UTF_8).length+
                        item.toString().getBytes(StandardCharsets.UTF_8).length)+1200;
                if(bytes>MAX_RESPONSE_BYTES) {
                    if(rows.length()==0 && csv.length()<100)
                        throw new IllegalStateException("Indexed path exceeds safe transport limit");
                    more=true;break;
                }
                rows.put(item); csv.append(record);next=path;
            }
            if(cursor.getCount()==PAGE_QUERY_LIMIT)more=true;
        }
        JSONObject response=new JSONObject().put("status","completed")
            .put("root",a.root).put("account_fingerprint",accountFingerprint(a.scope))
            .put("generation",generation)
            .put("count",rows.length()).put("next_after",next).put("has_more",more)
            .put("format",format);
        if("csv".equals(format))response.put("csv",csv.toString());
        else response.put("items",rows);
        if(response.toString().getBytes(StandardCharsets.UTF_8).length>8192)
            throw new IllegalStateException("Inventory response exceeds safe transport limit");
        return response;
    }

    private static JSONObject dispatch(Context ctx,String action,JSONObject payload)throws Exception {
        FgTeraboxClient cloud=new FgTeraboxClient(ctx);
        Approval a=approval(ctx,cloud);
        if("rounder.inventory.meta".equals(action)){
            index(ctx,cloud).ensureInventory(a.root,false);
            return state(ctx,a);
        }
        if("rounder.inventory.page".equals(action))return page(ctx,a,payload);
        throw new IllegalArgumentException("Unsupported read-only inventory action");
    }

    private static Bundle result(JSONObject object) {
        Bundle b=new Bundle(); b.putString("result_json",object.toString()); return b;
    }
    private static JSONObject error(Exception e) throws Exception{
        return new JSONObject().put("ok",false).put("status","failed")
            .put("reason",e instanceof SecurityException?"access_denied":
                (e.getMessage()==null?"inventory_unavailable":e.getMessage()));
    }

    @Override public boolean onCreate(){return true;}

    @Override public Bundle call(String method,String arg,Bundle extras) {
        try {
            Context ctx=getContext(); if(ctx==null)throw new IllegalStateException("Context unavailable");
            checkCaller(ctx);
            if("asterion.v1.capabilities".equals(method)){
                return result(new JSONObject().put("pack_version",1).put("actions",
                    new JSONArray().put(new JSONObject().put("name","rounder.inventory.meta")
                        .put("intent","read"))
                    .put(new JSONObject().put("name","rounder.inventory.page")
                        .put("intent","read"))));
            }
            if(extras==null||extras.getInt("protocol_version")!=1)
                throw new IllegalArgumentException("Unsupported bridge protocol");
            String id=extras.getString("request_id","");
            if(!id.matches("[A-Za-z0-9_.:-]{8,100}"))
                throw new IllegalArgumentException("Invalid request id");
            SharedPreferences receipts=ctx.getSharedPreferences(SETTINGS+"_receipts",Context.MODE_PRIVATE);
            String record=receipts.getString("request:"+id,"");
            if("asterion.v1.invoke".equals(method)){
                String action=extras.getString("action","");
                String payload=extras.getString("payload_json","{}");
                if(payload.length()>4096)throw new IllegalArgumentException("Payload too large");
                JSONObject req=new JSONObject().put("action",action).put("payload",new JSONObject(payload));
                if(!record.isEmpty() && !record.equals(req.toString()))
                    throw new IllegalArgumentException("Request id reused for different action");
                if(record.isEmpty() && !receipts.edit()
                    .putString("request:"+id,req.toString()).commit())
                    throw new IllegalStateException("Could not persist read-only receipt");
                record=req.toString();
            } else if(!"asterion.v1.status".equals(method) &&
                      !"asterion.v1.cancel".equals(method)){
                throw new IllegalArgumentException("Unsupported provider method");
            }
            if(record.isEmpty())throw new IllegalArgumentException("Unknown inventory request");
            JSONObject req=new JSONObject(record);
            if("asterion.v1.cancel".equals(method)){
                return result(new JSONObject().put("ok",true).put("status","completed")
                    .put("reason","Read-only page request is terminal; shared index is unaffected"));
            }
            JSONObject out=dispatch(ctx,req.getString("action"),req.getJSONObject("payload"));
            return result(new JSONObject().put("ok",true)
                .put("status",out.optString("status","completed")).put("result",out));
        }catch(Exception e){
            try{return result(error(e));}
            catch(Exception ignored){return new Bundle();}
        }
    }

    @Override public String getType(Uri uri){throw new UnsupportedOperationException();}
    @Override public Cursor query(Uri uri,String[] p,String s,String[] a,String o){throw new UnsupportedOperationException();}
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
}

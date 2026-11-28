package com.openlocal.office.core;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.TextView;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** One-time migration export. Never copies account cookies, sessions,
 * credentials, storage permissions or media. The owner chooses the file. */
public final class RounderMigrationExportActivity extends Activity {
    private static final String SCHEMA="asterion.rounder.reader-export.v1";
    private static final int LIMIT=4*1024*1024;
    private static final ExecutorService WORK=Executors.newSingleThreadExecutor();
    private static final Set<String> CONTROLS=new HashSet<>(Arrays.asList("fg.controls.bg","fg.controls.ink","fg.controls.size","fg.controls.font",
        "fg.controls.mode:epub","fg.controls.mode:pdf","fg.controls.mode:comic","fg.controls.mode:text"));
    private File snapshot;
    private TextView status;
    private static File root(Activity context){return new File(context.getCacheDir(),"rounder-reader-export");}
    public static void request(Activity owner,String payload){
        if(payload==null||payload.length()>LIMIT)return;
        owner.runOnUiThread(()->{
            if(owner.isFinishing()||owner.isDestroyed())return;
            new AlertDialog.Builder(owner).setTitle("Export reading metadata")
                .setMessage("Save bookmarks, reading appearance and recent file metadata to a document you choose. No credentials or file contents are exported.")
                .setNegativeButton("Cancel",null).setPositiveButton("Choose file",(d,w)->WORK.execute(()->{
                    File f=null;
                    try{
                        JSONObject raw=new JSONObject(payload),records=raw.getJSONObject("records");
                        if(!SCHEMA.equals(raw.getString("schema"))||records.length()>10000)throw new IOException("Invalid export");
                        JSONObject safe=new JSONObject();
                        Iterator<String> keys=records.keys();
                        while(keys.hasNext()){
                            String key=keys.next();
                            if(key.length()>1024||!(key.startsWith("fg.book.preferences.v2.")||CONTROLS.contains(key)||"asterion-rounder-recent-v1".equals(key)))throw new IOException("Unknown reader field");
                            String value=records.getString(key);
                            if(value.length()>128*1024)throw new IOException("Reader field too large");
                            if("asterion-rounder-recent-v1".equals(key)){
                                JSONArray rows=new JSONArray(value),filtered=new JSONArray();
                                if(rows.length()>24)throw new IOException("Recent history limit");
                                for(int i=0;i<rows.length();i++){
                                    JSONObject r=rows.getJSONObject(i),clean=new JSONObject();
                                    for(String name:new String[]{"name","title","path"}){
                                        String item=r.optString(name,"");
                                        if(item.length()>4096)throw new IOException("History field too large");
                                        clean.put(name,item);
                                    }
                                    String uri=r.optString("uri","");
                                    clean.put("uri",uri.startsWith("content://")&&!uri.contains("?")&&!uri.contains("#")&&uri.length()<=4096?uri:"");
                                    clean.put("terabox",r.optBoolean("terabox",false));
                                    for(String name:new String[]{"size","modified","at"})clean.put(name,r.optLong(name,0L));
                                    filtered.put(clean);
                                }
                                value=filtered.toString();
                            }else if(key.startsWith("fg.book.preferences.v2.")){
                                JSONObject item=new JSONObject(value),clean=new JSONObject();
                                if(key.endsWith(".position")){
                                    int chapter=item.getInt("chapter");double fraction=item.getDouble("percent");
                                    if(chapter<0||chapter>1000000||!Double.isFinite(fraction)||fraction<0||fraction>1)throw new IOException("Invalid bookmark");
                                    clean.put("chapter",chapter).put("percent",fraction);
                                }else{
                                    for(String k:new String[]{"theme","font","size","line","margin"})if(item.has(k))clean.put(k,item.get(k));
                                }
                                value=clean.toString();
                            }
                            safe.put(key,value);
                        }
                        byte[] bytes=new JSONObject().put("schema",SCHEMA).put("records",safe).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
                        if(bytes.length>LIMIT)throw new IOException("Export exceeds limit");
                        File dir=root(owner);if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Cannot stage export");
                        String id=UUID.randomUUID().toString();
                        f=new File(dir,id+".json");
                        try(FileOutputStream out=new FileOutputStream(f)){out.write(bytes);out.getFD().sync();}
                        final File staged=f;
                        owner.runOnUiThread(()->{
                            if(owner.isDestroyed()||owner.isFinishing()){staged.delete();return;}
                            owner.startActivity(new Intent(owner,RounderMigrationExportActivity.class).putExtra("snapshot",id));
                        });
                    }catch(Exception e){
                        if(f!=null)f.delete();
                        owner.runOnUiThread(()->{if(!owner.isDestroyed())new AlertDialog.Builder(owner).setMessage("Export failed: "+e.getClass().getSimpleName()).setPositiveButton("Close",null).show();});
                    }
                })).show();
        });
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        String id=getIntent().getStringExtra("snapshot");
        if(id==null||!id.matches("[0-9a-f-]{36}")){finish();return;}
        snapshot=new File(root(this),id+".json");
        if(!snapshot.isFile()||snapshot.length()>LIMIT){finish();return;}
        status=new TextView(this);status.setPadding(24,24,24,24);status.setText("Choose the reader metadata export destination.");setContentView(status);
        if(state==null){
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/json")
                .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"Asterion-Rounder-reader-export.json");
            startActivityForResult(intent,718);
        }
    }
    @Override protected void onActivityResult(int code,int result,Intent data){
        super.onActivityResult(code,result,data);
        if(code!=718)return;
        if(result!=RESULT_OK||data==null||data.getData()==null){snapshot.delete();finish();return;}
        Uri destination=data.getData();status.setText("Saving and verifying export…");
        WORK.execute(()->{
            String message;
            try{
                byte[] original=java.nio.file.Files.readAllBytes(snapshot.toPath());
                try(OutputStream out=getContentResolver().openOutputStream(destination,"wt")){
                    if(out==null)throw new IOException("Destination unavailable");out.write(original);
                }
                try(InputStream in=getContentResolver().openInputStream(destination)){
                    if(in==null)throw new IOException("Readback unavailable");
                    int off=0;byte[] b=new byte[32768];
                    for(int n;(n=in.read(b))!=-1;){
                        if(n>original.length-off)throw new IOException("Export length mismatch");
                        for(int i=0;i<n;i++)if(b[i]!=original[off+i])throw new IOException("Export bytes differ");
                        off+=n;
                    }
                    if(off!=original.length)throw new IOException("Incomplete export");
                }
                snapshot.delete();message="Reader metadata exported and read back successfully.";
            }catch(Exception e){message="Export not verified: "+e.getClass().getSimpleName()+". Original reader data is unchanged.";}
            String finalMessage=message;
            runOnUiThread(()->{if(!isDestroyed())new AlertDialog.Builder(this).setMessage(finalMessage).setPositiveButton("Close",(d,w)->finish()).setOnCancelListener(d->finish()).show();});
        });
    }
}

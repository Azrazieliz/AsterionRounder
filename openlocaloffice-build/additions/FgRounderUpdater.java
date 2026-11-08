package com.openlocal.office.core;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native self-updater. Inspired by the Control in-app installer workflow.
 * Only the project's official GitHub release APK, signed with the installed
 * app's same Android signer and with a strictly newer versionCode, is eligible.
 * Android's own package installer always handles the final user confirmation.
 */
public final class FgRounderUpdater {
    public interface Events {void send(String event);}
    private static final String API=
        "https://api.github.com/repos/Azrazieliz/AsterionRounder/releases?per_page=20";
    private static final String ASSET="app-release-signed.apk";
    private static final long MAX_BYTES=150L*1024*1024;
    private final Activity activity;
    private final Events events;
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private volatile boolean busy;
    private volatile Candidate latest;

    private static final class Candidate {
        String tag,url,sha;
        long size;
        int release;
    }
    public FgRounderUpdater(Activity activity,Events events){
        this.activity=activity;this.events=events;
    }
    private void emit(String status,String message,int percent,JSONObject extra){
        try{
            JSONObject payload=new JSONObject().put("status",status)
                .put("message",message).put("percent",percent);
            if(extra!=null){
                for(java.util.Iterator<String> keys=extra.keys();keys.hasNext();){
                    String k=keys.next();payload.put(k,extra.opt(k));
                }
            }
            events.send(payload.toString());
        }catch(Exception ignored){}
    }
    private void fail(String stage,Exception error){
        Log.w("FG_UPDATER","Update "+stage+" failed",error);
        emit("error",error.getMessage()==null?"Update unavailable":error.getMessage(),-1,null);
    }
    private static String asHttps(String value)throws Exception{
        URL url=new URL(value);
        String host=url.getHost().toLowerCase(Locale.ROOT);
        if(!"https".equalsIgnoreCase(url.getProtocol())||
           !("api.github.com".equals(host)||"github.com".equals(host)||
            "release-assets.githubusercontent.com".equals(host)||
            host.endsWith(".githubusercontent.com")))
            throw new SecurityException("Unexpected update host");
        return url.toExternalForm();
    }
    private static HttpURLConnection open(String target)throws Exception{
        String link=asHttps(target);
        for(int redirects=0;redirects<6;redirects++){
            HttpURLConnection c=(HttpURLConnection)new URL(link).openConnection();
            c.setInstanceFollowRedirects(false);
            c.setRequestProperty("User-Agent","AsterionRounderNativeUpdater/1");
            c.setRequestProperty("Accept","application/vnd.github+json");
            c.setConnectTimeout(12000);c.setReadTimeout(35000);
            int code=c.getResponseCode();
            if(code==301||code==302||code==303||code==307||code==308){
                String destination=c.getHeaderField("Location");
                c.disconnect();
                if(destination==null)throw new java.io.IOException("Update download redirect missing");
                link=asHttps(new URL(new URL(link),destination).toExternalForm());
                continue;
            }
            if(code!=200){
                c.disconnect();
                throw new java.io.IOException("Update server HTTP "+code);
            }
            return c;
        }
        throw new java.io.IOException("Too many update redirects");
    }
    private static byte[] metadata(String url,int limit)throws Exception {
        HttpURLConnection conn=open(url);
        try(InputStream in=conn.getInputStream();
            java.io.ByteArrayOutputStream buffer=new java.io.ByteArrayOutputStream()){
            byte[] block=new byte[8192];int n;
            while((n=in.read(block))!=-1){
                if(buffer.size()+n>limit)throw new java.io.IOException("Update metadata exceeds limit");
                buffer.write(block,0,n);
            }
            return buffer.toByteArray();
        }finally{conn.disconnect();}
    }
    private static String hex(byte[] bytes){
        StringBuilder builder=new StringBuilder(bytes.length*2);
        for(byte b:bytes)builder.append(String.format(Locale.ROOT,"%02x",b&255));
        return builder.toString();
    }
    private static Candidate discover()throws Exception {
        JSONArray releases=new JSONArray(new String(metadata(API,768*1024),
            java.nio.charset.StandardCharsets.UTF_8));
        Candidate best=null;
        for(int i=0;i<releases.length();i++){
            JSONObject release=releases.optJSONObject(i);
            if(release==null||release.optBoolean("draft",false))continue;
            String tag=release.optString("tag_name","");
            if(!tag.matches("file-gestioner-release-[0-9]+"))continue;
            int number;
            try{number=Integer.parseInt(tag.substring(tag.lastIndexOf('-')+1));}
            catch(NumberFormatException error){continue;}
            JSONArray assets=release.optJSONArray("assets");
            if(assets==null)continue;
            for(int j=0;j<assets.length();j++){
                JSONObject item=assets.optJSONObject(j);
                if(item==null||!ASSET.equals(item.optString("name")))continue;
                long size=item.optLong("size",0);
                String sha=item.optString("digest","");
                String uri=item.optString("browser_download_url","");
                if(size<4096||size>MAX_BYTES||!sha.matches("sha256:[0-9a-fA-F]{64}"))
                    continue;
                String expected="https://github.com/Azrazieliz/AsterionRounder/releases/download/"+tag+"/"+ASSET;
                if(!expected.equals(uri))continue;
                if(best==null||number>best.release){
                    best=new Candidate();best.tag=tag;best.release=number;
                    best.url=uri;best.sha=sha.substring(7).toLowerCase(Locale.ROOT);
                    best.size=size;
                }
            }
        }
        return best;
    }
    private long installedCode()throws Exception {
        PackageManager pm=activity.getPackageManager();
        PackageInfo installed=pm.getPackageInfo(activity.getPackageName(),0);
        return Build.VERSION.SDK_INT>=28?
            installed.getLongVersionCode():installed.versionCode;
    }
    public void check(){
        if(busy)return;
        busy=true;
        emit("checking","Checking official Rounder releases…",0,null);
        io.execute(()->{
            try{
                Candidate found=discover();latest=found;
                if(found==null){emit("none","No verified signed release is available.",-1,null);return;}
                JSONObject detail=new JSONObject().put("tag",found.tag)
                    .put("installedCode",installedCode())
                    .put("size",found.size)
                    .put("note","The downloaded APK will be checked for a newer Android version and the installed signer.");
                emit("available","Signed release "+found.release+" found",0,detail);
            }catch(Exception error){fail("check",error);}
            finally{busy=false;}
        });
    }
    private static Signature[] signing(PackageInfo info){
        if(Build.VERSION.SDK_INT<28)
            return info.signatures==null?new Signature[0]:info.signatures;
        if(info.signingInfo==null)return new Signature[0];
        return info.signingInfo.getApkContentsSigners();
    }
    private static String[] fingerprints(Signature[] values)throws Exception{
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        String[] result=new String[values.length];
        for(int i=0;i<values.length;i++)result[i]=hex(digest.digest(values[i].toByteArray()));
        Arrays.sort(result);
        return result;
    }
    private long verifiedCode(File file)throws Exception{
        PackageManager pm=activity.getPackageManager();
        int flags=Build.VERSION.SDK_INT>=28?
            PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES;
        PackageInfo apk=pm.getPackageArchiveInfo(file.getAbsolutePath(),flags);
        PackageInfo installed=pm.getPackageInfo(activity.getPackageName(),flags);
        if(apk==null||installed==null||!activity.getPackageName().equals(apk.packageName))
            throw new SecurityException("Downloaded APK has a different Android package identity");
        String[] expected=fingerprints(signing(installed));
        String[] actual=fingerprints(signing(apk));
        if(expected.length==0||actual.length==0||!Arrays.equals(expected,actual))
            throw new SecurityException("APK signing certificate differs from installed Rounder");
        long current=Build.VERSION.SDK_INT>=28?installed.getLongVersionCode():installed.versionCode;
        long update=Build.VERSION.SDK_INT>=28?apk.getLongVersionCode():apk.versionCode;
        if(update<=current)throw new IllegalArgumentException(
            "Already current: installed version "+current+", release version "+update);
        return update;
    }
    private File download(Candidate candidate)throws Exception{
        File target=FgRounderUpdateProvider.stagedFile(activity);
        File dir=target.getParentFile();
        if(!dir.isDirectory()&&!dir.mkdirs())throw new java.io.IOException("Cannot create update cache");
        File temp=new File(dir,"download.partial.apk");
        if(temp.exists()&&!temp.delete())throw new java.io.IOException("Cannot reset partial update");
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        long total=0;
        try{
            HttpURLConnection conn=open(candidate.url);
            try(InputStream in=conn.getInputStream();OutputStream out=new FileOutputStream(temp)){
                byte[] buffer=new byte[32768];int n;int previous=-1;
                while((n=in.read(buffer))!=-1){
                    total+=n;if(total>MAX_BYTES||total>candidate.size)
                        throw new java.io.IOException("APK exceeds declared release size");
                    out.write(buffer,0,n);digest.update(buffer,0,n);
                    int progress=(int)(total*100/Math.max(1,candidate.size));
                    if(progress!=previous && (progress%5==0||progress==100)){
                        previous=progress;
                        emit("downloading","Downloading signed Rounder APK",progress,null);
                    }
                }
            }finally{conn.disconnect();}
            if(total!=candidate.size)
                throw new java.io.IOException("APK size mismatch");
            String actual=hex(digest.digest());
            if(!actual.equals(candidate.sha))
                throw new SecurityException("APK SHA-256 mismatch");
            long code=verifiedCode(temp);
            if(target.exists()&&!target.delete())
                throw new java.io.IOException("Cannot replace staged APK");
            if(!temp.renameTo(target))throw new java.io.IOException("Cannot stage verified APK");
            emit("verified","Signed Android update v"+code+" verified.",100,
                new JSONObject().put("versionCode",code).put("tag",candidate.tag));
            return target;
        }catch(Exception exception){
            temp.delete();throw exception;
        }
    }
    private void promptInstaller(File file){
        activity.runOnUiThread(()->{
            try{
                if(Build.VERSION.SDK_INT>=26&&!activity.getPackageManager().canRequestPackageInstalls()){
                    Intent settings=new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:"+activity.getPackageName()));
                    emit("permission","Allow updates from Rounder in Android settings, then press Install again.",100,null);
                    activity.startActivity(settings);
                    return;
                }
                Intent install=new Intent(Intent.ACTION_VIEW);
                Uri content=FgRounderUpdateProvider.APK;
                install.setDataAndType(content,"application/vnd.android.package-archive");
                install.setClipData(ClipData.newRawUri("Verified Rounder APK",content));
                install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                activity.startActivity(install);
                emit("installer","Android installer opened. Confirm the update to proceed.",100,null);
            }catch(Exception error){fail("installer",error);}
        });
    }
    public void install(){
        if(busy)return;
        busy=true;
        io.execute(()->{
            try{
                File target=FgRounderUpdateProvider.stagedFile(activity);
                Candidate candidate=latest;
                if(candidate==null)candidate=discover();
                if(candidate==null)throw new java.io.IOException("No signed release to install");
                if(target.isFile()&&target.length()==candidate.size){
                    MessageDigest d=MessageDigest.getInstance("SHA-256");
                    try(InputStream in=new FileInputStream(target)){
                        byte[] bytes=new byte[32768];int n;
                        while((n=in.read(bytes))!=-1)d.update(bytes,0,n);
                    }
                    if(hex(d.digest()).equals(candidate.sha)){
                        verifiedCode(target);
                        emit("verified","Previously downloaded signed APK verified.",100,null);
                        promptInstaller(target);return;
                    }
                }
                File staged=download(candidate);
                promptInstaller(staged);
            }catch(IllegalArgumentException already){
                emit("current",already.getMessage(),100,null);
            }catch(Exception error){fail("install",error);}
            finally{busy=false;}
        });
    }
}
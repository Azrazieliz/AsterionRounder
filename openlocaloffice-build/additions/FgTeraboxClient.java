package com.openlocal.office.core;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.Uri;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.*;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Native TeraBox cloud access, independent of PC connectivity.
 * Portable client intended for reuse by AsterionCore. The supplied ndus
 * session cookie is encrypted using Android Keystore, never sent to logs, JS,
 * third-party providers or file URLs. First-page responses are independent of
 * whole-folder enumeration; callers advance pages in the background.
 */
public final class FgTeraboxClient {
    private static final String KEY_ALIAS="fg_terabox_ndus_v1";
    private static final String API="https://www.terabox.com";
    private static final int PAGE=100;
    private final Context app;
    private final SharedPreferences prefs;
    private final java.util.concurrent.atomic.AtomicInteger thumbnailWrites=
        new java.util.concurrent.atomic.AtomicInteger();
    private final Map<String,String> thumbUrls=Collections.synchronizedMap(
        new LinkedHashMap<String,String>(1200,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,String> oldest){
                return size()>1600;
            }
        });
    // A short-lived hot page index avoids repeatedly inflating the same
    // ~100-entry cloud metadata page for every nearby thumbnail miss.
    // Bound both count and age; disk cache remains canonical and survives restarts.
    private static final class HotPage {
        final JSONArray rows;
        final long loadedAt;
        HotPage(JSONArray rows,long loadedAt){this.rows=rows;this.loadedAt=loadedAt;}
    }
    private final Map<String,HotPage> hotPages=
        new LinkedHashMap<String,HotPage>(48,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,HotPage> oldest){
                return size()>32;
            }
        };
    private void cacheHotPage(String key,JSONArray rows){
        synchronized(hotPages){
            hotPages.put(key,new HotPage(rows,android.os.SystemClock.elapsedRealtime()));
        }
    }
    public FgTeraboxClient(Context context){
        app=context.getApplicationContext();
        prefs=app.getSharedPreferences("fg_terabox_secure",Context.MODE_PRIVATE);
    }
    public static int pageSize(){return PAGE;}
    private SecretKey key() throws Exception {
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        SecretKey existing=(SecretKey)ks.getKey(KEY_ALIAS,null);
        if(existing!=null)return existing;
        KeyGenerator gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        gen.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256).build());
        return gen.generateKey();
    }
    public synchronized boolean setCookie(String userInput){
        if(userInput==null)return false;
        String token=userInput.trim();
        java.util.regex.Matcher found=java.util.regex.Pattern
            .compile("(?:^|;\\s*)ndus=([^;]+)",java.util.regex.Pattern.CASE_INSENSITIVE)
            .matcher(token);
        if(found.find())token=found.group(1).trim();
        else if(token.contains(";")||token.contains("="))return false;
        if(token.length()<12||token.length()>8192||token.contains("\n")||
           token.contains("\r")||token.contains(" "))return false;
        try{
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key());
            byte[] ciphertext=cipher.doFinal(token.getBytes(StandardCharsets.UTF_8));
            synchronized(hotPages){hotPages.clear();}
            prefs.edit().putString("preview_scope",java.util.UUID.randomUUID().toString())
                .putString("ndus",Base64.encodeToString(ciphertext,Base64.NO_WRAP))
                .putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
                .apply();
            return true;
        }catch(Exception error){
            android.util.Log.w("FG_TERA","Keystore failed: "+error.getClass().getSimpleName());
            return false;
        }
    }
    public synchronized void disconnect(){
        linkCache.clear();thumbUrls.clear();
        synchronized(hotPages){hotPages.clear();}
        prefs.edit().remove("ndus").remove("iv").remove("preview_scope").apply();
    }
    public boolean configured(){return prefs.contains("ndus")&&prefs.contains("iv");}
    // Random UUID is rotated on reconnect and is NOT the ndus token.
    // Scoped private metadata pages can never leak between TeraBox accounts.
    public String metadataScope(){return prefs.getString("preview_scope","");}
    private String cookie() throws Exception{
        String ciphertext=prefs.getString("ndus",null);
        String iv=prefs.getString("iv",null);
        if(ciphertext==null||iv==null)throw new IOException("TeraBox account is not connected");
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,
            Base64.decode(iv,Base64.NO_WRAP)));
        return "ndus="+new String(cipher.doFinal(
            Base64.decode(ciphertext,Base64.NO_WRAP)),StandardCharsets.UTF_8);
    }
    private static String safePath(String path){
        if(path==null||path.isEmpty()||"/".equals(path))return "/";
        if(!path.startsWith("/")||path.contains("\r")||path.contains("\n")||
            path.contains("\\")||path.contains("/../")||path.endsWith("/..")||
            path.contains("/./")||path.endsWith("/."))throw new IllegalArgumentException("Invalid cloud path");
        return path;
    }
    private static String typeFor(String name){
        String low=name.toLowerCase(Locale.ROOT);
        if(low.endsWith(".png"))return "image/png";
        if(low.endsWith(".webp"))return "image/webp";
        if(low.endsWith(".gif"))return "image/gif";
        if(low.endsWith(".avif"))return "image/avif";
        if(low.endsWith(".jpg")||low.endsWith(".jpeg"))return "image/jpeg";
        if(low.endsWith(".pdf"))return "application/pdf";
        if(low.endsWith(".mp4"))return "video/mp4";
        if(low.endsWith(".webm"))return "video/webm";
        if(low.endsWith(".zip"))return "application/zip";
        return "application/octet-stream";
    }
    public static boolean image(String path){
        return typeFor(path).startsWith("image/");
    }
    public static String mime(String path){return typeFor(path);}
    private JSONObject api(String endpoint,Map<String,String> args) throws Exception{
        Uri.Builder url=Uri.parse(API+endpoint).buildUpon();
        url.appendQueryParameter("app_id","250528")
            .appendQueryParameter("channel","dubox")
            .appendQueryParameter("clienttype","0");
        for(Map.Entry<String,String> entry:args.entrySet())
            url.appendQueryParameter(entry.getKey(),entry.getValue());
        HttpURLConnection connection=(HttpURLConnection)new URL(url.build().toString()).openConnection();
        connection.setConnectTimeout(8500);
        connection.setReadTimeout(35000);
        connection.setRequestProperty("Cookie",cookie());
        connection.setRequestProperty("Referer",API+"/");
        connection.setRequestProperty("X-Requested-With","XMLHttpRequest");
        connection.setRequestProperty("Accept","application/json, text/plain, */*");
        connection.setRequestProperty("User-Agent","Mozilla/5.0 (Linux; Android) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36");
        try{
            int status=connection.getResponseCode();
            if(status!=200)throw new IOException("TeraBox HTTP "+status);
            try(InputStream input=connection.getInputStream();
                ByteArrayOutputStream output=new ByteArrayOutputStream()){
                byte[] buffer=new byte[32768];int n,total=0;
                while((n=input.read(buffer))>=0){
                    total+=n;
                    if(total>5*1024*1024)throw new IOException("Cloud response exceeds metadata limit");
                    output.write(buffer,0,n);
                }
                JSONObject json=new JSONObject(output.toString("UTF-8"));
                int error=json.optInt("errno",0);
                if(error!=0)throw new IOException("TeraBox error code "+error+
                    (error==2?" (session may have expired)":""));
                return json;
            }
        }finally{connection.disconnect();}
    }

    /**
     * Authenticated server-side file operations. Never downloads, renames on
     * collision, or deletes data. Based on TeraBox's /api/filemanager contract;
     * a provider rejection is an error, not a silently successful move.
     */
    private JSONObject postCloud(String endpoint,Map<String,String> query,
                                 Map<String,String> fields)throws Exception {
        Uri.Builder url=Uri.parse(API+endpoint).buildUpon()
            .appendQueryParameter("app_id","250528")
            .appendQueryParameter("channel","dubox")
            .appendQueryParameter("clienttype","0");
        for(Map.Entry<String,String> arg:query.entrySet())
            url.appendQueryParameter(arg.getKey(),arg.getValue());
        HttpURLConnection conn=(HttpURLConnection)new URL(url.build().toString()).openConnection();
        conn.setInstanceFollowRedirects(false);
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(8500);
        conn.setReadTimeout(45000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Cookie",cookie());
        conn.setRequestProperty("Referer",API+"/");
        conn.setRequestProperty("X-Requested-With","XMLHttpRequest");
        conn.setRequestProperty("Accept","application/json");
        conn.setRequestProperty("User-Agent","Mozilla/5.0 (Linux; Android) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36");
        conn.setRequestProperty("Content-Type","application/x-www-form-urlencoded; charset=UTF-8");
        StringBuilder form=new StringBuilder();
        for(Map.Entry<String,String> field:fields.entrySet()){
            if(form.length()>0)form.append('&');
            form.append(java.net.URLEncoder.encode(field.getKey(),"UTF-8"));
            form.append('=');
            form.append(java.net.URLEncoder.encode(field.getValue(),"UTF-8"));
        }
        byte[] data=form.toString().getBytes(StandardCharsets.UTF_8);
        if(data.length>8192)throw new IOException("Cloud operation too large");
        try {
            conn.setFixedLengthStreamingMode(data.length);
            try(OutputStream out=conn.getOutputStream()){out.write(data);}
            int status=conn.getResponseCode();
            if(status!=200)throw new IOException("Cloud operation HTTP "+status);
            try(InputStream in=conn.getInputStream();
                ByteArrayOutputStream out=new ByteArrayOutputStream()){
                byte[] block=new byte[4096];int count;
                while((count=in.read(block))>=0){
                    if(out.size()+count>128*1024)throw new IOException("Cloud response too large");
                    out.write(block,0,count);
                }
                JSONObject response=new JSONObject(out.toString("UTF-8"));
                if(!response.has("errno")||response.optInt("errno",-1)!=0)
                    throw new IOException("Cloud operation rejected: "+response.optInt("errno",-1));
                if(response.optJSONObject("info")!=null&&
                   response.getJSONObject("info").optInt("errno",0)!=0)
                    throw new IOException("Cloud operation reported nested failure");
                return response;
            }
        }finally{conn.disconnect();}
    }
    /** Explicitly create a destination directory. Never overwrite existing. */
    public void createDirectory(String path)throws Exception {
        String safe=safePath(path);
        if("/".equals(safe))return;
        Map<String,String> query=new LinkedHashMap<>();
        query.put("a","commit");
        Map<String,String> form=new LinkedHashMap<>();
        form.put("path",safe);form.put("isdir","1");
        form.put("block_list","[]");
        postCloud("/api/create",query,form);
    }
    /** Fail-closed server-side move with source and destination verification. */
    public void moveFileChecked(String source,String directory,String name,
                                long expectedSize)throws Exception {
        String from=safePath(source),dest=safePath(directory);
        if(from.equals("/")||dest.equals("/")||name==null||
            name.isBlank()||name.contains("/")||name.contains("\\")||
            name.equals(".")||name.equals("..")||
            from.equals(dest+"/"+name))
            throw new IllegalArgumentException("Invalid move");
        JSONArray files=new JSONArray();
        files.put(new JSONObject().put("path",from).put("dest",dest)
            .put("newname",name));
        Map<String,String> query=new LinkedHashMap<>();
        query.put("onnest","fail");query.put("opera","move");
        Map<String,String> form=new LinkedHashMap<>();
        form.put("async","0");form.put("filelist",files.toString());
        form.put("ondup","fail");
        postCloud("/api/filemanager",query,form);
        String target=dest+"/"+name;
        JSONObject readBack=fileDetails(target);
        if(!target.equals(readBack.optString("path","")))
            throw new IOException("Move response unverified: destination path");
        long remoteSize=readBack.optLong("size",-1);
        if(expectedSize>=0&&remoteSize!=expectedSize)
            throw new IOException("Move response unverified: destination size");
    }


    /**
     * Explicit owner-selected deletion of one cloud file. Request is sent
     * only after the original and a surviving matching copy were validated
     * by the organizer. Never called by scheduled sorting.
     *
     * TeraBox's filemanager/delete can move the file to its recycle bin;
     * actual recovery is provider-dependent. Verify absence before counting.
     */
    public void deleteDuplicateChecked(String path,String knownMd5,long knownSize)
            throws Exception {
        String safe=safePath(path);
        if(safe.equals("/")||knownSize<0||knownMd5==null||
           !knownMd5.matches("[0-9a-f]{32}"))
            throw new IllegalArgumentException("Invalid duplicate deletion request");
        JSONObject original=fileDetails(safe);
        String remoteMd5=original.optString("md5","").toLowerCase(Locale.ROOT);
        if(!knownMd5.equals(remoteMd5)||original.optLong("size",-1)!=knownSize)
            throw new IOException("Original content has changed; deletion refused");
        Map<String,String> query=new LinkedHashMap<>();
        query.put("opera","delete");
        query.put("onnest","fail");
        Map<String,String> form=new LinkedHashMap<>();
        form.put("async","0");
        form.put("filelist",new JSONArray().put(safe).toString());
        JSONObject response=postCloud("/api/filemanager",query,form);
        JSONArray info=response.optJSONArray("info");
        if(info!=null){
            for(int i=0;i<info.length();i++){
                JSONObject row=info.optJSONObject(i);
                if(row!=null&&row.optInt("errno",0)!=0)
                    throw new IOException("TeraBox rejected file deletion");
            }
        }
        // Metadata endpoint is authoritative for newly missing paths.
        // Unknown transport errors are not reported as confirmed deletion.
        JSONObject reread;
        try{reread=fileDetails(safe);}
        catch(IOException absent){
            // The provider can return a generic metadata failure, so the
            // result remains unverified until a fresh parent listing confirms.
            reread=null;
        }
        if(reread!=null&&reread.optString("path","").equals(safe))
            throw new IOException("TeraBox still reports the selected file");
        String parent=safe.substring(0,safe.lastIndexOf('/'));
        if(parent.isEmpty())parent="/";
        boolean stillListed=false;
        // Fresh listPage bypasses disk metadata cache, and does not fetch media.
        JSONArray listed=listPage(parent,1);
        for(int i=0;i<listed.length();i++){
            JSONObject row=listed.optJSONObject(i);
            if(row!=null&&safe.equals(row.optString("path",""))){
                stillListed=true;break;
            }
        }
        if(stillListed)
            throw new IOException("Deletion unverified: source remains in cloud folder");
        // For directories larger than one page, a single listing cannot prove
        // absence; leave the operation in a review-needed state.
        if(listed.length()>=pageSize())
            throw new IOException("Deletion submitted; verify cloud recycle bin and refresh index");
    }

    /** Fresh metadata for newest incoming items; bypass the browsing cache. */
    public JSONArray listIncomingPage(String path,int page)throws Exception{
        if(page<1||page>20)throw new IllegalArgumentException("Incoming page out of range");
        Map<String,String> args=new LinkedHashMap<>();
        args.put("dir",safePath(path));
        args.put("page",Integer.toString(page));
        args.put("num",Integer.toString(PAGE));
        args.put("order","time");args.put("desc","1");args.put("web","1");
        JSONObject data=api("/api/list",args);
        JSONArray rows=data.optJSONArray("list");
        if(rows==null)throw new IOException("TeraBox incoming listing not available");
        return rows;
    }
    public JSONArray listPage(String path,int page) throws Exception{
        if(page<1||page>100000)throw new IllegalArgumentException("Page out of range");
        Map<String,String> args=new LinkedHashMap<>();
        args.put("dir",safePath(path));args.put("page",Integer.toString(page));
        args.put("num",Integer.toString(PAGE));
        args.put("web","1");
        JSONObject result=api("/api/list",args);
        JSONArray rows=result.optJSONArray("list");
        if(rows==null)throw new IOException("TeraBox did not return a file list");
        for(int i=0;i<rows.length();i++){
            JSONObject item=rows.optJSONObject(i);
            if(item==null||item.optInt("isdir",0)==1)continue;
            JSONObject thumbs=item.optJSONObject("thumbs");
            if(thumbs==null)continue;
            String url=thumbs.optString("url3",thumbs.optString("url2",""));
            String cloudPath=item.optString("path","");
            if(!cloudPath.isEmpty()&&(url.startsWith("https://")||
                url.startsWith("http://")))thumbUrls.put(cloudPath,url);
        }
        return rows;
    }
    /**
     * Persist DIRECTORY METADATA only. Files and original image pixels are
     * never copied. Reopening a huge library reuses its last short-lived
     * page index, while new/changed entries are rechecked after the TTL.
     */
    public JSONArray listPageCached(String folder,int page)throws Exception{
        final String scope=metadataScope();
        if(scope.isEmpty())return listPage(folder,page);
        String hotKey=scope+"|"+folder+"|"+page;
        synchronized(hotPages){
            HotPage hit=hotPages.get(hotKey);
            if(hit!=null&&android.os.SystemClock.elapsedRealtime()-hit.loadedAt<90000)
                return hit.rows;
        }
        File dir=new File(app.getFilesDir(),"terabox-directory-pages-v1");
        if(!dir.isDirectory()&&!dir.mkdirs())return listPage(folder,page);
        File saved=new File(dir,cacheId(scope+"|"+folder+"|"+page)+".gz");
        long age=System.currentTimeMillis()-saved.lastModified();
        if(saved.isFile()&&age>=0&&age<15L*60*1000L){
            try(java.util.zip.GZIPInputStream in=new java.util.zip.GZIPInputStream(
                new FileInputStream(saved))){
                ByteArrayOutputStream out=new ByteArrayOutputStream(40*1024);
                byte[] buffer=new byte[8192];int n;
                while((n=in.read(buffer))!=-1){
                    if(out.size()+n>1024*1024)throw new IOException("Invalid metadata index");
                    out.write(buffer,0,n);
                }
                JSONArray rows=new JSONArray(out.toString("UTF-8"));
                // Restore signed thumbnail URLs supplied in the original
                // directory listing so one filemetas call per thumbnail
                // is never required merely because the process restarted.
                for(int i=0;i<rows.length();i++){
                    JSONObject item=rows.optJSONObject(i);
                    if(item==null||item.optInt("isdir",0)!=0)continue;
                    JSONObject thumbs=item.optJSONObject("thumbs");
                    if(thumbs==null)continue;
                    String url=thumbs.optString("url3",thumbs.optString("url2",""));
                    String path=item.optString("path","");
                    if(!path.isEmpty()&&url.startsWith("https://"))
                        thumbUrls.put(path,url);
                }
                cacheHotPage(hotKey,rows);
                return rows;
            }catch(Exception invalid){saved.delete();}
        }
        JSONArray latest=listPage(folder,page);
        cacheHotPage(hotKey,latest);
        byte[] bytes=latest.toString().getBytes(StandardCharsets.UTF_8);
        if(bytes.length<=1024*1024){
            File tmp=new File(dir,saved.getName()+"."+java.util.UUID.randomUUID()+".part");
            try(java.util.zip.GZIPOutputStream zip=new java.util.zip.GZIPOutputStream(
                new FileOutputStream(tmp))){
                zip.write(bytes);
            }catch(Exception ex){tmp.delete();return latest;}
            if(!tmp.renameTo(saved)){
                if(saved.exists())saved.delete();
                if(!tmp.renameTo(saved))tmp.delete();
            }
        }
        return latest;
    }

    public JSONObject fileDetails(String path) throws Exception{
        JSONArray names=new JSONArray();names.put(safePath(path));
        Map<String,String> args=new LinkedHashMap<>();
        args.put("target",names.toString());args.put("dlink","1");
        args.put("origin","dlna");
        JSONObject result=api("/api/filemetas",args);
        JSONArray info=result.optJSONArray("info");
        if(info==null||info.length()<1)throw new IOException("TeraBox file metadata unavailable");
        JSONObject details=info.getJSONObject(0);
        if(details.optInt("errno",0)!=0)throw new IOException("TeraBox file is inaccessible");
        return details;
    }
    private static final class Link {
        final String url;
        final long timestamp;
        Link(String url,long timestamp){this.url=url;this.timestamp=timestamp;}
    }
    private final Map<String,Link> linkCache=Collections.synchronizedMap(
        new LinkedHashMap<String,Link>(64,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,Link> entry){
                return size()>128;
            }
        });
    private String liveLink(String path) throws Exception{
        path=safePath(path);
        Link cached=linkCache.get(path);
        long now=android.os.SystemClock.elapsedRealtime();
        if(cached!=null&&now-cached.timestamp<180000)return cached.url;
        String link=fileDetails(path).optString("dlink","");
        if(!link.startsWith("https://"))
            throw new IOException("TeraBox has not supplied an HTTPS file stream");
        linkCache.put(path,new Link(link,now));
        return link;
    }
    /**
     * Open a single persistent HTTPS byte-range response for sequential media
     * decoding. A seek creates a new response, but ordinary reads reuse the
     * existing connection instead of making one HTTP request per 512 KiB.
     * Never downloads, caches or exposes a complete movie.
     */
    public InputStream openRangeStream(String path,long offset) throws Exception {
        if(offset<0)throw new IllegalArgumentException("Negative media offset");
        String safe=safePath(path);
        for(int attempt=0;attempt<2;attempt++){
            URL url=new URL(liveLink(safe));
            for(int redirect=0;redirect<7;redirect++){
                if(!"https".equalsIgnoreCase(url.getProtocol()))
                    throw new IOException("Insecure TeraBox media redirect");
                HttpURLConnection c=(HttpURLConnection)url.openConnection();
                c.setInstanceFollowRedirects(false);
                c.setConnectTimeout(9000);
                c.setReadTimeout(35000);
                c.setRequestProperty("User-Agent",
                    "Mozilla/5.0 (Linux; Android) AppleWebKit/537.36");
                c.setRequestProperty("Referer","https://www.terabox.com/");
                c.setRequestProperty("Range","bytes="+offset+"-");
                c.setRequestProperty("Accept-Encoding","identity");
                String host=url.getHost().toLowerCase(Locale.ROOT);
                if(host.equals("terabox.com")||host.endsWith(".terabox.com")||
                   host.equals("dubox.com")||host.endsWith(".dubox.com")||
                   host.equals("freeterabox.com")||host.endsWith(".freeterabox.com"))
                    c.setRequestProperty("Cookie",cookie());
                try{
                    int status=c.getResponseCode();
                    if(status>=300&&status<400){
                        String location=c.getHeaderField("Location");
                        if(location==null||location.isEmpty())
                            throw new IOException("Missing cloud media redirect");
                        url=new URL(url,location);
                        c.disconnect();
                        continue;
                    }
                    if((status==401||status==403)&&attempt==0){
                        synchronized(linkCache){linkCache.remove(safe);}
                        c.disconnect();
                        break;
                    }
                    if(status!=206&&!(status==200&&offset==0))
                        throw new IOException("TeraBox media range HTTP "+status);
                    if(status==206){
                        String contentRange=c.getHeaderField("Content-Range");
                        if(contentRange==null||!contentRange.startsWith("bytes "+offset+"-"))
                            throw new IOException("Cloud media byte-range mismatch");
                    }
                    final InputStream response=c.getInputStream();
                    final HttpURLConnection live=c;
                    return new FilterInputStream(response){
                        @Override public void close() throws IOException {
                            try{super.close();}finally{live.disconnect();}
                        }
                    };
                }catch(Exception error){c.disconnect();throw error;}
            }
        }
        throw new IOException("TeraBox media stream authorization unavailable");
    }
    /**
     * Read exactly a bounded region of a TeraBox file, without a whole-file
     * temp copy. HTTP 206 and the matching Content-Range are mandatory for
     * nonzero offsets. This is the random-access contract used by Android's
     * DocumentsProvider for PDF, ZIP64, video and image decoders.
     */
    public byte[] readRange(String path,long offset,int requested) throws Exception{
        if(offset<0||requested<1||requested>2*1024*1024)
            throw new IllegalArgumentException("Invalid byte range");
        String safe=safePath(path);
        for(int attempt=0;attempt<2;attempt++){
            URL url=new URL(liveLink(safe));
            for(int redirect=0;redirect<7;redirect++){
                if(!"https".equalsIgnoreCase(url.getProtocol()))
                    throw new IOException("Insecure TeraBox range redirect");
                HttpURLConnection c=(HttpURLConnection)url.openConnection();
                c.setInstanceFollowRedirects(false);
                c.setConnectTimeout(9000);c.setReadTimeout(30000);
                c.setRequestProperty("User-Agent","Mozilla/5.0 (Linux; Android) AppleWebKit/537.36");
                c.setRequestProperty("Referer","https://www.terabox.com/");
                c.setRequestProperty("Range","bytes="+offset+"-"+(offset+requested-1));
                c.setRequestProperty("Accept-Encoding","identity");
                String host=url.getHost().toLowerCase(Locale.ROOT);
                if(host.equals("terabox.com")||host.endsWith(".terabox.com")||
                   host.equals("dubox.com")||host.endsWith(".dubox.com")||
                   host.equals("freeterabox.com")||host.endsWith(".freeterabox.com"))
                    c.setRequestProperty("Cookie",cookie());
                try{
                    int status=c.getResponseCode();
                    if(status>=300&&status<400){
                        String location=c.getHeaderField("Location");
                        if(location==null||location.isEmpty())throw new IOException("Missing redirect");
                        url=new URL(url,location);
                        continue;
                    }
                    if((status==403||status==401)&&attempt==0){
                        linkCache.remove(safe);
                        break;
                    }
                    if(status!=206 && !(status==200&&offset==0))
                        throw new IOException("TeraBox range unsupported (HTTP "+status+")");
                    if(status==206){
                        String range=c.getHeaderField("Content-Range");
                        if(range==null||!range.startsWith("bytes "+offset+"-"))
                            throw new IOException("TeraBox returned an incorrect byte range");
                    }
                    try(InputStream in=c.getInputStream();
                        ByteArrayOutputStream bytes=new ByteArrayOutputStream(requested)){
                        byte[] buffer=new byte[32768];
                        while(bytes.size()<requested){
                            int n=in.read(buffer,0,Math.min(buffer.length,requested-bytes.size()));
                            if(n<0)break;
                            if(n>0)bytes.write(buffer,0,n);
                        }
                        return bytes.toByteArray();
                    }
                }finally{c.disconnect();}
            }
        }
        throw new IOException("TeraBox access denied or too many redirects");
    }
    public InputStream open(String path) throws Exception{
        String link=liveLink(path);
        URL url=new URL(link);
        for(int redirect=0;redirect<7;redirect++){
            if(!"https".equalsIgnoreCase(url.getProtocol()))
                throw new IOException("Insecure cloud file redirect blocked");
            HttpURLConnection stream=(HttpURLConnection)url.openConnection();
            stream.setInstanceFollowRedirects(false);
            stream.setConnectTimeout(12000);stream.setReadTimeout(50000);
            stream.setRequestProperty("User-Agent","Mozilla/5.0 (Linux; Android) AppleWebKit/537.36");
            stream.setRequestProperty("Referer","https://www.terabox.com/");
            String host=url.getHost().toLowerCase(Locale.ROOT);
            // NDUS is sent only to the official TeraBox/Dubox domains.
            // Manual redirects prevent leaking it to arbitrary file CDNs.
            if(host.equals("terabox.com")||host.endsWith(".terabox.com")||
               host.equals("dubox.com")||host.endsWith(".dubox.com")||
                   host.equals("freeterabox.com")||host.endsWith(".freeterabox.com")){
                stream.setRequestProperty("Cookie",cookie());
            }
            try{
                int code=stream.getResponseCode();
                if(code>=300&&code<400){
                    String location=stream.getHeaderField("Location");
                    stream.disconnect();
                    if(location==null||location.isEmpty())
                        throw new IOException("Cloud file redirect has no destination");
                    url=new URL(url,location);continue;
                }
                if(code<200||code>=300)throw new IOException("Cloud download HTTP "+code);
                InputStream raw=stream.getInputStream();
                final HttpURLConnection connected=stream;
                return new FilterInputStream(raw){
                    @Override public void close() throws IOException{
                        try{super.close();}finally{connected.disconnect();}
                    }
                };
            }catch(Exception e){stream.disconnect();throw e;}
        }
        throw new IOException("Too many cloud download redirects");
    }
    /**
     * Read a cloud-provided thumbnail without downloading a full image.
     * Returned stream is closed by the WebResourceResponse consumer.
     */
    private static String cacheId(String value){
        try{
            byte[] bytes=java.security.MessageDigest.getInstance("SHA-256").digest(
                value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out=new StringBuilder();
            for(byte b:bytes)out.append(String.format(Locale.ROOT,"%02x",b&255));
            return out.toString();
        }catch(Exception ex){return Integer.toHexString(value.hashCode());}
    }
    private File coverDir() throws IOException{
        File dir=new File(app.getFilesDir(),"terabox-thumbnails-v4");
        if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Private thumbnail cache unavailable");
        return dir;
    }
    private void pruneCovers(File shard){
        File[] files=shard.listFiles((d,name)->name.endsWith(".jpg"));
        if(files==null||files.length<20)return;
        // 256 independent hash shards keep each maintenance pass bounded
        // even for 300,000+ private thumbnails. Leave most device space free.
        long quota=Math.min(12L*1024*1024*1024,
            Math.max(128L*1024*1024,shard.getUsableSpace()/4));
        long shardBudget=Math.max(512L*1024,quota/256);
        Arrays.sort(files,Comparator.comparingLong(File::lastModified).reversed());
        long total=0;
        for(int i=0;i<files.length;i++){
            total+=files[i].length();
            if(i>=2400||total>shardBudget)files[i].delete();
        }
    }
    /** Persistent, private, size-bounded thumbnails. No full image downloads. */
    public InputStream openThumbnail(String path) throws Exception{
        return openThumbnail(path,null,-1);
    }
    /**
     * An optional metadata-page hint recovers a batch of up to 100 signed
     * thumbnail URLs from the local page cache. This prevents a separate
     * /api/filemetas network call for every visible thumbnail after the
     * 1600-entry in-memory URL window has rotated out on huge collections.
     * The original file is never downloaded on this code path.
     */
    public InputStream openThumbnail(String path,String folder,int page) throws Exception{
        final String safe=safePath(path);
        String scope=prefs.getString("preview_scope","v1");
        File dir=coverDir();
        String key=cacheId(scope+":"+safe);
        File shard=new File(dir,key.substring(0,2));
        if(!shard.isDirectory()&&!shard.mkdirs())
            throw new IOException("Private thumbnail shard unavailable");
        File cached=new File(shard,key+".jpg");
        // Migrate older cache entries on demand. Moving a cached preview
        // preserves its bytes without downloading an original or thumbnail.
        if(!cached.isFile()){
            File oldFlat=new File(dir,key+".jpg");
            File oldV3=new File(new File(app.getCacheDir(),
                "terabox-thumbnails-v3"),key+".jpg");
            for(File old:new File[]{oldFlat,oldV3}){
                if(old.isFile()&&old.length()>50){
                    if(old.renameTo(cached))break;
                    try(InputStream in=new FileInputStream(old);
                        OutputStream out=new FileOutputStream(cached)){
                        byte[] bytes=new byte[16384];int n;
                        while((n=in.read(bytes))!=-1)out.write(bytes,0,n);
                        old.delete();
                    }catch(IOException error){cached.delete();}
                    if(cached.isFile()&&cached.length()>50)break;
                }
            }
        }
        if(cached.isFile()&&cached.length()>50){
            cached.setLastModified(System.currentTimeMillis());
            return new FileInputStream(cached);
        }
        String thumb=thumbUrls.get(safe);
        if((thumb==null||thumb.isEmpty())&&folder!=null&&page>0){
            // Most pages are already on disk. Even an expired page costs
            // one metadata request for ~100 files rather than one per image.
            try{listPageCached(folder,page);}catch(Exception metadataError){
                android.util.Log.d("FG_TERA","Thumbnail page refresh unavailable");
            }
            thumb=thumbUrls.get(safe);
        }
        if(thumb==null||thumb.isEmpty()){
            JSONObject details=fileDetails(safe);
            JSONObject urls=details.optJSONObject("thumbs");
            if(urls!=null)thumb=urls.optString("url3",urls.optString("url2",urls.optString("url1","")));
        }
        if(thumb==null||thumb.isEmpty())throw new IOException("No server thumbnail");
        URL url=new URL(thumb);
        if(!"https".equalsIgnoreCase(url.getProtocol()))
            throw new IOException("Insecure thumbnail URL");
        // TeraBox may redirect thumbnails to a signed CDN.
        for(int hop=0;hop<6;hop++){
            HttpURLConnection request=(HttpURLConnection)url.openConnection();
            request.setInstanceFollowRedirects(false);
            request.setConnectTimeout(7000);
            request.setReadTimeout(12000);
            request.setRequestProperty("User-Agent",
                "Mozilla/5.0 (Linux; Android) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36");
            request.setRequestProperty("Referer","https://www.terabox.com/");
            String host=url.getHost().toLowerCase(Locale.ROOT);
            if(host.equals("terabox.com")||host.endsWith(".terabox.com")||
               host.equals("dubox.com")||host.endsWith(".dubox.com")||
                   host.equals("freeterabox.com")||host.endsWith(".freeterabox.com"))
                request.setRequestProperty("Cookie",cookie());
            try{
                int response=request.getResponseCode();
                if(response>=300&&response<400){
                    String redirect=request.getHeaderField("Location");
                    if(redirect==null||redirect.isEmpty())throw new IOException("Thumbnail redirect missing");
                    url=new URL(url,redirect);
                    if(!"https".equalsIgnoreCase(url.getProtocol()))
                        throw new IOException("Insecure thumbnail redirect");
                    continue;
                }
                if(response!=200&&response!=206)throw new IOException("Thumbnail HTTP "+response);
                File tmp=new File(shard,cached.getName()+"."+java.util.UUID.randomUUID()+".part");
                try(InputStream in=request.getInputStream();
                    FileOutputStream out=new FileOutputStream(tmp)){
                    byte[] buffer=new byte[16384];int n;long total=0;
                    while((n=in.read(buffer))!=-1){
                        if(n==0)continue;
                        total+=n;
                        if(total>3L*1024*1024)throw new IOException("Server thumbnail too large");
                        out.write(buffer,0,n);
                    }
                }catch(Exception ex){tmp.delete();throw ex;}
                if(tmp.length()<=50){tmp.delete();throw new IOException("Empty server thumbnail");}
                if(!tmp.renameTo(cached)){
                    if(!cached.isFile())throw new IOException("Cannot retain private thumbnail");
                    tmp.delete();
                }
                // Enumeration+sorting on EVERY new thumbnail becomes quadratic
                // for large libraries. Maintenance is amortized over 128 writes.
                if((thumbnailWrites.incrementAndGet()&63)==0)pruneCovers(shard);
                return new FileInputStream(cached);
            }finally{request.disconnect();}
        }
        throw new IOException("Too many thumbnail redirects");
    }
    public void save(String path,OutputStream output) throws Exception{
        try(InputStream input=open(path)){
            byte[] bytes=new byte[128*1024];int n;
            while((n=input.read(bytes))>=0)output.write(bytes,0,n);
        }
    }
    /**
     * Only provider metadata determines a missing TeraBox preview. A provider
     * placeholder returned as a valid image is NOT automatically diagnosed as
     * restricted; the owner can flag those through Rounder's file actions.
     * An absent HTTPS thumbnail is an observable, accurate condition.
     */
    public static boolean previewUnavailable(JSONObject source){
        if(source==null||source.optInt("isdir",0)!=0||
           !image(source.optString("server_filename","")))return false;
        JSONObject urls=source.optJSONObject("thumbs");
        if(urls==null)return true;
        for(String key:new String[]{"url1","url2","url3"}){
            String value=urls.optString(key,"");
            if(value.startsWith("https://"))return false;
        }
        return true;
    }
    public static JSONObject mapEntry(JSONObject source) throws Exception{
        String name=source.optString("server_filename","");
        String path=source.optString("path","");
        if(name.isEmpty()||path.isEmpty())throw new IOException("Cloud item missing name/path");
        boolean folder=source.optInt("isdir",0)!=0;
        long size=source.optLong("size",-1);
        long modified=source.optLong("server_mtime",0)*1000L;
        return new JSONObject().put("id",path).put("path",path)
            .put("name",name).put("title",name).put("folder",folder)
            .put("size",size).put("modified",modified)
            .put("mime",folder?"vnd.android.document/directory":typeFor(name))
            .put("uri","fgterabox://file/"+Uri.encode(path))
            .put("terabox",true)
            .put("previewUnavailable",!folder&&previewUnavailable(source));
    }
}

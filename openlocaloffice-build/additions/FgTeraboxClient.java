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
 * Native TeraBox cloud access, independent of RoundSync and PC connectivity.
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
    private final Map<String,String> thumbUrls=Collections.synchronizedMap(
        new LinkedHashMap<String,String>(1200,0.75f,true){
            @Override protected boolean removeEldestEntry(Map.Entry<String,String> oldest){
                return size()>1600;
            }
        });
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
    public synchronized void disconnect(){linkCache.clear();thumbUrls.clear();prefs.edit().remove("ndus").remove("iv").remove("preview_scope").apply();}
    public boolean configured(){return prefs.contains("ndus")&&prefs.contains("iv");}
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
        File dir=new File(app.getCacheDir(),"terabox-thumbnails-v3");
        if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Private thumbnail cache unavailable");
        return dir;
    }
    private void pruneCovers(File dir){
        File[] files=dir.listFiles((d,name)->name.endsWith(".jpg"));
        if(files==null||files.length<120)return;
        Arrays.sort(files,Comparator.comparingLong(File::lastModified).reversed());
        long total=0;
        for(int i=0;i<files.length;i++){
            total+=files[i].length();
            if(i>=900||total>120L*1024*1024)files[i].delete();
        }
    }
    /** Persistent, private, size-bounded thumbnails. No full image downloads. */
    public InputStream openThumbnail(String path) throws Exception{
        final String safe=safePath(path);
        String scope=prefs.getString("preview_scope","v1");
        File dir=coverDir();
        File cached=new File(dir,cacheId(scope+":"+safe)+".jpg");
        if(cached.isFile()&&cached.length()>50){
            cached.setLastModified(System.currentTimeMillis());
            return new FileInputStream(cached);
        }
        String thumb=thumbUrls.get(safe);
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
                File tmp=new File(dir,cached.getName()+".part");
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
                pruneCovers(dir);
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
            .put("terabox",true);
    }
}

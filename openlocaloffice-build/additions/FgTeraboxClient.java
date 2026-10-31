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
            prefs.edit().putString("ndus",Base64.encodeToString(ciphertext,Base64.NO_WRAP))
                .putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
                .apply();
            return true;
        }catch(Exception error){
            android.util.Log.w("FG_TERA","Keystore failed: "+error.getClass().getSimpleName());
            return false;
        }
    }
    public synchronized void disconnect(){prefs.edit().remove("ndus").remove("iv").apply();}
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
            if(item==null||item.optInt("isdir",0)!=0)continue;
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
        JSONObject result=api("/api/filemetas",args);
        JSONArray info=result.optJSONArray("info");
        if(info==null||info.length()<1)throw new IOException("TeraBox file metadata unavailable");
        JSONObject details=info.getJSONObject(0);
        if(details.optInt("errno",0)!=0)throw new IOException("TeraBox file is inaccessible");
        return details;
    }
    public InputStream open(String path) throws Exception{
        String link=fileDetails(path).optString("dlink","");
        if(!link.startsWith("https://"))
            throw new IOException("TeraBox did not provide a secure download URL");
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
               host.equals("dubox.com")||host.endsWith(".dubox.com")){
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
    public InputStream openThumbnail(String path) throws Exception{
        String thumb=thumbUrls.get(safePath(path));
        if(thumb==null||thumb.isEmpty())return open(path);
        URL target=new URL(thumb);
        if(!target.getProtocol().equals("https"))
            throw new IOException("Unsecured thumbnail URL rejected");
        HttpURLConnection request=(HttpURLConnection)target.openConnection();
        request.setConnectTimeout(8500);
        request.setReadTimeout(30000);
        request.setRequestProperty("User-Agent","Mozilla/5.0 (Linux; Android) AppleWebKit/537.36");
        request.setRequestProperty("Referer","https://www.terabox.com/");
        String host=target.getHost().toLowerCase(Locale.ROOT);
        if(host.equals("terabox.com")||host.endsWith(".terabox.com")||
           host.equals("dubox.com")||host.endsWith(".dubox.com"))
            request.setRequestProperty("Cookie",cookie());
        int status=request.getResponseCode();
        if(status<200||status>=300){
            request.disconnect();
            throw new IOException("Thumbnail HTTP "+status);
        }
        InputStream content=request.getInputStream();
        return new FilterInputStream(content){
            @Override public void close() throws IOException{
                try{super.close();}finally{request.disconnect();}
            }
        };
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

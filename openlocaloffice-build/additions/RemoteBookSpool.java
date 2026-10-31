package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import android.os.SystemClock;
import android.util.Log;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.ConcurrentHashMap;

/** Reusable disk cache for SAF pipes. Each remote archive is downloaded once.
 * Only explicit book-opening requests invoke this class. Library thumbnails
 * never invoke it. No source file is modified.
 */
public final class RemoteBookSpool {
    private static final ConcurrentHashMap<String,Object> LOCKS=
        new ConcurrentHashMap<>();
    private RemoteBookSpool(){}

    private static String identity(Uri uri,long length) {
        try{
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            byte[] hash=digest.digest((uri.toString()+"|"+length)
                .getBytes(StandardCharsets.UTF_8));
            StringBuilder sb=new StringBuilder();
            for(byte b:hash)sb.append(String.format(Locale.ROOT,"%02x",b&255));
            return sb.toString();
        }catch(Exception e){
            throw new IllegalStateException("Cannot hash archive cache identity",e);
        }
    }
    /** A cached archive can be read locally without touching Round Sync. */
    public static File completedFile(Context ctx,Uri uri,long expected){
        if(uri==null)return null;
        File ready=new File(new File(ctx.getCacheDir(),"reading-v2"),
            identity(uri,expected)+".zip");
        return ready.isFile()&&ready.length()>0&&
            (expected<0||ready.length()==expected)?ready:null;
    }
    public static boolean hasCompleted(Context ctx,Uri uri,long expected) {
        return completedFile(ctx,uri,expected)!=null;
    }
    public interface PreviewListener {
        void onFirstPage(String name,byte[] image);
        default void onPage(String name,byte[] image){onFirstPage(name,image);}
        void onProgress(long transferred,long expected);
    }
    /** Blocks concurrent requests for this exact source until a single complete
     * copy is available. Retains successful copies across reader sessions.
     */
    public static File obtain(Context ctx,Uri uri,long expected) throws IOException {
        return obtain(ctx,uri,expected,null);
    }
    public static File obtain(Context ctx,Uri uri,long expected,
                              PreviewListener preview) throws IOException {
        String key=identity(uri,expected);
        Object lock=LOCKS.computeIfAbsent(key,k->new Object());
        synchronized(lock){
            File dir=new File(ctx.getCacheDir(),"reading-v2");
            if(!dir.exists()&&!dir.mkdirs())
                throw new IOException("Cannot create remote book cache");
            File ready=new File(dir,key+".zip");
            if(ready.isFile()&&ready.length()>0&&
                (expected<0||ready.length()==expected)){
                Log.i("FG_PERF","CLOUD_SPOOL_CACHE_HIT bytes="+ready.length());
                ready.setLastModified(System.currentTimeMillis());
                return ready;
            }
            if(ready.exists()&&!ready.delete())
                throw new IOException("Cannot discard incomplete remote book cache");
            File pending=new File(dir,key+".part");
            if(pending.exists()&&!pending.delete())
                throw new IOException("Cannot discard unfinished remote download");
            long start=SystemClock.elapsedRealtime();
            final long[] counter={0};
            try(InputStream input=ctx.getContentResolver().openInputStream(uri);
                OutputStream output=new BufferedOutputStream(
                    new FileOutputStream(pending),128*1024)){
                if(input==null)throw new IOException("Document provider returned no stream");
                java.io.FilterInputStream tee=new java.io.FilterInputStream(input){
                    private void account(int n){
                        if(n<=0)return;
                        counter[0]+=n;
                        if(preview!=null&&counter[0]/(1024*1024)!=
                           (counter[0]-n)/(1024*1024)){
                            try{preview.onProgress(counter[0],expected);}
                            catch(Exception ignored){}
                        }
                    }
                    @Override public int read() throws IOException{
                        int value=in.read();
                        if(value>=0){output.write(value);account(1);}
                        return value;
                    }
                    @Override public int read(byte[] dst,int off,int length)throws IOException{
                        int n=in.read(dst,off,length);
                        if(n>0){output.write(dst,off,n);account(n);}
                        return n;
                    }
                };
                // Pages are extracted in local-header order AS the same cloud
                // stream is cached. Publish each completed page immediately.
                // The provider is opened exactly once; there is no second
                // network request for page 2, 3, ... or the cover.
                if(preview!=null){
                    try {
                        java.util.zip.ZipInputStream zip=new java.util.zip.ZipInputStream(tee);
                        byte[] readBuffer=new byte[64*1024];
                        java.util.zip.ZipEntry entry;
                        int entries=0;
                        while((entry=zip.getNextEntry())!=null){
                            if(++entries>150000)throw new IOException("Excessive ZIP entries");
                            String name=entry.getName(),low=name.toLowerCase(Locale.ROOT);
                            boolean image=!entry.isDirectory()&&!name.startsWith(".")&&
                                !low.contains("__macosx")&&!low.contains("/._")&&
                                (low.endsWith(".png")||low.endsWith(".jpg")||
                                 low.endsWith(".jpeg")||low.endsWith(".webp"));
                            java.io.ByteArrayOutputStream page=image?
                                new java.io.ByteArrayOutputStream(128*1024):null;
                            int n;
                            while((n=zip.read(readBuffer))!=-1){
                                if(page!=null){
                                    if(page.size()+n>16*1024*1024)page=null;
                                    else page.write(readBuffer,0,n);
                                }
                            }
                            if(page!=null&&page.size()>100)
                                preview.onPage(name,page.toByteArray());
                            zip.closeEntry();
                        }
                    }catch(Exception e){
                        Log.w("FG_PERF","Progressive ZIP decoding stopped; finish download",e);
                    }
                }
                byte[] buffer=new byte[128*1024];
                int n;
                while((n=tee.read(buffer,0,buffer.length))!=-1){}
            }catch(IOException e){
                pending.delete();
                throw e;
            }
            long copied=counter[0];
            if(copied==0||(expected>0&&copied!=expected)){
                pending.delete();
                throw new IOException("Incomplete cloud archive: received "+copied+
                    " bytes, expected "+expected);
            }
            if(!pending.renameTo(ready)){
                pending.delete();
                throw new IOException("Cannot finalize remote book cache");
            }
            Log.i("FG_PERF","CLOUD_SPOOL_ms="+
                (SystemClock.elapsedRealtime()-start)+" bytes="+copied);
            return ready;
        }
    }
}

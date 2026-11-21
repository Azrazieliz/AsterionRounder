package com.openlocal.office.core;

import android.content.Context;
import android.graphics.Bitmap;
import android.media.MediaDataSource;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.JSONObject;

/** Lazy, private preview frames for real local and TeraBox videos. Never downloads whole movies. */
public final class FgRounderVideoPreviews {
    private static final int FRAME_WIDTH=512, FRAME_HEIGHT=320;
    private static final AtomicInteger writes=new AtomicInteger();
    private FgRounderVideoPreviews(){}

    public static boolean isVideo(String name){
        if(name==null)return false;
        String lower=name.toLowerCase(Locale.ROOT);
        return lower.endsWith(".mp4")||lower.endsWith(".webm")||
            lower.endsWith(".mkv")||lower.endsWith(".mov")||lower.endsWith(".avi");
    }
    private interface FrameSource { Bitmap frame() throws Exception; }
    private static String fingerprint(String value)throws Exception{
        byte[] bytes=MessageDigest.getInstance("SHA-256").digest(
            value.getBytes(StandardCharsets.UTF_8));
        StringBuilder out=new StringBuilder(64);
        for(byte b:bytes)out.append(String.format(Locale.ROOT,"%02x",b&255));
        return out.toString();
    }
    private static InputStream cached(Context context,String source,FrameSource generator)
            throws Exception{
        File dir=new File(context.getCacheDir(),"rounder-video-frames-v1");
        if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Video preview cache unavailable");
        String key=fingerprint(source);
        File target=new File(dir,key+".jpg");
        if(target.isFile()&&target.length()>128){
            target.setLastModified(System.currentTimeMillis());
            return new FileInputStream(target);
        }
        Bitmap image=generator.frame();
        if(image==null)throw new IOException("No decodable frame in original video");
        byte[] bytes;
        try{
            ByteArrayOutputStream out=new ByteArrayOutputStream(64*1024);
            if(!image.compress(Bitmap.CompressFormat.JPEG,78,out))
                throw new IOException("Video frame encoding failed");
            bytes=out.toByteArray();
        }finally{image.recycle();}
        if(bytes.length<128||bytes.length>1024*1024)
            throw new IOException("Video preview out of bounds");
        File partial=new File(dir,key+"."+Thread.currentThread().getId()+".part");
        try(FileOutputStream out=new FileOutputStream(partial)){out.write(bytes);}
        if(!partial.renameTo(target)){
            partial.delete();
            if(target.isFile()&&target.length()>128)return new FileInputStream(target);
            return new ByteArrayInputStream(bytes);
        }
        if((writes.incrementAndGet()&31)==0)prune(dir);
        return new FileInputStream(target);
    }
    private static void prune(File dir){
        File[] files=dir.listFiles((parent,name)->name.endsWith(".jpg"));
        if(files==null||files.length<64)return;
        Arrays.sort(files,Comparator.comparingLong(File::lastModified).reversed());
        long total=0;
        for(int i=0;i<files.length;i++){
            total+=files[i].length();
            if(i>=2000||total>256L*1024*1024)files[i].delete();
        }
    }
    private static Bitmap frame(MediaMetadataRetriever retriever){
        Bitmap result=retriever.getScaledFrameAtTime(500000L,
            MediaMetadataRetriever.OPTION_CLOSEST_SYNC,FRAME_WIDTH,FRAME_HEIGHT);
        if(result==null)result=retriever.getScaledFrameAtTime(-1L,
            MediaMetadataRetriever.OPTION_CLOSEST_SYNC,FRAME_WIDTH,FRAME_HEIGHT);
        return result;
    }
    public static InputStream local(Context context,Uri uri,long size,long modified)
            throws Exception{
        if(uri==null)throw new IOException("No original video URI");
        return cached(context,"local:"+uri+":"+size+":"+modified,()->{
            MediaMetadataRetriever retriever=new MediaMetadataRetriever();
            try{
                retriever.setDataSource(context,uri);
                return frame(retriever);
            }finally{retriever.release();}
        });
    }
    public static InputStream cloud(Context context,FgTeraboxClient provider,String path)
            throws Exception{
        if(!isVideo(path)||path==null||!path.startsWith("/"))
            throw new IOException("Invalid remote video preview path");
        JSONObject details=provider.fileDetails(path);
        long size=details.optLong("size",-1L);
        if(size<=0)throw new IOException("Video size unavailable");
        long modified=details.optLong("server_mtime",0L);
        String key="cloud:"+provider.metadataScope()+":"+path+":"+size+":"+modified;
        return cached(context,key,()->{
            MediaMetadataRetriever retriever=new MediaMetadataRetriever();
            try(RangedVideo source=new RangedVideo(provider,path,size)){
                retriever.setDataSource(source);
                return frame(retriever);
            }finally{retriever.release();}
        });
    }
    /** Bounded random access lets Android retrieve MP4 headers and keyframes only. */
    private static final class RangedVideo extends MediaDataSource{
        private static final int WINDOW=256*1024, MAX_TOTAL=16*1024*1024;
        private final FgTeraboxClient client;
        private final String path;
        private final long length;
        private long start=-1,total=0;
        private byte[] window=new byte[0];
        private boolean closed=false;
        RangedVideo(FgTeraboxClient client,String path,long size){
            this.client=client;this.path=path;this.length=size;
        }
        @Override public synchronized int readAt(long position,byte[] destination,
                int offset,int count)throws IOException{
            if(closed)throw new IOException("Video frame source closed");
            if(position<0||offset<0||count<0||offset>destination.length-count)
                throw new IOException("Invalid video frame range");
            if(position>=length)return -1;
            if(count==0)return 0;
            if(position<start||position>=start+window.length){
                int request=(int)Math.min(WINDOW,length-position);
                if(total+request>MAX_TOTAL)throw new IOException("Video frame byte budget exceeded");
                try{window=client.readRange(path,position,request);}
                catch(Exception failure){throw new IOException("Video range not available",failure);}
                start=position;
                total+=window.length;
                if(window.length==0)return -1;
            }
            int inside=(int)(position-start);
            int n=Math.min(count,window.length-inside);
            if(n<=0)return -1;
            System.arraycopy(window,inside,destination,offset,n);
            return n;
        }
        @Override public long getSize(){return length;}
        @Override public synchronized void close(){closed=true;window=new byte[0];}
    }
}

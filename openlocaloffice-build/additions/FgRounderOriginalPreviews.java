package com.openlocal.office.core;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Private, account-scoped previews generated from authenticated ORIGINAL TeraBox
 * file bytes. Never uses the TeraBox thumbnail endpoint or stores originals.
 * Only a visible thumbnail triggers a bounded read. GIFs are handled separately
 * as image/gif streams so Android WebView can display their animation.
 */
public final class FgRounderOriginalPreviews {
    private static final int MAX_ENCODED_BYTES=16*1024*1024;
    private static final Semaphore DECODERS=new Semaphore(2,true);
    private static final AtomicInteger WRITES=new AtomicInteger();
    private final Context context;
    private final FgTeraboxClient cloud;

    public FgRounderOriginalPreviews(Context context,FgTeraboxClient cloud){
        this.context=context.getApplicationContext();
        this.cloud=cloud;
    }

    private static String digest(String input)throws Exception{
        byte[] hash=MessageDigest.getInstance("SHA-256").digest(
            input.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        StringBuilder result=new StringBuilder(hash.length*2);
        for(byte b:hash)result.append(String.format(Locale.ROOT,"%02x",b&255));
        return result.toString();
    }
    private File cache(String path)throws Exception{
        String key=digest(cloud.metadataScope()+":"+path);
        File shard=new File(new File(context.getFilesDir(),"rounder-original-preview-v1"),
            key.substring(0,2));
        if(!shard.isDirectory()&&!shard.mkdirs())
            throw new IOException("Private original-preview cache unavailable");
        return new File(shard,key+".jpg");
    }
    private static boolean validJpeg(File file){
        if(!file.isFile()||file.length()<100)return false;
        try(FileInputStream in=new FileInputStream(file)){
            return in.read()==0xff&&in.read()==0xd8&&in.read()==0xff;
        }catch(Exception ignored){return false;}
    }
    private static void prune(File shard){
        File[] files=shard.listFiles((d,name)->name.endsWith(".jpg"));
        if(files==null||files.length<20)return;
        Arrays.sort(files,Comparator.comparingLong(File::lastModified).reversed());
        long used=0;
        // 256 shards x 2 MiB ~= 512 MiB maximum private derived-thumbnail budget.
        for(int i=0;i<files.length;i++){
            used+=files[i].length();
            if(i>=600||used>2L*1024*1024)files[i].delete();
        }
    }
    /** Read at most 16 MiB of the original; never retain source image bytes. */
    private byte[] firstBytes(String path)throws Exception{
        try(InputStream input=cloud.openRangeStream(path,0)){
            ByteArrayOutputStream output=new ByteArrayOutputStream(64*1024);
            byte[] block=new byte[32*1024];
            int remaining=MAX_ENCODED_BYTES,n;
            while(remaining>0&&(n=input.read(block,0,Math.min(block.length,remaining)))!=-1){
                if(n==0)continue;
                output.write(block,0,n);
                remaining-=n;
            }
            return output.toByteArray();
        }
    }
    /** A JPEG for a still-image library card, generated from the ORIGINAL. */
    public InputStream openStill(String path)throws Exception{
        if(path==null||!path.startsWith("/")||
           !FgTeraboxClient.image(path)||path.toLowerCase(Locale.ROOT).endsWith(".gif"))
            throw new IOException("Not a still-image path");
        File cached=cache(path);
        if(validJpeg(cached)){
            cached.setLastModified(System.currentTimeMillis());
            return new FileInputStream(cached);
        }
        DECODERS.acquire();
        try{
            if(validJpeg(cached))return new FileInputStream(cached);
            byte[] encoded=firstBytes(path);
            BitmapFactory.Options bounds=new BitmapFactory.Options();
            bounds.inJustDecodeBounds=true;
            BitmapFactory.decodeByteArray(encoded,0,encoded.length,bounds);
            if(bounds.outWidth<1||bounds.outHeight<1||
               bounds.outWidth>100000||bounds.outHeight>100000)
                throw new IOException("Original image is not decodable within preview budget");
            int sample=1;
            while(bounds.outWidth/sample>800||bounds.outHeight/sample>800||
                  (long)(bounds.outWidth/sample)*(bounds.outHeight/sample)>900000)
                sample*=2;
            BitmapFactory.Options options=new BitmapFactory.Options();
            options.inSampleSize=sample;
            options.inPreferredConfig=Bitmap.Config.RGB_565;
            Bitmap result=BitmapFactory.decodeByteArray(encoded,0,encoded.length,options);
            if(result==null)throw new IOException("Original image decode failed");
            File temp=new File(cached.getParentFile(),
                cached.getName()+"."+java.util.UUID.randomUUID()+".part");
            try{
                try(FileOutputStream out=new FileOutputStream(temp)){
                    if(!result.compress(Bitmap.CompressFormat.JPEG,82,out))
                        throw new IOException("Original preview encoding failed");
                }
                if(!temp.renameTo(cached)){
                    if(!validJpeg(cached))
                        throw new IOException("Could not commit original preview");
                }
            }finally{
                result.recycle();
                temp.delete();
            }
            if(!validJpeg(cached))throw new IOException("Encoded preview invalid");
            if((WRITES.incrementAndGet()&63)==0)prune(cached.getParentFile());
            return new FileInputStream(cached);
        }finally{
            DECODERS.release();
        }
    }
}

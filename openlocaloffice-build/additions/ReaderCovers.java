package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.pdf.PdfRenderer;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.Semaphore;

/** Bounded, disk-cached cover extraction. Large cloud ZIPs never get
 * downloaded just to populate an attractive bookshelf.
 */
public final class ReaderCovers {
    private static final Semaphore WORKERS=new Semaphore(2);
    private ReaderCovers(){}
    /** A Round Sync SAF archive descriptor may be a pipe; even a 4 MB CBZ
     * caused an entire remote transfer just to discover its first image.
     * Keep already generated local cover cache, but never initiate a cloud
     * archive transfer in the background on the library screen. */
    public static boolean isExpensiveCloudCover(Uri uri,String name){
        if(uri==null||name==null)return false;
        String authority=uri.getAuthority();
        if(authority==null)return false;
        return "de.felixnuesse.extract.vcp".equals(authority) &&
            (isArchive(name)||"folder-cover.jpg".equals(name));
    }
    public static boolean hasCached(Context ctx,Uri uri,long size,long modified){
        if(uri==null)return false;
        File file=new File(new File(ctx.getCacheDir(),"covers-v2"),
            hash(uri.toString()+"|"+size+"|"+modified)+".jpg");
        return file.isFile()&&file.length()>0;
    }
    public static InputStream open(Context ctx,Uri source,String name,
                                   long size,long lastModified) throws IOException {
        File dir=new File(ctx.getCacheDir(),"covers-v2");
        if(!dir.exists()&&!dir.mkdirs())throw new IOException("Cover cache unavailable");
        String key=hash(source.toString()+"|"+size+"|"+lastModified);
        File cached=new File(dir,key+".jpg");
        if(cached.exists()&&cached.length()>0)return new FileInputStream(cached);
        boolean acquired=false;
        try {
            WORKERS.acquire();
            acquired=true;
            if(cached.exists()&&cached.length()>0)return new FileInputStream(cached);
            // For pipe-only TeraBox streams, extracting a thumbnail from a
            // 2GiB remote ZIP would copy the *entire* file. Skip it instead.
            if(isArchive(name)&&size>64L*1024*1024&&
               !isExpensiveCloudCover(source,name)&&!seekable(ctx,source))
                throw new IOException("Cloud archive needs a local/seekable copy before cover preview");
            Bitmap bitmap=isExpensiveCloudCover(source,name)&&isArchive(name)?
                decodeCloudArchiveCover(ctx,source,size):decode(ctx,source,name);
            if(bitmap==null)throw new IOException("No supported illustration/cover");
            File temp=new File(dir,key+".tmp");
            try(FileOutputStream out=new FileOutputStream(temp)){
                if(!bitmap.compress(Bitmap.CompressFormat.JPEG,84,out))
                    throw new IOException("Cannot encode thumbnail");
            }finally{bitmap.recycle();}
            if(!temp.renameTo(cached)){
                if(!cached.exists())throw new IOException("Unable to write cover cache");
                temp.delete();
            }
            return new FileInputStream(cached);
        }catch(InterruptedException error){
            Thread.currentThread().interrupt();
            throw new IOException("Cover loading interrupted",error);
        }finally {
            if(acquired)WORKERS.release();
        }
    }
    private static boolean isArchive(String filename){
        String s=filename.toLowerCase(Locale.ROOT);
        return s.endsWith(".zip")||s.endsWith(".cbz")||s.endsWith(".epub");
    }
    private static boolean seekable(Context ctx,Uri uri){
        try(ParcelFileDescriptor fd=ctx.getContentResolver().openFileDescriptor(uri,"r")){
            if(fd==null)return false;
            Os.lseek(fd.getFileDescriptor(),0,OsConstants.SEEK_CUR);
            return true;
        }catch(Exception e){return false;}
    }
    /** Bound cloud thumbnail reads to an early ZIP prefix: never copy an
     * entire book just to display a cover. The provider stream is closed
     * immediately after finding an image or reaching the read budget.
     */
    private static Bitmap decodeCloudArchiveCover(Context ctx,Uri uri,long size)
        throws IOException {
        File local=RemoteBookSpool.completedFile(ctx,uri,size);
        if(local!=null){
            try(java.util.zip.ZipFile zip=new java.util.zip.ZipFile(local)){
                java.util.zip.ZipEntry selected=null;
                java.util.Enumeration<? extends java.util.zip.ZipEntry> all=zip.entries();
                while(all.hasMoreElements()){
                    java.util.zip.ZipEntry item=all.nextElement();
                    if(item.isDirectory()||!rasterEntry(item.getName()))continue;
                    if(selected==null||preferredImageName(item.getName(),selected.getName())<0)
                        selected=item;
                }
                if(selected!=null&&selected.getSize()<=7L*1024*1024){
                    try(InputStream image=zip.getInputStream(selected)){
                        return BitmapFactory.decodeStream(image);
                    }
                }
            }catch(Exception error){
                throw new IOException("Cached cloud cover could not be decoded",error);
            }
        }
        final long limit=4L*1024*1024;
        try(InputStream network=ctx.getContentResolver().openInputStream(uri)){
            if(network==null)return null;
            InputStream bounded=new java.io.FilterInputStream(network){
                long used=0;
                @Override public int read()throws IOException{
                    if(used>=limit)throw new IOException("Cloud cover prefix budget reached");
                    int b=in.read();if(b>=0)used++;return b;
                }
                @Override public int read(byte[] buffer,int off,int len)throws IOException{
                    if(used>=limit)throw new IOException("Cloud cover prefix budget reached");
                    int n=in.read(buffer,off,(int)Math.min(len,limit-used));
                    if(n>0)used+=n;return n;
                }
            };
            java.util.zip.ZipInputStream zip=new java.util.zip.ZipInputStream(
                new BufferedInputStream(bounded,64*1024));
            for(int entries=0;entries<80;entries++){
                java.util.zip.ZipEntry item=zip.getNextEntry();
                if(item==null)break;
                if(!item.isDirectory()&&rasterEntry(item.getName())&&
                    item.getSize()<=7L*1024*1024){
                    java.io.ByteArrayOutputStream image=new java.io.ByteArrayOutputStream();
                    byte[] bytes=new byte[32768];int count;
                    while((count=zip.read(bytes))!=-1){
                        if(image.size()+count>7*1024*1024)return null;
                        image.write(bytes,0,count);
                    }
                    byte[] content=image.toByteArray();
                    Bitmap bitmap=BitmapFactory.decodeByteArray(content,0,content.length);
                    if(bitmap!=null)return bitmap;
                }else{
                    // Skip data, but never exceed the bounded provider reads.
                    zip.closeEntry();
                }
            }
        }catch(IOException notAvailable){
            android.util.Log.i("FG_COVER","No cover in first 4 MiB of cloud ZIP: "+
                notAvailable.getMessage());
        }
        return null;
    }
    private static boolean rasterEntry(String name){
        String n=name.toLowerCase(Locale.ROOT);
        return !n.startsWith(".")&&!n.contains("__macosx")&&!n.contains("/._")&&
            (n.endsWith(".png")||n.endsWith(".jpg")||n.endsWith(".jpeg")||n.endsWith(".webp"));
    }
    private static int preferredImageName(String a,String b){
        String x=a.toLowerCase(Locale.ROOT),y=b.toLowerCase(Locale.ROOT);
        boolean ca=x.contains("cover"),cb=y.contains("cover");
        if(ca!=cb)return ca?-1:1;
        // Numeric ordering without loading image bytes.
        return x.compareTo(y);
    }
    private static Bitmap decode(Context ctx,Uri uri,String name) throws IOException{
        String lower=name.toLowerCase(Locale.ROOT);
        if(lower.endsWith(".pdf")){
            try(ParcelFileDescriptor fd=ctx.getContentResolver().openFileDescriptor(uri,"r")){
                if(fd==null)return null;
                try(PdfRenderer renderer=new PdfRenderer(fd)){
                    if(renderer.getPageCount()==0)return null;
                    try(PdfRenderer.Page page=renderer.openPage(0)){
                        int w=360,h=Math.min(660,Math.max(1,360*page.getHeight()/Math.max(1,page.getWidth())));
                        Bitmap bitmap=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
                        bitmap.eraseColor(android.graphics.Color.WHITE);
                        page.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                        return bitmap;
                    }
                }
            }
        }
        if(isArchive(name)){
            try(BookArchive book=new BookArchive(ctx,uri,lower.endsWith(".epub"))){
                if(!lower.endsWith(".epub")&&book.imageCount()==0)return null;
                // EPUB: honor package cover metadata. ZIP/CBZ: use the first
                // actual numbered image, not an arbitrary filename farther in.
                String candidate=book.preferredCover();
                if(candidate==null)return null;
                try(InputStream bounds=book.coverStream(candidate)){
                    BitmapFactory.Options meta=new BitmapFactory.Options();
                    meta.inJustDecodeBounds=true;BitmapFactory.decodeStream(bounds,null,meta);
                    if(meta.outWidth<=0||meta.outHeight<=0)return null;
                    int ratio=1;
                    while(meta.outWidth/ratio>380*2||meta.outHeight/ratio>620*2)ratio*=2;
                    BitmapFactory.Options opts=new BitmapFactory.Options();
                    opts.inSampleSize=ratio;opts.inPreferredConfig=Bitmap.Config.RGB_565;
                    try(InputStream image=book.coverStream(candidate)){
                        return BitmapFactory.decodeStream(image,null,opts);
                    }
                }
            }catch(Exception e){throw new IOException("Cover not available: "+e.getMessage(),e);}
        }
        try(InputStream bounds=ctx.getContentResolver().openInputStream(uri)){
            if(bounds==null)return null;
            BitmapFactory.Options meta=new BitmapFactory.Options();
            meta.inJustDecodeBounds=true;BitmapFactory.decodeStream(bounds,null,meta);
            if(meta.outWidth<=0||meta.outHeight<=0)return null;
            int ratio=1;
            while(meta.outWidth/ratio>380*2||meta.outHeight/ratio>620*2)ratio*=2;
            BitmapFactory.Options opts=new BitmapFactory.Options();
            opts.inSampleSize=ratio;opts.inPreferredConfig=Bitmap.Config.RGB_565;
            try(InputStream input=ctx.getContentResolver().openInputStream(uri)){
                return input==null?null:BitmapFactory.decodeStream(input,null,opts);
            }
        }
    }
    private static String hash(String input){
        try{
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(
                input.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder s=new StringBuilder();
            for(byte b:digest)s.append(String.format(Locale.ROOT,"%02x",b&0xff));
            return s.toString();
        }catch(Exception e){return Integer.toHexString(input.hashCode());}
    }
}

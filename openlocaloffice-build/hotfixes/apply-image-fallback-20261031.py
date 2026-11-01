#!/usr/bin/env python3
"""Serve an explicitly requested, memory-bounded, scaled JPEG fallback for
valid PNG/WebP/big images that Chromium fails to decode from SAF streams.
Primary stream remains lossless; fallback only triggers on IMG load error.
"""
from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
anchor='    private void openFolderImages(String uriText){'
assert s.count(anchor)==1
helper=r'''    private java.io.InputStream fgFallbackOpen(Uri uri) throws Exception{
        try{
            InputStream stream=getContentResolver().openInputStream(uri);
            if(stream!=null)return stream;
        }catch(Exception e){
            android.util.Log.w("FG_IMAGE","SAF primary stream unavailable",e);
        }
        android.os.ParcelFileDescriptor fd=getContentResolver().openFileDescriptor(uri,"r");
        if(fd==null)throw new IOException("Image provider refused to open source");
        return new android.os.ParcelFileDescriptor.AutoCloseInputStream(fd);
    }
    private WebResourceResponse fgFallbackBitmap(Uri uri){
        try{
            android.graphics.BitmapFactory.Options options=
                new android.graphics.BitmapFactory.Options();
            options.inJustDecodeBounds=true;
            try(InputStream input=fgFallbackOpen(uri)){
                android.graphics.BitmapFactory.decodeStream(input,null,options);
            }
            if(options.outWidth<1||options.outHeight<1)
                throw new IOException("Not a decodable image");
            int sample=1;
            while(options.outWidth/sample>4096||options.outHeight/sample>4096||
                options.outWidth/(double)sample*(options.outHeight/sample)>10000000)
                sample*=2;
            options.inJustDecodeBounds=false;
            options.inSampleSize=sample;
            options.inPreferredConfig=android.graphics.Bitmap.Config.RGB_565;
            android.graphics.Bitmap bitmap;
            try(InputStream input=fgFallbackOpen(uri)){
                bitmap=android.graphics.BitmapFactory.decodeStream(input,null,options);
            }
            if(bitmap==null)throw new IOException("Bitmap decoder returned no pixels");
            java.io.ByteArrayOutputStream bytes=new java.io.ByteArrayOutputStream(512*1024);
            try{
                if(!bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG,90,bytes))
                    throw new IOException("Fallback image encoder failed");
            }finally{bitmap.recycle();}
            android.util.Log.i("FG_IMAGE","IMAGE_FALLBACK_READY pixels="+
                options.outWidth+"x"+options.outHeight+
                " sample="+sample+" bytes="+bytes.size());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(bytes.toByteArray()));
        }catch(Throwable e){
            android.util.Log.e("FG_IMAGE","IMAGE_FALLBACK_FAILED source="+
                uri.getAuthority(),e);
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
'''
s=s.replace(anchor,helper+anchor,1)
anchor='                    if(assetPath!=null&&assetPath.startsWith("/folder-img/")){'
assert s.count(anchor)==1
route=r'''                    if(assetPath!=null&&assetPath.startsWith("/fallback/")){
                        String[] part=assetPath.split("/");
                        if(part.length==4&&part[2].equals(imageStreamToken)&&
                           currentUri!=null)
                            return fgFallbackBitmap(currentUri);
                    }
                    if(assetPath!=null&&assetPath.startsWith("/fallback-folder/")){
                        String[] part=assetPath.split("/");
                        if(part.length==4&&part[2].equals(fgFolderToken)){
                            try{
                                int number=Integer.parseInt(part[3]);
                                FolderPage page=fgFolderPageMap.get(number);
                                if(page!=null)return fgFallbackBitmap(page.uri);
                            }catch(Exception ignored){}
                        }
                    }
'''
s=s.replace(anchor,route+anchor,1)
main.write_text(s)
print("Chromium image decode fallback: bounded native sampled bitmap; no corruption of original file")

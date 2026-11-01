package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** A genuine Koikatsu card is a PNG with a characteristic appended serialized
 * character payload AFTER the IEND chunk. A normal PNG is never a 3D mesh.
 */
public final class KoikatsuCards {
    private KoikatsuCards(){}
    public static boolean isCharacterCard(Context context,Uri uri){
        try(InputStream in=new BufferedInputStream(context.getContentResolver().openInputStream(uri),32*1024)){
            byte[] header=new byte[8];
            if(!exact(in,header)||!java.util.Arrays.equals(header,
                new byte[]{(byte)137,80,78,71,13,10,26,10}))return false;
            long consumed=8;
            while(consumed<512L*1024*1024){
                byte[] h=new byte[8];if(!exact(in,h))return false;
                long length=((h[0]&255L)<<24)|((h[1]&255L)<<16)|((h[2]&255L)<<8)|(h[3]&255L);
                String kind=new String(h,4,4,StandardCharsets.US_ASCII);
                if(length>40L*1024*1024)return false;
                skip(in,length+4);consumed+=12+length;
                if(kind.equals("IEND")){
                    // The authentic serialized Koikatsu payload starts after
                    // the PNG IEND chunk; some creator cards prepend metadata.
                    // Scan bounded trailing bytes, not image pixels or only
                    // the first 4 KiB. Never mistake an ordinary PNG for 3D.
                    byte[] trailer=new byte[8192];
                    int remaining=256*1024, carry=0;
                    while(remaining>0){
                        int n=in.read(trailer,carry,Math.min(trailer.length-carry,remaining));
                        if(n<0)break;
                        remaining-=n;
                        int size=carry+n;
                        String fragment=new String(trailer,0,size,StandardCharsets.ISO_8859_1);
                        if(fragment.contains("KoiKatuChara")||
                           fragment.contains("KoikatsuChara")||
                           fragment.contains("KoiKatuCharaSunshine")||
                           fragment.contains("KoiKatuCharaFile"))return true;
                        carry=Math.min(32,size);
                        System.arraycopy(trailer,size-carry,trailer,0,carry);
                    }
                    return false;
                }
            }
        }catch(Exception ignored){}
        return false;
    }
    private static boolean exact(InputStream in,byte[] bytes)throws IOException{
        int at=0;while(at<bytes.length){
            int n=in.read(bytes,at,bytes.length-at);
            if(n<0)return false;at+=n;
        }return true;
    }
    private static void skip(InputStream in,long count)throws IOException{
        long left=count;
        while(left>0){
            long n=in.skip(left);
            if(n>0){left-=n;continue;}
            if(in.read()<0)throw new EOFException("Truncated PNG");
            left--;
        }
    }
}

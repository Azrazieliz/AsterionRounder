package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import android.provider.DocumentsContract;
import androidx.media3.common.C;
import androidx.media3.datasource.DataSource;
import androidx.media3.datasource.DataSpec;
import androidx.media3.datasource.TransferListener;
import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Media3 adapter for seekable TeraBox HTTP byte-range reads.
 * Never downloads an entire video into a temporary file.
 */
@androidx.media3.common.util.UnstableApi
public final class FgTeraboxMediaDataSource implements DataSource {
    private final Uri contentUri;
    private final FgTeraboxClient cloud;
    private String cloudPath;
    private long position;
    private long remaining=C.LENGTH_UNSET;
    private byte[] buffer;
    private int cursor;
    private boolean closed;

    public FgTeraboxMediaDataSource(Context context,Uri uri){
        contentUri=uri;
        cloud=new FgTeraboxClient(context.getApplicationContext());
    }
    @Override public long open(DataSpec spec)throws IOException {
        if(closed)throw new IOException("Player stream closed");
        try{
            cloudPath=FgTeraboxDocumentsProvider.cloudPath(contentUri);
            position=spec.position;
            remaining=spec.length;
            if(position<0)throw new IOException("Invalid media position");
            if(remaining==C.LENGTH_UNSET){
                long length=FgTeraboxDocumentsProvider.sizeHint(contentUri);
                if(length>=0)remaining=Math.max(0,length-position);
            }
            buffer=null;cursor=0;
            return remaining;
        }catch(Exception e){throw new IOException("Cannot open TeraBox media",e);}
    }
    @Override public int read(byte[] destination,int offset,int length)throws IOException {
        if(closed)throw new IOException("Player stream closed");
        if(length==0)return 0;
        if(remaining==0)return C.RESULT_END_OF_INPUT;
        if(buffer==null||cursor>=buffer.length){
            try{
                int request=(int)(remaining<0 ? 256*1024:
                    Math.min(256*1024L,remaining));
                if(request==0)return C.RESULT_END_OF_INPUT;
                buffer=cloud.readRange(cloudPath,position,request);
                cursor=0;
                if(buffer.length==0)return C.RESULT_END_OF_INPUT;
            }catch(Exception e){
                throw new IOException("TeraBox byte-range read failed",e);
            }
        }
        int n=Math.min(length,buffer.length-cursor);
        if(remaining>=0)n=(int)Math.min(n,remaining);
        if(n<=0)return C.RESULT_END_OF_INPUT;
        System.arraycopy(buffer,cursor,destination,offset,n);
        cursor+=n;position+=n;
        if(remaining>=0)remaining-=n;
        return n;
    }
    @Override public Uri getUri(){return contentUri;}
    @Override public Map<String,List<String>> getResponseHeaders(){return Collections.emptyMap();}
    @Override public void addTransferListener(TransferListener listener){}
    @Override public void close(){closed=true;buffer=null;cursor=0;}
}

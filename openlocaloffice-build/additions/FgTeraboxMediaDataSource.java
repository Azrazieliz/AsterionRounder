package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import android.provider.DocumentsContract;
import androidx.media3.common.C;
import androidx.media3.datasource.DataSource;
import androidx.media3.datasource.DataSpec;
import androidx.media3.datasource.TransferListener;
import java.io.IOException;
import java.io.InputStream;
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
    private InputStream stream;
    private boolean closed;

    public FgTeraboxMediaDataSource(Context context,Uri uri){
        contentUri=uri;
        cloud=new FgTeraboxClient(context.getApplicationContext());
    }
    @Override public long open(DataSpec spec)throws IOException {
        try{
            // Media3 may reopen the SAME DataSource after seeking. close()
            // releases only the current response, not the entire instance.
            if(stream!=null){stream.close();stream=null;}
            closed=false;
            cloudPath=FgTeraboxDocumentsProvider.cloudPath(contentUri);
            position=spec.position;
            remaining=spec.length;
            if(position<0)throw new IOException("Invalid media position");
            if(remaining==C.LENGTH_UNSET){
                long length=FgTeraboxDocumentsProvider.sizeHint(contentUri);
                if(length>=0)remaining=Math.max(0,length-position);
            }
            stream=cloud.openRangeStream(cloudPath,position);
            return remaining;
        }catch(Exception e){throw new IOException("Cannot open TeraBox media",e);}
    }
    @Override public int read(byte[] destination,int offset,int length)throws IOException {
        if(closed||stream==null)throw new IOException("Player stream not open");
        if(length==0)return 0;
        if(remaining==0)return C.RESULT_END_OF_INPUT;
        int requested=remaining<0?length:(int)Math.min((long)length,remaining);
        int count=stream.read(destination,offset,requested);
        if(count<0)return C.RESULT_END_OF_INPUT;
        position+=count;
        if(remaining>=0)remaining-=count;
        return count;
    }
    @Override public Uri getUri(){return contentUri;}
    @Override public Map<String,List<String>> getResponseHeaders(){return Collections.emptyMap();}
    @Override public void addTransferListener(TransferListener listener){}
    @Override public void close()throws IOException{
        closed=true;
        if(stream!=null){try{stream.close();}finally{stream=null;}}
    }
}

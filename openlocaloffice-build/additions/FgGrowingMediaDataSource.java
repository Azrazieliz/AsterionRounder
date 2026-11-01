package com.openlocal.office.core;

import android.net.Uri;
import androidx.media3.common.C;
import androidx.media3.datasource.DataSource;
import androidx.media3.datasource.DataSpec;
import androidx.media3.datasource.TransferListener;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Blocking file data source for a file that is being downloaded.
 * ExoPlayer may seek within bytes already received without reopening
 * the provider or waiting for the entire cloud video. Reader waits off UI.
 */
public final class FgGrowingMediaDataSource implements DataSource {
    public static final class Progress {
        public final File file;
        public volatile long available;
        public volatile long expected=C.LENGTH_UNSET;
        public volatile boolean finished;
        public volatile boolean cancelled;
        public volatile IOException failure;
        public final Object monitor=new Object();
        public Progress(File file){this.file=file;}
        public void wake(){synchronized(monitor){monitor.notifyAll();}}
    }
    private final Progress state;
    private RandomAccessFile reader;
    private long position;
    private long remaining;
    private Uri uri;

    public FgGrowingMediaDataSource(Progress state){this.state=state;}
    @Override public long open(DataSpec spec) throws IOException {
        if(state.cancelled)throw new IOException("Playback cancelled");
        reader=new RandomAccessFile(state.file,"r");
        position=spec.position;
        remaining=spec.length;
        uri=spec.uri;
        if(remaining!=C.LENGTH_UNSET)return remaining;
        return state.expected>position?state.expected-position:C.LENGTH_UNSET;
    }
    @Override public int read(byte[] bytes,int offset,int length)throws IOException {
        if(length==0)return 0;
        if(reader==null)throw new IOException("Media stream not opened");
        if(remaining==0)return C.RESULT_END_OF_INPUT;
        while(true){
            if(state.cancelled||Thread.currentThread().isInterrupted())
                throw new IOException("Playback cancelled");
            if(state.failure!=null)throw new IOException("Media download interrupted",state.failure);
            long available=state.available-position;
            if(available>0){
                int count=(int)Math.min((long)length,Math.min(available,Integer.MAX_VALUE));
                if(remaining>0)count=(int)Math.min(count,remaining);
                if(count<=0)return C.RESULT_END_OF_INPUT;
                reader.seek(position);
                int n=reader.read(bytes,offset,count);
                if(n>0){
                    position+=n;
                    if(remaining>0)remaining-=n;
                    return n;
                }
            }
            if(state.finished)return C.RESULT_END_OF_INPUT;
            try{
                synchronized(state.monitor){state.monitor.wait(180);}
            }catch(InterruptedException e){
                Thread.currentThread().interrupt();
                throw new IOException("Playback interrupted",e);
            }
        }
    }
    @Override public Uri getUri(){return uri;}
    @Override public Map<String,List<String>> getResponseHeaders(){
        return Collections.emptyMap();
    }
    @Override public void addTransferListener(TransferListener listener){}
    @Override public void close()throws IOException{
        if(reader!=null){reader.close();reader=null;}
    }
}
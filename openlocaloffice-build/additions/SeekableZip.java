package com.openlocal.office.core;

import android.os.ParcelFileDescriptor;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;

/**
 * Random-access ZIP/ZIP64 index on a SAF file descriptor.
 * No /proc/self/fd reopening, no full-file copy, no whole-archive byte array.
 * Reads ONLY EOCD + central directory before opening an image; works with a
 * 5GiB seekable file whose owner is Round Sync, TeraBox or another provider.
 */
public final class SeekableZip implements Closeable {
    private static final int LOCAL_SIG=0x04034b50, CENTRAL_SIG=0x02014b50;
    private static final int EOCD_SIG=0x06054b50, ZIP64_LOC_SIG=0x07064b50;
    private static final int ZIP64_END_SIG=0x06064b50;
    private final java.io.FileDescriptor fd;
    private final long length;
    private final LinkedHashMap<String,Record> records=new LinkedHashMap<>();
    private final ArrayList<ZipEntry> order=new ArrayList<>();
    private static final Charset CP437=Charset.forName("IBM437");

    private static final class Record {
        String name;
        long localOffset,packed,unpacked;
        int flags,method;
        ZipEntry entry;
    }
    public SeekableZip(ParcelFileDescriptor handle) throws IOException {
        fd=handle.getFileDescriptor();
        try {length=Os.lseek(fd,0L,OsConstants.SEEK_END);}
        catch(ErrnoException e){throw new IOException("This cloud provider offers a streaming-only document",e);}
        if(length<22)throw new IOException("Archive header is incomplete");
        buildIndex();
    }
    public long size(){return length;}
    public Enumeration<? extends ZipEntry> entries(){return Collections.enumeration(order);}
    public ZipEntry getEntry(String name){Record r=records.get(name);return r==null?null:r.entry;}
    public InputStream getInputStream(ZipEntry entry) throws IOException {
        if(entry==null)throw new FileNotFoundException("Archive entry not found");
        Record r=records.get(entry.getName());
        if(r==null)throw new FileNotFoundException(entry.getName());
        if((r.flags&1)!=0)throw new IOException("Encrypted archive entry is unsupported");
        if(r.method!=0&&r.method!=8)throw new IOException("Unsupported ZIP compression: "+r.method);
        if(r.packed<0||r.unpacked<0)throw new IOException("Invalid entry length");
        byte[] h=read(r.localOffset,30);
        if(u32(h,0)!=LOCAL_SIG)throw new IOException("ZIP local header mismatch");
        long data=r.localOffset+30+u16(h,26)+u16(h,28);
        if(data<0||r.packed>length-data)throw new IOException("ZIP member is incomplete");
        InputStream packed=new RangeStream(data,r.packed);
        if(r.method==0)return packed;
        return new InflaterInputStream(packed,new Inflater(true),64*1024);
    }
    private byte[] read(long off,int n) throws IOException {
        if(off<0||n<0||off>length||n>length-off)throw new EOFException("ZIP exceeds available bytes");
        byte[] b=new byte[n];int total=0;
        while(total<n){
            final int got;
            try{got=Os.pread(fd,b,total,n-total,off+total);}
            catch(ErrnoException e){throw new IOException("Cannot seek inside this document provider",e);}
            if(got<=0)throw new EOFException("ZIP entry was truncated");
            total+=got;
        }
        return b;
    }
    private static int u16(byte[] b,int at){
        return (b[at]&255)|((b[at+1]&255)<<8);
    }
    private static long u32(byte[] b,int at){
        return (b[at]&255L)|((b[at+1]&255L)<<8)|((b[at+2]&255L)<<16)|((b[at+3]&255L)<<24);
    }
    private static long u64(byte[] b,int at) throws IOException {
        long low=u32(b,at),high=u32(b,at+4);
        if(high>0x7fffffffL)throw new IOException("ZIP64 value is larger than supported");
        return (high<<32)|low;
    }
    private void buildIndex() throws IOException {
        int tailSize=(int)Math.min(length,22+65535);
        long tailStart=length-tailSize;
        byte[] tail=read(tailStart,tailSize);
        int end=-1;
        // EOCD ZIP comment length must agree with the physical end.
        for(int i=tailSize-22;i>=0;i--){
            if(u32(tail,i)==EOCD_SIG&&i+22+u16(tail,i+20)==tailSize){end=i;break;}
        }
        if(end<0)throw new IOException("ZIP central directory not found; cloud download may be incomplete");
        long entries=u16(tail,end+10),dirSize=u32(tail,end+12),dirOffset=u32(tail,end+16);
        if(entries==65535||dirSize==0xffffffffL||dirOffset==0xffffffffL){
            long locOffset=tailStart+end-20;
            byte[] locator=read(locOffset,20);
            if(u32(locator,0)!=ZIP64_LOC_SIG)throw new IOException("Missing ZIP64 locator");
            byte[] zip64=read(u64(locator,8),56);
            if(u32(zip64,0)!=ZIP64_END_SIG)throw new IOException("Missing ZIP64 directory");
            entries=u64(zip64,32);dirSize=u64(zip64,40);dirOffset=u64(zip64,48);
        }
        if(entries>250000||dirSize>120L*1024*1024)
            throw new IOException("Archive index exceeds supported safety limits");
        if(dirOffset<0||dirSize<0||dirOffset>length||dirSize>length-dirOffset)
            throw new IOException("Archive central directory is incomplete");
        // Remote SAF providers can turn every pread into a network range call.
        // Fetch the bounded central directory once, then parse entries in memory.
        // This avoids 2–3 remote reads per ZIP member (hundreds for webtoons).
        byte[] directory=read(dirOffset,(int)dirSize);
        int p=0,endAt=directory.length;
        for(long i=0;i<entries;i++){
            if(p>endAt-46)throw new IOException("Truncated ZIP central header");
            byte[] header=Arrays.copyOfRange(directory,p,p+46);
            if(u32(header,0)!=CENTRAL_SIG)throw new IOException("Damaged ZIP central directory");
            int flags=u16(header,8),method=u16(header,10);
            long packed=u32(header,20),unpacked=u32(header,24),local=u32(header,42);
            int nameLength=u16(header,28),extraLength=u16(header,30),commentLength=u16(header,32);
            long next=(long)p+46L+nameLength+extraLength+commentLength;
            if(next>endAt||next<0)throw new IOException("ZIP index member exceeds directory");
            byte[] nameBytes=Arrays.copyOfRange(directory,p+46,p+46+nameLength);
            String name=new String(nameBytes,(flags&0x800)!=0?StandardCharsets.UTF_8:CP437);
            if(name.indexOf('\0')>=0||name.contains("\\")||name.startsWith("/")||
               name.equals("..")||name.startsWith("../")||name.contains("/../"))
                throw new IOException("Invalid archive path");
            if(packed==0xffffffffL||unpacked==0xffffffffL||local==0xffffffffL){
                byte[] extras=Arrays.copyOfRange(directory,p+46+nameLength,p+46+nameLength+extraLength);
                int cursor=0; boolean resolved=false;
                while(cursor+4<=extras.length){
                    int id=u16(extras,cursor),size=u16(extras,cursor+2);
                    cursor+=4;
                    if(cursor+size>extras.length)throw new IOException("Broken ZIP extra field");
                    if(id==1){
                        int t=cursor,stop=cursor+size;
                        if(unpacked==0xffffffffL){if(t+8>stop)throw new IOException("ZIP64 size missing");unpacked=u64(extras,t);t+=8;}
                        if(packed==0xffffffffL){if(t+8>stop)throw new IOException("ZIP64 size missing");packed=u64(extras,t);t+=8;}
                        if(local==0xffffffffL){if(t+8>stop)throw new IOException("ZIP64 offset missing");local=u64(extras,t);}
                        resolved=true;break;
                    }
                    cursor+=size;
                }
                if(!resolved)throw new IOException("Missing ZIP64 member metadata");
            }
            if(local<0||local>=length||packed<0||unpacked<0)
                throw new IOException("Invalid ZIP member offsets");
            Record r=new Record();r.name=name;r.flags=flags;r.method=method;
            r.packed=packed;r.unpacked=unpacked;r.localOffset=local;
            r.entry=new ZipEntry(name);
            r.entry.setSize(unpacked);
            records.put(name,r);order.add(r.entry);
            p=(int)next;
        }
        if(records.isEmpty())throw new IOException("Archive has no files");
    }
    @Override public void close() throws IOException{/* The caller owns the SAF descriptor. */}
    private final class RangeStream extends InputStream {
        private long offset,remaining;
        RangeStream(long start,long bytes){offset=start;remaining=bytes;}
        @Override public int read() throws IOException {
            byte[] b=new byte[1];return read(b,0,1)<0?-1:b[0]&255;
        }
        @Override public int read(byte[] buffer,int start,int len) throws IOException {
            if(len==0)return 0;
            if(remaining<=0)return -1;
            int n=(int)Math.min(len,remaining);
            int received=0;
            try{received=Os.pread(fd,buffer,start,n,offset);}
            catch(ErrnoException e){throw new IOException("Cloud file was disconnected",e);}
            if(received<=0)throw new EOFException("Incomplete ZIP member from cloud provider");
            offset+=received;remaining-=received;return received;
        }
        @Override public long skip(long amount){long n=Math.max(0,Math.min(remaining,amount));remaining-=n;offset+=n;return n;}
    }
}

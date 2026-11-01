#!/usr/bin/env python3
"""Make ZIP and EPUB image reads independent of document switching/closing."""
from pathlib import Path
p=Path("app/src/main/java/com/openlocal/office/core/SeekableZip.java")
s=p.read_text(encoding="utf-8")
def one(old,new,label):
 global s
 count=s.count(old)
 if count!=1:raise RuntimeError(f"{label}: expected once, found {count}")
 s=s.replace(old,new,1)
one("    private final long length;","    private final long length;\n    private volatile boolean closed=false;","zip close state")
one("    public InputStream getInputStream(ZipEntry entry) throws IOException {",
    "    public synchronized InputStream getInputStream(ZipEntry entry) throws IOException {\n        if(closed)throw new IOException(\"Archive was replaced; open the selected book again\");",
    "zip entry guard")
one("""        byte[] h=read(r.localOffset,30);
        if(u32(h,0)!=LOCAL_SIG)throw new IOException("ZIP local header mismatch");
        long data=r.localOffset+30+u16(h,26)+u16(h,28);
        if(data<0||r.packed>length-data)throw new IOException("ZIP member is incomplete");
        InputStream packed=new RangeStream(data,r.packed);
        if(r.method==0)return packed;
        return new InflaterInputStream(packed,new Inflater(true),64*1024);""",
"""        // Each WebView image owns a duplicate OS descriptor. Closing the book
        // while an image is still decoding cannot interrupt pread64.
        // The duplicate is independently released by the returned stream.
        final java.io.FileDescriptor memberFd;
        try{memberFd=Os.dup(fd);}
        catch(ErrnoException issue){throw new IOException("Cannot retain archive member",issue);}
        try{
            byte[] h=readFrom(memberFd,r.localOffset,30);
            if(u32(h,0)!=LOCAL_SIG)throw new IOException("ZIP local header mismatch");
            long data=r.localOffset+30+u16(h,26)+u16(h,28);
            if(data<0||r.packed>length-data)throw new IOException("ZIP member is incomplete");
            InputStream packed=new RangeStream(memberFd,data,r.packed);
            if(r.method==0)return packed;
            return new InflaterInputStream(packed,new Inflater(true),64*1024);
        }catch(IOException|RuntimeException failure){
            try{Os.close(memberFd);}catch(ErrnoException ignored){}
            throw failure;
        }""","independent ZIP member streams")
one("    private byte[] read(long off,int n) throws IOException {\n        if(off<0",
"""    private byte[] read(long off,int n) throws IOException {
        return readFrom(fd,off,n);
    }
    private byte[] readFrom(java.io.FileDescriptor source,long off,int n) throws IOException {
        if(off<0""","pread helper")
one("try{got=Os.pread(fd,b,total,n-total,off+total);}",
    "try{got=Os.pread(source,b,total,n-total,off+total);}","pread snapshot")
one("    @Override public void close() throws IOException{/* The caller owns the SAF descriptor. */}",
    "    @Override public synchronized void close() throws IOException{closed=true; /* SAF descriptor belongs to caller */}",
    "close race")
one("""        private long offset,remaining;
        RangeStream(long start,long bytes){offset=start;remaining=bytes;}""",
"""        private final java.io.FileDescriptor memberFd;
        private boolean memberClosed=false;
        private long offset,remaining;
        RangeStream(java.io.FileDescriptor input,long start,long bytes){
            memberFd=input;offset=start;remaining=bytes;
        }
        @Override public synchronized void close() throws IOException {
            if(memberClosed)return;
            memberClosed=true;
            try{Os.close(memberFd);}catch(ErrnoException issue){
                throw new IOException("Could not release archive member",issue);
            }
        }""","member descriptor lifetime")
one("            if(len==0)return 0;\n            if(remaining<=0)return -1;",
    "            if(memberClosed)throw new IOException(\"ZIP image stream is closed\");\n            if(len==0)return 0;\n            if(remaining<=0)return -1;","closed member check")
one("try{received=Os.pread(fd,buffer,start,n,offset);}",
    "try{received=Os.pread(memberFd,buffer,start,n,offset);}","member pread")
p.write_text(s,encoding="utf-8")
print("SEEKABLE_ZIP_DUPLICATED_MEMBER_DESCRIPTOR_READY")

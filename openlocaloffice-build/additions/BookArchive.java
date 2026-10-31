package com.openlocal.office.core;

import android.content.Context;
import android.net.Uri;
import android.database.Cursor;
import android.provider.OpenableColumns;
import android.system.Os;
import android.system.OsConstants;
import android.os.ParcelFileDescriptor;
import android.webkit.WebResourceResponse;
import org.json.JSONArray;
import org.json.JSONObject;
import org.w3c.dom.*;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;

/** Read-only, seekable ZIP/EPUB reader that never loads an entire book into memory.
 * A 5+ GiB EPUB can be opened if the document provider gives a seekable descriptor,
 * or if the device has space for a temporary disk-backed copy.
 * Zip entries are read on demand; no file-wide 80 MiB gate.
 */
public final class BookArchive implements Closeable {
    private final Context context;
    private final Uri uri;
    private final ParcelFileDescriptor descriptor;
    private final File temporary;
    private final SeekableZip zip;
    private final ParcelFileDescriptor tempDescriptor;
    private final String token;
    private final ArrayList<Chapter> chapters = new ArrayList<>();
    private final LinkedHashMap<String,String> titles = new LinkedHashMap<>();
    private String bookTitle = "";
    private String author = "";
    private String preferredCoverName = null;
    private final ArrayList<String> archiveImages = new ArrayList<>();
    private final ArrayList<String> archiveAll = new ArrayList<>();
    private static final int MAX_CHAPTER_BYTES=6*1024*1024;
    private static final int MAX_METADATA_BYTES=2*1024*1024;
    private static final int MAX_IMAGE_BYTES=128*1024*1024;

    private static final class Chapter {
        final String name;
        final String title;
        Chapter(String name,String title){this.name=name;this.title=title;}
    }

    public BookArchive(Context ctx,Uri source,boolean epub) throws Exception {
        this(ctx,source,epub,null);
    }
    public BookArchive(Context ctx,Uri source,boolean epub,
                       RemoteBookSpool.PreviewListener preview) throws Exception {
        context=ctx.getApplicationContext();
        uri=source;
        token=UUID.randomUUID().toString();
        ParcelFileDescriptor handle=null;
        File temp=null;
        SeekableZip opened=null;
        ParcelFileDescriptor spoolHandle=null;
        try {
            long providerStart=android.os.SystemClock.elapsedRealtime();
            handle=context.getContentResolver().openFileDescriptor(uri,"r");
            android.util.Log.i("FG_PERF","SAF_OPEN_ms="+
                (android.os.SystemClock.elapsedRealtime()-providerStart)+
                " authority="+uri.getAuthority());
            if(handle==null)throw new IOException("Cannot read this document provider");
            android.util.Log.i("FG_PERF","SIZE_QUERY_BEGIN");
            long sizeStart=android.os.SystemClock.elapsedRealtime();
            long advertised=providerLength();
            android.util.Log.i("FG_PERF","SIZE_QUERY_ms="+
                (android.os.SystemClock.elapsedRealtime()-sizeStart));
            long physical=handle.getStatSize();
            android.util.Log.i("FG_PERF","FD_STAT_DONE");
            // A cloud provider can publish the intended size while still
            // downloading the file. Do not treat its partial local payload as
            // a valid permanent source or blindly copy it again.
            if(advertised>0&&physical>=0&&physical<advertised){
                throw new IOException("The cloud document is incomplete ("+
                    physical+" / "+advertised+" bytes). Complete Round Sync download first.");
            }
            try {
                // Read ZIP central directory directly from the SAF descriptor.
                // Unlike ZipFile("/proc/self/fd/NN"), this does not reopen
                // provider-owned FDs and does not download/copy them a second time.
                long indexStart=android.os.SystemClock.elapsedRealtime();
                android.util.Log.i("FG_PERF","ZIP_INDEX_BEGIN");
                opened=new SeekableZip(handle);
                android.util.Log.i("FG_PERF","ZIP_INDEX_ms="+
                    (android.os.SystemClock.elapsedRealtime()-indexStart));
            } catch(IOException indexError) {
                boolean seekable;
                try{Os.lseek(handle.getFileDescriptor(),0L,OsConstants.SEEK_CUR);seekable=true;}
                catch(Exception notSeekable){seekable=false;}
                if(seekable)throw new IOException(
                    "Unable to read ZIP index directly. The archive may be incomplete or damaged.",indexError);
                // A pipe-only cloud source requires a disk copy for ZIP random
                // access. Share one completed copy across readers and prevent
                // concurrent downloads of the same cloud book.
                File completed=RemoteBookSpool.obtain(context,uri,advertised,preview);
                spoolHandle=ParcelFileDescriptor.open(completed,
                    ParcelFileDescriptor.MODE_READ_ONLY);
                opened=new SeekableZip(spoolHandle);
            }
            zip=opened;
            descriptor=handle;
            temporary=temp;
            tempDescriptor=spoolHandle;
            Enumeration<? extends ZipEntry> entries=zip.entries();
            int index=0;
            while(entries.hasMoreElements()){
                ZipEntry entry=entries.nextElement();
                if(++index>150000)throw new IOException("Archive index is unusually large");
                String name=entry.getName();
                if(!entry.isDirectory()){
                    archiveAll.add(name);
                    if(isReadablePage(name))archiveImages.add(name);
                }
            }
            // Comic reading order is 1, 2, 3 ... 10, NOT 1, 10, 2.
            archiveImages.sort(BookArchive::compareNatural);
            archiveAll.sort(BookArchive::compareNatural);
            if(epub)readPackage();
        }catch(Exception failure){
            if(opened!=null)try{opened.close();}catch(IOException ignored){}
            if(handle!=null)try{handle.close();}catch(IOException ignored){}
            if(spoolHandle!=null)try{spoolHandle.close();}catch(IOException ignored){}
            if(temp!=null)temp.delete();
            throw failure;
        }
    }
    private long providerLength(){
        try(Cursor cursor=context.getContentResolver().query(uri,
            new String[]{OpenableColumns.SIZE},null,null,null)){
            if(cursor!=null&&cursor.moveToFirst()&&!cursor.isNull(0))
                return cursor.getLong(0);
        }catch(Exception ignored){}
        return -1L;
    }
    public String token(){return token;}
    public String title(){return bookTitle;}
    public String author(){return author;}
    public int chapterCount(){return chapters.size();}
    public int imageCount(){return archiveImages.size();}
    /** EPUB manifest cover (when present) or first raster illustration.
     * ZIP/CBZ: always use the first numerically ordered image. */
    public String preferredCover() {
        if(preferredCoverName!=null&&zip.getEntry(preferredCoverName)!=null
           &&isRaster(preferredCoverName))return preferredCoverName;
        for(String image:archiveImages)if(isRaster(image))return image;
        return null;
    }
    private static boolean isRaster(String path){
        return isImage(path)&&!path.toLowerCase(Locale.ROOT).endsWith(".svg");
    }
    /** A ZIP is a comic when nearly all displayable entries are image pages,
     * independent of the ZIP extension or enclosing directory name.
     * Metadata/hidden files do not influence classification. */
    public boolean comicLike(){
        if(archiveImages.size()<2)return false;
        int readable=0;
        for(String name:archiveAll){
            String base=name.substring(name.lastIndexOf('/')+1);
            if(base.startsWith(".")||name.startsWith("__MACOSX/")||
               base.equalsIgnoreCase("Thumbs.db"))continue;
            readable++;
        }
        return readable>=2&&archiveImages.size()*10L>=readable*8L;
    }
    public static int compareNatural(String left,String right){
        int a=0,b=0;
        while(a<left.length()&&b<right.length()){
            char ac=left.charAt(a),bc=right.charAt(b);
            if(Character.isDigit(ac)&&Character.isDigit(bc)){
                int ae=a,be=b;
                while(ae<left.length()&&Character.isDigit(left.charAt(ae)))ae++;
                while(be<right.length()&&Character.isDigit(right.charAt(be)))be++;
                int as=a;while(as<ae&&left.charAt(as)=='0')as++;
                int bs=b;while(bs<be&&right.charAt(bs)=='0')bs++;
                int al=ae-as,bl=be-bs;
                if(al!=bl)return Integer.compare(al,bl);
                for(int k=0;k<al;k++){
                    int cmp=Character.compare(left.charAt(as+k),right.charAt(bs+k));
                    if(cmp!=0)return cmp;
                }
                if(ae-a!=be-b)return Integer.compare(ae-a,be-b);
                a=ae;b=be;
            }else{
                int cmp=Character.compare(Character.toLowerCase(ac),Character.toLowerCase(bc));
                if(cmp!=0)return cmp;
                a++;b++;
            }
        }
        return Integer.compare(left.length()-a,right.length()-b);
    }
    public String imageName(int index){return archiveImages.get(index);}
    public String assetUrl(String name){return "https://fg-assets.invalid/book/"+token+"/"+encodePath(name);}
    public JSONObject metadata() throws Exception {
        JSONObject object=new JSONObject();
        object.put("type","epub");
        object.put("format","epub");
        object.put("title",bookTitle);
        object.put("author",author);
        object.put("chapters",chapters.size());
        object.put("token",token);
        return object;
    }
    public JSONArray contents() throws Exception {
        JSONArray list=new JSONArray();
        for(int i=0;i<chapters.size();i++){
            Chapter c=chapters.get(i);
            list.put(new JSONObject().put("index",i).put("title",c.title));
        }
        return list;
    }
    public JSONObject chapter(int index) throws Exception {
        if(index<0||index>=chapters.size())throw new IOException("Chapter index out of range");
        Chapter c=chapters.get(index);
        byte[] data=readSmall(c.name,MAX_CHAPTER_BYTES);
        return new JSONObject()
            .put("index",index).put("title",c.title)
            .put("base",assetUrl(c.name)).put("html",new String(data,StandardCharsets.UTF_8));
    }
    public JSONArray images() throws Exception {
        JSONArray list=new JSONArray();
        for(int i=0;i<archiveImages.size();i++) {
            String entry=archiveImages.get(i);
            list.put(new JSONObject().put("index",i).put("name",entry)
                .put("preview",true).put("streamed",true));
        }
        return list;
    }
    public JSONArray fileList() throws Exception {
        JSONArray list=new JSONArray();
        for(int i=0;i<archiveAll.size();i++){
            String name=archiveAll.get(i);
            ZipEntry e=zip.getEntry(name);
            list.put(new JSONObject().put("name",name).put("size",e==null?-1:e.getSize())
                .put("streamed",isImage(name)).put("preview",isImage(name)||isText(name)));
        }
        return list;
    }
    private static boolean isText(String name){
        String n=name.toLowerCase(Locale.ROOT);
        return n.endsWith(".txt")||n.endsWith(".md")||n.endsWith(".json")||
            n.endsWith(".xml")||n.endsWith(".csv")||n.endsWith(".html")||
            n.endsWith(".xhtml")||n.endsWith(".yaml");
    }
    public String entryBase64(String name) throws Exception {
        if(!isText(name)&&!isImage(name))return "";
        byte[] raw=readSmall(name,isImage(name)?12*1024*1024:4*1024*1024);
        return android.util.Base64.encodeToString(raw,android.util.Base64.NO_WRAP);
    }
    public String urlForEntry(String name) {
        if(!isImage(name)||zip.getEntry(name)==null)return "";
        return assetUrl(name);
    }
    public WebResourceResponse response(String requestedPath) throws IOException {
        // The URL contains an unguessable session token and a path that is
        // compared against actual ZipFile entries. Never fetch outside the EPUB.
        String prefix="/book/"+token+"/";
        if(!requestedPath.startsWith(prefix))return null;
        String path=decodePath(requestedPath.substring(prefix.length()));
        if(path.startsWith("/")||path.contains("\\")||path.contains("\0")||
           path.contains("../")||path.equals(".."))return null;
        ZipEntry entry=zip.getEntry(path);
        if(entry==null||entry.isDirectory()||!isImage(path))return null;
        if(entry.getSize()>MAX_IMAGE_BYTES)throw new IOException("A single book image exceeds the 128 MiB decoding safety limit");
        InputStream stream=zip.getInputStream(entry);
        return new WebResourceResponse(mime(path),null,new BoundedStream(stream,MAX_IMAGE_BYTES));
    }
    /** Only the requested image is decompressed. Used by native bookshelf covers. */
    public InputStream coverStream(String name) throws IOException {
        if(name==null||!isImage(name))throw new IOException("Not a cover image");
        ZipEntry entry=zip.getEntry(name);
        if(entry==null||entry.isDirectory()||entry.getSize()>128L*1024*1024)
            throw new IOException("Cover is missing or exceeds decoding safety limit");
        return zip.getInputStream(entry);
    }
    public String archiveEntry(int index) throws Exception {
        if(index<0||index>=archiveImages.size())throw new IOException("Image index invalid");
        return assetUrl(archiveImages.get(index));
    }
    /** ZIP metadata and Finder sidecar images must never become comic pages. */
    private static boolean isReadablePage(String name){
        if(!isImage(name))return false;
        for(String segment:name.replace('\\','/').split("/")){
            if(segment.startsWith(".")||segment.equalsIgnoreCase("__MACOSX")||
               segment.equalsIgnoreCase("Thumbs.db"))return false;
        }
        return true;
    }
    private static boolean isImage(String name){
        String lower=name.toLowerCase(Locale.ROOT);
        return lower.endsWith(".jpg")||lower.endsWith(".jpeg")||lower.endsWith(".png")||
            lower.endsWith(".gif")||lower.endsWith(".webp")||lower.endsWith(".avif")||
            lower.endsWith(".svg")||lower.endsWith(".bmp");
    }
    private static String mime(String name){
        String n=name.toLowerCase(Locale.ROOT);
        if(n.endsWith(".png"))return "image/png";
        if(n.endsWith(".gif"))return "image/gif";
        if(n.endsWith(".webp"))return "image/webp";
        if(n.endsWith(".avif"))return "image/avif";
        if(n.endsWith(".svg"))return "image/svg+xml";
        if(n.endsWith(".bmp"))return "image/bmp";
        return "image/jpeg";
    }
    private static String encodePath(String path){
        // Encode each segment without allowing an external URL. URL encoding
        // encodes spaces as +; replace with %20 for URLs.
        StringBuilder out=new StringBuilder();
        for(String part:path.split("/",-1)){
            if(out.length()>0)out.append('/');
            try{out.append(java.net.URLEncoder.encode(part,"UTF-8").replace("+","%20"));}
            catch(Exception e){throw new IllegalArgumentException(e);}
        }
        return out.toString();
    }
    private static String decodePath(String path){
        try{return java.net.URLDecoder.decode(path,"UTF-8");}
        catch(Exception e){return "";}
    }
    private byte[] readSmall(String path,int max) throws IOException{
        ZipEntry e=zip.getEntry(path);
        if(e==null)throw new IOException("Book resource not found: "+path);
        if(e.getSize()>max)throw new IOException("A chapter is too large for one render section");
        try(InputStream stream=zip.getInputStream(e)){
            ByteArrayOutputStream output=new ByteArrayOutputStream();
            byte[] buffer=new byte[32768];int n;
            while((n=stream.read(buffer))!=-1){
                if(output.size()+n>max)throw new IOException("Book chapter exceeds bounded render buffer");
                output.write(buffer,0,n);
            }
            return output.toByteArray();
        }
    }
    /** The Android platform XML parser does not consistently implement
     * Apache/Xerces setFeature URIs. EPUB2 packages may also declare a harmless
     * external OPF DTD. Strip the external declaration rather than causing
     * ParserConfigurationException or allowing network/entity resolution.
     * Reject internal entity subsets and DTD entity declarations explicitly.
     */
    private static org.w3c.dom.Document document(byte[] bytes) throws Exception {
        String xml=new String(bytes,StandardCharsets.UTF_8);
        if(java.util.regex.Pattern.compile("(?is)<!\\s*ENTITY\\b|<!\\s*DOCTYPE[^>]*\\[")
            .matcher(xml).find())throw new IOException("EPUB XML contains unsupported entity declarations");
        xml=xml.replaceAll("(?is)<!\\s*DOCTYPE\\s+[^>]*>","");
        DocumentBuilderFactory f=DocumentBuilderFactory.newInstance();
        f.setNamespaceAware(true);
        f.setExpandEntityReferences(false);
        javax.xml.parsers.DocumentBuilder parser=f.newDocumentBuilder();
        parser.setEntityResolver((publicId,systemId)->
            new org.xml.sax.InputSource(new java.io.StringReader("")));
        return parser.parse(new ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8)));
    }
    private static Element element(Node node){return node instanceof Element?(Element)node:null;}
    private static String field(Element e,String attr){return e==null?"":e.getAttribute(attr);}
    private static String contents(Element root,String name){
        NodeList nodes=root.getElementsByTagNameNS("*",name);
        return nodes.getLength()>0?nodes.item(0).getTextContent().trim():"";
    }
    private static String folder(String name){
        int i=name.lastIndexOf('/');return i<0?"":name.substring(0,i+1);
    }
    private static String normalPath(String from,String href){
        try {
            String hrefPath=href.split("[?#]",2)[0];
            String combined=folder(from)+java.net.URLDecoder.decode(hrefPath,"UTF-8");
            Deque<String> segments=new ArrayDeque<>();
            for(String section:combined.split("/")){
                if(section.isEmpty()||section.equals("."))continue;
                if(section.equals("..")){
                    if(segments.isEmpty())return "";
                    segments.removeLast();
                }else segments.addLast(section);
            }
            return String.join("/",segments);
        }catch(Exception e){return "";}
    }
    private void readPackage() throws Exception {
        org.w3c.dom.Document container=document(readSmall("META-INF/container.xml",MAX_METADATA_BYTES));
        NodeList roots=container.getElementsByTagNameNS("*","rootfile");
        if(roots.getLength()==0)throw new IOException("EPUB is missing its package description");
        String opf=field(element(roots.item(0)),"full-path");
        if(opf.isBlank())throw new IOException("EPUB package path missing");
        org.w3c.dom.Document packageDoc=document(readSmall(opf,MAX_METADATA_BYTES));
        Element root=packageDoc.getDocumentElement();
        bookTitle=contents(root,"title");author=contents(root,"creator");
        String navPath=null;
        String ncxPath=null;
        Map<String,String> navTitles=new LinkedHashMap<>();
        Map<String,String> byId=new LinkedHashMap<>();
        Map<String,String> display=new LinkedHashMap<>();
        NodeList manifest=packageDoc.getElementsByTagNameNS("*","item");
        for(int i=0;i<manifest.getLength();i++){
            Element item=element(manifest.item(i));
            String id=field(item,"id"),href=field(item,"href");
            if(id.isBlank()||href.isBlank())continue;
            String name=normalPath(opf,href);
            if(!name.isBlank()){
                byId.put(id,name);display.put(id,href);
                String properties=field(item,"properties");
                if(Arrays.asList(properties.split("\\s+")).contains("nav"))navPath=name;
                if("application/x-dtbncx+xml".equalsIgnoreCase(field(item,"media-type")))
                    ncxPath=name;
                if(Arrays.asList(properties.split("\\s+")).contains("cover-image")
                   &&isRaster(name))preferredCoverName=name;
            }
        }
        // EPUB2 identifies its cover by the OPF metadata id.
        if(preferredCoverName==null){
            NodeList meta=packageDoc.getElementsByTagNameNS("*","meta");
            for(int i=0;i<meta.getLength();i++){
                Element item=element(meta.item(i));
                if("cover".equalsIgnoreCase(field(item,"name"))){
                    String image=byId.get(field(item,"content"));
                    if(image!=null&&isRaster(image)){preferredCoverName=image;break;}
                }
            }
        }
        // Navigation documents supply real editorial chapter titles. Only use
        // filenames as a last resort for malformed or very old EPUBs.
        if(navPath!=null) {
            try {
                org.w3c.dom.Document navigation=document(readSmall(navPath,MAX_METADATA_BYTES));
                NodeList links=navigation.getElementsByTagNameNS("*","a");
                for(int i=0;i<links.getLength();i++){
                    Element link=element(links.item(i));
                    String href=field(link,"href"),label=link.getTextContent().trim();
                    String resolved=normalPath(navPath,href);
                    if(!resolved.isBlank()&&!label.isBlank()&&label.length()<220)
                        navTitles.putIfAbsent(resolved,label);
                }
            }catch(Exception ignored){/* A missing/invalid NAV must not erase valid reading spine */ }
        }
        // EPUB2 titles live in toc.ncx, not an EPUB3 NAV document.
        // Resolve NCX content targets relative to the NCX itself and strip
        // fragment identifiers. A broken NCX must never hide a valid spine.
        if(ncxPath!=null && navTitles.isEmpty()){
            try{
                org.w3c.dom.Document ncx=document(readSmall(ncxPath,MAX_METADATA_BYTES));
                NodeList points=ncx.getElementsByTagNameNS("*","navPoint");
                for(int i=0;i<points.getLength();i++){
                    Element point=element(points.item(i));
                    Element label=null,target=null;
                    for(Node child=point.getFirstChild();child!=null;child=child.getNextSibling()){
                        Element e=element(child);
                        if(e==null)continue;
                        String local=e.getLocalName();
                        if("navLabel".equals(local))label=e;
                        else if("content".equals(local))target=e;
                    }
                    if(label==null||target==null)continue;
                    NodeList textNodes=label.getElementsByTagNameNS("*","text");
                    String title=textNodes.getLength()>0?
                        textNodes.item(0).getTextContent().trim():"";
                    String resolved=normalPath(ncxPath,field(target,"src"));
                    if(!title.isBlank()&&title.length()<220&&!resolved.isBlank())
                        navTitles.putIfAbsent(resolved,title);
                }
            }catch(Exception ignored){/* preserve spine even with malformed NCX */}
        }
        NodeList spine=packageDoc.getElementsByTagNameNS("*","itemref");
        for(int i=0;i<spine.getLength();i++){
            Element item=element(spine.item(i));
            String id=field(item,"idref"),name=byId.get(id);
            if(name==null||!name.toLowerCase(Locale.ROOT).matches(".*\\.x?html?$"))continue;
            String title=navTitles.getOrDefault(name,"Chapter "+(chapters.size()+1));
            chapters.add(new Chapter(name,title));
        }
        if(chapters.isEmpty())throw new IOException("EPUB contains no readable spine chapters");
    }
    @Override public void close() throws IOException {
        zip.close();descriptor.close();
        if(tempDescriptor!=null)tempDescriptor.close();
        if(temporary!=null)temporary.delete();
    }
    private static final class BoundedStream extends FilterInputStream{
        private final long limit;private long total;
        BoundedStream(InputStream source,long max){super(source);limit=max;}
        @Override public int read()throws IOException{
            int n=super.read();if(n!=-1&&++total>limit)throw new IOException("Book image too large");return n;
        }
        @Override public int read(byte[] data,int off,int len)throws IOException{
            int n=super.read(data,off,len);
            if(n>0&&(total+=n)>limit)throw new IOException("Book image too large");
            return n;
        }
    }
}

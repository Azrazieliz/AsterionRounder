from pathlib import Path
import re
root=Path('app/src/main')
main=root/'java/com/openlocal/office/MainActivity.java'
s=main.read_text(encoding='utf-8')
# Restore original full image streaming as the default for ALL sizes.
old='''                    long imageBytes=displaySize(uri);
                    String url="https://fg-assets.invalid/"+
                        (imageBytes>=12L*1024*1024?"fallback/":"raw/")+
                        imageStreamToken+"/image";'''
assert s.count(old)==1,("auto large-image fallback",s.count(old))
s=s.replace(old,'''                    String url="https://fg-assets.invalid/raw/"+
                        imageStreamToken+"/image";''',1)
# Never substitute thumbnails for the real image requested.
a=s.index('    private WebResourceResponse fgTbImage(Uri source){')
b=s.index('    private void saveTbFile(',a)
s=s[:a]+'''    private WebResourceResponse fgTbImage(Uri source){
        try {
            String[] parts=source.getPath().split("/");
            if(parts.length!=4||!parts[2].equals(fgTbToken))
                throw new IOException("Invalid cloud image session");
            TbPage item=fgTbPages.get(Integer.parseInt(parts[3]));
            if(item==null)throw new IOException("Cloud image no longer in current folder");
            // Full-content image requests always read the original via TeraBox.
            // Thumbnails are served only by cover/preview endpoints.
            return new WebResourceResponse(
                com.openlocal.office.core.FgTeraboxClient.mime(item.name),null,
                tb().open(item.path));
        }catch(Exception error){
            android.util.Log.w("FG_IMAGE","Original cloud image unavailable: "+
                error.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
'''+s[b:]
# Purge stale whole-file caches left by older app revisions without affecting
# encrypted credentials, bookmarks, user originals, or thumbnail caches.
anchor='''        web.loadUrl("file:///android_asset/index.html");'''
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
        new Thread(()->{
            for(java.io.File dir:new java.io.File[]{
                new java.io.File(getCacheDir(),"reading-v2"),
                new java.io.File(getCacheDir(),"fg-media-v2"),
                new java.io.File(getCacheDir(),"reading-volatile-v3"),
                new java.io.File(getExternalCacheDir()!=null?
                    getExternalCacheDir():getCacheDir(),"fg-media-v2")}){
                if(!dir.isDirectory())continue;
                java.io.File[] children=dir.listFiles();
                if(children!=null)for(java.io.File candidate:children)
                    if(candidate.isFile())candidate.delete();
            }
            android.util.Log.i("FG_CACHE","Legacy full-document cache cleanup complete");
        },"fg-cache-migration").start();
''',1)
main.write_text(s,encoding='utf-8')
# Never persist complete originals, only scoped preview outputs.
g=Path('app/build.gradle.kts')
if not g.exists():g=Path('app/build.gradle')
v=g.read_text(encoding='utf-8')
assert '0.14.9' in v
v,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)21\b',r'\g<1>22',v,count=1)
assert n==1
v=v.replace('0.14.9','0.15.0',1)
g.write_text(v,encoding='utf-8')
print('No automatic content fallback, original TeraBox stream, legacy whole-file cache cleanup, version 0.15.0')

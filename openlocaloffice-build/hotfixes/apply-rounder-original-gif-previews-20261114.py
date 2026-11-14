#!/usr/bin/env python3
"""Route Rounder cloud covers through original-file reads, not TeraBox previews.

Applied after all older library / brand fixes. Existing card DOM/CSS, download
rights, TeraBox account and reader interfaces remain unchanged.
"""
from pathlib import Path
import re

root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
code=main.read_text(encoding="utf-8")
start=code.index("    private WebResourceResponse fgTbCover(Uri source){")
end=code.index("    private WebResourceResponse fgTbImage(Uri source){",start)
old=code[start:end]
assert "openThumbnail(path,folder,page)" in old
replacement=r'''    private WebResourceResponse fgTbCover(Uri source){
        String id=source.getLastPathSegment();
        if(id==null||id.length()>8192)return new WebResourceResponse(
            "image/jpeg",null,new ByteArrayInputStream(new byte[0]));
        try{
            int split=id.lastIndexOf('.');
            if(split<1)throw new IOException("Missing thumbnail page");
            int page=Integer.parseInt(id.substring(split+1));
            if(page<1||page>10000)throw new IOException("Invalid thumbnail page");
            String path=new String(android.util.Base64.decode(id.substring(0,split),
                android.util.Base64.URL_SAFE|android.util.Base64.NO_WRAP|
                android.util.Base64.NO_PADDING),java.nio.charset.StandardCharsets.UTF_8);
            if(!path.startsWith("/")||!com.openlocal.office.core.FgTeraboxClient.image(path))
                throw new IOException("Invalid original image path");
            // Direct, authenticated original GIF bytes retain native animation.
            // These are lazy visible-card requests, not background cloud downloads.
            String mime=com.openlocal.office.core.FgTeraboxClient.mime(path);
            if("image/gif".equals(mime))
                return new WebResourceResponse("image/gif",null,tb().open(path));
            // Static thumbnail pixels are decoded locally from ORIGINAL file data.
            // Never ask /thumbs or a provider-shared preview URL for this route.
            try{
                return new WebResourceResponse("image/jpeg",null,
                    new com.openlocal.office.core.FgRounderOriginalPreviews(
                        MainActivity.this,tb()).openStill(path));
            }catch(Exception boundedDecodeError){
                android.util.Log.i("FG_ORIGINAL_PREVIEW",
                    "Bounded still preview unavailable; streaming original "+
                    boundedDecodeError.getClass().getSimpleName());
                // A valid very large or uncommon image may exceed thumbnail
                // budget: let WebView decode its authenticated ORIGINAL stream.
                return new WebResourceResponse(mime,null,tb().open(path));
            }
        }catch(Exception problem){
            android.util.Log.w("FG_ORIGINAL_PREVIEW",
                "Original image preview unavailable: "+
                problem.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
'''
# Keep the image collection's existing /terabox-preview/session/index route.
# The earlier reader repair inserted fgTbPreview between fgTbCover and fgTbImage;
# replacing the entire region had inadvertently removed that native method.
# Both endpoints must decode authenticated original data, never call /thumbs.
preview=r'''    private WebResourceResponse fgTbPreview(Uri source){
        try{
            String[] parts=source.getPath().split("/");
            if(parts.length!=4||!parts[2].equals(fgTbToken))
                throw new IOException("Invalid cloud preview session");
            TbPage item=fgTbPages.get(Integer.parseInt(parts[3]));
            if(item==null)throw new IOException("Preview is not in the current collection");
            String path=item.path;
            String mime=com.openlocal.office.core.FgTeraboxClient.mime(item.name);
            if("image/gif".equals(mime))
                return new WebResourceResponse(mime,null,tb().open(path));
            try{
                return new WebResourceResponse("image/jpeg",null,
                    new com.openlocal.office.core.FgRounderOriginalPreviews(
                        MainActivity.this,tb()).openStill(path));
            }catch(Exception budgetError){
                return new WebResourceResponse(mime,null,tb().open(path));
            }
        }catch(Exception problem){
            android.util.Log.w("FG_ORIGINAL_PREVIEW",
                "Collection image preview unavailable: "+
                problem.getClass().getSimpleName());
            return new WebResourceResponse("image/jpeg",null,
                new ByteArrayInputStream(new byte[0]));
        }
    }
'''
assert "private WebResourceResponse fgTbPreview(Uri source)" in old, "Expected legacy reader preview to be present before replacement"
code=code[:start]+replacement+preview+code[end:]
# SAF-based local / cloud DocumentsProvider library also supports GIF covers.
# This does NOT affect the actual reader, only its thumbnail URL.
anchor='''                            return new WebResourceResponse("image/jpeg",null,
                                ReaderCovers.open(MainActivity.this,coverSource,
                                    coverName,coverSize,coverModified));'''
assert code.count(anchor)==1, ("Expected original SAF cover handler",code.count(anchor))
code=code.replace(anchor,'''                            if(coverName.toLowerCase(java.util.Locale.ROOT).endsWith(".gif"))
                                return new WebResourceResponse("image/gif",null,
                                    getContentResolver().openInputStream(coverSource));
'''+anchor,1)
# SAF listings must emit GIF thumbnail URLs. No card markup/layout changes.
needle='''low.endsWith(".png")||low.endsWith(".webp");'''
assert code.count(needle)>=1, ("Expected image extension filter",code.count(needle))
code=code.replace(needle,'''low.endsWith(".png")||low.endsWith(".webp")||
                                low.endsWith(".gif")||low.endsWith(".avif")||
                                low.endsWith(".bmp");''')
main.write_text(code,encoding="utf-8")

# Make native type sniffing agree with the JavaScript image classifier.
client=root/"java/com/openlocal/office/core/FgTeraboxClient.java"
cloud=client.read_text(encoding="utf-8")
needle='''        if(low.endsWith(".gif"))return "image/gif";'''
assert cloud.count(needle)==1
cloud=cloud.replace(needle,needle+'''
        if(low.endsWith(".bmp"))return "image/bmp";''',1)
client.write_text(cloud,encoding="utf-8")

# URLs were historically sent to the browser with unchanged identifiers.
# A versioned URL is necessary to avoid loading a browser-cached prohibited
# CDN placeholder from an earlier app release.
lib=root/"assets/premium-library.js"
js=lib.read_text(encoding="utf-8")
needle="job.image.src=job.url;"
assert js.count(needle)==1,("Expected remote cover assignment",js.count(needle))
js=js.replace(needle,
    "job.image.src=job.url+(job.url.includes('?')?'&':'?')+'source=original-v1';",1)
lib.write_text(js,encoding="utf-8")
print("ROUNDER_ORIGINAL_CLOUD_PREVIEWS_OK: static originals locally decoded, GIFs streamed animated, cache scoped")

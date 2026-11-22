#!/usr/bin/env python3
"""Restore Rounder's approved two-wide video gallery and real video covers.

Apply once after the final 2026-11-14 preview patch, to the assembled project.
Retains all existing local/cloud readers, WebView card controls, scroll engine,
signing, native player, and private files. No original movie is copied.
"""
from pathlib import Path

base = Path("app/src/main")
main = base / "java/com/openlocal/office/MainActivity.java"
native = main.read_text(encoding="utf-8")
library = base / "assets/premium-library.js"
js = library.read_text(encoding="utf-8")
style = base / "assets/style.css"
css = style.read_text(encoding="utf-8")
index = base / "java/com/openlocal/office/core/FgTeraboxSearchIndex.java"
cloud_index = index.read_text(encoding="utf-8")

def once(code, before, after, what):
    count = code.count(before)
    if count != 1:
        raise AssertionError(f"{what}: expected exactly one assembly anchor, found {count}")
    return code.replace(before, after, 1)

# Direct TeraBox listing's image-cover conditional differs between overlays.
# Insert an independent video assignment at the stable batch emission point:
# no existing image behavior or private cloud file is changed.
start = native.index("    private void listTeraboxNative(")
end = native.index("    private ", start + len("    private void listTeraboxNative("))
listing = native[start:end]
anchor = "                            batch.put(mapped);"
replacement = """                            if(!mapped.optBoolean("folder")&&
                               com.openlocal.office.core.FgRounderVideoPreviews.isVideo(
                                   mapped.optString("name",""))){
                                mapped.put("cover","https://fg-assets.invalid/tb-cover/"+
                                    fgTbCoverId(path,page));
                                mapped.put("remoteCover",true);
                            }
""" + anchor
listing = once(listing, anchor, replacement, "cloud video cover before batch")
native = native[:start] + listing + native[end:]

# The existing SAF library is streamed in batches. Add the same lazy cover
# URL to local videos without scanning the file during folder enumeration.
start = native.index('boolean image=item.optBoolean("folder")||',
                     native.index("    private void loadLibrary(String folder){"))
end = native.index("if(image){", start)
selection = native[start:end]
semicolon = selection.rfind(";")
assert semicolon >= 0 and "low.endsWith" in selection
selection = (selection[:semicolon].rstrip() +
    "||\n                                com.openlocal.office.core.FgRounderVideoPreviews.isVideo(name)" +
    selection[semicolon:])
native = native[:start] + selection + native[end:]

# /cover/{id} already verifies the URI against the current SAF listing. Decode
# video frames locally and cache a tiny JPEG instead of routing them to the
# book cover decoder, which only accepts images and documents.
anchor = '''                            return new WebResourceResponse("image/jpeg",null,
                                ReaderCovers.open(MainActivity.this,coverSource,
                                    coverName,coverSize,coverModified));'''
replacement = '''                            if(com.openlocal.office.core.FgRounderVideoPreviews.isVideo(coverName))
                                return new WebResourceResponse("image/jpeg",null,
                                    com.openlocal.office.core.FgRounderVideoPreviews.local(
                                        MainActivity.this,coverSource,coverSize,coverModified));
''' + anchor
native = once(native, anchor, replacement, "SAF video frame decoding")

# The 2026-11-14 image-only proxy guard rejected all video thumbnails. Let
# videos use the existing encrypted/account-scoped server thumbnail first,
# then a bounded source-range keyframe if the provider has no thumbnail.
guard = '''if(!path.startsWith("/")||!com.openlocal.office.core.FgTeraboxClient.image(path))
                throw new IOException("Invalid cloud cover path");
            String mime=com.openlocal.office.core.FgTeraboxClient.mime(path);'''
replacement = '''if(!path.startsWith("/")||
               (!com.openlocal.office.core.FgTeraboxClient.image(path)&&
                !com.openlocal.office.core.FgRounderVideoPreviews.isVideo(path)))
                throw new IOException("Invalid cloud cover path");
            String mime=com.openlocal.office.core.FgTeraboxClient.mime(path);
            if(com.openlocal.office.core.FgRounderVideoPreviews.isVideo(path)){
                try{
                    int slash=path.lastIndexOf('/');
                    return new WebResourceResponse("image/jpeg",null,
                        tb().openThumbnail(path,path.substring(0,slash),page));
                }catch(Exception providerError){
                    android.util.Log.i("FG_VIDEO_PREVIEW",
                        "Server video thumbnail unavailable: "+providerError.getClass().getSimpleName());
                    return new WebResourceResponse("image/jpeg",null,
                        com.openlocal.office.core.FgRounderVideoPreviews.cloud(
                            MainActivity.this,tb(),path));
                }
            }'''
native = once(native, guard, replacement, "authenticated TeraBox video preview")
main.write_text(native, encoding="utf-8")

# Indexed recursive search needs the same real cover as live listing.
anchor = '''                            results.put(item);'''
replacement = '''                            if("video".equals(cursor.getString(2))){
                                item.put("cover",coverUrl(path,cursor.getInt(7)))
                                    .put("remoteCover",true);
                            }
''' + anchor
cloud_index = once(cloud_index, anchor, replacement, "indexed video thumbnails")
index.write_text(cloud_index, encoding="utf-8")

# Cache layout categories once per folder/index revision, not on every
# WebView scroll. A mixed folder can contain tall book/image/folder cards:
# those rows must retain the original portrait height to avoid clipping.
js = once(js,
    "let virtualFiles=[],virtualFolders=[],virtualHasCovers=false,folderRegion=null;",
    "let virtualFiles=[],virtualFolders=[],virtualHasCovers=false,virtualHasVideos=false,virtualHasPortraits=false,folderRegion=null;",
    "cache gallery mix flags")
js = once(js,
    "   virtualHasCovers=virtualFiles.some(e=>!!e.cover);",
    """   virtualHasCovers=virtualFiles.some(e=>!!e.cover);
   virtualHasVideos=virtualFiles.some(e=>classify(e)==='video');
   virtualHasPortraits=virtualFiles.some(e=>classify(e)!=='video');""",
    "derive video and portrait flags once per data revision")

# The continuous renderer replaced 'fg-lib-video-grid' with the generic
# three-column grid. Restore the class for mixed folders and video filters.
anchor = ''' const useList=list;
 deck.className='fg-lib-grid'+(useList?' fg-lib-list':' fg-vault-media-grid');
 const computedCols='''
replacement = ''' const useList=list;
 const hasVideos=!useList&&virtualHasVideos;
 deck.className='fg-lib-grid'+(useList?' fg-lib-list':' fg-vault-media-grid')+
   (hasVideos?' fg-lib-video-grid':'');
 const computedCols='''
js = once(js, anchor, replacement, "continuous two-column video grid")
anchor = ''' const rowHeight=useList?124:Math.ceil(cellWidth*1.5+86);'''
replacement = ''' const rowHeight=useList?124:Math.ceil(cellWidth*(hasVideos&&!virtualHasPortraits?9/16:1.5)+86);'''
js = once(js, anchor, replacement, "accurate virtual row height for video landscape cards")
library.write_text(js, encoding="utf-8")

# Higher-specificity final override, after all earlier 3-column rules.
# Only video-containing grids are changed; document, image and book grids
# retain their approved layout. Do not crop preview frames.
css += """
/* Owner-approved Rounder video gallery; applied after classic/compact themes. */
.fg-library-root .fg-lib-grid.fg-lib-video-grid:not(.fg-lib-list){
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  gap:18px 12px!important
}
.fg-library-root .fg-lib-video .fg-lib-cover{
  aspect-ratio:16/9!important;
  min-height:0!important
}
.fg-library-root .fg-lib-video .fg-lib-cover-image{
  object-fit:contain!important
}
"""
style.write_text(css, encoding="utf-8")
print("ROUNDER_TWO_WIDE_VIDEO_COVERS_READY: local, direct TeraBox, indexed search, native bounded frames")

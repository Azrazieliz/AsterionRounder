'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root='app/src/main/';
const main=fs.readFileSync(root+'java/com/openlocal/office/MainActivity.java','utf8');
const local=fs.readFileSync(root+'java/com/openlocal/office/core/FgRounderOriginalPreviews.java','utf8');
const cloud=fs.readFileSync(root+'java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
const library=fs.readFileSync(root+'assets/premium-library.js','utf8');
const required=(s,fragments,label)=>fragments.forEach(x=>assert(s.includes(x),label+': '+x));
const start=main.indexOf('private WebResourceResponse fgTbCover(Uri source)');
const end=main.indexOf('private WebResourceResponse fgTbImage(Uri source)',start);
assert(start>=0&&end>start,'Missing native TeraBox preview route');
const route=main.slice(start,end);
required(route,[
  'FgRounderOriginalPreviews','openStill(path)','"image/gif",null,tb().open(path)',
  'streaming original','fgTbCover(Uri source)',
  'tb().openThumbnail(path,folder,page)','fgTbOriginalCover(path,mime)',
  'fgCloudIndex().isPreviewAffected(path)'
],'native original preview');
assert(route.indexOf('tb().openThumbnail(path,folder,page)')<route.indexOf('return fgTbOriginalCover(path,mime)'),
  'Normal images must prefer TeraBox thumbnails before original fallback');
const previewStart=main.indexOf('private WebResourceResponse fgTbPreview(Uri source)',start);
assert(previewStart>start&&previewStart<end,'Existing collection preview route must remain');
const previewRoute=main.slice(previewStart,end);
required(previewRoute,[
 'FgRounderOriginalPreviews','openStill(path)',
 '"image/gif".equals(mime)','tb().open(path)',
 'fgTbPages.get(Integer.parseInt(parts[3]))','tb().openThumbnail(path)'
],'original image collection preview');
assert(previewRoute.indexOf('tb().openThumbnail(path)')<previewRoute.indexOf('return fgTbOriginalCover(path,mime)'),
  'Collection images must prefer provider thumbnails unless affected');
required(local,[
  'cloud.openRangeStream(path,0)','MAX_ENCODED_BYTES=16*1024*1024',
  'new Semaphore(2,true)','BitmapFactory.decodeByteArray',
  'Bitmap.CompressFormat.JPEG','context.getFilesDir()','cloud.metadataScope()',
  'rounder-original-preview-v1','2L*1024*1024'
],'bounded account-scoped generated thumbnail');
assert(!local.includes('cloud.openThumbnail('),'Generated preview cannot reuse restricted thumbnail');
required(main,[
  'coverName.toLowerCase(java.util.Locale.ROOT).endsWith(".gif")',
  'new WebResourceResponse("image/gif",null,',
  'low.endsWith(".gif")'
],'local / SAF GIF animated preview');
required(library,["source=hybrid-v2","function card(item,i)","const cover=E('div','fg-lib-cover');"],'original cards retained / stale browser preview invalidation');
required(cloud,['if(low.endsWith(".gif"))return "image/gif";','if(low.endsWith(".bmp"))return "image/bmp";'],'cloud MIME');
console.log('ROUNDER_ORIGINAL_THUMBNAIL_SOURCE_PASS: provider-first hybrid previews, animated GIF fallback, bounded private cache, unchanged cards');

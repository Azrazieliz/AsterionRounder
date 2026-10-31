/* Asterion Rounder: regression gates on the fully assembled Android source. */
const fs=require('fs'),assert=require('node:assert/strict');
const reader=fs.readFileSync('app/src/main/assets/reader-controls.js','utf8');
const archive=fs.readFileSync('app/src/main/assets/universal-reader.js','utf8');
const book=fs.readFileSync('app/src/main/assets/epub-reader.js','utf8');
const media=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgMediaPlayer.java','utf8');
const cloud=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
assert.match(reader,/append:payload=>add\(Array\.isArray\(payload\)\?payload:payload\?\.pages\)/,
  'Native batches are arrays, never silently discard them');
assert.match(reader,/section\.style\.minHeight='80vh'/,
  'Pending images reserve viewport height to avoid loading the entire folder');
assert.match(reader,/index\+8/, 'Bound each new batch to eight images');
assert(!reader.includes("rootMargin:'320% 0px'"),'Avoid excessive prefetch radius');
assert.match(archive,/MAX_IMAGE_FETCHES=remoteArchive\?2:3/,
  'Only nearby pages may fetch full images concurrently');
assert.match(archive,/im\.loading='eager'/,
  'Explicitly scheduled archive images must start fetching');
assert.match(book,/requested\.size>=2/, 'EPUB must not queue hundreds of chapter streams');
assert.match(book,/EPUB_CHAPTER_RENDERED/, 'EPUB must report actual visible chapter content');
assert.match(media,/teraboxDirect\)playTeraboxRanges/, 'Cloud video stays on seekable streaming path');
assert.match(media,/PlayerView.ControllerVisibilityListener/,
  'Overlay navigation follows Media3 playback controls rather than a full-width bar');
assert.match(media,/mediaNavigator.navigate\(-1,false\)/,
  'Previous video is wired to playlist navigation');
assert.match(media,/mediaNavigator.navigate\(1,false\)/,
  'Next video is wired to playlist navigation');
assert.match(media,/mediaNavigator.navigate\(0,true\)/,
  'Shuffle is wired to playlist navigation');
assert.doesNotMatch(media,/playlistPos=new FrameLayout\.LayoutParams/,
  'Legacy fullscreen previous next random text bar must not return');
assert.match(cloud,/public byte\[\] readRange/, 'Cloud files retain byte-range access');
assert.match(cloud,/public InputStream openRangeStream/, 'Video streaming must use one HTTP response per seek');
const data=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgTeraboxMediaDataSource.java','utf8');
assert.match(data,/stream=cloud.openRangeStream\(cloudPath,position\)/,
  'Media player must avoid per-512-KiB HTTPS requests');
assert.doesNotMatch(data,/buffer=cloud.readRange/,
  'Media player must not reconnect on every buffered chunk');
assert.match(data,/closed=false;\s*cloudPath=/,
  'Reused Media3 DataSource must reopen correctly after seek');
for(const name of ['reader-controls.js','universal-reader.js','epub-reader.js']){
  new (require('vm').Script)(fs.readFileSync('app/src/main/assets/'+name,'utf8'),{filename:name});
}
const pages=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgTeraboxDocumentsProvider.java','utf8');
const metadataClient=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
const library=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const covers=fs.readFileSync('app/src/main/java/com/openlocal/office/core/ReaderCovers.java','utf8');
assert.match(pages,/queryChildDocuments\(String documentId,String\[\] projection,Bundle args\)/,
  'Cloud metadata must support bounded paged SAF queries for 100K+ files');
assert.match(pages,/PAGE_OFFSET="asterion.page.offset"/,
  'Bulk catalog must be accessible to other Asterion apps using a granted tree');
assert.match(pages,/terabox-metadata-v1/,
  'Metadata index must survive process restarts');
assert.match(pages,/queuePage\(folder,next,nextKey,nextFile\)/,
  'Cloud metadata pages must prefetch without opening originals');
assert.match(metadataClient,/getFilesDir\(\),"terabox-thumbnails-v4"/,
  'Only thumbnail images persist in private application files');
assert.match(covers,/getFilesDir\(\),"covers-v3"/,
  'Previously displayed covers must persist in private application files');
assert.match(library,/const retainedCards=new Map\(\)/,
  'Re-rendering metadata must not discard already loaded cover IMG nodes');
assert.match(library,/if\(signature!==lastVisibleKeys\)/,
  'Unchanged library pages must not be rebuilt while metadata arrives');
assert.doesNotMatch(reader,/img\.removeAttribute\('src'\);\s*\}\s*\}\s*\},\{root:view/,
  'Scrolling out of view must not always clear existing image pixels');
assert.match(reader,/append:payload=>add\(Array\.isArray\(payload\)\?payload:payload\?\.pages\)/,
  'Native streamed image batches must be accepted without loss');
const nativeTerabox=fs.readFileSync('../hotfixes/apply-direct-terabox-20261031.py','utf8');
assert.match(nativeTerabox,/newFixedThreadPool\(4\)/,
  'Cloud metadata listing uses bounded parallelism');
assert.match(nativeTerabox,/listPageCached\(requested,requestedPage\)/,
  'Cloud background jobs request metadata pages, not original image streams');
assert.match(nativeTerabox,/listPool.shutdownNow\(\)/,
  'Leaving a folder must cancel outstanding cloud metadata workers');
assert.match(metadataClient,/key.substring\(0,2\)/,
  'Persistent thumbnails must be sharded for very large libraries');
assert.match(metadataClient,/terabox-thumbnails-v3/,
  'Existing private thumbnails must migrate without another download');
assert.match(metadataClient,/2400\|\|total>shardBudget/,
  'Private thumbnail cache must be bounded by storage and shard size');
// Performance regressions: opening a 300K-image folder must not perform an
// O(all previously received pages) rebuild for every new metadata batch.
new (require('vm').Script)(library,{filename:'premium-library.js'});
assert.match(library,/const naturalCollator=new Intl.Collator/,
  'File comparisons must share one Intl.Collator');
assert.match(library,/indexedRevision===catalogRevision&&indexedKey===key/,
  'Changing library pages must reuse the filtered and sorted index');
assert.match(library,/state\.known\.add\(key\)/,
  'Growing image collections must dedupe using an incremental Set');
assert.doesNotMatch(library,/const known=new Set\(state\.siblings\.map/,
  'Do not rebuild the known-images set after every cloud batch');
assert.match(library,/const sameCollection=collectionCacheKey===nextCollectionKey/,
  'Reopening a folder must retain already rendered images');
assert.match(nativeTerabox,/fgTbCoverId\(path,page\)/,
  'Cover URLs must be stable and encode their metadata page');
assert.doesNotMatch(nativeTerabox,/fgTbCoverIds/,
  'Native memory must not hold a second map of 300K cover paths');
assert.match(nativeTerabox,/tb\(\)\.openThumbnail\(path,folder,page\)/,
  'Cloud cover requests must recover thumbnail URLs by metadata page');
assert.match(metadataClient,/listPageCached\(folder,page\)/,
  'Thumbnail cache misses should reuse a full cached metadata page instead of per-file metadata calls');
console.log('ASTERION_READER_CONTRACT_PASS');

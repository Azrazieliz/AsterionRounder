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
assert.match(book,/requested\.size>=4/, 'EPUB uses four bounded chapter requests, not an unbounded queue');
assert.match(book,/EPUB_CHAPTER_RENDERED/, 'EPUB must report actual visible chapter content');
assert.match(media,/teraboxDirect\)playTeraboxRanges/, 'Cloud video stays on seekable streaming path');
assert.match(media,/setShowPreviousButton\(false\)/,
  'Hide duplicate Media3 previous controls in fullscreen');
assert.match(media,/setShowNextButton\(false\)/,
  'Hide duplicate Media3 next controls in fullscreen');
assert.match(media,/R\.id\.exo_prev/,
  'Explicitly suppress legacy Media3 previous overlay icon');
assert.match(media,/R\.id\.exo_next/,
  'Explicitly suppress legacy Media3 next overlay icon');

assert.match(media,/display.setUseController\(false\)/,
  'Video hides Media3 controls and uses exactly one Aloha-style transport overlay');
assert.match(media,/root.addView\(transport,new FrameLayout.LayoutParams\(-2,-2,Gravity.CENTER\)\)/,
  'Compact video transport must remain centered rather than full-width');
assert.match(media,/root.addView\(footer,footerPosition\)/,
  'Video seek and small playback-mode control must have one safe-area-aware bottom bar');
assert.match(media,/mediaNavigator.navigate\(-1,false\)/,
  'Previous video is wired to playlist navigation');
assert.match(media,/mediaNavigator.navigate\(1,false\)/,
  'Next video is wired to playlist navigation');
assert.match(media,/playbackMode==2\?0:1,playbackMode==2/,
  'Shuffle and Play Next modes must advance through folder navigation');
assert.match(media,/player.seekTo\(0\);player.play\(\)/,
  'Replay mode must restart the current video without a download');
assert.match(media,/final View modeSymbol=new View\(activity\)/,
  'A single native-vector icon must display the active playback type');
assert.match(media,/onVideoSizeChanged/,
  'Portrait or landscape playback must respect the video dimensions');
assert.match(media,/SCREEN_ORIENTATION_LOCKED/,
  'Orientation lock must remain independently clickable');
assert.match(media,/footerPosition.rightMargin/,
  'Bottom transport controls must clear the Android landscape navigation area');
assert.match(media,/playbackMode=\(playbackMode\+1\)%3/,
  'Tapping the small icon must cycle Play Next, Replay and Shuffle');
assert.doesNotMatch(media,/final LinearLayout modes=new LinearLayout\(activity\)/,
  'Do not restore the oversized three-button playback mode bar');
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
assert.match(metadataClient,/private final Map<String,HotPage> hotPages/,
  'Recently used TeraBox pages must be cached in bounded RAM');
assert.match(metadataClient,/size\(\)>32/,
  'Hot page cache must not grow without limit');

const remote=fs.readFileSync('app/src/main/assets/fg-remote-ui.js','utf8');
new (require('vm').Script)(remote,{filename:'fg-remote-ui.js'});
assert.match(remote,/document\.body\.classList\.add\('fg-pc-active'\)/,
  'Remote viewport must enter foreground full-screen mode');
assert.match(remote,/&width='\+width\+'&height='\+height/,
  '3D frames must match the actual phone viewport');
assert.match(remote,/panX=clamp/,
  'Two-finger panning must move camera without moving 3D objects');
assert.match(remote,/requestFrame\(\)/,
  'Orbit and zoom must request fresh PC frames');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
assert.match(css,/z-index:2147483640!important/,
  '3D scene must sit above image-reader navigation and entry controls');
assert.match(css,/fg-lib-grid\.fg-lib-video-grid/,
  'Video cards require a horizontal two-column preview grid');
assert.match(css,/scroll-snap-type:x mandatory/,
  'Image pages require horizontal snap behavior');
const bridgeSource=fs.readFileSync('../pc-remote/fg_remote_server.py','utf8');
assert.match(bridgeSource,/camera_rotation=\[math\.degrees\(pitch\),180\+math\.degrees\(yaw\),0\]/,
  'Koikatsu orbit must point camera back toward the stationary target');
assert.match(bridgeSource,/request\.write_text\(f"\{width\},\{height\}"/,
  'PC must render full-height phone frames instead of a 680x800 square');
const library=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const covers=fs.readFileSync('app/src/main/java/com/openlocal/office/core/ReaderCovers.java','utf8');
assert.match(pages,/queryChildDocuments\(String documentId,String\[\] projection,Bundle args\)/,
  'Cloud metadata must support bounded paged SAF queries for 100K+ files');
assert.match(pages,/PAGE_OFFSET="asterion.page.offset"/,
  'Bulk catalog must be accessible to other Asterion apps using a granted tree');
assert.match(pages,/terabox-metadata-v1/,
  'Metadata index must survive process restarts');
assert.match(pages,/JSONArray cloud=client\.listPageCached\(folder,page\)/,
  'AsterionCore must reuse Rounder native TeraBox metadata cache');
assert.match(pages,/result\.putBoolean\("asterion.page.ready",ready\)/,
  'All available indexed metadata pages must be usable during refresh');
assert.match(pages,/limit!=4\*INDEX_PAGE_SIZE/,
  'Core connector must support 400-row metadata batches');
assert.match(pages,/openDocumentThumbnail\(/,
  'AsterionCore must receive native cached thumbnails, not full original images');
assert.match(pages,/FLAG_SUPPORTS_THUMBNAIL/,
  'Rounder must advertise thumbnail support on cloud image documents');
assert.match(pages,/queuePage\(folder,next,key,file\)/,
  'Cloud metadata pages must prefetch without opening originals');
assert.match(metadataClient,/getFilesDir\(\),"terabox-thumbnails-v4"/,
  'Only thumbnail images persist in private application files');
assert.match(covers,/getFilesDir\(\),"covers-v3"/,
  'Previously displayed covers must persist in private application files');
assert.match(library,/const retainedCards=new Map\(\)/,
  'Re-rendering metadata must not discard already loaded cover IMG nodes');
assert.match(library,/if\(signature!==lastVisibleKeys\)/,
  'Unchanged library pages must not be rebuilt while metadata arrives');
assert.doesNotMatch(library,/deck\.replaceChildren\(\);empty\.replaceChildren\(\)/,
  'Do not clear visible cover images before checking the catalog signature');
assert.match(library,/deck\.insertBefore\(node,existing\|\|null\)/,
  'Keep existing decoded cover nodes while reordering pages');
assert.match(library,/fg-lib-video-grid/,
  'Video collection must use a landscape grid');
assert.match(library,/asterion-rounder-recent-v1/,
  'Home must retain recently opened files between sessions');
assert.match(reader,/view\.addEventListener\('pointerup'/,
  'Touch swipes must navigate images horizontally');
assert.match(reader,/x<=\.28\)moveImage\(-1\)/,
  'Tapping the left side must navigate to the previous image');
assert.match(reader,/imageMode==='pages'\)view\.scrollTo\(\{left:/,
  'Paged reader must switch horizontally');
assert.doesNotMatch(reader,/image\.removeAttribute\('src'\)/,
  'Image timeouts must never remove a displayed image source');
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
// Rounder fully replaces the former cloud adapter. No third-party provider
// authority, playback workaround or UI label may be reintroduced by overlays.
for(const source of [
  'app/src/main/java/com/openlocal/office/MainActivity.java',
  'app/src/main/java/com/openlocal/office/core/ReaderLibrary.java',
  'app/src/main/java/com/openlocal/office/core/ReaderCovers.java',
  'app/src/main/java/com/openlocal/office/core/FgMediaPlayer.java',
  'app/src/main/java/com/openlocal/office/core/BookArchive.java',
  'app/src/main/java/com/openlocal/office/core/SeekableZip.java',
  'app/src/main/java/com/openlocal/office/core/FgTeraboxClient.java',
  'app/src/main/assets/premium-library.js',
  'app/src/main/assets/reader-controls.js'
]){
  const data=fs.readFileSync(source,'utf8');
  assert.doesNotMatch(data,/round[\s_-]?sync|felixnuesse/i,
    'Legacy RoundSync implementation must not return: '+source);
}
assert.match(media,/if\(teraboxDirect\)playTeraboxRanges\(\);\s*else play\(original\)/,
  'Remote video must follow the native TeraBox range path, without legacy provider copies');
const zipSource=fs.readFileSync('app/src/main/java/com/openlocal/office/core/SeekableZip.java','utf8');
assert.match(zipSource,/memberFd=Os\.dup\(fd\)/,
  'Every ZIP image stream must survive previous book closure');
assert.match(zipSource,/Os\.pread\(memberFd,buffer,start,n,offset\)/,
  'ZIP member reads must use their own retained descriptor');
const main=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
assert.match(main,/getNativePcStatus\(String session\)/,
  '3D status must bypass file-backed WebView CORS restrictions');
assert.match(main,/fgAuthenticatedPcFrame\(u\)/,
  'Native PC 3D image proxy must intercept resource requests');
assert.match(remote,/https:\/\/fg-assets\.invalid\/pc-frame\?/,
  '3D images must load natively instead of browser fetching localhost');
const libUi=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const controls=fs.readFileSync('app/src/main/assets/reader-controls.js','utf8');
const archives=fs.readFileSync('app/src/main/assets/universal-reader.js','utf8');
const epub=fs.readFileSync('app/src/main/assets/epub-reader.js','utf8');
assert.match(libUi,/deck.classList.toggle\('fg-lib-compact-files'/,
  'Document-heavy folders must use compact rows');
assert.match(libUi,/welcome.hidden=true;dashboard.hidden=true/,
  'Remove nonfunctional welcome dashboard');
assert.match(css,/repeat\(2,minmax\(0,1fr\)\)!important/,
  'Mobile previews should be two wide');
assert.match(css,/\.fg-library-root \.fg-lib-more,\.fg-library-root \.fg-lib-type\{display:none!important\}/,
  'Do not cover filenames or previews with redundant tags and menu buttons');
assert.match(controls,/mode==='pages'\?'Pages':mode==='hscroll'\?'H-scroll':'V-scroll'/,
  'Reading mode button must name the ACTIVE mode');
assert.match(controls,/readerPage=0/,
  'Pages mode must retain an explicit page index');
assert.match(archives,/fg-archive-list fg-archive-compact/,
  'Noncomic ZIPs must use a compact file list');
assert.match(epub,/requested.size>=4/,
  'EPUB chapters may load concurrently rather than fixed pairs');
assert.match(epub,/Never erase previously rendered illustrations/,
  'EPUB previously loaded images must remain visible');
console.log('ASTERION_READER_CONTRACT_PASS');

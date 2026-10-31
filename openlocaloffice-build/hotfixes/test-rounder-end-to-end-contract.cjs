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
console.log('ASTERION_READER_CONTRACT_PASS');

/* Build gate: image folders must reach their actual renderer; cloud videos
 * must start playback before the entire copy has completed.
 */
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const js=fs.readFileSync('app/src/main/assets/reader-controls.js','utf8');
const lib=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const main=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
const media=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgMediaPlayer.java','utf8');
const growing=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgGrowingMediaDataSource.java','utf8');
assert(!lib.includes("if(item.folder){\n   bridge()?.openImageFolder"),'Folder overlay is still blocking image pages');
assert(lib.includes("enterFolder(item.id);return;"),'Folders must browse normally rather than force image reading');
assert(js.includes('window.appBusy?.(false);'),'Image open path leaves busy spinner displayed indefinitely');
assert(js.includes("if(data?.type==='folderImages'||data?.type==='image')"),'Dedicated image route absent');
const block=js.slice(js.indexOf("window.loadDocument=function(data){"));
assert(block.includes("renderImageFolder(data.type==='image'?{") &&
  block.indexOf("renderImageFolder(data.type==='image'?{")<block.indexOf("upstream.apply(this,arguments)"),
  'Dedicated image reader must bypass generic document viewer');
assert(js.includes('window.FileGestionerFolder='),'Dynamic image batches missing');
assert(js.includes("stack.insertBefore(frag,sentinel)"),'On-screen pages not appended');
assert(main.includes('fgFolderPageMap'),'Native folder images route missing');
assert(main.includes('fgFolderToken'),'Native folder token missing');
assert(main.includes('FgMediaPlayer'),'Media3 playback missing');
assert(media.includes('player.setMediaSource(new ProgressiveMediaSource.Factory(factory)'),
  'Growing cache is not connected to playback');
assert(media.indexOf('play(original)')<media.indexOf('private void copyThenPlay'),
  'Direct playback should be attempted first');
assert(media.includes('state.available=written;')&&media.includes('state.wake()'),
  'DataSource cannot see downloaded video bytes');
assert(growing.includes('state.available-position')&&growing.includes('state.finished'),
  'Growing file reader cannot return pages while receiving file');
const lower=main.indexOf('String lowerMediaName=name.toLowerCase(java.util.Locale.ROOT);');
const sniff=main.indexOf('String quickType = detectType(uri, name);');
assert(lower!==-1&&sniff!==-1&&lower<sniff,
  'MP4 must be opened without slow image/content sniffing');
const libFile=fs.readFileSync('app/src/main/java/com/openlocal/office/core/ReaderLibrary.java','utf8');
assert(libFile.includes('public static Listing stream('),'Incremental folder enumeration missing');
assert(libFile.includes('if(batch.length()>=(firstBatch?1:48))') &&
       libFile.includes('DocumentsContract.EXTRA_LOADING') &&
       libFile.includes('DocumentsContract.EXTRA_ERROR') &&
       libFile.includes('do{') &&
       libFile.includes('}while(items.moveToNext());'),
       'RoundSync must expose loading/errors and retain first streamed row');
assert(!libFile.includes('if(++total>=PAGE_SIZE)break;') ||
       main.includes('ReaderLibrary.stream(this,root,folder'),
       'Library still truncates folders at 500 files');
// The native folder reader is not the generic loader: it must reveal #editor.
assert(js.includes("editor.classList.remove('hidden');"),'Image folder editor stays hidden');
const folderPatch=fs.readFileSync('../hotfixes/apply-streamed-image-folders-20261031.py','utf8');
assert(folderPatch.includes("DocumentsContract.getTreeDocumentId(libraryTree)"),
  'Folder access still depends on transient listing state');
const style=fs.readFileSync('app/src/main/assets/style.css','utf8');
assert(style.includes('display:block!important;height:100%!important;min-height:0!important'),
  'Folder editor does not fill the reading viewport');
assert(media.includes('SCREEN_ORIENTATION_SENSOR_LANDSCAPE'),'Video must rotate to landscape');
assert(media.includes('SYSTEM_UI_FLAG_IMMERSIVE_STICKY'),'Video must hide system bars');
assert(media.includes('direction*10000L'),'Left/right double tap must skip ten seconds');
assert(media.includes('setShowRewindButton(false)')&&media.includes('setShowFastForwardButton(false)'),
  'Video must remove old ten-second buttons');
assert(media.includes('if(video)leaveVideoFullscreen()'),'Video must restore normal orientation');
const patchedFolder=fs.readFileSync('../hotfixes/apply-streamed-image-folders-20261031.py','utf8');
assert(patchedFolder.includes('private void openImageInFolder(String folderId,String selectedUri)'),
  'Native image collection selection missing');
assert(patchedFolder.includes('ReaderLibrary.stream(this,libraryTree,folderId'),
  'Cloud image folder must share the adaptive SAF query and immediate streaming path');
assert(patchedFolder.includes('@JavascriptInterface public void openImageInFolder'),
  'Image collection missing JavaScript bridge');
assert(lib.includes('bridge().openImageInFolder(currentFolder,item.uri)'),
  'Image tile still opens only one file');
assert(lib.includes("['all','All files'],['image','Images']"),
  'Dedicated Images filter missing');
assert(js.includes('fg-image-toolbar')&&!js.includes('requestAnimationFrame(()=>requestAnimationFrame(attach));\n   return;'),
  'Image viewer still shows EPUB controls');
assert(js.includes('imageMode=data.standalone'), 'Single-image smart-fit mode missing');
assert(style.includes('.fg-image-reader .fg-image-paged .fg-image-rotated .fg-folder-image'),
  'Landscape pictures still cannot use portrait screen efficiently');
assert(lib.includes('function showFileActions(item)')&&
       lib.includes('function fileSheet(title,note)')&&
       lib.includes('function fileAction(sheet,label,description,callback')&&
       lib.includes('function showSortMenu()')&&
       lib.includes('function operationResult(result)'),
       'Contextual file handlers are referenced but not defined');
assert(lib.includes('showFileActions(item)'), 'File-specific action sheet missing');
assert(lib.includes('sortDescending'), 'Sort order selection missing');
assert(lib.includes('closeFileActions'), 'Contextual file controls cannot close');
assert(lib.includes('operationResult'), 'File management result feedback missing');
assert(lib.includes('lastRender=Date.now()'), 'Cloud listing renders are being starved');
assert(lib.includes('imageReaderReady'), 'Image collection native handshake missing');
assert(main.includes('shareLibraryFile'), 'Android file sharing not connected');
assert(main.includes('openLibraryExternally'), 'Android external-open not connected');
assert(main.includes('renameLibraryFile'), 'SAF rename not connected');
assert(main.includes('deleteLibraryFile'), 'SAF delete not connected');
assert(main.includes('canManageLibraryFiles'), 'SAF write permission guard missing');
const streamBody=libFile.slice(libFile.indexOf('public static Listing stream('),
 libFile.indexOf('public static Listing list('));
assert(streamBody.includes('item.put("id",did)') &&
  !streamBody.includes('!supported('),
  'Unrecognized extensions must not be filtered out');
assert(main.includes('requestedFolder'), 'Stale cloud folder results not tagged');
const app=fs.readFileSync('app/src/main/assets/app.js','utf8');
assert(lib.includes("pendingFolderImageRead=item.id"),'Cloud image folder action must reuse SAF listing');
assert(lib.includes('if(state.live && scanning)'), 'Image collection must wait for cloud rows');
assert(lib.includes('state.siblings.push(entry)'), 'Later cloud images must join the active reader');
assert(lib.includes('if(!visible)return;'),'Hidden library must not rerender for every cloud batch');
assert(main.includes('COLLECTION_FIRST_BATCH_ms'), 'First cloud metadata batch latency not reported');
assert(main.includes('transferSafFile(')&&main.includes('fgTransferCancelled'),
  'Streaming copy/move and cancellation are missing');
assert(app.includes("doc.format==='xlsx'?1048576:100000"),
  'Full spreadsheet row navigation is still artificially capped');
assert(style.includes('body.fg-spreadsheet-reading .bar'),
  'Spreadsheet must avoid the Android status bar');
const remote=fs.readFileSync('app/src/main/assets/fg-remote-ui.js','utf8');
assert(js.includes("if(data?.type==='folderImages'||data?.type==='image')"),
  'Direct Koikatsu PNG must use dedicated image reader and never EPUB controls');
assert(js.includes("koikatsuCard:data.koikatsuCard===true"),
  'Native Koikatsu marker must carry through to image-specific 3D action');
assert(js.includes("window.AndroidBridge?.returnToExternalFile?.()"),
  'Files/RoundSync external image back navigation missing');
assert(main.includes('boolean returnToExternalFile()'),
  'Native Android external file origin handling missing');
assert(remote.includes('if(data.error&&!data.session)'),
  'Async Koikatsu pending sessions still terminate before rendering');
assert(remote.includes("frame.hidden=true"),
  'PC viewer still shows broken-image icon instead of loading state');
const fallbackSource=fs.readFileSync('../hotfixes/apply-image-fallback-20261031.py','utf8');
assert(js.includes("IMAGE_NATIVE_FALLBACK_REQUESTED")&&
  fallbackSource.includes("fgFallbackBitmap("),
  'Broken PNG image native fallback is missing');
assert(main.includes('verifyKoikatsuInBackground('),
  'Koikatsu card validation blocks PNG opening');
assert(remote.includes('getRemoteEndpoint?.()')&&
  remote.includes('showRemoteConfig()'),
  'PC remote endpoint settings missing');
assert(main.includes('setRemoteEndpoint(String value)')&&
  main.includes('remote.startsWith("https://")'),
  'Native PC transport is still hardcoded to ADB loopback');
assert(lib.includes('function hideForReader(){') &&
  lib.includes("if(document.body.classList.contains('fg-folder-reading'))hideForReader();"),
  'External images are still hidden behind welcome library overlay');
assert(js.includes("setImageViewing?.(true)") && js.includes("fg-koikatsu-float"),'Image reader must hide Android navigation and expose reachable Koikatsu action');
assert(style.includes("position:fixed!important;bottom:max(94px"),'Image controls remain behind Android system navigation');
assert(main.includes("setImageImmersiveInternal") && main.includes("WindowInsets.Type.navigationBars()"),'Native immersive reader is missing');
assert(libFile.includes("Storage provider omitted file ID or name"),'SAF error reporting is incomplete');
const tb=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
assert(tb.includes('AES/GCM/NoPadding')&&tb.includes('AndroidKeyStore'), 'TeraBox ndus cannot be stored in plaintext');
assert(tb.includes('listPage(')&&tb.includes('fileDetails(')&&tb.includes('save('),
  'Native direct TeraBox cloud browsing and download are incomplete');
assert(main.includes('listTeraboxNative(')&&main.includes('beginTbImages(')&&main.includes('fgTbImage('),
  'Direct TeraBox browser is not connected to image reader');
assert(lib.includes('getTeraboxConfigured?.()')&&lib.includes('appendTeraboxImageCollectionChunk'),
  'Native cloud account selector or progressive image loading missing');
assert(js.includes('verifyCurrentKoikatsuCard')&&js.includes("koikatsu.textContent='Open 3D'"),
  'Native 3D card verification cannot be initiated from image reader');
console.log('PASS: image folder visible, streamed pages, direct MP4 and growing cache byte reads.');

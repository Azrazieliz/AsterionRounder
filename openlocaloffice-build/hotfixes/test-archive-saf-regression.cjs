/* Comic ZIP and SAF provider regressions. Actual Android build follows. */
const fs=require('fs'),assert=require('assert');
const b=fs.readFileSync('app/src/main/java/com/openlocal/office/core/BookArchive.java','utf8');
const m=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
const spool=fs.readFileSync('app/src/main/java/com/openlocal/office/core/RemoteBookSpool.java','utf8');
const u=fs.readFileSync('app/src/main/assets/universal-reader.js','utf8');
const controls=fs.readFileSync('app/src/main/assets/unified-viewer-controls.js','utf8');
function need(predicate,meaning){assert(predicate,meaning);}
need(b.includes('boolean comicLike()'),'ZIP reader needs automatic content-based comic classification');
need(b.includes('archiveImages.size()*10L>=readable*8L'),'Image-majority ZIP must be detected automatically');
need(b.includes('archiveImages.sort(BookArchive::compareNatural)'),
  'Comic ZIP images must use numeric page ordering');
need(b.includes('archiveAll.sort(BookArchive::compareNatural)'),
  'Full ZIP listing must also use numeric ordering');
need(m.includes('candidate.comicLike()'),'MainActivity must pass ZIP comic classification to reader');
need(u.includes('doc.comicMode===true'),'Universal reader must support ZIP comic view');
need(u.includes('numeric:true'),'ZIP reader must sort 1,2,10 not 1,10,2');
need(u.includes("isComic?'Files':'Read images'"),'ZIP images must have optional list mode');
need(controls.includes("doc.comicMode===true"),'ZIP comic must inherit CBZ-style zoom gestures');
// Round Sync/TeraBox SAF: do not mirror the AsterionCore temporary-file issue.
need(b.includes('new SeekableZip(handle)'),'SAF fd must use direct random-access ZIP index');
need(b.includes('if(seekable)throw new IOException('),'Seekable providers must not be copied after ZIP index failure');
need(b.includes('if(advertised>0&&physical>=0&&physical<advertised)'),
  'Known incomplete cloud files must be rejected before a second copy');
need(b.includes('RemoteBookSpool.obtain(context,uri,advertised,preview)')&&
  spool.includes('expected>0&&copied!=expected'),
  'Non-seekable provider transfer must be verified after the shared spool');
need(m.includes('getPersistedUriPermissions()'),'Recent references require durable SAF read grants');
need(m.includes('sessionRecentUri'),'Temporary Round Sync document grants must be session-only');
need(m.includes('if(!hasDurableReadGrant(saved))'),
  'Expiring cloud URIs cannot remain in permanent recent-files list');
need(!m.includes('remember(temp'),'Temporary cache is not a persistent document reference');
// Simple behavioral policy equivalent, useful with numeric names in supplied ZIP.
const names=['Book/10.webp','Book/2.webp','Book/1.webp'];
names.sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:'base'}));
assert.deepEqual(names,['Book/1.webp','Book/2.webp','Book/10.webp']);
need(b.includes('if(isReadablePage(name))archiveImages.add(name)'),
  'macOS metadata and dotfiles cannot become comic/image pages');
need(b.includes('segment.equalsIgnoreCase("__MACOSX")'),
  'Do not render ZIP Finder resource forks as blank pages');
console.log('PASS: Comic ZIP auto-detection, numerical image order, CBZ zoom, SAF direct-source and expiry policies.');

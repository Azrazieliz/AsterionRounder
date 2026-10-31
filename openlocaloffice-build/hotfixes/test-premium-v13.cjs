const fs=require('fs'),assert=require('assert');
const root='app/src/main/',path=root+'java/com/openlocal/office/';
const read=p=>fs.readFileSync(p,'utf8');
const main=read(path+'MainActivity.java');
const zip=read(path+'core/SeekableZip.java');
const archive=read(path+'core/BookArchive.java');
const lib=read(path+'core/ReaderLibrary.java');
const cover=read(path+'core/ReaderCovers.java');
const cards=read(path+'core/KoikatsuCards.java');
const ui=read(root+'assets/premium-library.js');
const css=read(root+'assets/style.css');
const book=read(root+'assets/universal-reader.js');
function need(expr,msg){assert(expr,msg);}
need(zip.includes('Os.pread(fd'),'Random-access ZIP should read directly from provider FD');
need(zip.includes('ZIP64_END_SIG')&&zip.includes('ZIP64_LOC_SIG'),
     'ZIP64 support required for multi-gigabyte files');
need(zip.includes('new Inflater(true)'),'Deflated ZIP pages must stream independently');
need(!zip.includes('new byte[(int)length'),'Never load multi-GB archives into one array');
need(archive.includes('new SeekableZip(handle)')&&
     !archive.includes('new ZipFile("/proc'),'Avoid repeat SAF opening and redundant copies');
need(archive.includes('if(seekable)throw new IOException('),
     'Do not fall back to huge duplicate copy when cloud descriptor is seekable');
need(lib.includes('DocumentsContract.buildChildDocumentsUriUsingTree'),
     'User-chosen folder must enumerate using SAF');
need(lib.includes('PAGE_SIZE=500'),'Bounded collection directory paging');
need(cover.includes('new Semaphore(2)'),'Only two cover decoders concurrently');
need(cover.includes('BitmapFactory.Options')&&cover.includes('inSampleSize'),
     'Book covers must sample down to thumbnail dimensions');
need(cover.includes('isArchive(name)&&size>64L*1024*1024&&')&&
     cover.includes('!isExpensiveCloudCover(source,name)&&!seekable')&&
     cover.includes('final long limit=4L*1024*1024'),
     'Cloud archive cover requests must be bounded, never spool full 2 GB books');
need(main.includes('openLibraryFile(String value)'),'Book cover must open original URI');
need(main.includes('allowedLibraryUris.contains(value)'),'Only approved library items may open');
need(main.includes('ReaderCovers.open('),'Actual illustration covers must be served offline');
need(cards.includes('KoiKatuChara')&&cards.includes('IEND'),
     'Koikatsu PNG must be identified by appended card payload, not guessed by name');
need(main.includes('openKoikatsu3d()')&&main.includes('REQ_KOIKATSU_PREVIEW'),
     'Card must allow picking real converted Blender preview and persist its URI');
need(ui.includes('fg-lib-cover-image')&&ui.includes('img')&&ui.includes('FileGestionerLibrary'),
     'Premium library must prioritize real thumbnail art');
need(ui.includes('fg-lib-filter')&&ui.includes('fg-lib-search'),
     'Library must include polished filter/search controls');
need(css.includes('.fg-lib-cover')&&css.includes('.fg-lib-grid'),
     'Cover grid styling required');
need(book.includes('koikatsuCard===true'),
     'Character PNG needs a visible 3D preview affordance');
console.log('PASS: fast seekable ZIP/ZIP64, lazy cover cache, SAF library, Koikatsu PNG→real 3D pairing and polished visual reader.');

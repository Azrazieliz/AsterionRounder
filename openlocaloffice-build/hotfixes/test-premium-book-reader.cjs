/* EPUB structural and large-file reader regression gates.
 * Integration is compiled again by Android Gradle with the actual platform.
 */
const fs=require('fs'),assert=require('assert');
const j=fs.readFileSync('app/src/main/assets/epub-reader.js','utf8');
const reader=fs.readFileSync('app/src/main/assets/universal-reader.js','utf8');
const main=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
const book=fs.readFileSync('app/src/main/java/com/openlocal/office/core/BookArchive.java','utf8');
const stream=fs.readFileSync('app/src/main/java/com/openlocal/office/core/StreamedText.java','utf8');
const spool=fs.readFileSync('app/src/main/java/com/openlocal/office/core/RemoteBookSpool.java','utf8');
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const style=fs.readFileSync('app/src/main/assets/style.css','utf8');
function need(value,message){assert(value,message);}
need(book.includes('getElementsByTagNameNS("*","itemref")'),'Must use EPUB spine order, not sorted XHTML names');
need(book.includes('META-INF/container.xml'),'Must locate EPUB package through container.xml');
need(book.includes('get("idref")')===false&&book.includes('field(item,"idref")'),
     'Spine items need idref lookup');
need(book.includes('new SeekableZip(handle)'),'Must index seekable SAF ZIP without reopening or copying file');
need(book.includes('RemoteBookSpool.obtain(context,uri,advertised,preview)')&&
     spool.includes('BufferedOutputStream(')&&spool.includes('new FileOutputStream(pending)'),
     'Nonseekable provider must use a reusable, serialized disk spool');
need(spool.includes('synchronized(lock)')&&spool.includes('CLOUD_SPOOL_CACHE_HIT'),
     'Repeated opens must reuse the successful download and avoid concurrent copies');
need(book.includes('MAX_CHAPTER_BYTES'),'Large book chunks must remain bounded');
need(book.includes('WebResourceResponse response('),'Illustrations must stream individually through WebView');
need(!book.includes('new byte[(int)'),'Book may never be cast to an in-memory int array');
need(main.indexOf('if ("epub".equals(quickType))')<main.indexOf('if (size > MAX_FILE_BYTES)'),
     'EPUB opening must precede the 80MiB EDITOR cap');
need(main.indexOf('if ("cbz".equals(quickType)||"zip".equals(quickType))')<
     main.indexOf('if (size > MAX_FILE_BYTES)'),'Comics/archive readers must stream');
need(main.indexOf('if(isImageType(quickType))')<
     main.indexOf('if (size > MAX_FILE_BYTES)'),'Large standalone images must stream');
need(main.includes('new StreamedText(this,uri)'),'Huge text documents must have incremental read');
need(stream.includes('char[] chars=new char[count]'),'Text stream must allocate only requested window');
need(j.includes('new DOMParser()'),'EPUB should render XHTML semantics');
need(j.includes('target.loading=')&&j.includes('lazy'),'Illustrations must be lazy');
need(j.includes('original')&&j.includes('fg-book-article'),'Original chapter paragraphs must render as book text');
need(j.includes('settings.theme')&&j.includes('settings.font')&&
     j.includes('settings.line')&&j.includes('settings.margin'),
     'Reading personalization must cover theme/font/line/margins');
need(j.includes('localStorage.setItem(key')&&j.includes('Bookmark reading position'),
     'Persistent per-book preferences and bookmark required');
need(j.includes('if(!allow.has(tag))')&&j.includes("includes(tag)")&&
     j.includes('location.origin==='),'External executable content and media must not load');
need(style.includes('.fg-book{')&&style.includes('fg-book-theme-paper'),
     'Night and Paper reading themes required');
need(html.indexOf('unified-viewer-controls.js')<html.indexOf('epub-reader.js'),
     'EPUB wrapper must attach after shared UI control wrapper');
need(reader.includes("else if(d.type==='streamText')streamText()"),
     'Large TXT/MD/code must display a streaming surface');
need(reader.includes('doc.streamed&&doc.url'),'Large standalone images must avoid Base64 readAll');
need(reader.includes('getArchiveImageUrl'),'Large CBZ illustrations must use streamed URLs');
console.log('PASS: EPUB spine, lazy assets, book personalization, file-wide cap bypass, image/archive/text streaming.');

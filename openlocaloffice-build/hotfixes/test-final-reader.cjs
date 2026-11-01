/* Release gate for real Android EPUB parser, covers and navigation.
 * Dynamic tests: Android emulator must also log FG_BOOK EPUB_READY and BACK_TO_LIBRARY.
 */
const fs=require('fs'),assert=require('assert');
const read=(path)=>fs.readFileSync(path,'utf8');
const book=read('app/src/main/java/com/openlocal/office/core/BookArchive.java');
const covers=read('app/src/main/java/com/openlocal/office/core/ReaderCovers.java');
const main=read('app/src/main/java/com/openlocal/office/MainActivity.java');
const library=read('app/src/main/assets/premium-library.js');
const fixture=read('../hotfixes/create-large-epub-fixture.py');
assert(!book.includes('f.setFeature("http://apache.org/xml/features/disallow-doctype-decl",true)'),
 'Do not call an unsupported Android DocumentBuilderFactory parser feature');
assert(book.includes('parser.setEntityResolver('),'External XML resolution must be blocked');
assert(book.includes('DOCTYPE'),'Standard EPUB2 external DTD must not crash parsing');
assert(book.includes('cover-image')&&book.includes('preferredCoverName'),
 'Actual EPUB2/EPUB3 cover metadata must be supported');
assert(covers.includes('book.preferredCover()'),
 'Bookshelf must extract cover or first actual ZIP/CBZ page');
assert(book.includes('archiveImages.sort(BookArchive::compareNatural)'),
 'Archive preview must honor numerical first-image order');
assert(main.includes('onBackPressed()')&&main.includes('evaluateJavascript('),
 'System navigation bar Back must connect to document/library state');
assert(library.includes('handleBack:handleAndroidBack'),'Library navigation method missing');
assert(library.includes('drawer.classList.add('),'Back should close reading appearance first');
assert(library.includes('BACK_TO_LIBRARY'),'Emulator must log library navigation');
assert(fixture.includes('<!DOCTYPE package PUBLIC'),'EPUB runtime regression must include the failure trigger');
const reader=read('app/src/main/assets/epub-reader.js');
assert(book.includes('application/x-dtbncx+xml')&&book.includes('navPoint'),
  'EPUB2 NCX chapter names must be resolved to the actual spine');
assert(!reader.includes("document.getElementById('openBtn')?.click()"),
  'EPUB top-left Back must not open the file picker');
assert(reader.includes('Return to library'),'EPUB toolbar should return to library');
console.log('PASS: Android-safe EPUB XML, EPUB2 NCX chapters, real covers and Back-to-library navigation');

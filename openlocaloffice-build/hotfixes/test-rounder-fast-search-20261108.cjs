#!/usr/bin/env node
'use strict';
const fs=require('fs'),assert=require('assert');
const java=fs.readFileSync('app/src/main/java/com/openlocal/office/core/FgSearchIndex.java','utf8');
const main=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
const ui=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
function contains(text,value,msg){assert(text.includes(value),msg||value);}
for(const term of [
 'extends SQLiteOpenHelper','CREATE TABLE files','CREATE TABLE pending',
 'DocumentsContract.buildChildDocumentsUriUsingTree','getTreeDocumentId(tree)',
 'pending(root,generation,doc,path)','INSERT OR REPLACE INTO files',
 'SELECT doc,name,mime,kind,folder,size,modified,parent_path FROM files',
 'AND lookup LIKE ?', 'PAGE+1', 'contains(Uri tree,String id)',
 'setWriteAheadLoggingEnabled(true)',
 'complete.add(root)', 'root,generation,doc'
])contains(java,term,'Persistent index contract missing: '+term);
for(const term of [
 '@JavascriptInterface public void searchLibraryIndex(',
 '@JavascriptInterface public void refreshLibraryIndex()',
 '@JavascriptInterface public void openIndexedFile(String documentId)',
 'getPersistedUriPermissions()','fgSearch().contains(root,documentId)',
 'fgDirectoryVersion.incrementAndGet()'
])contains(main,term,'Native SAF bridge missing: '+term);
for(const term of [
 'localIndexedMode()', 'renderIndexedResults()', 'receiveIndexedSearch(data)',
 'indexProgress(data)','bridge()?.searchLibraryIndex?.(',
 'bridge()?.openIndexedFile?.(item.id)',
 'Search all subfolders','scheduleIndexSearch(0,130)',
 'item.searchPath','if(localIndexedMode())return;'
])contains(ui,term,'Indexed search UI missing: '+term);
contains(gradle,'versionCode = 37');
contains(gradle,'versionName = "0.15.15"');
// Search must never start an entire SAF directory scan for every keystroke.
const event=ui.slice(ui.indexOf("search.addEventListener('input'"),ui.indexOf('const homeNav='));
assert(!event.includes('listLibrary?.('),'Search input triggered a directory traversal');
// Results from below the current folder must open via the authorized indexed document ID.
const open=ui.slice(ui.indexOf('function openBook(item)'),ui.indexOf('function card('));
assert(open.indexOf('if(item.indexedSearch')<open.indexOf('if(item.folder)'),
  'Search results must bypass current-folder open logic');
console.log('ROUNDERS_SEARCH_CONTRACT_OK: persisted SAF index, recursive roots, native query, indexed opens, 0 query-time rescans');

#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const base='app/src/main/';
const code=fs.readFileSync(base+'java/com/openlocal/office/core/FgTeraboxSearchIndex.java','utf8');
const main=fs.readFileSync(base+'java/com/openlocal/office/MainActivity.java','utf8');
const ui=fs.readFileSync(base+'assets/premium-library.js','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
for(const v of [
 'extends SQLiteOpenHelper','"rounder-terabox-search-v1.db"',
 'CREATE TABLE accounts','CREATE TABLE objects','CREATE TABLE pending',
 'scope TEXT NOT NULL','cloud.listPageCached(task.path,task.page)',
 'FgTeraboxClient.mapEntry(raw)','while((task=next(db,scope,generation))!=null)',
 'UPDATE pending SET page=?','DELETE FROM pending WHERE scope=?',
 'SELECT o.path,o.name,o.kind,o.folder,o.size,o.modified,o.parent,o.listing_page',
 'AND o.needle LIKE ?','LIMIT ? OFFSET ?','"searchPath"','Uri.encode(path)',
 'cloud.metadataScope()','String.valueOf(e.getMessage())',
 'LEFT JOIN preview_marks mark','o.preview_missing',
 'CREATE TABLE preview_marks','FgTeraboxClient.previewUnavailable(raw)',
 'return value.replace(','public void clear()'
])assert(code.includes(v),'Cloud index lacks '+v);
for(const v of [
 'searchTeraboxIndex(','refreshTeraboxIndex()','startTeraboxIndex()',
 'getTeraboxSearchScope()','stopTeraboxListing()','fgCloudIndex().ensure(false)',
 'fgCloudIndex().clear()'
])assert(main.includes(v),'Native bridge lacks '+v);
for(const v of [
 'function cloudIndexedMode(){return cloudMode&&!!phrase.trim();}',
 'function indexedMode(){return localIndexedMode()||cloudIndexedMode();}',
 'bridge()?.searchTeraboxIndex?.(phrase,filter,indexedOffset,token)',
 'bridge()?.startTeraboxIndex?.()',
 'bridge()?.refreshTeraboxIndex?.()',
 'bridge()?.stopTeraboxListing?.()',
 'if(item.indexedSearch&&cloudMode)',
 'bridge()?.openTeraboxFile?.(item.path,item.name)',
 "search.placeholder=cloudMode?'Search all TeraBox folders':'Search all subfolders'",
 "const old=indexedMode()",
 "if(indexedMode())return;"
])assert(ui.includes(v),'Cloud search UI lacks '+v);
const handler=ui.slice(ui.indexOf("search.addEventListener('input'"),ui.indexOf("const homeNav="));
assert(!handler.includes('listTerabox?.('),'Typing search must not trigger cloud rescans');
assert.match(gradle,/versionCode\s*=\s*38/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.16"/);
console.log('ROUNDERS_TERABOX_SEARCH_CONTRACT_OK: account-scope, durable paged traversal, global query, authorized provider open, no query-time cloud crawl');

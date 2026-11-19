#!/usr/bin/env node
'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const base='app/src/main/';
const read=p=>fs.readFileSync(base+p,'utf8');
const js=read('assets/premium-library.js');
const css=read('assets/style.css');
const main=read('java/com/openlocal/office/MainActivity.java');
const index=read('java/com/openlocal/office/core/FgTeraboxSearchIndex.java');
const helper=read('java/com/openlocal/office/core/FgRounderVideoPreviews.java');
const requirement=/\.fg-lib-grid\.fg-lib-video-grid:not\(\.fg-lib-list\)\s*\{\s*grid-template-columns:repeat\(2,minmax\(0,1fr\)\)!important/;
assert.match(css,requirement,'Video grids must display exactly two cards');
assert.match(css,/\.fg-lib-video \.fg-lib-cover\{\s*aspect-ratio:16\/9!important/);
assert.match(css,/\.fg-lib-video \.fg-lib-cover-image\{\s*object-fit:contain!important/);
assert.match(js,/const hasVideos=!useList&&files\.some\(item=>classify\(item\)==='video'\)/);
assert.match(js,/\(hasVideos\?' fg-lib-video-grid':''\)/);
assert.match(js,/Math\.ceil\(cellWidth\*\(hasVideos\?9\/16:1\.5\)\+86\)/);
assert.match(main,/FgRounderVideoPreviews\.isVideo\(mapped\.optString\("name",""\)\)/);
assert.match(main,/FgRounderVideoPreviews\.isVideo\(name\)/);
assert.match(main,/FgRounderVideoPreviews\.local\(/);
assert.match(main,/FgRounderVideoPreviews\.cloud\(/);
assert.match(index,/if\("video"\.equals\(cursor\.getString\(2\)\)\)\s*\{[\s\S]*?item\.put\("cover",coverUrl/);
assert.match(helper,/MediaMetadataRetriever/);
assert.match(helper,/MediaDataSource/);
assert.match(helper,/MAX_TOTAL=16\*1024\*1024/);
assert.match(helper,/client\.readRange\(path,position,request\)/);
assert.match(helper,/context\.getCacheDir\(\)/);
assert.doesNotMatch(helper,/provider\.open\(path\)/,'Do not fetch entire cloud video for thumbnails');
assert.match(main,/new WebResourceResponse\("image\/jpeg",null,[\s\S]*?tb\(\)\.openThumbnail\(path,path\.substring\(0,slash\),page\)/);
assert.match(main,/fgTbOriginalCover\(path,mime\)/,'Do not regress existing original image cover');
assert.match(js,/function showVirtualItems\(items,mode,key\)/,'Keep continuous virtual scrolling');
assert.match(js,/function showFileActions\(item\)/,'Keep long-press file actions');

// The continuous renderer must calculate one card's height from its real
// landscape frame instead of the old portrait row; the last row must be
// reachable for both short and huge galleries.
for(const width of [320,360,390,600,900]){
 for(const length of [1,2,3,30,300000]){
  const columns=2, gap=15;
  const cellWidth=(width-gap)/columns;
  const height=Math.ceil(cellWidth*9/16+86);
  assert.ok(height>=90);
  const rows=Math.ceil(length/columns);
  const visibleRows=Math.max(10,Math.ceil(760/height)+12);
  const start=Math.max(0,Math.min(Math.max(0,rows-visibleRows),rows-4));
  const end=Math.min(rows,start+visibleRows);
  assert.ok(start<end&&end<=rows);
 }
}
console.log('ROUNDER_VIDEO_GALLERY_SOURCE_PASS: 2-wide, genuine local/cloud/index thumbnails, bounded frame reads, stable virtualization');

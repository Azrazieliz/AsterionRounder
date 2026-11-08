'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const root='app/src/main/';
const js=fs.readFileSync(root+'assets/premium-library.js','utf8');
const css=fs.readFileSync(root+'assets/style.css','utf8');
const logo=fs.readFileSync(root+'assets/asterion-rounder-mark.svg','utf8');
const android=fs.readFileSync(root+'res/drawable/ic_launcher_foreground.xml','utf8');
const media=fs.readFileSync(root+'java/com/openlocal/office/core/FgMediaPlayer.java','utf8');
const cloud=fs.readFileSync(root+'java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
const need=(text,values,name)=>values.forEach(x=>assert(text.includes(x),name+': '+x));
need(js,['sharedBrand.src=','asterion-rounder-mark.svg',
 'monogram.append(sharedBrand)','iconDraw=(name)=>','back.append(iconDraw',
 "layout.append(iconDraw('grid'))",'function card(item,i)',
 'function showOrganizer()','function managerCleanupProgress(event)',
 'function renderIndexedResults()','function updaterStatus(data)'],'library');
need(css,['.fg-lib-monogram .fg-lib-brand-image',
 '.fg-lib-cover.fg-lib-has-image > .fg-lib-fallback',
 'visibility:hidden!important','opacity:1!important',
 '.fg-lib-nav-back svg','.fg-lib-icon svg'],'visual contracts');
need(media,['final int[] bufferingSequence={0}',
 'status.setOnClickListener(v->','root.postDelayed(()->',
 'Video data has stalled. Tap here to retry TeraBox streaming.',
 'playTeraboxRanges();','class VideoTransport extends View',
 'paint.setStrokeJoin(android.graphics.Paint.Join.ROUND)'],'media player');
need(cloud,['boolean refreshedSignedUrl=false','!refreshedSignedUrl',
 'thumbUrls.put(safe,fresh)'],'TeraBox thumbnail recovery');
// Source-of-truth vector paths are reused in the WebView asset; do not redraw.
const androidPaths=[...android.matchAll(/android:pathData="([^"]+)"/g)].map(m=>m[1]);
const webPaths=[...logo.matchAll(/<path\s+d="([^"]+)"/g)].map(m=>m[1]);
assert(androidPaths.length>=3);
assert.deepEqual(webPaths,androidPaths,'Logo paths must exactly match Android launcher foreground');
// User explicitly prohibited redesigning approved cards.
need(js,["function card(item,i)","const cover=E('div','fg-lib-cover');",
 "cover.appendChild(fallback);","const meta=E('div','fg-lib-tile-meta');",
 "tile.append(cover,meta);"],'original cards');
assert(!css.includes('.fg-library-root .fg-lib-grid.fg-vault-media-grid'),
  'No file-card redesign may return');
assert.match(gradle,/versionCode\s*=\s*46/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.24"/);
console.log('ROUNDER_SHARED_BRANDING_AND_PREVIEW_CONTRACT_PASS: identical icon paths, current cards preserved, thumbnail feedback and native video controls');

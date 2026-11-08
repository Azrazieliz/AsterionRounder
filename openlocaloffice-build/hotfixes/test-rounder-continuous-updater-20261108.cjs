#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base='app/src/main/';
const ui=fs.readFileSync(base+'assets/premium-library.js','utf8');
const css=fs.readFileSync(base+'assets/style.css','utf8');
const main=fs.readFileSync(base+'java/com/openlocal/office/MainActivity.java','utf8');
const updater=fs.readFileSync(base+'java/com/openlocal/office/core/FgRounderUpdater.java','utf8');
const provider=fs.readFileSync(base+'java/com/openlocal/office/core/FgRounderUpdateProvider.java','utf8');
const manifest=fs.readFileSync(base+'AndroidManifest.xml','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
const need=(src,v)=>assert(src.includes(v),'Required implementation missing: '+v);
for(const field of [
 'function showVirtualItems(items,mode,key)',
 'function folderCard(item)',
 'function handleContinuousScroll()',
 'virtualTop.style.height=',
 'virtualBottom.style.height=',
 'window.getComputedStyle(deck).gridTemplateColumns',
 'showVirtualItems(indexedResults',
 'showVirtualItems(shown',
 'indexedResults.concat(next)',
 'scheduleIndexSearch(indexedResults.length,0)',
 'body.addEventListener(\'scroll\',handleContinuousScroll',
 'function updaterStatus(data)',
 'function showUpdater()',
 'function renderUpdater()',
 'bridge()?.installRounderUpdate?.()',
 'bridge()?.checkRounderUpdate?.()',
 "actions.append(openBtn,organizeBtn,updateBtn,settingsBtn)",
 "body.append(toolbar,filters,loading,deck,empty,footer)",
 'document.body.append(updaterPanel)'
])need(ui,field);
assert(!ui.includes("const pages=Math.ceil(shown.length/PAGE);"),
  'Page-count calculation remains in UI');
assert(!ui.includes("const prev=b('‹ Previous'"),
  'Previous/Next page buttons must be removed');
assert(!ui.includes("const input=E('input','fg-lib-page-number')"),
  'Visible page number input must be removed');
assert(!ui.includes("nav.append(prev,E('span','','Page '"),
  'Indexed search pager must be removed');
assert(!ui.includes('actions.append(openBtn,collectionBtn,tbBtn)'),
  'Remove obsolete 3-way storage navigation');
assert(!ui.includes('body.append(premiumIntro,toolbar,filters'),
  'Do not show duplicated giant collection hero');
need(css,'.fg-vault-folder-grid');
need(css,'.fg-vault-updater-backdrop');
need(css,'.fg-lib-header');
need(css,'.fg-vault-spacer');
for(const item of [
 'public void check()', 'public void install()',
 'private long verifiedCode(File file)',
 'PackageManager.GET_SIGNING_CERTIFICATES',
 'activity.getPackageName().equals(apk.packageName)',
 'Arrays.equals(expected,actual)',
 'update<=current',
 'APK SHA-256 mismatch',
 'asHttps(', 'file-gestioner-release-[0-9]+',
 'release-assets.githubusercontent.com',
 'Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES',
 'Intent.ACTION_VIEW',
 'FLAG_GRANT_READ_URI_PERMISSION',
 'FgRounderUpdateProvider.APK'
])need(updater,item);
need(provider,'MODE_READ_ONLY');
need(provider,'read only');
need(provider,'getCacheDir()');
need(provider,'public final class FgRounderUpdateProvider');
need(main,'@JavascriptInterface public void checkRounderUpdate()');
need(main,'@JavascriptInterface public void installRounderUpdate()');
need(manifest,'com.openlocal.office.rounderupdates');
need(manifest,'android.permission.REQUEST_INSTALL_PACKAGES');
need(manifest,'android:exported="false"');
assert.match(gradle,/versionCode\s*=\s*41/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.19"/);
console.log('ROUNDER_CONTINUOUS_UPDATE_CONTRACT_OK: no numeric pages, bounded DOM, source thumbnails, safe Android in-app updates');

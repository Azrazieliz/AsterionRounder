#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const base='app/src/main/';
const ui=fs.readFileSync(base+'assets/premium-library.js','utf8');
const css=fs.readFileSync(base+'assets/style.css','utf8');
const native=fs.readFileSync(base+'java/com/openlocal/office/MainActivity.java','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
for(const marker of [
  'fallback.append(E(\'span\',\'fg-lib-fallback-glyph\',icon(c)),',
  "E('strong','fg-lib-fallback-title',item.title)",
  'virtualFolders=[];', 'virtualFiles=items;',
  'drawFolderRail([],mode);','const useList=list;',
  'const rowHeight=useList?124:Math.ceil(cellWidth*1.5+86);',
  'virtualTop.style.height=', 'virtualBottom.style.height=',
  "function handleContinuousScroll()",
  "function showOrganizer()",
  "function updaterStatus(data)",
  "function showUpdater()",
  "function folderPreviews(data)",
  "function receiveIndexedSearch(data)",
  "bridge()?.installRounderUpdate?.()",
  "bridge()?.searchTeraboxIndex?.("
])assert(ui.includes(marker),'Missing functionality/style: '+marker);
for(const marker of [
  'Asterion Rounder: restored original library UI.',
  '.fg-lib-header{', '.fg-lib-grid{', '.fg-lib-cover{',
  '.fg-org-backdrop{','.fg-org-source-settings{',
  '.fg-vault-updater-backdrop{',
  '.fg-library-root .fg-vault-spacer{display:block!important'
])assert(css.includes(marker),'Missing baseline/function CSS: '+marker);
assert(!css.includes('/* Atlas × Obsidian cloud-first Rounder 0.15.17.'),
       'Previous rejected Atlas/Obsidian redesign must not be retained');
assert(!css.includes('/* Rounder v0.15.19 — actual content-first'),
       'Previous rejected compact redesign must not be retained');
assert(!css.includes('.fg-library-root .fg-vault-spacer{display:none'),
       'Virtual spacer must remain visible to support continuous scroll');
assert(!ui.includes("const pages=Math.ceil(shown.length/PAGE);"),'Numeric pagination reintroduced');
assert(!ui.includes("const prev=b('‹ Previous'"),'Old page navigation reintroduced');
assert(!ui.includes('actions.append(openBtn,collectionBtn,tbBtn)'),
       'Do not restore removed collection source navigation');
assert(native.includes('@JavascriptInterface public void organizerApply(String json)'));
assert(native.includes('@JavascriptInterface public void checkRounderUpdate()'));
assert.match(gradle,/versionCode\s*=\s*43/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.21"/);
console.log('ROUNDER_ORIGINAL_VISUAL_RESTORED: earlier UI, native cloud/organizer/updater kept, continuous scroll intact');

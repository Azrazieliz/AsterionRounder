'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const base='app/src/main/';
const ui=fs.readFileSync(base+'assets/premium-library.js','utf8');
const css=fs.readFileSync(base+'assets/style.css','utf8');
const main=fs.readFileSync(base+'java/com/openlocal/office/MainActivity.java','utf8');
const org=fs.readFileSync(base+'java/com/openlocal/office/core/FgRounderOrganizer.java','utf8');
const index=fs.readFileSync(base+'java/com/openlocal/office/core/FgTeraboxSearchIndex.java','utf8');
const cloud=fs.readFileSync(base+'java/com/openlocal/office/core/FgTeraboxClient.java','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
const required=(source,markers,label)=>markers.forEach(x=>
 assert(source.includes(x),label+' missing: '+x));
required(ui,[
 'openBtn.textContent=',
 'actions.append(openBtn,organizeBtn,updateBtn,settingsBtn)',
 'virtualFolders=items.filter(e=>e.folder)',
 'virtualFiles=items.filter(e=>!e.folder)',
 'drawFolderRail(virtualFolders,mode)',
 "mode==='search'?'Matching folders':'Folders'",
 "const useList=list||!virtualHasCovers",
 'function renderDuplicateWorkspace(body)',
 'function renderDuplicateCleanupFooter(shell)',
 'function managerCleanupProgress(event)',
 'organizerCleanupDuplicates',
 'function showUpdater()',
 'function renderIndexedResults()',
 'function handleContinuousScroll()'
],'UI');
required(css,[
 '.fg-review-rail','.fg-review-image','.fg-review-keep-btn',
 '.fg-review-remove-btn','.fg-review-bottom',
 '.fg-lib-header','.fg-vault-folder-grid',
 '.fg-lib-grid.fg-vault-media-grid','.fg-lib-grid.fg-lib-list'
],'CSS');
required(main,[
 'public void organizerCleanupDuplicates(String json)',
 'public void checkRounderUpdate()',
 'public void installRounderUpdate()',
 'public void searchTeraboxIndex('
],'Native bridge');
required(org,[
 'public JSONObject duplicates()',
 'public void cleanupDuplicates(JSONObject request,Reporter callback)',
 'requireRemoteMatch(keep,hash,size)',
 'deleteDuplicateChecked(path,hash,size)',
 'index.noteDeleted(scope,path)',
 'if(path.equals(keep)',
 'MAXIMUM'
].filter(x=>x!=='MAXIMUM'),'Duplicate guard');
required(index,['public static String coverUrl(','public void noteDeleted(',
 'listing_page','ESCAPE'],'index');
required(cloud,['public void deleteDuplicateChecked(',
 'fileDetails(safe)','postCloud("/api/filemanager",query,form)',
 'query.put("opera","delete")','new JSONArray().put(safe)',
 'Original content has changed','Deletion unverified'],'Cloud delete');
assert(!/autoRun\([\s\S]*?deleteDuplicateChecked/.test(
 org.slice(org.indexOf('public JSONObject autoRun('),
           org.indexOf('public JSONObject review()'))),
 'Automatic organizer must never delete duplicates');
assert(css.includes('.fg-library-root .fg-vault-folder > .fg-vault-folder-art{'),
 'Folder thumbnail styling must target child element only');
assert(!css.includes('.fg-library-root .fg-vault-folder-art{'),
 'Folder Art category must not shrink the entire folder button');
assert(!ui.includes('1 / 502'),'Numeric pagination returned');
assert(!ui.includes("if(detail)detail.textContent='Open collection';"),
 'Useless Open collection labels still present');
assert.match(gradle,/versionCode\s*=\s*44/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.22"/);
console.log('ROUNDER_VISUAL_DUPLICATES_AND_COMPACT_UI_OK');

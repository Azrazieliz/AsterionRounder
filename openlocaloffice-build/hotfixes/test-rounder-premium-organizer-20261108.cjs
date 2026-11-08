#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const main=fs.readFileSync('app/src/main/java/com/openlocal/office/MainActivity.java','utf8');
const root='app/src/main/java/com/openlocal/office/core/';
const idx=fs.readFileSync(root+'FgTeraboxSearchIndex.java','utf8');
const client=fs.readFileSync(root+'FgTeraboxClient.java','utf8');
const engine=fs.readFileSync(root+'FgRounderOrganizer.java','utf8');
const job=fs.readFileSync(root+'FgRounderOrganizeJob.java','utf8');
const ui=fs.readFileSync('app/src/main/assets/premium-library.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');
const gradle=fs.readFileSync('app/build.gradle.kts','utf8');
function has(src,items){for(const item of items)assert(src.includes(item),'Missing contract: '+item);}
has(engine,['public JSONObject duplicates()','GROUP BY checksum,size',
 'GROUP BY needle,size','matching cloud MD5 and size',
 'same filename and size (unverified)','public JSONObject review()',
 'public JSONObject scanIncoming(boolean quick)','public JSONObject autoRun(',
 'public void apply(JSONArray paths','setAutoEnabled(boolean enabled)',
 'if(automatic) prefs.edit().putBoolean(','APPLY_LIMIT','/Nocturne/Kuroha',
 '/Nocturne/Kyora','/Nocturne/VideoFlow','/Art/Pixiv',
 '/Art/Cosplay','/Books/Downloads','/Apps/Downloads',
 'if(size!=original.optLong("size",-1))','cloud.moveFileChecked(',
 'index.noteMoved(','private static final Object EXECUTION_LOCK=']);
assert(!/cloud\.delete|\.deleteFile\(|removeCloudFile\(/.test(engine),
 'Organizer must have no destructive delete path');
has(client,['private JSONObject postCloud(','postCloud("/api/create",',
 'postCloud("/api/filemanager",','form.put("ondup","fail")',
 'readBack=fileDetails(target)','expectedSize>=0&&remoteSize!=expectedSize',
 'public JSONArray listIncomingPage(']);
has(idx,['ALTER TABLE objects ADD COLUMN checksum','CREATE INDEX objects_exact',
 'listing_page','public JSONObject folderPreviews(','public int ingestIncoming(']);
has(main,['organizerReview()','organizerDuplicates()','organizerScan()',
 'organizerApply(String json)','organizerStop()','organizerAuto(boolean enable)',
 'fetchTeraboxFolderPreviews(String folders)','FgRounderOrganizeJob.schedule']);
has(job,['extends JobService','setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)',
 'setPeriodic(PERIOD)','organizer.autoRun(']);
has(ui,['let cloudMode=true;','showOrganizer()','function managerProgress(event)',
 'function managerDuplicates(data)','function managerReview(data)',
 'function folderPreviews(data)','fg-premium-mosaic','fg-premium-folder',
 'fetchTeraboxFolderPreviews?.(','Automatically organize trusted incoming files',
 'bridge()?.organizerStop?.()','bridge()?.organizerApply?.(']);
assert(!ui.includes('actions.append(openBtn,collectionBtn,tbBtn)'),
 'Redundant local/cloud triple navigation still shown');
has(css,['Atlas × Obsidian cloud-first Rounder 0.15.17',
 '.fg-premium-mosaic','.fg-org-sheet']);
has(manifest,['FgRounderOrganizeJob','android.permission.BIND_JOB_SERVICE']);
assert.match(gradle,/versionCode\s*=\s*39/);
assert.match(gradle,/versionName\s*=\s*"0\.15\.17"/);
console.log('ROUNDER_ORGANIZER_CONTRACT_PASS: reviewed moves, metadata duplicate tiers, no deletion, opt-in scheduled scans, premium cloud UI');

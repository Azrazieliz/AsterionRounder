'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root='app/src/main/';
const read=(p)=>fs.readFileSync(root+p,'utf8');
const ui=read('assets/premium-library.js');
const native=read('java/com/openlocal/office/MainActivity.java');
const cloud=read('java/com/openlocal/office/core/FgTeraboxClient.java');
const index=read('java/com/openlocal/office/core/FgTeraboxSearchIndex.java');
const thumbnails=read('java/com/openlocal/office/core/FgRounderOriginalPreviews.java');
const required=(body,needles,name)=>{
  for(const needle of needles)
    assert(body.includes(needle),name+' missing: '+needle);
};
required(cloud,[
  'previewUnavailable(JSONObject source)',
  'source.optJSONObject("thumbs")',
  'value.startsWith("https://")',
  '.put("previewUnavailable",!folder&&previewUnavailable(source))'
],'provider metadata');
required(index,[
  '"rounder-terabox-search-v1.db",null,3',
  'preview_missing INTEGER NOT NULL DEFAULT 0',
  'CREATE TABLE preview_marks',
  'CREATE INDEX objects_preview',
  'if(oldVersion<3)',
  'UPDATE accounts SET active=0,building=0,indexed=0,error=NULL',
  'FgTeraboxClient.previewUnavailable(raw)?1:0',
  'public java.util.Set<String> markedForPage(JSONArray page)',
  'public void markPreview(String path,boolean affected)',
  'DELETE FROM preview_marks WHERE scope<>?',
  'DELETE FROM preview_marks WHERE scope=? AND path=?',
  'boolean affected="affected".equals(category)',
  '(!text.trim().isEmpty()||affected)',
  "o.kind='image' AND (o.preview_missing=1 OR COALESCE(mark.marked,0)=1)",
  '.put("previewManuallyMarked",manual)',
  '.put("previewUnavailable",missing)'
],'persisted cloud preview index');
required(native,[
  'java.util.Set<String> reviewed=fgCloudIndex().markedForPage(cloud)',
  'mapped.put("previewManuallyMarked",reviewed.contains(path))',
  'public void markTeraboxPreview(String path,boolean affected)',
  'fgCloudIndex().markPreview(path,affected)',
  'FileGestionerLibrary?.previewMarkResult('
],'native review bridge');
required(ui,[
  "['affected','Affected previews']",
  "function cloudIndexedMode(){return cloudMode&&(!!phrase.trim()||filter==='affected');}",
  "if(key==='affected'&&!cloudMode)continue;",
  "if(indexedMode()){",
  'fg-preview-affected',
  'Remove affected-preview flag',
  'Flag affected preview',
  'function previewMarkResult(data){',
  'if(!data||data.scope!==bridge()?.getTeraboxSearchScope?.())return;',
  'previewMarkResult,',
  'scheduleIndexSearch(0,0)'
],'existing Rounder library filter');
required(thumbnails,[
  'cloud.openRangeStream(path,0)',
  'MAX_ENCODED_BYTES=16*1024*1024',
  'rounder-original-preview-v1',
  'cloud.metadataScope()',
  'Semaphore(2,true)'
],'bounded authenticated original thumbnail');
const start=native.indexOf('private WebResourceResponse fgTbCover(Uri source)');
const end=native.indexOf('private WebResourceResponse fgTbImage(Uri source)',start);
assert(start>=0&&end>start,'Original image card route missing');
const cover=native.slice(start,end);
assert(!cover.includes('openThumbnail('),'Visible covers may not use TeraBox restricted-preview API');
assert(cover.includes('openStill(path)'),'Static previews must decode original bytes');
assert(cover.includes('"image/gif",null,tb().open(path)'),'GIF previews must retain animation');
assert(!ui.includes('function classifyByImageContent'), 'No speculative content labeling');
assert(index.includes('LEFT JOIN preview_marks mark'), 'Owner flags must survive search index queries');
assert(index.includes('scope=?'), 'Account-scope isolation required');
console.log('ROUNDER_AFFECTED_PREVIEW_PASS: original-file thumbnails, metadata-based filter, reviewed placeholders, account separation, GIF support');

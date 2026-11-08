
/* Visual duplicate review. Only cryptographic cloud metadata groups can be
   submitted for deletion; uncertain filename/size matches remain read-only. */
const duplicateKeep=new Map();
const duplicateRemove=new Set();
let duplicateDisplayLimit=8;
function duplicateKey(g){return g.id||((g.hash||'')+':'+g.size);}
function prettySize(bytes){
 const n=Number(bytes)||0;
 if(n<1024)return n+' B';
 if(n<1048576)return (n/1024).toFixed(n<10240?1:0)+' KB';
 if(n<1073741824)return (n/1048576).toFixed(1)+' MB';
 return (n/1073741824).toFixed(2)+' GB';
}
function resetDuplicateSelection(){
 duplicateKeep.clear();duplicateRemove.clear();duplicateDisplayLimit=8;
}
function initializeDuplicateSelection(data){
 resetDuplicateSelection();
 let n=0;
 for(const g of data?.exact||[]){
   if(g.reviewOnly||!Array.isArray(g.files)||g.files.length<2)continue;
   duplicateKeep.set(duplicateKey(g),g.files[0].path);
   for(const file of g.files.slice(1)){
     if(n>=30)break;
     duplicateRemove.add(file.path);n++;
   }
 }
}
function selectedDuplicates(){
 const result={groups:[],files:0,bytes:0};
 for(const group of managerDupeData?.exact||[]){
   if(group.reviewOnly||!Array.isArray(group.files)||group.files.length<2)continue;
   const keep=duplicateKeep.get(duplicateKey(group))||group.files[0].path;
   const remove=group.files.filter(f=>f.path!==keep&&duplicateRemove.has(f.path))
     .map(f=>f.path);
   if(remove.length){
     result.groups.push({keep,remove});
     result.files+=remove.length;
     result.bytes+=remove.length*(Number(group.size)||0);
   }
 }
 return result;
}
function renderDuplicatePreview(file){
 const preview=E('div','fg-review-thumb');
 if(file.cover&&file.kind==='image'){
   const img=E('img','fg-review-image');
   img.alt='Actual cloud preview: '+file.name;
   img.decoding='async';img.loading='lazy';
   const failed=E('span','fg-review-fallback','Preview unavailable');
   failed.hidden=true;
   img.addEventListener('error',()=>{img.remove();failed.hidden=false;});
   img.src=file.cover;preview.append(img,failed);
 }else preview.append(E('span','fg-review-fallback',
   file.kind==='video'?'Video':file.kind==='audio'?'Audio':'File'));
 return preview;
}
function renderDuplicateWorkspace(body){
 if(!managerDupeData){
   body.append(E('p','fg-org-muted','Comparing cloud file metadata…'));
   return;
 }
 const exact=managerDupeData.exact||[],uncertain=managerDupeData.possible||[];
 const selection=selectedDuplicates();
 const intro=E('div','fg-review-intro');
 const sizeBox=E('div','fg-review-sizeblock');
 sizeBox.append(E('strong','fg-review-size',prettySize(selection.bytes)),
   E('span','fg-review-caption',selection.files+
     ' selected for removal · '+exact.length+' verified groups'));
 intro.append(sizeBox);
 const controls=E('div','fg-review-toolbar');
 controls.append(b('Select duplicates','fg-review-small',()=>{
   duplicateRemove.clear();let n=0;
   for(const g of exact){
     if(g.reviewOnly)continue;
     const keep=duplicateKeep.get(duplicateKey(g))||g.files?.[0]?.path;
     for(const f of g.files||[]){
       if(f.path!==keep&&n<30){duplicateRemove.add(f.path);n++;}
     }
   }
   renderOrganizer();
 }));
 controls.append(b('Deselect','fg-review-small',()=>{
   duplicateRemove.clear();renderOrganizer();
 }));
 intro.append(controls);
 intro.append(E('p','fg-review-explainer',
   'Each group contains matching TeraBox MD5 and size. Choose the original to keep and the copies to remove.'));
 body.append(intro);
 if(!exact.length){
   body.append(E('p','fg-org-empty-state',
     managerDupeData.indexReady?
       'No matching copies found in the indexed files.':'TeraBox indexing is still preparing duplicate comparisons.'));
 }
 for(const [i,g] of exact.slice(0,duplicateDisplayLimit).entries()){
   const files=g.files||[];
   const id=duplicateKey(g);
   const keep=duplicateKeep.get(id)||files[0]?.path||'';
   const group=E('section','fg-review-group');
   const top=E('div','fg-review-group-top');
   top.append(E('strong','','Group '+(i+1)+' · '+g.count+' copies'),
     E('span','',prettySize(g.size)+' each'));
   group.append(top);
   const rail=E('div','fg-review-rail');
   for(const file of files){
     const isKeep=file.path===keep;
     const isRemove=!isKeep&&duplicateRemove.has(file.path);
     const tile=E('div','fg-review-item'+
       (isKeep?' fg-review-keeper':isRemove?' fg-review-marked':''));
     const preview=renderDuplicatePreview(file);
     preview.append(E('span','fg-review-state',
       isKeep?'KEEP':isRemove?'REMOVE':'UNSELECTED'));
     tile.append(preview);
     tile.append(E('strong','fg-review-filename',file.name||file.path.split('/').pop()));
     const path=E('span','fg-review-path',file.path);
     path.title=file.path;tile.append(path);
     if(!g.reviewOnly){
       const actions=E('div','fg-review-item-controls');
       const keepBtn=b(isKeep?'Retained':'Keep','fg-review-keep-btn'+
         (isKeep?' active':''),()=>{
           const old=duplicateKeep.get(id)||files[0].path;
           duplicateKeep.set(id,file.path);
           duplicateRemove.delete(file.path);
           if(old!==file.path&&duplicateRemove.size<30)duplicateRemove.add(old);
           renderOrganizer();
         });
       const removeBtn=b(isRemove?'Remove ✓':'Remove','fg-review-remove-btn'+
         (isRemove?' active':''),()=>{
           if(file.path===duplicateKeep.get(id))return;
           if(duplicateRemove.has(file.path))duplicateRemove.delete(file.path);
           else if(duplicateRemove.size<30)duplicateRemove.add(file.path);
           else managerMessage='Up to 30 removals per cleanup. Deselect another copy first.';
           renderOrganizer();
         });
       removeBtn.disabled=isKeep||managerRunning;keepBtn.disabled=managerRunning;
       actions.append(keepBtn,removeBtn);tile.append(actions);
     }else tile.append(E('small','fg-review-path',
       'Additional copies exist. Review the full group before cleanup.'));
     rail.append(tile);
   }
   group.append(rail);body.append(group);
 }
 if(exact.length>duplicateDisplayLimit){
   body.append(b('Show '+Math.min(8,exact.length-duplicateDisplayLimit)+
     ' more groups','fg-review-more',()=>{
       duplicateDisplayLimit+=8;renderOrganizer();
     }));
 }
 if(uncertain.length){
   const maybe=E('details','fg-review-uncertain');
   maybe.append(E('summary','',uncertain.length+
     ' possible groups — matching filename and size only'));
   maybe.append(E('p','fg-org-muted',
     'These are not proven identical. They cannot be cleaned up without content verification.'));
   for(const g of uncertain.slice(0,20)){
     const row=E('div','fg-review-uncertain-group');
     row.append(E('strong','',g.count+' similar files · '+prettySize(g.size)));
     for(const f of g.files||[])row.append(E('span','fg-review-path',f.path));
     maybe.append(row);
   }
   body.append(maybe);
 }
}
function renderDuplicateCleanupFooter(shell){
 const selection=selectedDuplicates();
 const footer=E('div','fg-review-bottom');
 footer.append(E('strong','',selection.files+' files · '+prettySize(selection.bytes)));
 const action=b(managerRunning?'Processing…':'Clean up selected','fg-review-cleanup',()=>{
   const selected=selectedDuplicates();
   if(!selected.files||selected.files>30)return;
   if(!window.confirm('Delete '+selected.files+' matching copies ('+
     prettySize(selected.bytes)+') from TeraBox? A matching original stays in each group. Cloud deletion can be irreversible depending on TeraBox recovery settings.'))return;
   managerRunning=true;
   managerMessage='Verifying retained files and deleting selected copies…';
   renderOrganizer();
   bridge()?.organizerCleanupDuplicates?.(JSON.stringify({groups:selected.groups}));
 });
 action.disabled=managerRunning||selection.files<1||selection.files>30;
 footer.append(action);
 if(managerRunning)footer.append(b('Stop after current file','fg-review-small',
   ()=>bridge()?.organizerStop?.()));
 shell.append(footer);
}
function managerCleanupProgress(event){
 if(!event||event.operation!=='duplicates')return;
 if(event.finished){
   managerRunning=false;
   managerMessage=(event.deleted||0)+' deleted and verified · '+
     (event.review||0)+' require review'+(event.stopped?' · stopped':'');
   bridge()?.organizerDuplicates?.();
 }else{
   if(event.status==='deleted')duplicateRemove.delete(event.source);
   managerMessage=(Number(event.completed)+1)+'/'+event.total+' · '+
     (event.status==='deleted'?'Confirmed removed: '+event.source:
      'Review needed: '+(event.error||event.source));
 }
 renderOrganizer();
}

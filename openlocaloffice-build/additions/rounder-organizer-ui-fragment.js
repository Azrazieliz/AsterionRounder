
// Deterministic organizer: all file moves require explicit authorization or opt-in.
function closeOrganizer(){
 if(managerRunning)return;
 managerPanel?.remove();managerPanel=null;
}
function showOrganizer(){
 if(!bridge()?.getTeraboxConfigured?.()){showTeraboxSettings();return;}
 if(managerPanel)return;
 managerData=null;managerDupeData=null;managerMessage='';
 managerSelected.clear();managerView='moves';managerRunning=false;
 managerPanel=E('div','fg-org-backdrop');
 const shell=E('section','fg-org-sheet');
 shell.setAttribute('role','dialog');shell.setAttribute('aria-modal','true');
 shell.setAttribute('aria-label','Cloud organizer');
 managerPanel.append(shell);document.body.append(managerPanel);
 bridge()?.organizerReview?.();bridge()?.organizerDuplicates?.();
 renderOrganizer();
}
function managerRefreshReview(){bridge()?.organizerReview?.();bridge()?.organizerDuplicates?.();}
function managerSourceSaved(){
 managerMessage='Source folder saved. Future intake scans use the confirmed location.';
 renderOrganizer();
}
function managerReview(data){
 managerData=data;renderOrganizer();
}
function managerDuplicates(data){managerDupeData=data;renderOrganizer();}
function managerScan(data){
 managerMessage='Incoming scan: '+(data?.folders||0)+' folders checked, '+
  (data?.indexed||0)+' metadata entries processed.'+
  (data?.partial?' Remaining folders continue in later cycles.':'');
 renderOrganizer();
}
function managerAuto(value){
 if(managerData)managerData.auto=!!value;
 managerMessage=value?'Scheduled sorting enabled for this TeraBox account.':
  'Scheduled sorting disabled.';
 renderOrganizer();
}
function managerError(data){
 managerRunning=false;
 managerMessage='Operation unavailable: '+(data?.error||'Unknown error');
 renderOrganizer();
}
function managerProgress(event){
 if(!event)return;
 if(event.finished){
   managerRunning=false;
   managerMessage='Moved '+(event.moved||0)+' · Review '+(event.review||0)+
    (event.stopped?' · Stopped':'');
   bridge()?.organizerReview?.();bridge()?.organizerDuplicates?.();
 }else{
   if(event.status==='moved')managerSelected.delete(event.source);
   managerMessage=(event.completed+1)+'/'+event.total+
     ' · '+(event.status==='moved'?'Moved: '+event.source:'Review: '+
     (event.error||event.source));
 }
 renderOrganizer();
}
function renderOrganizer(){
 const shell=managerPanel?.querySelector('.fg-org-sheet');
 if(!shell)return;
 shell.replaceChildren();
 const header=E('div','fg-org-header');
 const headingBox=E('div','');
 headingBox.append(E('span','fg-premium-eyebrow','CLOUD MANAGEMENT'),
   E('h2','','Organizer'));
 const close=b('✕','fg-org-close',closeOrganizer);
 close.disabled=managerRunning;close.setAttribute('aria-label','Close organizer');
 header.append(headingBox,close);shell.append(header);
 shell.append(E('p','fg-org-description',
  'Deterministic file sorting and duplicate detection. No AI. No automatic deletion.'));
 const tabs=E('div','fg-org-tabs');
 for(const [key,label] of [['moves','Sort incoming'],['dupes','Duplicates']]){
   tabs.append(b(label,managerView===key?'fg-org-tab active':'fg-org-tab',()=>{
     managerView=key;renderOrganizer();
   }));
 }
 shell.append(tabs);
 const body=E('div','fg-org-content');
 if(managerView==='moves'){
   if(!managerData){
     body.append(E('p','fg-org-muted','Reading indexed file rules…'));
   }else{
     const count=managerData.proposals?.length||0;
     body.append(E('p','fg-org-stat',count+' proposed moves'+
       (managerData.hasMore?' · More available after these are reviewed':'')));
     const apps=E('details','fg-org-source-settings');
     apps.append(E('summary','fg-org-source-header',
       'Connected Asterion sources · '+(managerData.sources||[]).filter(x=>x.configured).length+
       ' of '+(managerData.sources||[]).length+' configured'));
     const sourceList=E('div','fg-org-source-list');
     sourceList.append(E('p','fg-org-muted',
       'Select real incoming/export folders. A file extension alone cannot identify its originating app. Historical folders can be mapped to Asterion Downloader; they are not separate apps.'));
     for(const source of managerData.sources||[]){
       const record=E('div','fg-org-source-record');
       const sourceLabel=E('label','fg-org-source-name',source.name);
       const sourceInput=E('input','fg-org-source-input');
       sourceInput.type='text';sourceInput.value=source.root||'';
       sourceInput.placeholder='/Actual/App/Export/Folder';
       sourceInput.autocomplete='off';
       sourceInput.setAttribute('aria-label',source.name+' incoming folder');
       const autoRow=E('label','fg-org-auto');
       const auto=E('input','');auto.type='checkbox';
       auto.checked=!!source.auto;
       autoRow.append(auto,E('span','','Allow scheduled moves for this source'));
       const save=b('Save source','fg-org-small',()=>{
         if(auto.checked&&!source.auto&&!window.confirm(
           'Allow automatically moving files from '+source.name+
           ' after configuring this source export folder?')){
           auto.checked=false;return;
         }
         bridge()?.organizerConfigureSource?.(source.id,sourceInput.value,auto.checked);
         managerMessage='Saving source '+source.name+'…';renderOrganizer();
       });
       record.append(sourceLabel,sourceInput,autoRow,save);sourceList.append(record);
     }
     apps.append(sourceList);body.append(apps);
     body.append(E('p','fg-org-muted',
       'Asterion Downloader is one app. Other apps are recognized only when their actual export folders are configured. Uncertain file types are left unchanged.'));
     const rows=E('div','fg-org-filelist');
     for(const item of managerData.proposals||[]){
       const row=E('label','fg-org-row');
       const input=E('input','fg-org-check');input.type='checkbox';
       input.checked=managerSelected.has(item.source);
       input.disabled=managerRunning;
       input.addEventListener('change',()=>{
         if(input.checked)managerSelected.add(item.source);
         else managerSelected.delete(item.source);
       });
       const detail=E('div','fg-org-rowtext');
       detail.append(E('strong','',item.source.split('/').pop()||item.source),
         E('span','','From '+item.source),
         E('span','fg-org-destination','To '+item.target),
         E('small','',item.reason||'Extension rule'));
       row.append(input,detail);rows.append(row);
     }
     body.append(rows);
     const controls=E('div','fg-org-controls');
     controls.append(b('Select first 30','fg-org-small',()=>{
       managerSelected.clear();
       for(const item of (managerData.proposals||[]).slice(0,30))
         managerSelected.add(item.source);
       renderOrganizer();
     }));
     const apply=b(managerRunning?'Moving…':'Move selected','fg-org-primary',()=>{
       const selected=[...managerSelected].slice(0,30);
       if(!selected.length)return;
       if(!window.confirm('Move '+selected.length+
           ' selected files into their proposed TeraBox destinations?'))return;
       managerRunning=true;managerMessage='Moving selected files…';
       renderOrganizer();
       bridge()?.organizerApply?.(JSON.stringify(selected));
     });
     apply.disabled=managerRunning||managerSelected.size===0;
     controls.append(apply);
     if(managerRunning)controls.append(b('Stop after current file','fg-org-small',
       ()=>bridge()?.organizerStop?.()));
     body.append(controls);
   }
   const scan=b('Check incoming downloads','fg-org-scan',()=>{
     managerMessage='Checking incoming source folders…';renderOrganizer();
     bridge()?.organizerScan?.();
   });
   scan.disabled=managerRunning;body.append(scan);
   const row=E('label','fg-org-auto');
   const toggle=E('input','');toggle.type='checkbox';
   toggle.checked=!!managerData?.auto;toggle.disabled=managerRunning;
   toggle.addEventListener('change',()=>{
     if(toggle.checked&&!window.confirm(
       'Enable scheduled sorting of trusted incoming file types for this TeraBox account? File moves will happen automatically. Duplicates are never deleted.')){
       toggle.checked=false;return;
     }
     bridge()?.organizerAuto?.(toggle.checked);
   });
   row.append(toggle,E('span','','Automatically organize trusted incoming files (opt-in)'));
   body.append(row);
 }else{
   if(!managerDupeData)body.append(E('p','fg-org-muted','Checking indexed duplicate groups…'));
   else {
     for(const [key,title] of [['exact','Matching cloud hashes'],['possible','Possible duplicates']]){
       const groups=managerDupeData[key]||[];
       body.append(E('h3','fg-org-group-title',title+' · '+groups.length+' groups'));
       if(!groups.length)body.append(E('p','fg-org-muted',
         key==='exact'?'No MD5-and-size groups found in indexed metadata.':
         'No same-name/same-size candidates found.'));
       for(const group of groups){
         const details=E('details','fg-org-dupe');
         details.append(E('summary','',group.count+' files · '+
           group.size+' bytes · '+group.basis));
         const list=E('div','fg-org-paths');
         for(const path of group.paths||[])list.append(E('p','',path));
         details.append(list);body.append(details);
       }
     }
     body.append(E('p','fg-org-muted',
       'Provider MD5 matches are strong metadata evidence. Same-name candidates require verification; no files are deleted.'));
   }
 }
 if(managerMessage)body.prepend(E('p','fg-org-status',managerMessage));
 shell.append(body);
}

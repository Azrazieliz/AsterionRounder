/* File Gestioner Library — visual-first offline bookshelf. */
(()=>{'use strict';
const bridge=()=>window.AndroidBridge;
const E=(tag,cls,content)=>{const n=document.createElement(tag);if(cls)n.className=cls;
  if(content!==undefined)n.textContent=content;return n;};
const b=(label,cls,fn)=>{const n=E('button',cls,label);n.type='button';
  n.addEventListener('click',fn);return n;};
const root=E('section','fg-library-root fg-lib-hidden');
root.id='fg-library';
const header=E('header','fg-lib-header'),body=E('main','fg-lib-body');
const brand=E('div','fg-lib-brand');
const monogram=E('div','fg-lib-monogram','FG');
const titleGroup=E('div','fg-lib-title-group');
titleGroup.append(E('strong','fg-lib-brand-title','File Gestioner'),
                  E('span','fg-lib-brand-subtitle','YOUR PRIVATE LIBRARY'));
brand.append(monogram,titleGroup);
const actions=E('div','fg-lib-actions');
const openBtn=b('Open file','fg-lib-primary',()=>bridge()?.pickFile?.());
const collectionBtn=b('Collection','fg-lib-secondary',()=>{
 cloudMode=false;currentFolder='';stack=[];bridge()?.pickLibraryFolder?.();
});
const tbBtn=b('TeraBox','fg-lib-secondary',()=>{
 cloudMode=true;currentFolder='';stack=[];
 if(bridge()?.getTeraboxConfigured?.())show();
 else showTeraboxSettings();
});
tbBtn.title='Native cloud browsing — no RoundSync required';
actions.append(openBtn,collectionBtn,tbBtn);header.append(brand,actions);
const welcome=E('section','fg-lib-welcome');
const kicker=E('p','fg-lib-kicker','OFFLINE READING');
const hero=E('h1','fg-lib-hero','Your files. Your control.');
const subtitle=E('p','fg-lib-subtitle',
  'Browse local and connected storage. Files remain on their original provider.');
welcome.append(kicker,hero,subtitle);
const toolbar=E('section','fg-lib-toolbar');
const back=b('‹','fg-lib-nav-back',()=>navigateBack());
back.setAttribute('aria-label','Return to parent folder');
const heading=E('div','fg-lib-collection-title','Library');
const count=E('span','fg-lib-count','');
const headBox=E('div','fg-lib-head-info');headBox.append(heading,count);
const search=E('input','fg-lib-search');
search.type='search';search.placeholder='Search your books';search.autocomplete='off';
search.setAttribute('aria-label','Search your library');
const layout=b('▦','fg-lib-icon',()=>{list=!list;layout.textContent=list?'☷':'▦';render();});
layout.setAttribute('aria-label','Toggle grid and list');
const sortButton=b('Name ↑','fg-lib-sort',()=>showSortMenu());
sortButton.setAttribute('aria-label','Sort files');
toolbar.append(back,headBox,search,sortButton,layout);
const filters=E('div','fg-lib-filters');
const deck=E('div','fg-lib-grid');
const empty=E('div','fg-lib-empty');
const loading=E('div','fg-lib-loading','Loading your collection…');
const footer=E('div','fg-lib-footer',
  'YOUR FILES · LOCAL & CONNECTED STORAGE');
body.append(welcome,toolbar,filters,loading,deck,empty,footer);
root.append(header,body);
document.body.insertBefore(root,document.getElementById('busy')||null);
const categories=[
 ['all','All files'],['image','Images'],['video','Video'],['audio','Audio'],
 ['book','Books'],['comic','Comics'],['archive','Archives'],['pdf','PDF'],
 ['document','Documents'],['model','3D assets'],['file','Other']
];
let entries=[],list=false,currentFolder='',stack=[],filter='all',phrase='',loaded=false,visible=false,activeUri='';
let cloudMode=false;
let activeVersion=null,scanning=false,pageStart=0,renderTimer=0,lastRender=0;
let imagePumpVersion=0,imagePumpState=null,listingRequest='',operationDialog=null,pendingFolderImageRead=null;
let sortBy='name',sortDescending=false;
const PAGE=96;
function classify(entry){
 if(entry.folder)return 'folder';
 const x=entry.name.toLowerCase();
 if(/\.(cbz|cbr)$/.test(x))return 'comic';
 if(/\.(zip|7z|rar|tar|gz)$/.test(x))return 'archive';
 if(/\.(epub)$/.test(x))return 'book';
 if(/\.(pdf)$/.test(x))return 'pdf';
 if(/\.(png|jpe?g|webp|avif|gif|bmp)$/.test(x))return 'image';
 if(/\.(mp4|webm|mkv|mov|avi)$/.test(x))return 'video';
 if(/\.(mp3|m4a|flac|wav|ogg|opus)$/.test(x))return 'audio';
 if(/\.(glb|gltf|fbx|obj|vrm|blend|pmx|pmd)$/.test(x))return 'model';
 if(/\.(docx?|xlsx?|csv|txt|md|rtf|odt|ods|sdocx|pptx?)$/.test(x))return 'document';
 return 'file';
}
function formatSize(n){
 if(n==null||n<0)return '';
 if(n>=1024**3)return (n/(1024**3)).toFixed(n>=10*1024**3?0:1)+' GB';
 if(n>=1024**2)return (n/(1024**2)).toFixed(n>=10*1024**2?0:1)+' MB';
 return Math.round(n/1024)+' KB';
}
function label(e){
 const c=classify(e);
 return {comic:'COMIC',archive:'ARCHIVE',image:'IMAGE',video:'VIDEO',
   audio:'AUDIO',pdf:'PDF',book:'EBOOK',document:'DOCUMENT',
   model:'3D ASSET',file:'FILE',folder:'FOLDER'}[c];
}
function icon(c){return {comic:'▧',archive:'▦',image:'▧',video:'▶',audio:'♫',
 pdf:'▤',book:'▤',document:'▤',model:'◇',file:'□',folder:'▣'}[c];}
function tint(name){
 let h=42;for(const ch of name)h=(h*33+ch.charCodeAt(0))>>>0;
 return (h%260)+30;
}
function openBook(item){
 if(item.folder){
   // A folder is a folder. Image reading is a deliberate separate action.
   enterFolder(item.id);return;
 }
 activeUri=item.uri;
 root.classList.add('fg-lib-hidden');
 visible=false;
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.remove('hidden');
 if(cloudMode && item.terabox && classify(item)==='image' &&
     bridge()?.beginTeraboxImageCollection){
   const siblings=entries.filter(x=>!x.folder&&x.terabox&&classify(x)==='image')
     .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
   const version=++imagePumpVersion;
   imagePumpState={version,siblings,offset:0,started:false,live:scanning,
     folder:currentFolder,paused:false,feed:null,terabox:true};
   bridge().beginTeraboxImageCollection(item.path,item.name);
 }else if(cloudMode && item.terabox){
   visible=true;root.classList.remove('fg-lib-hidden');
   bridge()?.saveTeraboxFile?.(item.path,item.name);
 }else if(classify(item)==='image' && bridge()?.beginImageCollection){
   // The library already has the siblings' SAF URIs. Reusing them avoids
   // a second expensive Round Sync directory query (or a failed cloud scan).
   const siblings=entries.filter(x=>!x.folder&&classify(x)==='image')
     .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
   const version=++imagePumpVersion;
   imagePumpState={version,siblings,offset:0,started:false,live:scanning,folder:currentFolder,paused:false,feed:null};
   // Native loads the viewer first. It notifies us after installing the
   // image-reader callback, so no early Round Sync batch can be lost.
   bridge().beginImageCollection(item.uri);
 }else if(classify(item)==='image' && bridge()?.openImageInFolder){
   bridge().openImageInFolder(currentFolder,item.uri);
 }else if(classify(item)==='file' && bridge()?.openLibraryExternally){
   // Never pretend an unknown file can be decoded by a reader.
   bridge().openLibraryExternally(item.uri);
 }else{
   bridge()?.openLibraryFile?.(item.uri);
 }
}
// Never start five remote archive transfers at once. Image requests run only
// after the corresponding tile intersects the viewport; each finishes before
// the next starts. Opening a book cancels the pending (not-yet-started) work.
const queuedCovers=new WeakSet();
const coverJobs=[];
let activeCoverJobs=0;
const MAX_CLOUD_COVERS=2;
function pumpCovers(){
 while(activeCoverJobs<MAX_CLOUD_COVERS&&coverJobs.length){
   const job=coverJobs.shift();
   if(!job.image.isConnected||!visible)continue;
   activeCoverJobs++;
   const indicator=E('span','fg-lib-cover-loading','Loading cover…');
   job.cover.appendChild(indicator);
   let done=false,timeout=0;
   const finish=()=>{
     if(done)return;done=true;clearTimeout(timeout);
     job.image.removeEventListener('load',finish);
     job.image.removeEventListener('error',finish);
     indicator.remove();
     activeCoverJobs=Math.max(0,activeCoverJobs-1);
     pumpCovers();
   };
   job.image.addEventListener('load',finish);
   job.image.addEventListener('error',finish);
   timeout=setTimeout(finish,10000);
   job.image.src=job.url;
 }
}
const coverObserver=window.IntersectionObserver?new IntersectionObserver(changes=>{
 for(const item of changes){
   if(!item.isIntersecting)continue;
   coverObserver.unobserve(item.target);
   item.target._fgStartCover?.();
 }
},{root:body,rootMargin:'0px'}):null;
function loadRemoteCover(image,url,cover){
 if(queuedCovers.has(image))return;
 queuedCovers.add(image);
 coverJobs.push({image,url,cover});
 pumpCovers();
}

function closeFileActions(){operationDialog?.remove();operationDialog=null;}
function fileSheet(title,note){
 closeFileActions();
 const overlay=E('div','fg-file-sheet-overlay');
 const sheet=E('section','fg-file-sheet');
 sheet.setAttribute('role','dialog');sheet.setAttribute('aria-modal','true');
 sheet.setAttribute('aria-label',title);
 overlay.addEventListener('click',e=>{if(e.target===overlay)closeFileActions();});
 const head=E('header','fg-file-sheet-head');
 head.append(E('strong','',title),b('×','fg-file-sheet-close',closeFileActions));
 sheet.append(head);
 if(note)sheet.append(E('p','fg-file-sheet-subtitle',note));
 overlay.append(sheet);document.body.append(overlay);operationDialog=overlay;
 return sheet;
}
function fileAction(sheet,label,description,callback,{danger=false,disabled=false}={}){
 const control=b(label,'fg-file-action'+(danger?' fg-file-danger':''),callback);
 control.disabled=disabled;
 if(description)control.append(E('small','fg-file-action-description',description));
 sheet.append(control);return control;
}
function showSortMenu(){
 const sheet=fileSheet('Sort files','Choose how to order this collection');
 const labels={name:'Name',modified:'Last modified',size:'Size',type:'File type'};
 for(const [key,label] of Object.entries(labels))
   fileAction(sheet,(sortBy===key?'✓ ':'')+label,'',()=>{
     if(sortBy===key)sortDescending=!sortDescending;
     else{sortBy=key;sortDescending=(key==='modified'||key==='size');}
     sortButton.textContent=labels[sortBy]+(sortDescending?' ↓':' ↑');
     pageStart=0;closeFileActions();render();
   });
}
function fileProperties(item){
 const sheet=fileSheet(item.name,'Properties of the original file');
 const dl=E('dl','fg-file-details');
 const data=[
  ['Type',item.folder?'Folder':label(item)],
  ['Size',item.folder?'—':formatSize(item.size)||'Unknown'],
  ['Modified',item.modified?new Date(item.modified).toLocaleString():'Unknown'],
  ['Provider',/de\.felixnuesse\.extract\.vcp/.test(item.uri||'')?'Round Sync':'Storage provider'],
  ['MIME',item.mime||'Not reported']
 ];
 for(const [key,value] of data)dl.append(E('dt','',key),E('dd','',value));
 sheet.append(dl);
 fileAction(sheet,'Close','',closeFileActions);
}
function showFileActions(item){
 if(item.terabox){
   const sheet=fileSheet(item.name,(item.folder?'TeraBox folder':'TeraBox · '+formatSize(item.size)));
   fileAction(sheet,item.folder?'Browse folder':'Open file',
      'Cloud content without RoundSync',()=>{closeFileActions();openBook(item);});
   if(!item.folder)fileAction(sheet,'Download to…',
      'Choose a destination; original remains in your cloud account',
      ()=>{closeFileActions();bridge()?.saveTeraboxFile?.(item.path,item.name);});
   fileAction(sheet,'Close','',closeFileActions);
   return;
 }
 const kind=classify(item);
 const write=Boolean(bridge()?.canManageLibraryFiles?.());
 const sheet=fileSheet(item.name,(item.folder?'Folder':label(item))+
   (formatSize(item.size)?' · '+formatSize(item.size):''));
 const openLabel=item.folder?'Browse folder':
    kind==='image'?'Read image collection':kind==='comic'?'Read comic archive':
    kind==='archive'?'Open archive':kind==='pdf'?'Read PDF':
    kind==='video'?'Play video fullscreen':kind==='audio'?'Play audio':
    kind==='book'?'Read ebook':kind==='model'?'Open 3D asset':
    kind==='file'?'Open with Android':
    /\.(csv|xlsx|xls)$/i.test(item.name)?'Open spreadsheet':'Open document';
 fileAction(sheet,openLabel,'Use the matching file viewer',()=>{
   closeFileActions();openBook(item);
 });
 if(item.folder)
   fileAction(sheet,'Read folder images','Read images as soon as cloud metadata becomes available',()=>{
     closeFileActions();
     pendingFolderImageRead=item.id;
     enterFolder(item.id);
   });
 if(kind==='image')
   fileAction(sheet,'View only this image','Keep this image separate from its folder',()=>{
     closeFileActions();activeUri=item.uri;
     visible=false;root.classList.add('fg-lib-hidden');
     document.getElementById('home')?.classList.add('hidden');
     document.getElementById('work')?.classList.remove('hidden');
     bridge()?.openLibraryFile?.(item.uri);
   });
 if(!item.folder){
   fileAction(sheet,'Open with another app','Choose an installed Android application',()=>{
     closeFileActions();bridge()?.openLibraryExternally?.(item.uri);
   });
   fileAction(sheet,'Share original file','Share through the Android share sheet',()=>{
     closeFileActions();bridge()?.shareLibraryFile?.(item.uri);
   });
   fileAction(sheet,'Copy to folder','Stream to local or cloud storage, keeping the original',()=>{
     closeFileActions();bridge()?.copyLibraryFile?.(item.uri);
     showTransferSheet('Copying file');
   });
   fileAction(sheet,'Move to folder','Delete the original only after the destination is verified',()=>{
     closeFileActions();bridge()?.moveLibraryFile?.(item.uri);
     showTransferSheet('Moving file');
   },{disabled:!write});
 }
 if(!item.folder){
   const lower=item.name.toLowerCase();
   const image=/\.(png|jpe?g|bmp|webp)$/.test(lower);
   const firstPdf=/\.pdf$/.test(lower);
   const separated=/\.(csv|tsv)$/.test(lower);
   if(image||firstPdf||separated)
     fileAction(sheet,'Convert format','Save as a new file; the original is unchanged',()=>{
       const choose=fileSheet('Convert '+item.name,'Select a supported output. Your original is preserved.');
       const variants=image?[
         ['PNG','png'],['JPEG · 92% quality','jpeg'],['WebP · 92% quality','webp'],
         ['PDF · single image page','pdf']
       ]:firstPdf?[['PNG · first PDF page only','png']]:
         lower.endsWith('.csv')?[['TSV · tab-separated','tsv']]:
         [['CSV · comma-separated','csv']];
       for(const [label,format] of variants)
         fileAction(choose,label,'Android will ask where to save the converted file',()=>{
           closeFileActions();bridge()?.convertLibraryFile?.(item.uri,format);
         });
     });
 }
 fileAction(sheet,'Properties','Size, type, date and storage provider',()=>fileProperties(item));
 if(!item.folder){
   fileAction(sheet,'Rename','Rename in the original storage provider',()=>{
     const edit=fileSheet('Rename file','Retain the extension unless changing the format');
     const field=E('input','fg-file-name-input');field.value=item.name;
     field.maxLength=240;field.setAttribute('aria-label','New file name');
     edit.append(field);
     fileAction(edit,'Save name','',()=>{
       const name=field.value.trim();
       if(!name||name===item.name||/[/\\]/.test(name))return;
       bridge()?.renameLibraryFile?.(item.uri,name);closeFileActions();
     });
     field.focus();
   },{disabled:!write});
   fileAction(sheet,'Delete file','This permanently removes the original file',()=>{
     const confirm=fileSheet('Delete original file?','This cannot be undone.');
     confirm.append(E('p','fg-file-delete-name',item.name));
     fileAction(confirm,'Cancel','',closeFileActions);
     fileAction(confirm,'Delete permanently','Confirm deletion of the original file',()=>{
       bridge()?.deleteLibraryFile?.(item.uri);closeFileActions();
     },{danger:true});
   },{danger:true,disabled:!write});
   if(!write)sheet.append(E('p','fg-file-write-note',
     'Rename and delete require write permission from this storage provider. Re-select the collection to request write access.'));
 }
}
function showTransferSheet(title){
 const sheet=fileSheet(title,'Choose the destination in the Android folder picker.');
 const note=E('p','fg-transfer-note','After selecting a folder, the transfer will stream without loading the whole file into memory.');
 note.setAttribute('role','status');sheet.append(note);
 const progress=E('progress','fg-transfer-progress');progress.max=100;progress.value=0;
 sheet.append(progress);
 fileAction(sheet,'Cancel transfer','Safely stop copying; the original stays intact',()=>{
   bridge()?.cancelLibraryTransfer?.();closeFileActions();
 });
}
function transferProgress(progress){
 if(!operationDialog||!progress)return;
 const bar=operationDialog.querySelector('.fg-transfer-progress');
 const note=operationDialog.querySelector('.fg-transfer-note');
 if(!bar||!note)return;
 const transferred=Number(progress.transferred)||0,total=Number(progress.total)||0;
 if(total>0){
   bar.value=Math.min(100,Math.round(transferred/total*100));
   note.textContent='Copied '+formatSize(transferred)+' of '+formatSize(total)+
     ' ('+bar.value+'%)';
 }else if(transferred>0)note.textContent='Copied '+formatSize(transferred)+'…';
}
function operationResult(result){
 if(!result)return;
 const toast=E('div','fg-file-toast',
   (result.ok?'':'Action failed: ')+(result.detail||result.operation));
 toast.setAttribute('role','status');document.body.append(toast);
 setTimeout(()=>toast.remove(),4500);
 if(result.ok&&['rename','delete','move','copy'].includes(result.operation))request();
 if(['move','copy','transfer'].includes(result.operation))closeFileActions();
}

function card(item,i){
 const c=classify(item),tile=E('article','fg-lib-tile fg-lib-'+c);
 tile.setAttribute('role','button');tile.setAttribute('tabindex','0');
 const cover=E('div','fg-lib-cover');
 cover.style.setProperty('--fg-hue',String(tint(item.name)));
 const fallback=E('div','fg-lib-fallback');
 fallback.append(E('span','fg-lib-fallback-glyph',icon(c)),
                 E('strong','fg-lib-fallback-title',item.title));
 cover.appendChild(fallback);
 if(item.cover){
   const image=E('img','fg-lib-cover-image');
   image.loading='lazy';image.decoding='async';
   image.alt='Cover · '+item.title;
   image.addEventListener('load',()=>{cover.classList.add('fg-lib-has-image');});
   image.addEventListener('error',()=>{if(!item.remoteCover)image.remove();});
   cover.appendChild(image);
   if(item.remoteCover){
     // Automatic, sequential, visibility-prioritized cloud thumbnail loading.
     cover._fgStartCover=()=>loadRemoteCover(image,item.cover,cover);
     if(coverObserver)coverObserver.observe(cover);
     else cover._fgStartCover();
   }else image.src=item.cover;
 }
 const badge=E('span','fg-lib-type',label(item));
 cover.appendChild(badge);
 const meta=E('div','fg-lib-tile-meta');
 meta.append(E('strong','fg-lib-item-title',item.title),
             E('span','fg-lib-item-detail',formatSize(item.size)||
               (item.folder?'Open collection':'')));
 tile.append(cover,meta);
 const more=b('⋮','fg-lib-more',e=>{e.stopPropagation();showFileActions(item);});
 more.title='File actions';more.setAttribute('aria-label','Actions for '+item.name);
 tile.append(more);
 let hold=0;
 tile.addEventListener('pointerdown',e=>{
   if(e.pointerType==='touch' && !e.target.closest('.fg-lib-more')){
     hold=setTimeout(()=>{hold=0;tile.dataset.longPressed='yes';showFileActions(item);},580);
   }
 },{passive:true});
 for(const event of ['pointerup','pointercancel','pointermove'])
   tile.addEventListener(event,()=>{if(hold){clearTimeout(hold);hold=0;}},{passive:true});
 tile.addEventListener('click',e=>{
   if(e.target.closest('.fg-lib-more'))return;
   if(tile.dataset.longPressed){delete tile.dataset.longPressed;return;}
   openBook(item);
 });
 tile.addEventListener('keydown',e=>{
   if(e.target!==tile)return;
   if(e.key==='Enter'||e.key===' '){e.preventDefault();openBook(item);}
 });
 return tile;
}
function render(){
 if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
 deck.className='fg-lib-grid'+(list?' fg-lib-list':'');
 deck.replaceChildren();empty.replaceChildren();
 root.querySelectorAll('.fg-lib-pager').forEach(n=>n.remove());
 const needle=phrase.trim().toLocaleLowerCase();
 const shown=entries.filter(e=>{
   const c=classify(e);
   return (filter==='all'||c===filter||c==='folder')&&
     (!needle||e.title.toLocaleLowerCase().includes(needle));
 }).sort((a,b)=>{
   if(a.folder!==b.folder)return a.folder?-1:1;
   let difference=0;
   if(sortBy==='size')difference=(a.size||0)-(b.size||0);
   else if(sortBy==='modified')difference=(a.modified||0)-(b.modified||0);
   else if(sortBy==='type')difference=classify(a).localeCompare(classify(b));
   else difference=a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'});
   return (sortDescending?-1:1)*(difference||
      a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
 });
 const max=Math.max(0,shown.length-1);
 pageStart=Math.min(pageStart,Math.floor(max/PAGE)*PAGE);
 const fragment=document.createDocumentFragment();
 shown.slice(pageStart,pageStart+PAGE).forEach((entry,i)=>
   fragment.appendChild(card(entry,pageStart+i)));
 deck.appendChild(fragment);
 const pages=Math.ceil(shown.length/PAGE);
 const current=Math.floor(pageStart/PAGE)+1;
 if(pages>1){
   const nav=E('nav','fg-lib-pager');
   const prev=b('‹ Previous','fg-lib-page-control',()=>{
     pageStart=Math.max(0,pageStart-PAGE);render();body.scrollTop=0;
   });
   prev.disabled=pageStart<=0;
   const forward=b('Next ›','fg-lib-page-control',()=>{
     pageStart=Math.min((pages-1)*PAGE,pageStart+PAGE);render();body.scrollTop=0;
   });
   forward.disabled=pageStart+PAGE>=shown.length;
   const input=E('input','fg-lib-page-number');
   input.type='number';input.min='1';input.max=String(pages);input.value=String(current);
   input.setAttribute('aria-label','Library page number');
   input.onchange=()=>{
     pageStart=Math.min((pages-1)*PAGE,
       Math.max(0,(Math.round(Number(input.value)||1)-1)*PAGE));
     render();body.scrollTop=0;
   };
   nav.append(prev,E('span','', 'Page '),input,
     E('span','',' / '+pages),forward);
   deck.after(nav);
   if(current>1){
     const earlier=nav.cloneNode(false);
     earlier.className='fg-lib-pager';
     earlier.append(E('span','', (pageStart+1)+'–'+Math.min(shown.length,pageStart+PAGE)+' of '+shown.length));
     deck.before(earlier);
   }
 }
 count.textContent=entries.length+(scanning?' · scanning…':' files')+
   ' · showing '+(shown.length?String(pageStart+1):'0')+
   '–'+Math.min(shown.length,pageStart+PAGE);
 if(!shown.length){
   empty.append(E('div','fg-lib-empty-icon',entries.length?'⌕':'▤'),
     E('strong','',entries.length?'No matching titles':'Nothing in this collection yet'),
     E('p','',entries.length?'Try another title or category.':
       'Choose a folder containing books, documents or models.'));
 }
}
function createFilters(){
 filters.replaceChildren();
 for(const [key,name] of categories){
   const control=b(name,'fg-lib-filter'+(filter===key?' fg-lib-selected':''),
     ()=>{filter=key;pageStart=0;createFilters();render();});
   filters.append(control);
 }
}
function request(){
 if(cloudMode && !bridge()?.getTeraboxConfigured?.()){showTeraboxSettings();return;}
 if(!cloudMode && !bridge()?.getLibraryRoot?.()){showEmpty();return;}
 activeVersion=null;scanning=true;pageStart=0;entries=[];loaded=false;
 listingRequest=currentFolder||'';lastRender=0;
 if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
 loading.textContent='Loading your collection…';
 loading.classList.remove('fg-lib-hidden');deck.classList.add('fg-lib-hidden');
 empty.classList.add('fg-lib-hidden');
 if(cloudMode)bridge()?.listTerabox?.(currentFolder||'');
 else bridge()?.listLibrary?.(currentFolder);
}
function showTeraboxSettings(){
 closeFileActions();
 visible=true;root.classList.remove('fg-lib-hidden');
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.add('hidden');
 welcome.classList.add('fg-lib-hidden');
 toolbar.classList.remove('fg-lib-hidden');
 filters.classList.add('fg-lib-hidden');
 deck.classList.add('fg-lib-hidden');
 loading.classList.add('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');empty.replaceChildren();
 heading.textContent='Native TeraBox';
 const panel=E('div','fg-tb-setup');
 const head=E('h2','','Connect your TeraBox');
 const desc=E('p','','Paste your ndus session cookie. It stays encrypted on this phone. Direct cloud browsing works without RoundSync or a PC.');
 const input=E('input','fg-tb-cookie');
 input.type='password';input.autocomplete='off';input.spellcheck=false;
 input.placeholder='ndus cookie';input.setAttribute('aria-label','TeraBox ndus cookie');
 const info=E('p','fg-tb-status','');
 const save=b('Connect securely','fg-lib-primary',()=>{
   if(!bridge()?.setTeraboxCookie?.(input.value.trim())){
     info.textContent='Invalid cookie format. Paste only the ndus value or ndus=…';
     return;
   }
   input.value='';cloudMode=true;currentFolder='';stack=[];
   show();
 });
 const local=b('Local library','fg-lib-secondary',()=>{
   cloudMode=false;currentFolder='';stack=[];show();
 });
 const disconnect=b('Disconnect TeraBox','fg-lib-secondary',()=>{
   bridge()?.disconnectTerabox?.();cloudMode=false;currentFolder='';stack=[];
   show();
 });
 panel.append(head,desc,input,info,save,local);
 if(bridge()?.getTeraboxConfigured?.())panel.append(disconnect);
 empty.append(panel);
}
const tbStyles=E('style','');
tbStyles.textContent=[
'.fg-tb-setup{display:flex;flex-direction:column;gap:14px;max-width:580px;margin:24px auto;padding:24px;border-radius:20px;background:#182235;border:1px solid #3e526d;color:#eff4ff}',
'.fg-tb-setup h2{margin:0;font:700 24px/1.2 system-ui}',
'.fg-tb-setup p{margin:0;font:14px/1.5 system-ui;color:#bcc9da}',
'.fg-tb-setup .fg-tb-cookie{width:100%;box-sizing:border-box;padding:16px;border-radius:12px;background:#0c1321;border:1px solid #677994;color:#fff;font:15px system-ui;min-height:52px}',
'.fg-lib-actions [aria-pressed=true]{border-color:#8eacff!important;background:#344c76!important}'
].join('\n');
document.head.append(tbStyles);
function showEmpty(){
 loaded=false;entries=[];deck.replaceChildren();loading.classList.add('fg-lib-hidden');
 welcome.classList.remove('fg-lib-hidden');toolbar.classList.add('fg-lib-hidden');
 filters.classList.add('fg-lib-hidden');empty.classList.remove('fg-lib-hidden');
 empty.replaceChildren();
 const add=b('Add a collection','fg-lib-large-action',
   ()=>bridge()?.pickLibraryFolder?.());
 empty.append(E('div','fg-lib-empty-icon','▧'),
   E('strong','','Build your personal library'),
   E('p','','Select a folder to see the actual covers of your books and image archives.'),
   add);
}
function enterFolder(id){
 const entry=entries.find(x=>x.folder&&x.id===id);
 if(!entry){error('Could not open folder');return;}
 // If the directory contains no images, show its regular file listing
 // instead of leaving a hidden library and an empty reader.
 root.classList.remove('fg-lib-hidden');
 visible=true;
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.add('hidden');
 stack.push(currentFolder);currentFolder=id;request();
}
function openSibling(direction){
 const sorted=entries.filter(e=>!e.folder&&
   /\.(epub|pdf|zip|cbz|cbr|jpe?g|png|webp|gif|avif)$/i.test(e.name||''))
   .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
 const i=sorted.findIndex(e=>e.uri===activeUri);
 if(i<0||!sorted.length)return false;
 const next=sorted[i+Math.sign(direction)];
 if(!next)return false;
 openBook(next);
 return true;
}
function navigateBack(){
 pendingFolderImageRead=null;
 closeFileActions();
 if(stack.length){currentFolder=stack.pop();request();return;}
 show();
}
function hideForReader(){
 // External ACTION_VIEW images may reach window.loadDocument before the
 // library initializes. Never cover the active image with the welcome page.
 visible=false;root.classList.add('fg-lib-hidden');
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.remove('hidden');
}
function show(){
 pendingFolderImageRead=null;
 closeFileActions();
 imagePumpVersion++;imagePumpState=null;
 window.FileGestionerReading?.close?.();
 document.body.classList.remove('fg-folder-reading');
 visible=true;root.classList.remove('fg-lib-hidden');
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.add('hidden');
 document.body.classList.remove('fg-book-mode','fg-pdf-reading','fg-unified-reading');
 if(!cloudMode&&!bridge()?.getLibraryRoot?.()){showEmpty();return;}
 welcome.classList.add('fg-lib-hidden');toolbar.classList.remove('fg-lib-hidden');
 tbBtn.setAttribute('aria-pressed',cloudMode?'true':'false');
 collectionBtn.setAttribute('aria-pressed',cloudMode?'false':'true');
 heading.textContent=cloudMode?'TeraBox':'Your library';
 filters.classList.remove('fg-lib-hidden');
 createFilters();
 request();
}
function append(payload){
 if(!payload||!Array.isArray(payload.items))return;
 if('requestedFolder' in payload && payload.requestedFolder!==listingRequest)return;
 if(activeVersion===null){
   activeVersion=payload.version;
   // SAF reports the resolved tree document ID, not the empty root alias.
   currentFolder=payload.folder||currentFolder;
 }
 if(payload.version!==activeVersion||payload.folder!==currentFolder)return;
 const fresh=payload.items.filter(e=>!e.folder&&classify(e)==='image');
 entries.push(...payload.items);
 scanning=!payload.finished;loaded=true;
 const state=imagePumpState;
 if(state && state.live && state.folder===payload.folder){
   const known=new Set(state.siblings.map(e=>e.uri));
   for(const entry of fresh)if(!known.has(entry.uri)){
     known.add(entry.uri);state.siblings.push(entry);
   }
   if(payload.finished)state.live=false;
   if(state.paused&&state.feed){state.paused=false;state.feed();}
 }
 if(pendingFolderImageRead===payload.folder&&fresh.length){
   pendingFolderImageRead=null;
   const first=entries.filter(e=>!e.folder&&classify(e)==='image')
     .sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}))[0];
   if(first)openBook(first);
 }
 if(payload.finished&&pendingFolderImageRead===payload.folder)pendingFolderImageRead=null;
 // Keep the indexed metadata for paging and image streaming, but do not
 // repeatedly rebuild the hidden library during an active reader session.
 if(!visible)return;
 loading.classList.add('fg-lib-hidden');deck.classList.remove('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');
 heading.textContent=stack.length?'Collection':'Your library';
 welcome.classList.add('fg-lib-hidden');toolbar.classList.remove('fg-lib-hidden');
 filters.classList.remove('fg-lib-hidden');
 // Do not debounce every 96-row batch: fast cloud streams would otherwise
 // postpone the first visible page until the entire huge folder is scanned.
 const elapsed=Date.now()-lastRender;
 if(!lastRender||payload.finished||elapsed>=240){
   if(renderTimer){clearTimeout(renderTimer);renderTimer=0;}
   render();lastRender=Date.now();
 }else if(!renderTimer){
   renderTimer=setTimeout(()=>{renderTimer=0;render();lastRender=Date.now();},240-elapsed);
 }
}
function receive(payload){
 loaded=true;
 entries=Array.isArray(payload.items)?payload.items:[];
 currentFolder=payload.folder||currentFolder;
 loading.classList.add('fg-lib-hidden');deck.classList.remove('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');
 heading.textContent=stack.length?'Collection':'Your library';
 welcome.classList.add('fg-lib-hidden');toolbar.classList.remove('fg-lib-hidden');
 filters.classList.remove('fg-lib-hidden');render();
}
function loadingStatus(message){
 if(!visible)return;
 loading.classList.remove('fg-lib-hidden');
 loading.textContent=message||'Waiting for cloud directory metadata…';
 deck.classList.add('fg-lib-hidden');
 empty.classList.add('fg-lib-hidden');
}
function error(message){
 // Errors during image-folder opening must be visible, not trapped behind
 // the hidden library and an empty reader.
 visible=true;root.classList.remove('fg-lib-hidden');
 loading.classList.add('fg-lib-hidden');deck.classList.add('fg-lib-hidden');
 empty.classList.remove('fg-lib-hidden');
 empty.replaceChildren(E('strong','','This folder could not be read'),
                      E('p','',message||'Check cloud availability and file permissions'),
                      b('Try again','fg-lib-large-action',request));
}
search.addEventListener('input',()=>{phrase=search.value;pageStart=0;render();});
const homeNav=b('Library','fg-lib-top-link',show);
homeNav.title='Open your library';
document.querySelector('.bar .actions')?.prepend(homeNav);
// Document opens from the Files picker, Round Sync and direct share intents
// must enter the same reader state as a library-card click.
const upstreamLoad=window.loadDocument;
window.loadDocument=function(payload){
 visible=false;
 root.classList.add('fg-lib-hidden');
 document.getElementById('home')?.classList.add('hidden');
 document.getElementById('work')?.classList.remove('hidden');
 return upstreamLoad(payload);
};
function handleAndroidBack(){
 if(operationDialog){closeFileActions();return true;}
 if(window.FileGestionerReading?.handleBack?.())return true;
 // Reading settings are a modal surface, not an exit command.
 const drawer=document.querySelector('.fg-book-drawer:not(.fg-book-hidden)');
 if(drawer){drawer.classList.add('fg-book-hidden');return true;}
 if(visible){
   // Also tolerate older reader states in which the library flag remained
   // true after a document was opened from an external Android provider.
   if(!document.getElementById('work')?.classList.contains('hidden')){
     show();bridge()?.readerDiagnostic?.('BACK_TO_LIBRARY');return true;
   }
   if(stack.length){navigateBack();return true;}
   // Root collection is the app's top-level destination.
   return false;
 }
 // Return to the actual library, regardless of whether the source was
 // opened through Round Sync, Files, or a collection tile.
 show();
 bridge()?.readerDiagnostic?.('BACK_TO_LIBRARY');
 return true;
}
window.FileGestionerLibrary={
 show,hideForReader,receive,append,error,loadingStatus,operationResult,transferProgress,handleBack:handleAndroidBack,enterFolder,openSibling,
 imageReaderReady:()=>{
   const state=imagePumpState;
   if(!state||state.started||state.version!==imagePumpVersion)return;
   state.started=true;
   const feed=()=>{
     if(imagePumpState!==state||imagePumpVersion!==state.version)return;
     if(state.offset>=state.siblings.length){
       if(state.live && scanning){state.paused=true;return;}
       bridge()?.finishImageCollection?.();imagePumpState=null;return;
     }
     const batch=state.siblings.slice(state.offset,state.offset+64)
       .map(x=>state.terabox?{path:x.path,name:x.name}:{uri:x.uri,name:x.name});
     state.offset+=64;
     if(state.terabox)bridge()?.appendTeraboxImageCollectionChunk?.(JSON.stringify(batch));
     else bridge()?.appendImageCollectionChunk?.(JSON.stringify(batch));
     setTimeout(feed,0);
   };
   state.feed=feed;
   feed();
 },
 isVisible:()=>visible,
 openCollection:()=>{
   currentFolder='';stack=[];show();
 },missingCollection:showEmpty
};
const initializeLibrary=()=>{
 // Handle both early page loads and scripts loaded after DOMContentLoaded.
 if(window.__fgLibraryInitialized)return;
 window.__fgLibraryInitialized=true;
 if(document.body.classList.contains('fg-folder-reading'))hideForReader();
 else show();
 bridge()?.readerDiagnostic?.('LIBRARY_READY');
};
if(document.readyState==='loading')
 document.addEventListener('DOMContentLoaded',initializeLibrary,{once:true});
else initializeLibrary();
})();

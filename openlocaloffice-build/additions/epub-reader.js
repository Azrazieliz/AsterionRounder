/* File Gestioner · Premium continuous EPUB reader
   Chapter/spine navigation from EPUB package, original illustrations from
   local ZIP streams, no document-wide content flattening or page slideshow.
*/
(()=>{'use strict';
const $=id=>document.getElementById(id);
const previous=window.loadDocument;
let cleanup=null;
function el(tag,cls,content){
  const e=document.createElement(tag);
  if(cls)e.className=cls;
  if(content!==undefined)e.textContent=content;
  return e;
}
function button(label,action,aria){
  const b=el('button','fg-book-button',label);
  b.type='button';b.setAttribute('aria-label',aria||label);
  b.addEventListener('click',action);return b;
}
function chapterFragment(html,base){
  const parser=new DOMParser();
  const documentSource=parser.parseFromString(html,'text/html');
  const fragment=document.createDocumentFragment();
  const allow=new Set([
    'p','div','span','article','section','header','footer','main','figure','figcaption',
    'h1','h2','h3','h4','h5','h6','blockquote','q','cite','pre','code',
    'strong','b','em','i','u','s','del','ins','small','sub','sup',
    'ul','ol','li','dl','dt','dd','hr','br','img','table','thead','tbody',
    'tfoot','tr','th','td','caption','ruby','rt','rp','time','a'
  ]);
  const voidTags=new Set(['img','br','hr']);
  const imageRef=value=>{
    if(!value||value.startsWith('#')||/^(?:data:|blob:|https?:|file:|javascript:|\/\/)/i.test(value))return null;
    try{
      const location=new URL(value,base);
      return location.origin==='https://fg-assets.invalid'?
        location.href:null;
    }catch(_){return null;}
  };
  function convert(node,depth=0){
    if(depth>60)return document.createTextNode('');
    if(node.nodeType===3)return document.createTextNode(node.nodeValue||'');
    if(node.nodeType!==1)return document.createDocumentFragment();
    const tag=node.localName?.toLowerCase()||'';
    if(tag==='svg'){
      // EPUB 2 image-only pages commonly wrap the cover in SVG <image>.
      // Extract only the referenced local raster asset; never execute SVG.
      const embedded=node.querySelector('image');
      const href=embedded?.getAttribute('href')||
        embedded?.getAttribute('xlink:href')||
        embedded?.getAttributeNS('http://www.w3.org/1999/xlink','href');
      const url=imageRef(href);
      if(!url)return document.createDocumentFragment();
      const figure=el('figure','fg-book-illustration');
      const image=el('img','fg-book-cover-image');
      image.src=url;image.loading='lazy';image.decoding='async';
      image.alt=embedded?.getAttribute('aria-label')||'Book illustration';
      figure.appendChild(image);
      return figure;
    }
    if(['script','style','iframe','object','embed','form','input','video','audio',
        'noscript','math','canvas','link','meta'].includes(tag))
      return document.createDocumentFragment();
    if(!allow.has(tag)){
      const frag=document.createDocumentFragment();
      for(const child of node.childNodes)frag.appendChild(convert(child,depth+1));
      return frag;
    }
    const target=el(tag);
    if(node.hasAttribute('lang'))target.lang=node.getAttribute('lang');
    if(node.getAttribute('dir')==='rtl')target.dir='rtl';
    if(node.getAttribute('dir')==='ltr')target.dir='ltr';
    if(tag==='img'){
      const url=imageRef(node.getAttribute('src')||node.getAttribute('data-src'));
      if(!url)return document.createDocumentFragment();
      target.src=url;
      target.alt=node.getAttribute('alt')||'';
      target.loading='lazy';target.decoding='async';
      target.referrerPolicy='no-referrer';target.draggable=false;
      return target;
    }
    if(tag==='a'){
      // Footnotes stay inside the book, never navigate to external sites.
      const href=node.getAttribute('href')||'';
      if(href.startsWith('#')&&href.length<128)target.dataset.footnote=href.slice(1);
      target.setAttribute('role','link');
    }
    if(tag==='th'||tag==='td'){
      for(const key of ['rowspan','colspan']){
        const v=parseInt(node.getAttribute(key),10);
        if(v>0&&v<=20)target.setAttribute(key,String(v));
      }
    }
    for(const child of node.childNodes)target.appendChild(convert(child,depth+1));
    return target;
  }
  for(const child of documentSource.body.childNodes)
    fragment.appendChild(convert(child));
  return fragment;
}
function epub(doc){
  cleanup?.();cleanup=null;
  const bridge=window.AndroidBridge;
  const editor=$('editor'),work=$('work');
  let list=[];
  try{list=JSON.parse(bridge?.getBookContents?.()||'[]');}
  catch(error){window.showError?.('Cannot read this book index');return;}
  if(!Array.isArray(list)||!list.length){window.showError?.('This book has no readable chapters');return;}
  const key='fg.book.preferences.v2.'+String(doc.name||doc.title||'book');
  const defaults={theme:'midnight',font:'literary',size:19,line:1.7,margin:20};
  let settings={...defaults};
  try{
    const saved=JSON.parse(localStorage.getItem(key)||'null');
    if(saved&&typeof saved==='object')for(const name of Object.keys(defaults))
      if(Object.hasOwn(saved,name))settings[name]=saved[name];
  }catch(_){}
  const root=el('div','fg-book fg-book-theme-midnight');
  root.setAttribute('role','document');
  const heading=el('div','fg-book-top');
  const backTitle=el('div','fg-book-heading');
  const title=el('strong','fg-book-name',doc.title||doc.name||'Book');
  const author=el('span','fg-book-author',doc.author||'');
  backTitle.append(title,author);
  const tocButton=button('Contents',()=>showContents(true),'Open table of contents');
  const settingsButton=button('Aa',()=>showSettings(true),'Reading appearance');
  const openAnother=button('‹',()=>window.FileGestionerLibrary?.show?.(),
    'Return to library');
  openAnother.classList.add('fg-book-back');
  heading.append(openAnother,backTitle,tocButton,settingsButton);
  const scroll=el('div','fg-book-scroll');
  scroll.setAttribute('tabindex','0');
  scroll.setAttribute('aria-label','Book text. Scroll continuously to read.');
  const bookContent=el('div','fg-book-content');
  const nodes=[],loaded=new Set(),queue=new Set(),heights=new Map();
  let disposed=false,obs=null,workQueued=false,scrollFrame=0,current=0,showUi=true;
  let restoreMark=null;
  const bottom=el('div','fg-book-bottom');
  const position=el('span','fg-book-progress','Chapter 1 / '+list.length);
  const bookmark=button('◇',saveBookmark,'Bookmark reading position');
  const drawer=el('aside','fg-book-drawer fg-book-hidden');
  const drawerTitle=el('div','fg-book-drawer-title');
  const drawerClose=button('×',()=>drawer.classList.add('fg-book-hidden'),'Close settings');
  const drawerBody=el('div','fg-book-drawer-body');
  drawer.append(drawerTitle,drawerBody);
  bottom.append(position,bookmark);
  bookContent.append(...list.map((part,index)=>{
    const section=el('section','fg-book-chapter');
    section.dataset.chapter=String(index);
    section.setAttribute('aria-label','Chapter '+(index+1));
    const placeholder=el('div','fg-book-loading','');
    section.appendChild(placeholder);nodes.push(section);return section;
  }));
  scroll.appendChild(bookContent);
  root.append(heading,scroll,bottom,drawer);
  editor.classList.add('fg-reader-host');
  editor.replaceChildren(root);
  for(const id of ['sheetBar','spreadsheetTools','textFormat','notice'])
    $(id)?.classList.add('hidden');
  document.querySelector('.searchbar')?.classList.add('hidden');
  $('saveBtn').disabled=true;$('copyBtn').disabled=true;
  document.body.classList.add('fg-book-mode');
  function store(){try{localStorage.setItem(key,JSON.stringify(settings));}catch(_){}}
  function apply(){
    const theme=['midnight','paper','white','sepia'].includes(settings.theme)?
      settings.theme:'midnight';
    root.className='fg-book fg-book-theme-'+theme;
    root.style.setProperty('--fg-book-font',
      settings.font==='sans'?'system-ui, sans-serif':
      settings.font==='classic'?'Georgia, "Noto Serif", serif':
      '"Noto Serif", Georgia, serif');
    root.style.setProperty('--fg-book-font-size',
      Math.max(13,Math.min(36,Number(settings.size)||19))+'px');
    root.style.setProperty('--fg-book-leading',
      String(Math.max(1.3,Math.min(2.3,Number(settings.line)||1.7))));
    root.style.setProperty('--fg-book-side',
      Math.max(8,Math.min(55,Number(settings.margin)||20))+'px');
    store();
  }
  function toggleUi(display){
    showUi=display;heading.classList.toggle('fg-book-chrome-hidden',!showUi);
    bottom.classList.toggle('fg-book-chrome-hidden',!showUi);
  }
  function showDrawer(name){
    drawerTitle.replaceChildren(el('strong','',name),drawerClose);
    drawerBody.replaceChildren();drawer.classList.remove('fg-book-hidden');
  }
  function showContents(open){
    if(!open){drawer.classList.add('fg-book-hidden');return;}
    showDrawer('Contents');
    list.forEach((chapter,i)=>{
      const item=button(chapter.title||'Chapter '+(i+1),()=>{
        drawer.classList.add('fg-book-hidden');
        load(i);nodes[i].scrollIntoView({behavior:'auto',block:'start'});
        toggleUi(false);
      },'Go to chapter '+(i+1));
      item.classList.add('fg-book-toc-item');item.dataset.index=String(i);
      drawerBody.appendChild(item);
    });
  }
  function settingButtons(label,choices,currentKey){
    drawerBody.appendChild(el('div','fg-book-option-title',label));
    const row=el('div','fg-book-option-row');
    choices.forEach(([value,name])=>{
      const action=button(name,()=>{
        settings[currentKey]=value;apply();showSettings(true);
      });
      if(settings[currentKey]===value)action.classList.add('fg-book-option-selected');
      row.appendChild(action);
    });
    drawerBody.appendChild(row);
  }
  function showSettings(open){
    if(!open){drawer.classList.add('fg-book-hidden');return;}
    showDrawer('Reading appearance');
    settingButtons('Theme',[
      ['midnight','Night'],['paper','Paper'],['white','White'],['sepia','Sepia']
    ],'theme');
    settingButtons('Font',[
      ['literary','Literary'],['classic','Classic'],['sans','Modern']
    ],'font');
    settingButtons('Text size',[
      [16,'Small'],[19,'Comfort'],[22,'Large'],[26,'XL']
    ],'size');
    settingButtons('Line spacing',[
      [1.45,'Compact'],[1.7,'Balanced'],[2,'Airy']
    ],'line');
    settingButtons('Margins',[[12,'Narrow'],[20,'Normal'],[34,'Wide']],'margin');
  }
  function saveBookmark(){
    const item=nodes[current];
    const percent=item?.offsetHeight?
      Math.max(0,Math.min(1,(scroll.scrollTop-item.offsetTop)/item.offsetHeight)):0;
    try{localStorage.setItem(key+'.position',JSON.stringify({chapter:current,percent}));}
    catch(_){}
    bookmark.textContent='◆';
  }
  function enqueue(i){
    if(disposed||i<0||i>=nodes.length||loaded.has(i)||queue.has(i))return;
    queue.add(i);
    if(!workQueued){workQueued=true;requestAnimationFrame(process);}
  }
  function load(i){enqueue(i);}
  function process(){
    workQueued=false;if(disposed||!queue.size)return;
    const i=queue.values().next().value;queue.delete(i);
    const container=nodes[i];
    try{
      const data=JSON.parse(bridge.getBookChapter(i));
      if(data.error)throw Error(data.error);
      const chapter=el('article','fg-book-article');
      chapter.appendChild(chapterFragment(data.html||'',data.base));
      container.replaceChildren(chapter);
      loaded.add(i);
      if(container.offsetHeight>0)heights.set(i,container.offsetHeight);
      if(restoreMark&&restoreMark.chapter===i){
        const percent=Math.max(0,Math.min(1,Number(restoreMark.percent)||0));
        scroll.scrollTop=container.offsetTop+container.offsetHeight*percent;
        restoreMark=null;
      }
    }catch(error){
      container.replaceChildren(el('p','fg-book-error','This chapter could not be displayed.'));
    }
    trim();
    if(queue.size){workQueued=true;requestAnimationFrame(process);}
  }
  function trim(){
    const view=scroll.getBoundingClientRect();
    for(const index of Array.from(loaded)){
      const box=nodes[index].getBoundingClientRect();
      if(box.bottom<view.top-3*scroll.clientHeight ||
         box.top>view.bottom+3*scroll.clientHeight){
        const height=nodes[index].offsetHeight;
        if(height>0)heights.set(index,height);
        loaded.delete(index);
        const placeholder=el('div','fg-book-loading');
        placeholder.style.height=(heights.get(index)||240)+'px';
        nodes[index].replaceChildren(placeholder);
      }
    }
  }
  function track(){
    if(disposed)return;
    let nearest=current,best=Infinity;
    const marker=scroll.getBoundingClientRect().top+scroll.clientHeight*.3;
    nodes.forEach((node,i)=>{
      const r=node.getBoundingClientRect();
      const distance=marker<r.top?r.top-marker:marker>r.bottom?marker-r.bottom:0;
      if(distance<best){nearest=i;best=distance;}
    });
    current=nearest;
    position.textContent=(current+1)+' / '+list.length+
      ' · '+(list[current]?.title||'');
    for(let i=Math.max(0,current-1);i<=Math.min(nodes.length-1,current+2);i++)enqueue(i);
    trim();
  }
  scroll.addEventListener('scroll',()=>{
    if(scrollFrame)return;
    scrollFrame=requestAnimationFrame(()=>{scrollFrame=0;track();});
  },{passive:true});
  scroll.addEventListener('click',e=>{
    if(e.target.closest?.('img,a,button'))return;
    // Hide controls without interfering with ordinary reading.
    toggleUi(!showUi);
  });
  scroll.addEventListener('keydown',e=>{
    if(e.key==='Escape'){drawer.classList.add('fg-book-hidden');return;}
    if(e.key==='ArrowDown')scroll.scrollBy({top:100,behavior:'smooth'});
  });
  if(window.IntersectionObserver){
    obs=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(entry.isIntersecting)enqueue(Number(entry.target.dataset.chapter));
      });
    },{root:scroll,rootMargin:'110% 0px'});
    nodes.forEach(n=>obs.observe(n));
  }
  apply();
  enqueue(0);
  requestAnimationFrame(()=>{
    try{
      const stored=JSON.parse(localStorage.getItem(key+'.position')||'null');
      if(stored&&Number.isInteger(stored.chapter)&&stored.chapter>=0&&stored.chapter<nodes.length){
        current=stored.chapter;restoreMark=stored;enqueue(current);
        nodes[current].scrollIntoView({behavior:'auto',block:'start'});
      }
    }catch(_){}
    track();
  });
  cleanup=()=>{
    disposed=true;obs?.disconnect();queue.clear();
    if(scrollFrame)cancelAnimationFrame(scrollFrame);
    root.remove();document.body.classList.remove('fg-book-mode');
    cleanup=null;
  };
}
window.loadDocument=function(d){
  if(cleanup)cleanup();
  previous(d);
  if(d.type==='epub')epub(d);
};
window.FileGestionerBookReader={version:'1.0',supportsSpine:true,lazyChapters:true};
})();

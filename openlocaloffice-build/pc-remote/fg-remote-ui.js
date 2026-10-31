/* File Gestioner native PC viewer. Independent Koikatsu and Blender sessions.
   This displays frames rendered by PC-native applications, NEVER a fake GLB.
   The PC server is authenticated and reachable through the USB ADB loopback.
*/
(()=>{
'use strict';
// User-configured HTTPS tunnel is the normal remote transport.
const defaultLocal='http://127.0.0.1:39273';
const endpoint=()=>String(bridge()?.getRemoteEndpoint?.()||'').trim();
const URL_ROOT=()=>endpoint()||defaultLocal;
const bridge=()=>window.AndroidBridge||null;
let overlay=null,status=null,viewport=null,frame=null,active=null,kind='cube',busy=false,scheduled=false;
let yaw=.4,pitch=.2,distance=2.5,contacts=new Map(),lastSpan=0,serial=0,dead=false;
const el=(tag,cls,text)=>{
  const x=document.createElement(tag);
  if(cls)x.className=cls;
  if(text!==undefined)x.textContent=text;
  return x;
};
const setStatus=t=>{if(status)status.textContent=t;};
function showRemoteConfig(){
 const wrapper=el('div','fg-pc-remote-config');
 const text=el('input','fg-pc-remote-address');
 text.type='url';text.inputMode='url';
 text.placeholder='https://your-private-pc-tunnel.example';
 text.value=endpoint();text.setAttribute('aria-label','Secure remote PC endpoint');
 const secret=el('input','fg-pc-token');
 secret.type='password';secret.autocomplete='off';
 secret.placeholder='One-time PC authorization (only if not connected)';
 secret.setAttribute('aria-label','PC authorization key');
 secret.hidden=Boolean(bridge()?.getRemoteToken?.());
 const save=el('button','fg-pc-action','Save PC connection');
 const result=el('div','fg-pc-config-status','');
 save.onclick=()=>{
   const value=text.value.trim().replace(/\/+$/,'');
   if(!/^https:\/\/[^\s/#?]+(?::\d+)?$/.test(value)){
     result.textContent='Use an HTTPS address for the private PC relay.';return;
   }
   if(!secret.hidden && secret.value.trim()){
     bridge()?.setRemoteToken?.(secret.value.trim());
     secret.value='';
   }
   if(bridge()?.setRemoteEndpoint?.(value)){
     result.textContent='Encrypted remote connection saved for future sessions.';
     wrapper.remove();
   }else result.textContent='Remote address was rejected.';
 };
 wrapper.append(text);
 if(!secret.hidden)wrapper.append(secret);
 wrapper.append(save,result);
 return wrapper;
}
const token=()=>String(bridge()?.getRemoteToken?.()||'').trim();
async function api(path,opts={}){
  const auth=token();if(!auth)throw Error('PC authorization is not configured. Open Remote settings once.');
  const resp=await fetch(URL_ROOT()+path,{...opts,headers:{...(opts.headers||{}),'X-FG-Token':auth},cache:'no-store'});
  if(!resp.ok){
    let details='';try{details=(await resp.json()).error||''}catch(_){}
    throw Error(details||'PC bridge HTTP '+resp.status);
  }
  return resp;
}
async function render(){
  if(!active||dead||busy)return;
  busy=true;const at=++serial;
  try{
    setStatus(kind==='cube'||kind==='blend'?'Blender rendering in background…':'Koikatsu rendering in background…');
    const url='/api/frame?session='+encodeURIComponent(active)+
      '&yaw='+encodeURIComponent(yaw)+'&pitch='+encodeURIComponent(pitch)+
      '&distance='+encodeURIComponent(distance);
    const data=await (await api(url)).blob();
    if(dead||at!==serial)return;
    const objectUrl=URL.createObjectURL(data);
    const previous=frame.dataset.objectUrl;
    frame.src=objectUrl;frame.dataset.objectUrl=objectUrl;
    if(previous)URL.revokeObjectURL(previous);
    setStatus('Native frame received · drawing…');
  }catch(e){setStatus(String(e.message||e));}
  finally{
    busy=false;
    if(scheduled&&!dead){scheduled=false;render();}
  }
}
function requestFrame(){if(!active||dead)return;if(busy)scheduled=true;else render();}
async function awaitNativeReady(sid){
  const started=Date.now();
  while(!dead&&active===sid&&Date.now()-started<110000){
    try{
      const result=await (await api('/api/status?session='+encodeURIComponent(sid))).json();
      if(dead||active!==sid)return;
      if(result.error){setStatus(result.error);return;}
      if(result.ready){setStatus('Native character loaded · rendering…');requestFrame();return;}
      setStatus('Loading genuine Koikatsu character in PC Studio…');
    }catch(error){if(!dead)setStatus(String(error.message||error));return;}
    await new Promise(resolve=>setTimeout(resolve,1700));
  }
  if(!dead&&active===sid)setStatus('Koikatsu load did not finish. Reconnect to retry.');
}
function onOpen(response){
  try{
    const data=typeof response==='string'?JSON.parse(response):response;
    // Native Studio may accept the upload before it finishes loading.
    // A pending session must stay alive even when the bridge supplied an
    // informative warning; otherwise character renders never start.
    if(data.error&&!data.session){setStatus(data.error);return;}
    active=data.session||null;
    setStatus(data.ready?'Connected · preparing native 3D…':
      (data.error||'Native renderer is not yet online'));
    if(data.ready)requestFrame();
    else if(active)awaitNativeReady(active);
  }catch(e){setStatus('Invalid native PC response: '+e.message);}
}
function close(){
  dead=true;active=null;contacts.clear();serial++;
  if(frame?.dataset?.objectUrl)URL.revokeObjectURL(frame.dataset.objectUrl);
  if(overlay)overlay.remove();overlay=null;frame=null;status=null;
}
function open(nextKind='cube'){
  close();dead=false;kind=nextKind;active=null;busy=false;scheduled=false;
  yaw=.4;pitch=.2;distance=2.5;
  overlay=el('section','fg-pc-overlay');overlay.setAttribute('role','dialog');
  overlay.setAttribute('aria-label','Native PC 3D Viewer');
  const head=el('div','fg-pc-head');
  head.append(el('strong',null,kind==='koikatsu'?'Koikatsu · PC Native 3D':
    kind==='blend'?'Blender · PC Native Scene':'Blender · Independent Cube'));
  const closeButton=el('button','fg-pc-close','Close');
  closeButton.onclick=close;head.append(closeButton);overlay.append(head);
  // The paired PC is retained privately in Android preferences.
  // Do not show the token, password field, or recurring Pair prompts.
  viewport=el('div','fg-pc-viewport');
  frame=el('img','fg-pc-frame');frame.alt='Remote native 3D scene';
  frame.draggable=false;frame.hidden=true;
  frame.onload=()=>{if(!dead){frame.hidden=false;setStatus('PC-native 3D · drag to orbit · pinch to zoom');}};
  frame.onerror=()=>{if(!dead){frame.hidden=true;setStatus('Remote frame could not be displayed. Retry connection.');}};
  const placeholder=el('div','fg-pc-placeholder','Opening native 3D renderer on the connected PC…');
  viewport.append(placeholder,frame);overlay.append(viewport);
  frame.addEventListener('load',()=>{placeholder.hidden=true;});
  status=el('div','fg-pc-status','Not connected');
  overlay.append(status);
  const actions=el('div','fg-pc-actions');
  const connect=el('button','fg-pc-action','Reconnect');
  const connectNow=()=>{
    setStatus('Opening on connected PC…');
    if(!token()){setStatus('This installation needs the saved PC authorization.');return;}
    if(!endpoint()){setStatus('Configure the secure remote PC address once in Remote settings.');return;}
    try{bridge()?.remoteOpen3D?.(kind);}catch(e){setStatus(String(e));}
  };
  connect.onclick=connectNow;
  const reset=el('button','fg-pc-action','Reset view');
  reset.onclick=()=>{yaw=.4;pitch=.2;distance=2.5;requestFrame();};
  const settings=el('button','fg-pc-action','Remote settings');
  settings.onclick=()=>{
    const existing=overlay.querySelector('.fg-pc-remote-config');
    if(existing)existing.remove();
    else overlay.insertBefore(showRemoteConfig(),status);
  };
  actions.append(connect,reset,settings);overlay.append(actions);
  let center=null;
  viewport.addEventListener('pointerdown',e=>{
    viewport.setPointerCapture(e.pointerId);
    contacts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    center=null;
  });
  viewport.addEventListener('pointermove',e=>{
    if(!contacts.has(e.pointerId))return;
    const old=contacts.get(e.pointerId);
    contacts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(contacts.size===1){
      yaw+=(e.clientX-old.x)*.012;
      pitch=Math.max(-1.25,Math.min(1.25,pitch+(e.clientY-old.y)*.008));
    }else if(contacts.size===2){
      const points=[...contacts.values()];
      const span=Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y);
      if(lastSpan)distance=Math.max(1.05,Math.min(15,distance*lastSpan/Math.max(span,1)));
      lastSpan=span;
    }
  });
  const end=e=>{
    contacts.delete(e.pointerId);lastSpan=0;
    if(contacts.size===0)requestFrame();
  };
  viewport.addEventListener('pointerup',end);viewport.addEventListener('pointercancel',end);
  document.body.append(overlay);
  // The normal path is automatic, no user Pair or Open action required.
  if(token()&&endpoint())setTimeout(connectNow,0);
  else setStatus('Remote PC is not configured on this installation.');
}
window.FileGestionerRemoteViewer={open,onOpen,close};
const entry=el('button','fg-pc-entry','PC 3D');
entry.type='button';entry.setAttribute('aria-label','Open independent native Blender cube on PC');
let entryKind=null;
entry.hidden=true;
entry.onclick=()=>{if(entryKind)open(entryKind);};
const originalLoad=window.loadDocument;
if(typeof originalLoad==='function'){
  window.loadDocument=function(documentInfo){
    entryKind=documentInfo?.koikatsuCard===true?'koikatsu':
      documentInfo?.type==='model3d'&&['blend','blend1'].includes(documentInfo?.format)?'blend':null;
    entry.hidden=!entryKind;
    if(entryKind)entry.textContent=entryKind==='koikatsu'?'Open Koikatsu 3D':'Open in Blender';
    close();
    return originalLoad.apply(this,arguments);
  };
}
document.body.append(entry);
// Independent cube entry belongs to the Library's 3D tools, never on PDFs,
// books, spreadsheets or ordinary images. No permanent floating 3D control.
const cubeEntry=el('button','fg-lib-filter fg-pc-cube','Blender cube');
cubeEntry.type='button';cubeEntry.title='Render independent Blender cube on PC';
cubeEntry.onclick=()=>open('cube');
// Keep the primary Open file / Collection header uncluttered.
function placeCubeEntry(){
 const filters=document.querySelector('#fg-library .fg-lib-filters');
 if(filters&&!filters.contains(cubeEntry))filters.append(cubeEntry);
}
const observer=new MutationObserver(placeCubeEntry);
const filters=document.querySelector('#fg-library .fg-lib-filters');
if(filters){observer.observe(filters,{childList:true});placeCubeEntry();}

})();
#!/usr/bin/env python3
"""Apply final Rounder 596 UI corrections after existing gallery patches.

No replacement of images, media streams, search index, signed app identity or
TeraBox session handling. Fail hard on changed anchors.
"""
from pathlib import Path
root=Path("app/src/main/assets")
lib=root/"premium-library.js"
reader=root/"reader-controls.js"
style=root/"style.css"
polish=Path("../additions/rounder-premium-library-finish-20261121.css")
def one(src,old,new,name):
    count=src.count(old)
    if count!=1:
        raise AssertionError(f"{name}: expected one match, got {count}")
    return src.replace(old,new,1)

j=lib.read_text(encoding="utf-8")
j=one(j,"const cloudFolderButton=b('New folder','fg-lib-secondary',()=>cloudCreateFolder());",
      """const cloudFolderButton=b('+ New folder','fg-lib-secondary fg-lib-newfolder',()=>cloudCreateFolder());
 cloudFolderButton.id='pr-cloud-newfolder';
 cloudFolderButton.setAttribute('aria-label','Create folder in TeraBox');""",
      "premium cloud folder action")
# Existing read-only cloud tile menus must be visible and keyboard accessible,
# otherwise rename/move/delete are unreachable without a 580ms long-press.
j=one(j,
    " tile.append(cover,meta);",
    """ tile.append(cover,meta);
 const more=b('⋯','fg-lib-more',event=>{
   event.stopPropagation();showFileActions(item);
 });
 more.setAttribute('aria-label','More actions for '+item.name);
 more.setAttribute('title','Rename, move, copy and delete');
 meta.append(more);""",
    "visible unobtrusive file action button")
j=one(j,
    "   if(item.indexedSearch)return;\n   event.preventDefault();showFileActions(item);",
    "   event.preventDefault();showFileActions(item);",
    "cloud indexed search context actions")
j=one(j,
    "if(!item.indexedSearch && e.pointerType==='touch' && !e.target.closest('.fg-lib-more'))",
    "if(e.pointerType==='touch' && !e.target.closest('.fg-lib-more'))",
    "cloud indexed search touch actions")
# Prevent the app from offering moving a source into itself, and make the
# choice visible before invoking a native cloud mutation.
j=one(j,
    "fileAction(sheet,'Select this folder','No overwrites',()=>{",
    """const sourcePath=state.item.path||'';
     const destPath=state.path||'/';
     const invalid=destPath===sourcePath||
       destPath.startsWith(sourcePath+'/')||
       (state.action==='move'&&
        destPath===(sourcePath.slice(0,sourcePath.lastIndexOf('/'))||'/'));
     fileAction(sheet,'Select this folder',invalid?
       'This destination cannot be used':'No overwrites',()=>{""",
    "folder destination check")
j=one(j,
    "bridge()?.cloudFileOperation?.(action,source,path);\n     });",
    "bridge()?.cloudFileOperation?.(action,source,path);\n     },{disabled:invalid});",
    "disabled invalid destination")
# The folderrail is genuine navigation. The old layout had display:none
# remaining after the earlier image-mosaic removal. CSS restores it.
# Explicit open/copy/delete actions remain available via the ⋮ button.
j=one(j,
    "function folderCard(item){",
    "function folderCard(item){",
    "preserve dedicated folder cards")
# Ensure main page announces the active source correctly, including folders.
j=one(j,
    "['Provider',/com\\.openlocal\\.office\\.terabox\\.documents/.test(item.uri||'')?'TeraBox':'Android storage'],",
    "['Provider',item.terabox||/com\\.openlocal\\.office\\.terabox\\.documents/.test(item.uri||'')?'TeraBox':'Android storage'],",
    "correct cloud file properties")
lib.write_text(j,encoding="utf-8")

r=reader.read_text(encoding="utf-8")
# A fully immersive viewer starts with no persistent controls. Tapping the
# visible image presents actionable controls for four seconds; touching the
# toolbar itself holds them. Android Back and swipe navigation keep working.
r=one(r,
    "  bar.classList.add('fg-image-toolbar-collapsed');",
    """  let imageNavTimer=0;
  function hideImageNav(){
    bar.classList.add('fg-image-toolbar-hidden');
    bar.classList.remove('fg-image-toolbar-expanded');
    bar.classList.add('fg-image-toolbar-collapsed');
    collapse.textContent='⋯';
  }
  function revealImageNav(){
    clearTimeout(imageNavTimer);
    bar.classList.remove('fg-image-toolbar-hidden','fg-image-toolbar-collapsed');
    bar.classList.add('fg-image-toolbar-expanded');
    collapse.textContent='×';
    imageNavTimer=setTimeout(hideImageNav,4300);
  }
  bar.classList.add('fg-image-toolbar-hidden','fg-image-toolbar-collapsed');
  view.addEventListener('pointerup',e=>{
    if(e.button!==undefined&&e.button!==0)return;
    if(e.isPrimary===false)return;
    revealImageNav();
  },{passive:true,capture:true});
  bar.addEventListener('pointerdown',()=>clearTimeout(imageNavTimer),{passive:true});
  bar.addEventListener('pointerup',()=>{clearTimeout(imageNavTimer);
    if(!bar.classList.contains('fg-image-toolbar-hidden'))
      imageNavTimer=setTimeout(hideImageNav,4300);
  },{passive:true});""",
    "tap-only image controls")
reader.write_text(r,encoding="utf-8")

css=polish.read_text(encoding="utf-8")
if ".fg-library-root .fg-vault-folderrail{" not in css:
    raise AssertionError("Premium folder rail visual contract missing")
style.write_text(style.read_text(encoding="utf-8")+"\n"+css,
                 encoding="utf-8")
print("ROUNDER_PREMIUM_FINISH_READY: folder rail visible, real menus, no persistent image bar")

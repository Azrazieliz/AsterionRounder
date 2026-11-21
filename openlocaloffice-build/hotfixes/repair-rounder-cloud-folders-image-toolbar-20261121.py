#!/usr/bin/env python3
"""Fix Rounder gallery navigation leak and replace broken cloud-folder previews.

Applied only after the existing signed-APK assembly overlays. Does not touch
image pixels, app identity, readers, or TeraBox credentials.
"""
from pathlib import Path

root=Path("app/src/main")
lib=root/"assets/premium-library.js"
reader=root/"assets/reader-controls.js"
style=root/"assets/style.css"

def once(text,old,new,label):
    n=text.count(old)
    if n!=1:raise AssertionError("%s anchor: %s" % (label,n))
    return text.replace(old,new,1)

j=lib.read_text(encoding="utf-8")

# Do not request or display unstable folder-cover mosaics. Preserve media file
# thumbnail requests: those are separate and essential to the user's gallery.
for call in [
    "bridge()?.fetchTeraboxFolderPreviews?.(JSON.stringify(pending));",
    "bridge()?.fetchTeraboxFolderPreviews?.(JSON.stringify(folders));"
]:
    j=once(j,call,"void 0; /* No remote folder mosaic fetch. */",
           "remove broken folder cover fetch")

start=j.index("function folderCard(item){")
end=j.index("function drawFolderRail(",start)
folder=r'''function folderCard(item){
  const [symbol,type]=folderAccent(item.name);
  const row=E('article','fg-vault-folder-row');
  const open=b('','fg-vault-folder fg-vault-folder-'+type,()=>openBook(item));
  open.setAttribute('aria-label','Open folder '+item.name);
  const art=E('span','fg-vault-folder-art');
  art.append(E('span','fg-vault-folder-glyph',symbol));
  const meta=E('span','fg-vault-folder-content');
  meta.append(E('strong','',item.name),E('small','','TeraBox folder'));
  open.append(art,meta,E('span','fg-vault-folder-chevron','›'));
  const actions=b('⋮','fg-vault-folder-actions',()=>showFileActions(item));
  actions.setAttribute('aria-label','Actions for folder '+item.name);
  row.append(open,actions);
  return row;
}
'''
j=j[:start]+folder+j[end:]

# The legacy fallback card path sometimes received folder entries even though
# the continuous gallery renders a dedicated folder rail. Reuse the same
# compact icon row instead of allowing legacy mosaic and fallback overlays.
j=once(j,"function card(item,i){",
       "function card(item,i){\n if(item.folder)return folderCard(item);",
       "folder image-free fallback")

# Do not let the previous fixed-position reader toolbar be drawn on top of
# the cloud library when an image was closed or user navigates Back.
j=once(j,"function show(){",
       "function show(){\n document.body.classList.add('fg-rounder-library-visible');",
       "library visibility on show")
j=once(j,"function hideForReader(){",
       "function hideForReader(){\n document.body.classList.remove('fg-rounder-library-visible');",
       "image reader visibility")
j=once(j,"function showTeraboxSettings(){",
       "function showTeraboxSettings(){\n document.body.classList.add('fg-rounder-library-visible');",
       "cloud settings visibility")
j=once(j,"function error(message){",
       "function error(message){\n document.body.classList.add('fg-rounder-library-visible');",
       "library error visibility")
lib.write_text(j,encoding="utf-8")

r=reader.read_text(encoding="utf-8")
old="const collapse=btn('⌄','Toggle image controls',()=>bar.classList.toggle('fg-image-toolbar-small'));"
new="""const collapse=btn('⋯','Toggle image controls',()=>{
    const expanded=bar.classList.toggle('fg-image-toolbar-expanded');
    bar.classList.toggle('fg-image-toolbar-collapsed',!expanded);
    collapse.textContent=expanded?'×':'⋯';
  });
  collapse.classList.add('fg-image-toolbar-toggle');
  bar.classList.add('fg-image-toolbar-collapsed');"""
r=once(r,old,new,"image toolbar compact reveal control")
reader.write_text(r,encoding="utf-8")

css=r'''
/* Rounder: no reader controls on top of the active file library. */
body.fg-rounder-library-visible .fg-image-toolbar,
body.fg-rounder-library-visible .fg-controls,
body:has(.fg-library-root:not(.fg-lib-hidden)) .fg-image-toolbar,
body:has(.fg-library-root:not(.fg-lib-hidden)) .fg-controls{
  display:none!important;
}
/* Image reader: unobtrusive compact reveal, never full-width persistent bar. */
.fg-image-reader .fg-image-toolbar{
  position:fixed!important;
  top:auto!important;
  left:auto!important;
  right:12px!important;
  bottom:calc(9px + env(safe-area-inset-bottom))!important;
  display:flex!important;
  flex-direction:row!important;
  justify-content:center!important;
  align-items:center!important;
  gap:2px!important;
  box-sizing:border-box!important;
  width:auto!important;
  max-width:calc(100vw - 24px)!important;
  height:auto!important;
  min-height:0!important;
  margin:0!important;
  padding:3px!important;
  border:1px solid #ffffff24!important;
  border-radius:14px!important;
  background:rgba(13,20,32,.86)!important;
  box-shadow:0 2px 8px #0005!important;
  transform:none!important;
  opacity:1!important;
  z-index:150!important;
  backdrop-filter:blur(8px);
}
.fg-image-reader .fg-image-toolbar.fg-image-toolbar-collapsed{
  width:40px!important;height:40px!important;
  padding:2px!important;
}
.fg-image-reader .fg-image-toolbar.fg-image-toolbar-collapsed > :not(.fg-image-toolbar-toggle){
  display:none!important;
}
.fg-image-reader .fg-image-toolbar button{
  display:inline-flex!important;
  box-sizing:border-box!important;
  align-items:center!important;
  justify-content:center!important;
  width:36px!important;min-width:36px!important;max-width:36px!important;
  height:36px!important;min-height:36px!important;max-height:36px!important;
  margin:0!important;padding:0!important;border-radius:10px!important;
  font:650 15px system-ui!important;
}
.fg-image-reader .fg-image-toolbar .fg-image-toolbar-toggle{
  display:inline-flex!important;
}
.fg-image-reader .fg-image-toolbar.fg-image-toolbar-expanded{
  right:10px!important;left:10px!important;
  width:auto!important;max-width:none!important;
  justify-content:space-around!important;
}
.fg-image-reader .fg-image-toolbar-expanded .fg-image-position{
  display:block!important;
  min-width:52px!important;
  font:600 12px/1.2 system-ui!important;
  white-space:nowrap!important;
}
.fg-image-reader .fg-image-toolbar-expanded .fg-control-mode{
  width:auto!important;min-width:68px!important;max-width:92px!important;
  padding:0 7px!important;font:600 12px system-ui!important;
}
/* Stable, short icon-driven folder navigation; no broken cover gallery tiles. */
.fg-library-root .fg-vault-folder-row{
  display:grid!important;
  grid-template-columns:minmax(0,1fr) 36px!important;
  gap:5px!important;
  min-width:0!important;
  align-items:stretch!important;
}
.fg-library-root .fg-vault-folder-row .fg-vault-folder{
  width:100%!important;height:70px!important;
  min-height:70px!important;min-width:0!important;
}
.fg-library-root .fg-vault-folder-row .fg-vault-folder-art{
  width:43px!important;min-width:43px!important;height:44px!important;
  border-radius:10px!important;
}
.fg-library-root .fg-vault-folder-row .fg-vault-folder-actions{
  display:flex!important;align-items:center!important;justify-content:center!important;
  min-width:36px!important;min-height:44px!important;height:70px!important;
  padding:0!important;border:1px solid #344a60!important;
  border-radius:12px!important;background:#17273c!important;
  color:#d8c7ae!important;font:700 20px system-ui!important;
}
.fg-library-root .fg-vault-folder-grid{
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  gap:8px!important;
}
.fg-library-root .fg-premium-folder .fg-premium-mosaic,
.fg-library-root .fg-vault-folder-art .fg-vault-folder-image,
.fg-library-root .fg-vault-folder-art.fg-vault-has-cover img,
.fg-library-root .fg-premium-folder .fg-lib-cover-image{
  display:none!important;
}
.fg-library-root .fg-vault-folder-row .fg-vault-folder-content strong{
  overflow:hidden!important;text-overflow:ellipsis!important;
  white-space:nowrap!important;
}
@media(max-width:390px){
 .fg-library-root .fg-vault-folder-grid{grid-template-columns:1fr!important;}
}
'''
with style.open("a",encoding="utf-8") as output:output.write("\n"+css)
print("ROUNDER_GALLERY_CHROME_AND_FOLDER_ICON_REPAIR_READY")

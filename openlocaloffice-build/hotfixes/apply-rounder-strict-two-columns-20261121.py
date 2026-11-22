#!/usr/bin/env python3
"""Two columns, everywhere in Rounder's default visual library.

The mobile overflow came from reusing the legacy full-width folder row in a
narrow grid. Replace just the folder card and synchronize the virtual folder
row height with CSS. No TeraBox account, metadata or file operation touched.
"""
from pathlib import Path
root=Path("app/src/main/assets")
js=root/"premium-library.js"
style=root/"style.css"
css=Path("../additions/rounder-strict-two-columns-20261121.css")
source=js.read_text(encoding="utf-8")
start=source.index("function folderCard(item){")
end=source.index("function drawFolderRail(",start)
assert start < end
folder=r'''function folderCard(item){
 const [,kind]=folderAccent(item.name);
 const tile=E('article','fg-vault-folder-row fg-vault-folder-'+kind);
 const open=b('','fg-vault-folder',()=>openBook(item));
 open.setAttribute('aria-label','Open folder '+item.name);
 open.title=item.name;
 const artwork=E('span','fg-vault-folder-art');
 const ns='http://www.w3.org/2000/svg';
 const svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 24 24');
 svg.setAttribute('width','24');
 svg.setAttribute('height','24');
 svg.setAttribute('fill','none');
 svg.setAttribute('stroke','currentColor');
 svg.setAttribute('stroke-width','1.8');
 svg.setAttribute('stroke-linecap','round');
 svg.setAttribute('stroke-linejoin','round');
 svg.setAttribute('aria-hidden','true');
 const shape=document.createElementNS(ns,'path');
 shape.setAttribute('d','M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z');
 svg.append(shape);artwork.append(svg);
 const meta=E('span','fg-vault-folder-content');
 const title=E('strong','fg-vault-folder-name',item.name);
 title.title=item.name;
 meta.append(title,E('small','','Folder · TeraBox'));
 open.append(artwork,meta);
 const actions=b('⋯','fg-vault-folder-actions',()=>showFileActions(item));
 actions.setAttribute('aria-label','Manage folder '+item.name);
 actions.title='Rename, copy, move or delete '+item.name;
 tile.append(open,actions);
 return tile;
}
'''
source=source[:start]+folder+source[end:]
old=""" const columns=body.clientWidth>=700?
   Math.max(1,Math.floor((folderRail.clientWidth+8)/208)):2;
 const rows=Math.ceil(folders.length/columns),rowHeight=84;"""
new=""" const columns=2;
 const rows=Math.ceil(folders.length/columns),rowHeight=140;"""
if source.count(old)!=1:raise AssertionError("folder virtualization column contract changed")
source=source.replace(old,new,1)
# The latest assembled source already defaults to visual cards. Keep list
# presentation only when the user explicitly selects List mode.
if source.count("const useList=list;")!=1:
    raise AssertionError("default 2-column media contract changed")
js.write_text(source,encoding="utf-8")
css_text=css.read_text(encoding="utf-8")
assert "grid-template-columns:repeat(2,minmax(0,1fr))" in css_text
with style.open("a",encoding="utf-8") as sink:
    sink.write("\n/* Final two-column folder and media layout after all overlays */\n"+css_text)
print("ROUND_TWO_COLUMNS_VERIFIED: 2 folder columns; 2 media columns; virtual rows 140px")

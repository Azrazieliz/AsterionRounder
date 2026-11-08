#!/usr/bin/env python3
"""Rounder v0.15.22: compact real-library UI and visual duplicate selection.
Apply LAST, after source feature assembly, classic rollback and its tests.
All native TeraBox logic, virtual pagination, readers and update verifier remain.
"""
from pathlib import Path
import re
base=Path("app/src/main")
js=base/"assets/premium-library.js"
s=js.read_text(encoding="utf-8")
def once(old,new,reason):
    global s
    count=s.count(old)
    if count!=1:raise AssertionError(f"{reason}: expected 1 occurrence, found {count}")
    s=s.replace(old,new,1)

once("actions.append(openBtn,organizeBtn,updateBtn,settingsBtn);",
"""openBtn.textContent='Open';
openBtn.setAttribute('aria-label','Open a local Android file');
organizeBtn.textContent='Organize';
updateBtn.textContent='Update';
settingsBtn.setAttribute('aria-label','TeraBox settings');
actions.append(openBtn,organizeBtn,updateBtn,settingsBtn);""",
"compact functional header")
once("""   virtualFolders=[];
   virtualFiles=items;
   virtualHasCovers=virtualFiles.some(e=>!!e.cover);""",
"""   virtualFolders=items.filter(e=>e.folder);
   virtualFiles=items.filter(e=>!e.folder);
   virtualHasCovers=virtualFiles.some(e=>!!e.cover);""",
"folders as compact navigation rows")
once(" drawFolderRail([],mode);",
" drawFolderRail(virtualFolders,mode);","restore actual folders to existing virtual folder rail")
once(" const useList=list;",
" const useList=list||!virtualHasCovers||filter==='document'||filter==='file';",
"non-image files default to compact rows")
once(" const rowHeight=useList?124:Math.ceil(cellWidth*1.5+86);",
" const rowHeight=useList?78:Math.ceil(cellWidth*1.25+79);",
"accurate continuous file list geometry")
old_label="mode==='search'?'Matching collections':'Collections'"
assert s.count(old_label)==2,"Expected two folder labels"
s=s.replace(old_label,"mode==='search'?'Matching folders':'Folders'")
once("meta.append(E('strong','',item.name),E('small','','Folder · TeraBox'));",
"meta.append(E('strong','',item.name),E('small','','Folder'));",
"no generic open collection label")
once("if(detail)detail.textContent='Open collection';",
"if(detail)detail.textContent='Folder';",
"fallback folder metadata")
old_heading="heading.textContent=cloudMode?(currentFolder?'Collection':'Your library'):'Your library';"
assert s.count(old_heading)==2,"Expected two library heading assignments"
s=s.replace(old_heading,
    "heading.textContent=cloudMode?(currentFolder?currentFolder.split('/').filter(Boolean).slice(-1)[0]:'TeraBox'):'Local files';")
# Updated duplicate viewer is assembled inside the existing organizer fragment.
assert "renderDuplicateWorkspace(body)" in s
assert "function managerCleanupProgress(event)" in s
assert "organizerCleanupDuplicates" in s
assert "renderDuplicateCleanupFooter(shell)" in s

js.write_text(s,encoding="utf-8")
css=base/"assets/style.css"
theme=Path("../additions/rounder-compact-visual-ui.css").read_text(encoding="utf-8")
assert ".fg-review-rail" in theme and ".fg-vault-folder-grid" in theme
css.write_text(css.read_text(encoding="utf-8")+"\n"+theme,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)43\b',r'\g<1>44',g,count=1)
if n!=1:raise AssertionError("Expected prior restored UI versionCode 43")
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.21"',r'\g<1>"0.15.22"',g,count=1)
if n!=1:raise AssertionError("Expected prior restored UI versionName")
gradle.write_text(g,encoding="utf-8")
print("ROUNDER_VISUAL_DUPES_UI_OK: compact header, real folder previews, continuous gallery, visual duplicate cleanup")

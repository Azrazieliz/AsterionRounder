#!/usr/bin/env python3
"""Rounder v0.15.23: compact header and visual duplicate selection, original cards untouched.
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
# Preserve existing approved card rendering EXACTLY as restored by the
# previous stage. No folder rail, no layout/sizing/list-mode overrides.
assert "   virtualFolders=[];" in s
assert "   virtualFiles=items;" in s
assert " drawFolderRail([],mode);" in s
assert " const useList=list;" in s
assert " const rowHeight=useList?124:Math.ceil(cellWidth*1.5+86);" in s
# Only replace the redundant folder caption text; do not touch card structure.
once("if(detail)detail.textContent='Open collection';",
     "if(detail)detail.textContent='Folder';",
     "replace useless folder caption without altering its card")
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
assert ".fg-review-rail" in theme and ".fg-lib-header" in theme
assert ".fg-lib-grid.fg-vault-media-grid" not in theme
css.write_text(css.read_text(encoding="utf-8")+"\n"+theme,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)43\b',r'\g<1>45',g,count=1)
if n!=1:raise AssertionError("Expected prior restored UI versionCode 43")
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.21"',r'\g<1>"0.15.23"',g,count=1)
if n!=1:raise AssertionError("Expected prior restored UI versionName")
gradle.write_text(g,encoding="utf-8")
print("ROUNDER_VISUAL_DUPES_UI_OK: original cards preserved, compact header, visual duplicate cleanup")

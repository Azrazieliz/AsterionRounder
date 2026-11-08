#!/usr/bin/env python3
"""Restore Rounder's approved pre-Atlas/Obsidian library presentation.

The October/early-November base UI was still in the repository. Restore its
native layout, spacing, original file and folder cards, and existing colors.
DO NOT change TeraBox-first mode, recursive search, organizer, streaming,
continuous scrolling, readers, or signed in-app updater.
Run after the 0.15.20 UI assembly and before Android build/signing.
"""
from pathlib import Path
import re

base=Path("app/src/main")
js=base/"assets/premium-library.js"
s=js.read_text(encoding="utf-8")
css=base/"assets/style.css"
style=css.read_text(encoding="utf-8")
def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise AssertionError(f"{label}: expected one anchor; got {s.count(old)}")
    s=s.replace(old,new,1)

# Earlier cards represented folders and files in one gallery. The
# 2026-11-08 experiments split directories into a separate folder rail.
# Restore the old unified card grid but KEEP bounded, page-free scrolling.
once("""   virtualFolders=items.filter(e=>e.folder);
   virtualFiles=items.filter(e=>!e.folder);
   virtualHasCovers=virtualFiles.some(e=>!!e.cover);""",
"""   virtualFolders=[];
   virtualFiles=items;
   virtualHasCovers=virtualFiles.some(e=>!!e.cover);""",
"unified original folder/file gallery")
once(" drawFolderRail(virtualFolders,mode);",
     " drawFolderRail([],mode);","remove new folder rail")
once(" const useList=list||!virtualHasCovers||filter==='document'||filter==='file';",
     " const useList=list;","restore original default grid")
once(" const rowHeight=useList?78:276;",
""" const gridWidth=Math.max(100,deck.clientWidth);
 const cellWidth=(gridWidth-15*Math.max(0,columns-1))/columns;
 const rowHeight=useList?124:Math.ceil(cellWidth*1.5+86);""",
"support original aspect ratio with virtual scrolling")
once("""fallback.append(E('span','fg-lib-fallback-glyph',icon(c)));""",
"""fallback.append(E('span','fg-lib-fallback-glyph',icon(c)),
                 E('strong','fg-lib-fallback-title',item.title));""",
"restore original cover name design")
# Reintroduce previous title/count. Leave app/source state as TeraBox-first.
s=s.replace("heading.textContent=cloudMode?(currentFolder?'Folder':'TeraBox'):'Local files';",
            "heading.textContent=cloudMode?(currentFolder?'Collection':'Your library'):'Your library';")
# We don't reintroduce old local/cloud selection buttons: local storage stays
# accessible through Open file; the user's TeraBox-only constraint survives.
# Organize and Update are retained as working buttons.
js.write_text(s,encoding="utf-8")

# Restore all style rules before the two design experiments. The older
# production UI styling is already present earlier in app/src/main/assets/style.css.
marker="/* Atlas × Obsidian cloud-first Rounder 0.15.17. Real metadata/previews only. */"
if style.count(marker)!=1:
    raise AssertionError("Cannot locate the exact premium redesign CSS boundary")
old_style=style[:style.index(marker)]
premium=Path("../additions/rounder-premium-theme.css").read_text(encoding="utf-8")
continuous=Path("../additions/rounder-continuous-ui.css").read_text(encoding="utf-8")
org_start=premium.find(".fg-org-backdrop")
updater_start=continuous.find("/* Native signed update sheet */")
if org_start<0 or updater_start<0:
    raise AssertionError("Functional organizer/updater CSS sections missing")
# Only feature-related sheets are retained. The previous redesign and the
# experimental compact card/header rules are intentionally NOT re-added.
restored=old_style+"\n"+"""/* Asterion Rounder: restored original library UI. Native features preserved. */
.fg-premium-eyebrow{color:#d4ad82;font:700 10px/1.2 system-ui;letter-spacing:.15em}
.fg-library-root .fg-lib-actions{display:flex;flex-wrap:wrap;align-items:center;gap:7px}
.fg-library-root .fg-vault-update{color:#d6dcef!important;background:#283449!important;
 border:1px solid #52617d!important;border-radius:11px}
.fg-library-root .fg-vault-update-available{border-color:#d5b087!important;
 color:#e2bd93!important}
.fg-library-root .fg-vault-folderrail{display:none!important}
.fg-library-root .fg-vault-spacer{display:block!important;min-height:0!important}
.fg-library-root .fg-lib-pager,.fg-library-root .fg-lib-page-control{display:none!important}
.fg-library-root .fg-premium-intro{display:none!important}
.fg-library-root .fg-lib-actions button{min-height:36px}
.fg-library-root .fg-lib-grid{align-content:start}
.fg-library-root .fg-lib-tile{min-width:0}
.fg-library-root .fg-lib-grid .fg-lib-tile .fg-lib-fallback-title{display:-webkit-box}
.fg-library-root .fg-lib-grid.fg-lib-list .fg-lib-tile .fg-lib-fallback-title{display:none}
@media(max-width:510px){
 .fg-library-root .fg-lib-header{flex-wrap:wrap}
 .fg-library-root .fg-lib-brand{width:100%}
 .fg-library-root .fg-lib-actions{width:100%;flex-wrap:nowrap}
 .fg-library-root .fg-lib-actions button{flex:1 1 auto;min-width:0;
   padding:7px 8px!important;font-size:11px!important}
 .fg-library-root .fg-lib-actions .fg-premium-settings{flex:0 0 41px}
}
"""+"\n"+premium[org_start:]+"\n"+continuous[updater_start:]
css.write_text(restored,encoding="utf-8")

# Make a real Android-updateable restoration package; static source versions
# are replaced with the unique workflow run number during release stamping.
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r"(\bversionCode\s*=\s*)42\b",r"\g<1>43",g,count=1)
if n!=1:raise AssertionError("Expected source versionCode 42")
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.20"',r'\g<1>"0.15.21"',g,count=1)
if n!=1:raise AssertionError("Expected source versionName 0.15.20")
gradle.write_text(g,encoding="utf-8")
print("ROUNDER_CLASSIC_UI_RESTORED: original library card design, no page buttons, native functions preserved")

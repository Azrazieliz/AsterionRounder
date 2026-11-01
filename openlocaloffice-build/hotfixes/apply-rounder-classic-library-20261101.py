#!/usr/bin/env python3
"""v0.15.12: restore v0.15.10 library appearance, retain removal of Home.
Only library UI is reversed; player/3D/reader/ZIP fixes remain in place."""
from pathlib import Path
import re
root=Path("app")
assets=root/"src/main/assets"
lib=assets/"premium-library.js"
s=lib.read_text(encoding="utf-8")
def replace(a,b,label):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError(f"{label}: expected 1, saw {n}")
    s=s.replace(a,b,1)
replace("search.placeholder='Search files';",
        "search.placeholder='Search your books';","v0.15.10 search caption")
replace(""" tile.setAttribute('role','button');tile.setAttribute('tabindex','0');
 tile.setAttribute('aria-label',item.name+'. Hold to open file actions');""",
        " tile.setAttribute('role','button');tile.setAttribute('tabindex','0');",
        "original tile semantics")
replace(""" tile.addEventListener('contextmenu',e=>{e.preventDefault();showFileActions(item);});
 tile.addEventListener('click',e=>{""",
        " tile.addEventListener('click',e=>{","original card events")
replace(""" // Document-heavy directories get readable, compact rows; previews are
 // preserved for image/video/archive collections instead of giant placeholders.
 const visualCount=shown.filter(x=>['image','video','comic','book','pdf'].includes(classify(x))).length;
 deck.classList.toggle('fg-lib-compact-files',
   !list&&shown.length>0&&visualCount<shown.length*.45);
 const visiblePage=shown.slice(pageStart,pageStart+PAGE);""",
        " const visiblePage=shown.slice(pageStart,pageStart+PAGE);",
        "original card grid including ordinary files")
assert "body.append(toolbar,filters,loading,deck,empty,footer);" in s
assert "welcome.hidden=true;dashboard.hidden=true;" in s
assert "function drawDashboard(){\n dashboard.hidden=true;return;" in s
lib.write_text(s,encoding="utf-8")
css=assets/"style.css"
t=css.read_text(encoding="utf-8")
start=t.index("/* v0.15.11: clean collection; videos always two across on phones. */")
end=t.index("/* Page: one at a time. V-scroll: normal. H-scroll: continuous, never snapping. */",start)
t=t[:start]+t[end:]
# Preserve earlier 3-across mobile layout, filenames, type badges, menu, all original cover dimensions.
assert ".fg-lib-grid:not(.fg-lib-list)" in t
assert "repeat(3,minmax(0,1fr))!important;" in t
assert ".fg-library-root .fg-lib-more{" in t
css.write_text(t,encoding="utf-8")
gradle=root/"build.gradle.kts"
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)33\b',r'\g<1>34',g,count=1)
if n!=1:raise RuntimeError("expected versionCode 33")
g,n=re.subn(r'(\bversionName\s*(?:=\s*)?)"0\.15\.11"',r'\g<1>"0.15.12"',g,count=1)
if n!=1:raise RuntimeError("expected versionName 0.15.11")
gradle.write_text(g,encoding="utf-8")
print("V0_15_10_LIBRARY_RESTORED_HOME_ABSENT_ALL_OTHER_FIXES_RETAINED")

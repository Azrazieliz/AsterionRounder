#!/usr/bin/env python3
"""Finish v0.15.18 premium organizer assembly using preserved source fragments."""
from pathlib import Path
import re
base=Path("app/src/main")
lib=base/"assets/premium-library.js"
s=lib.read_text(encoding="utf-8")
anchor="function handleAndroidBack(){"
assert s.count(anchor)==1, "Native back handler anchor changed"
fragment=Path("../additions/rounder-organizer-ui-fragment.js").read_text(encoding="utf-8")
assert "function managerProgress(event)" in fragment
assert "function showOrganizer()" in fragment
assert "function managerError(data)" in fragment
visual=Path("../additions/rounder-visual-duplicates.js").read_text(encoding="utf-8")
assert "function renderDuplicateWorkspace(body)" in visual
assert "function managerCleanupProgress(event)" in visual
s=s.replace(anchor,fragment+"\n"+visual+"\n"+anchor,1)
lib.write_text(s,encoding="utf-8")
theme=Path("../additions/rounder-premium-theme.css").read_text(encoding="utf-8")
assert ".fg-org-backdrop" in theme and ".fg-premium-mosaic" in theme
css=base/"assets/style.css"
style=css.read_text(encoding="utf-8")
assert "Atlas × Obsidian cloud-first Rounder 0.15.17" not in style
css.write_text(style+"\n"+theme,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
g=gradle.read_text(encoding="utf-8")
g,n=re.subn(r'(\bversionCode\s*=\s*)38\b',r'\g<1>40',g,count=1)
assert n==1,"Expected previous v0.15.16 versionCode 38"
g,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.16"',r'\g<1>"0.15.18"',g,count=1)
assert n==1,"Expected v0.15.16 versionName"
gradle.write_text(g,encoding="utf-8")
print("ROUNDER_PREMIUM_ORGANIZER_V0.15.18_ASSEMBLED")

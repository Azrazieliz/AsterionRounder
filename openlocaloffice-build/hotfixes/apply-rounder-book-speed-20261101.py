#!/usr/bin/env python3
"""Bounded ZIP/EPUB prefetch; preserve original user files and image quality."""
from pathlib import Path
root=Path("app/src/main/assets")
p=root/"universal-reader.js"
s=p.read_text(encoding="utf-8")
old="const MAX_IMAGE_FETCHES=remoteArchive?2:3;"
assert s.count(old)==1
s=s.replace(old,"const MAX_IMAGE_FETCHES=3; // bounded concurrent archive image streams",1)
old="{root:body,rootMargin:'30% 0px'}"
assert s.count(old)==1
s=s.replace(old,"{root:body,rootMargin:'65% 0px'}",1)
p.write_text(s,encoding="utf-8")
p=root/"epub-reader.js";s=p.read_text(encoding="utf-8")
if 'Never erase previously rendered illustrations' not in s:
    old='  function trim(){'
    assert s.count(old)==1
    s=s.replace(old,'  function trim(){\n    // Never erase previously rendered illustrations.\n    return;',1)
old="target.loading='lazy';target.decoding='async';"
assert s.count(old)==1
s=s.replace(old,"target.loading='eager';target.decoding='async';",1)
old="{root:scroll,rootMargin:'110% 0px'}"
assert s.count(old)==1
s=s.replace(old,"{root:scroll,rootMargin:'140% 0px'}",1)
p.write_text(s,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
s=gradle.read_text(encoding="utf-8")
assert s.count("versionCode = 34")==1 and s.count('versionName = "0.15.12"')==1
s=s.replace("versionCode = 34","versionCode = 35",1).replace('versionName = "0.15.12"','versionName = "0.15.13"',1)
gradle.write_text(s,encoding="utf-8")
print("BOUNDED_ARCHIVE_PREFETCH_AND_EPUB_IMAGE_PRIORITY_READY")

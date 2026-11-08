#!/usr/bin/env python3
"""Stamp CI release identity so each signed APK can update its predecessor.
Only run after the static UI and updater checks have passed.
"""
from pathlib import Path
import json
import re
import sys

if len(sys.argv)!=2 or not sys.argv[1].isdigit():
    raise SystemExit("Pass the numeric GitHub Actions run number")
run=int(sys.argv[1])
if not (46 < run < 2_100_000_000):
    raise SystemExit("Release number must exceed the last static Android versionCode")
build=Path("app/build.gradle.kts")
data=build.read_text(encoding="utf-8")
data,n=re.subn(r'(\bversionCode\s*=\s*)46\b',lambda m:m.group(1)+str(run),data,count=1)
if n!=1:raise AssertionError("Expected Rounder v0.15.24 source versionCode 46")
data,n=re.subn(r'(\bversionName\s*=\s*)"0\.15\.24"',lambda m:m.group(1)+'"0.15.24.'+str(run)+'"',data,count=1)
if n!=1:raise AssertionError("Expected Rounder v0.15.20 source versionName")
build.write_text(data,encoding="utf-8")
asset=Path("app/src/main/assets/rounder-build.json")
asset.write_text(json.dumps({
    "releaseRun":run,
    "versionCode":run,
    "baseVersion":"0.15.24"
},separators=(",",":"))+"\n",encoding="utf-8")
assert json.loads(asset.read_text())["versionCode"]==run
print("ROUNDER_RELEASE_IDENTITY_OK run="+str(run)+" versionCode="+str(run))

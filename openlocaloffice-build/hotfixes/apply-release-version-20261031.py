#!/usr/bin/env python3
"""Bump retained production package identity for in-place signed upgrades."""
from pathlib import Path
import re
gradle=Path("app/build.gradle")
if not gradle.exists():gradle=Path("app/build.gradle.kts")
s=gradle.read_text()
def replace(pattern,new,label):
    global s
    s,count=re.subn(pattern,new,s,count=1)
    if count!=1:raise RuntimeError(f"Cannot update {label} in {gradle}")
replace(r'(?m)(\bversionCode\s*(?:=\s*)?)\d+',r'\g<1>13','versionCode')
replace(r'(?m)(\bversionName\s*(?:=\s*)?)["\'][^"\']+["\']',
        r'\g<1>"0.14.1"','versionName')
gradle.write_text(s)
print("Production package: versionCode 13, versionName 0.14.1, unchanged applicationId")

#!/usr/bin/env python3
"""Build independently installable preview without replacing user's existing signed app."""
from pathlib import Path
import re
p=Path("app/build.gradle.kts")
s=p.read_text()
target=r'(applicationId\s*=\s*"com\.openlocal\.office")'
s,n=re.subn(target,lambda m:m.group(1)+
    '\n        applicationIdSuffix = ".premiumfix"\n        versionNameSuffix = "-premiumfix"',s,count=1)
assert n==1,"Android package ID could not be safely adjusted"
p.write_text(s)
print("Parallel safe preview package: com.openlocal.office.premiumfix")

from pathlib import Path
import re
p=Path('app/build.gradle.kts')
if not p.exists():p=Path('app/build.gradle')
s=p.read_text(encoding='utf-8')
assert '0.15.0' in s
s,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)22\b',r'\g<1>23',s,count=1)
assert n==1
p.write_text(s.replace('0.15.0','0.15.1',1),encoding='utf-8')
print('Asterion Rounder 0.15.1 code23: 2MB bounded cloud ZIP64 range reads')

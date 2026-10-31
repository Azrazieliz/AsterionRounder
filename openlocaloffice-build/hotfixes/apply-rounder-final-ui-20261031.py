from pathlib import Path
import re
p=Path('app/build.gradle.kts')
if not p.exists():p=Path('app/build.gradle')
s=p.read_text(encoding='utf-8')
assert '0.14.7' in s
s,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)19\b',r'\g<1>20',s,count=1)
assert n==1
s=s.replace('0.14.7','0.14.8',1)
p.write_text(s,encoding='utf-8')
print('Asterion Rounder 0.14.8 code20, original package and release signer retained')

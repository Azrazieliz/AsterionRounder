from pathlib import Path
import re
root=Path('app/src/main')
manifest=root/'AndroidManifest.xml'
m=manifest.read_text()
needle='android:name="com.openlocal.office.core.FgTeraboxDocumentsProvider"'
assert m.count(needle)==1
m=m.replace(needle,needle+'\n        android:process=":terabox"',1)
manifest.write_text(m)
gradle=Path('app/build.gradle.kts')
if not gradle.exists():gradle=Path('app/build.gradle')
s=gradle.read_text()
assert '0.14.5' in s
s,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)17\b',r'\g<1>18',s,count=1)
assert n==1
s=s.replace('0.14.5','0.14.6',1)
gradle.write_text(s)
print('v0.14.6 isolates TeraBox SAF provider from the Asterion Rounder UI process, original app ID unchanged')

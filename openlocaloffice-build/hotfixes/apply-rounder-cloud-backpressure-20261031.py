from pathlib import Path
import re
root=Path('app/src/main')
main=root/'java/com/openlocal/office/MainActivity.java'
s=main.read_text(encoding='utf-8')
old='''                        ",\\\"streamed\\\":true,\\\"comicMode\\\":"+candidate.comicLike()+'''
assert s.count(old)==1,(s.count(old),old)
new='''                        ",\\\"streamed\\\":true,\\\"cloudSource\\\":"+
                        com.openlocal.office.core.FgTeraboxDocumentsProvider.AUTHORITY
                          .equals(uri.getAuthority())+
                        ",\\\"comicMode\\\":"+candidate.comicLike()+'''
s=s.replace(old,new,1)
main.write_text(s,encoding='utf-8')
css=root/'assets/style.css'
style=css.read_text(encoding='utf-8')
style+='''

/* Real TeraBox ZIP pages: reserve space BEFORE the HTTP byte-range read.
 * Without this, thousands of zero-height placeholders intersect the
 * viewport and WebView requests thousands of cloud images immediately.
 * No padding or borders are imposed once an image has actually loaded.
 */
.fg-comic-stack .fg-comic-section .fg-pdf-skeleton{
  min-height:85vh!important;
  height:85vh!important;
  box-sizing:border-box!important;
}
'''
css.write_text(style,encoding='utf-8')
gradle=Path('app/build.gradle.kts')
s=gradle.read_text(encoding='utf-8')
assert '0.14.8' in s
s,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)20\b',r'\g<1>21',s,count=1)
assert n==1
s=s.replace('0.14.8','0.14.9',1)
gradle.write_text(s,encoding='utf-8')
print('Real TeraBox cloud metadata, viewport reservations, release candidate 0.14.9 wired')

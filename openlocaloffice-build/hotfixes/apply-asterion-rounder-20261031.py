#!/usr/bin/env python3
"""Asterion Rounder: premium non-letter brand, cloud image fallback, safe reader chrome.
Built AFTER the previous 0.14.3 device fixes. No package/keystore reset.
"""
from pathlib import Path
import re
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text(encoding="utf-8")
start=s.index("    private WebResourceResponse fgTbImage(Uri source){")
end=s.index("    private void saveTbFile(",start)
s=s[:start]+r'''    private WebResourceResponse fgTbImage(Uri source){
        String[] parts=source.getPath().split("/");
        if(parts.length!=4||!parts[2].equals(fgTbToken))
            return new WebResourceResponse("image/jpeg",null,new ByteArrayInputStream(new byte[0]));
        try{
            int index=Integer.parseInt(parts[3]);
            TbPage item=fgTbPages.get(index);
            if(item==null)throw new IOException("Image not in active folder");
            try{
                // Full image streaming is always attempted first.
                return new WebResourceResponse(
                    com.openlocal.office.core.FgTeraboxClient.mime(item.name),null,
                    tb().open(item.path));
            }catch(Exception fullUnavailable){
                android.util.Log.w("FG_TERA","Full image stream unavailable ("
                    +fullUnavailable.getClass().getSimpleName()+"): "+
                    (fullUnavailable instanceof IOException?fullUnavailable.getMessage():"read failed"));
                // TeraBox often permits official preview URLs while the download
                // CDN refuses account dlinks. Render a preview, never a black page.
                return new WebResourceResponse("image/jpeg",null,
                    tb().openThumbnail(item.path));
            }
        }catch(Exception unavailable){
            android.util.Log.w("FG_TERA","Image and preview unavailable: "+
                unavailable.getClass().getSimpleName());
            return new WebResourceResponse("image/svg+xml","UTF-8",
                new ByteArrayInputStream(("<svg xmlns=\"http://www.w3.org/2000/svg\" "+
                  "width=\"640\" height=\"360\"><rect width=\"640\" height=\"360\" "+
                  "fill=\"#101724\"/><text x=\"50%\" y=\"50%\" fill=\"#e3c29c\" "+
                  "font-family=\"sans-serif\" text-anchor=\"middle\" font-size=\"22\">"+
                  "TeraBox preview unavailable</text></svg>").getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        }
    }
'''+s[end:]
# The pre-existing autoplay Koikatsu scan downloaded the entire opened cloud
# PNG in parallel with the reader, causing massive initial request contention.
a=s.index("        // Card classification is asynchronous; displaying the image never")
b=s.index("    private void appendTbImages(",a)
fragment=s[a:b]
assert 'tb().save(path,out)' in fragment and fragment.endswith('    }\n')
s=s[:a]+'''        // 3D card verification remains available on explicit user action.
        // No background full-size cloud PNG transfer during image opening.
    }
'''+s[b:]
# Existing file and 3D launchers remain. Never expose local filesystem paths to other apps.
main.write_text(s,encoding="utf-8")
# branding
strings=root/"res/values/strings.xml"
v=strings.read_text(encoding="utf-8")
v,n=re.subn(r'<string name="app_name">.*?</string>',
            '<string name="app_name">Asterion Rounder</string>',v,count=1)
assert n==1
strings.write_text(v,encoding="utf-8")
for path in (root/"assets/index.html",root/"assets/premium-library.js"):
    t=path.read_text(encoding="utf-8")
    t=t.replace("Asterion Files","Asterion Rounder")
    t=t.replace("YOUR PRIVATE LIBRARY","ASTERION · UNIVERSAL FILE PLATFORM")
    path.write_text(t,encoding="utf-8")
# Premium geometric orbit-star emblem, no letters.
vector='''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
  android:width="108dp" android:height="108dp"
  android:viewportWidth="108" android:viewportHeight="108">
  <path android:pathData="M15,68 C28,49 52,34 73,34 C88,34 95,39 89,50 C80,68 50,77 30,77 C19,77 13,73 15,68 Z"
   android:fillColor="#00000000" android:strokeColor="#F2CD8B"
   android:strokeWidth="4.5" android:strokeLineCap="round"/>
  <path android:pathData="M54,19 L62,43 L86,53 L62,62 L54,90 L45,62 L20,53 L45,43 Z"
   android:fillColor="#F3C780"/>
  <path android:pathData="M54,19 L62,43 L86,53 L54,54 Z"
   android:fillColor="#FFF2CF"/>
  <path android:pathData="M15,68 C28,49 52,34 73,34 C88,34 95,39 89,50"
   android:fillColor="#00000000" android:strokeColor="#FFE3AC"
   android:strokeWidth="2.4" android:strokeLineCap="round"/>
  <path android:pathData="M26,27 L29,34 L36,37 L29,40 L26,47 L23,40 L16,37 L23,34 Z"
   android:fillColor="#F8D492"/>
  <path android:pathData="M82,73 L84,79 L90,81 L84,83 L82,89 L80,83 L74,81 L80,79 Z"
   android:fillColor="#F8D492"/>
</vector>
'''
res=root/"res"
(res/"drawable/ic_launcher_foreground.xml").write_text(vector,encoding="utf-8")
# Legacy vector icon for Android launchers that do not support adaptive icons.
for filename in ("ic_launcher.xml","ic_launcher_round.xml"):
    p=res/"mipmap-anydpi"/filename
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(vector.replace('  <path android:pathData="M15,68',
      '  <path android:pathData="M0,0H108V108Z" android:fillColor="#0D1525"/>\n  <path android:pathData="M15,68',1),encoding="utf-8")
colors=res/"values/colors.xml"
v=colors.read_text()
v=v.replace("#111827","#0D1525")
colors.write_text(v)
# User-facing responsive layout: controls above navigation and never overlapping
# their own neighbors on narrow Android devices.
css=root/"assets/style.css"
c=css.read_text(encoding="utf-8")
c+='''
/* Asterion Rounder · Android 17 responsive gesture/controls protection */
.fg-lib-body{padding-bottom:calc(72px + env(safe-area-inset-bottom,0px))!important}
.fg-controls{bottom:calc(10px + env(safe-area-inset-bottom,0px))!important;
 width:min(calc(100vw - 16px),700px)!important;
 max-height:min(35dvh,220px)!important;box-sizing:border-box!important;
 padding:6px!important}
.fg-control-row{min-width:0;max-width:100%;overflow:hidden}
.fg-control-row>.fg-control-button{min-width:0!important;flex:1 1 0!important;
 padding:9px 2px!important;white-space:nowrap;text-overflow:ellipsis;
 overflow:hidden;min-height:38px!important;box-sizing:border-box}
.fg-control-position{min-width:44px!important;flex:0 0 44px!important}
.fg-control-scrub .fg-control-progress{min-width:0!important}
.fg-control-settings{bottom:calc(125px + env(safe-area-inset-bottom,0px))!important}
.fg-controls-mini{right:calc(8px + env(safe-area-inset-right,0px))!important;
 width:48px!important}
@media(max-width:440px){
  .fg-lib-header{box-sizing:border-box;max-width:100vw}
  .fg-lib-title-group{min-width:0;overflow:hidden}
  .fg-lib-brand-title{font-size:17px!important}
  .fg-lib-brand-subtitle{font-size:8px!important;line-height:1.5}
  .fg-lib-actions{grid-template-columns:repeat(3,minmax(0,1fr))!important;max-width:100%}
  .fg-lib-toolbar{flex-wrap:wrap;row-gap:10px}
  .fg-lib-search{flex:1 1 150px;width:auto;min-width:0}
  .fg-lib-sort{flex:0 0 auto}
  .fg-controls{font-size:11px}
  .fg-control-row>.fg-control-button{font-size:11px}
}
'''
css.write_text(c,encoding="utf-8")
# release version increments from existing v0.14.3, signing identity unchanged
gradle=Path("app/build.gradle.kts")
if not gradle.exists():gradle=Path("app/build.gradle")
g=gradle.read_text()
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)15\b',r'\g<1>16',g,count=1)
assert n==1, "VersionCode 15 expected from existing v0.14.3 patch"
assert '0.14.3' in g
g=g.replace('0.14.3','0.14.4',1)
gradle.write_text(g)
print("Rounder v0.14.4: star-orbit icon, TeraBox preview fallback, no auto-3D predownload, mobile-safe reader.")

#!/usr/bin/env python3
"""ASTERION adaptive launcher mark and functional library theme."""
from pathlib import Path
res=Path("app/src/main/res")
draw=res/"drawable"
draw.mkdir(parents=True,exist_ok=True)
(draw/"ic_launcher_foreground.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <!-- Orbital symbol and stylized A remain clear at launcher scale. -->
    <path android:pathData="M20,61 C19,41 34,23 53,21"
        android:strokeColor="#D3A770" android:strokeWidth="2.5"
        android:strokeLineCap="round" android:fillColor="#00000000"/>
    <path android:pathData="M87,47 C91,67 77,86 56,88"
        android:strokeColor="#D3A770" android:strokeWidth="2.5"
        android:strokeLineCap="round" android:fillColor="#00000000"/>
    <path android:pathData="M30,79 L50,32 L57,32 L77,79 L65,79 L60,66 L46,66 L41,79 Z"
        android:fillColor="#F9F4EA"/>
    <path android:pathData="M49,57 L53.5,46 L57,57 Z"
        android:fillColor="#0D1525"/>
    <path android:pathData="M55,22 L57,28 L63,30 L57,32 L55,38 L53,32 L47,30 L53,28 Z"
        android:fillColor="#D3A770"/>
    <path android:pathData="M76,27 L78,32 L83,34 L78,36 L76,41 L74,36 L69,34 L74,32 Z"
        android:fillColor="#D3A770"/>
    <path android:pathData="M27,79 L81,79" android:strokeColor="#D3A770"
        android:strokeLineCap="round" android:strokeWidth="2"
        android:fillColor="#00000000"/>
</vector>
""",encoding="utf-8")
colors=res/"values/colors.xml"
s=colors.read_text(encoding="utf-8")
s=s.replace("#111827","#0D1525")
colors.write_text(s,encoding="utf-8")
for target in [res/"mipmap-anydpi/ic_launcher.xml",res/"mipmap-anydpi/ic_launcher_round.xml"]:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
 android:width="108dp" android:height="108dp"
 android:viewportWidth="108" android:viewportHeight="108">
 <path android:pathData="M0,0H108V108H0Z" android:fillColor="#0D1525"/>
 <path android:pathData="M20,61 C19,41 34,23 53,21 M87,47 C91,67 77,86 56,88"
   android:strokeColor="#D3A770" android:strokeWidth="2.5" android:fillColor="#00000000"/>
 <path android:pathData="M30,79 L50,32 L57,32 L77,79 L65,79 L60,66 L46,66 L41,79 Z"
   android:fillColor="#F9F4EA"/>
 <path android:pathData="M49,57 L53.5,46 L57,57 Z" android:fillColor="#0D1525"/>
 <path android:pathData="M55,22 L57,28 L63,30 L57,32 L55,38 L53,32 L47,30 L53,28 Z"
   android:fillColor="#D3A770"/>
 <path android:pathData="M76,27 L78,32 L83,34 L78,36 L76,41 L74,36 L69,34 L74,32 Z"
   android:fillColor="#D3A770"/>
</vector>
""",encoding="utf-8")
for folder in ("mipmap-anydpi-v26","mipmap-anydpi-v33"):
    target=res/folder
    target.mkdir(parents=True,exist_ok=True)
    for name in ("ic_launcher.xml","ic_launcher_round.xml"):
        (target/name).write_text("""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
 <background android:drawable="@color/file_gestioner_icon_bg"/>
 <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
""",encoding="utf-8")
css=Path("app/src/main/assets/style.css")
c=css.read_text(encoding="utf-8")
c+="""

/* ASTERION FILES: real content-first library, not a theme mockup.
   Keep original reader controls/functional selectors intact. */
.fg-library-root{background:#0b1220;color:#edf2f7}
.fg-lib-header{background:linear-gradient(130deg,#182335,#0d1524);
 border-bottom:1px solid #d3a77036;box-shadow:0 4px 22px #0004}
.fg-lib-monogram{background:radial-gradient(circle at 40% 25%,#283a55,#101b2a 85%);
 border:1px solid #d3a770bb;color:#e1bb87;letter-spacing:0;
 font-size:25px;border-radius:13px;box-shadow:0 3px 21px #d3a77022}
.fg-lib-brand-title{font-weight:830;letter-spacing:.015em;color:#f9f3e9}
.fg-lib-brand-subtitle{color:#d3a770;letter-spacing:.105em}
.fg-lib-primary,.fg-lib-large-action,.fg-lib-selected{
 color:#0d1726!important;background:linear-gradient(125deg,#f1d7ad,#c58b52)!important;
 border-color:#e8bd85!important;box-shadow:0 5px 17px #ba854338!important}
.fg-lib-secondary,.fg-lib-icon{background:#202b3b!important;border-color:#3c4a5c!important;
 color:#e9edf5!important}
.fg-lib-kicker{color:#d9b98e}
.fg-lib-hero{color:#f7f2e9}
.fg-lib-subtitle{color:#b1bfce}
.fg-lib-search{background:#1c293a;border-color:#43516a;color:#f8f3ea}
.fg-lib-search:focus{border-color:#d3a770;box-shadow:0 0 0 2px #d3a77044}
.fg-lib-toolbar{border-bottom-color:#d3a77030}
.fg-lib-filter{background:#1e2a3b;border-color:#36465f;color:#d5dfeb}
.fg-lib-filter.fg-lib-selected{color:#132034!important}
.fg-lib-cover{background:radial-gradient(circle at 35% 18%,#ac8b6035,transparent 60%),
 linear-gradient(145deg,#23344a,#0f1927 80%);border:1px solid #d2b0822b}
.fg-lib-tile:focus-visible .fg-lib-cover{outline-color:#d9bd93}
.fg-lib-cover-loading{color:#e8cca6}
.fg-lib-fallback-glyph{color:#dbc29e}
.fg-lib-footer{border-top:1px solid #d3a7701d;color:#9bacbf}
@media (max-width:430px){
 .fg-lib-header{gap:8px;padding-left:13px;padding-right:13px}
 .fg-lib-actions{gap:5px}
 .fg-lib-actions button{padding:8px 9px;font-size:11px}
 .fg-lib-brand-title{font-size:15px}
 .fg-lib-brand-subtitle{font-size:8px}
 .fg-lib-monogram{width:37px;height:37px;flex-basis:37px}
}
"""
css.write_text(c,encoding="utf-8")
print("Asterion adaptive icon and responsive library theme written")


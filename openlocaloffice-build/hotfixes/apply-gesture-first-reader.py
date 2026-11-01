#!/usr/bin/env python3
from pathlib import Path
root=Path("app/src/main/assets")
reader=root/"universal-reader.js"
s=reader.read_text()
old=""" tools.append(pageLabel,progress,minus,percent,plus,fit);"""
if old in s:
    s=s.replace(old," tools.append(pageLabel,progress);")
else:
    import re
    s=re.sub(r"tools\.append\(pageLabel,\s*progress(?:,\s*minus,\s*percent,\s*plus,\s*fit)?\);", "tools.append(pageLabel,progress);", s)
s=s.replace("changeZoom(scale>=1.8?1:2,v.clientX-rect.left,v.clientY-rect.top)","changeZoom(1,v.clientX-rect.left,v.clientY-rect.top)")
s=s.replace("changeZoom(scale>=1.8?1:2,e.clientX-rect.left,e.clientY-rect.top)","changeZoom(1,e.clientX-rect.left,e.clientY-rect.top)")
# New document and image always open fitted; saved zoom must not override base fit.
s=s.replace("if(Math.abs(savedZoom-1)>.005)changeZoom(savedZoom);","// Initial view always fits the screen; double tap returns to fit.")
reader.write_text(s)
unified=root/"unified-viewer-controls.js"
s=unified.read_text()
old="""   dock.append(zoomOut,label,zoomIn,fit);
   $('work')?.appendChild(dock);"""
import re
s=re.sub(r"\s*dock\.append\(zoomOut,label,zoomIn,fit\);\s*\$\(\x27work\x27\)\?\.appendChild\(dock\);", "\\n   // Controls intentionally not mounted.\\n", s)
s=s.replace(old,"""   // Gesture-first UI: zoom controls are intentionally not mounted.
   // Keep the controller for pinch and keyboard / wheel gestures only.""")
s=s.replace("zoomTo(scale>=1.7?1:2,coords[0]-rect.left,coords[1]-rect.top)","zoomTo(1,coords[0]-rect.left,coords[1]-rect.top)")
s=s.replace("if(Math.abs(savedScale-1)>.005)requestAnimationFrame(()=>zoomTo(savedScale));","// Always open at native fitted width, regardless of prior zoom.")
unified.write_text(s)
css=root/"style.css"
css.write_text(css.read_text()+"""
/* Gesture-first document reader; no floating numeric zoom control. */
#fg-unified-dock,.fg-unified-dock{display:none!important}
.fg-comic-stack .fg-comic-section{margin:0!important;gap:0!important}
.fg-comic-stack img{margin:0!important;padding:0!important;vertical-align:top}
""")
print("Gesture-first reader controls: pinch, fitted initial width, double tap reset")

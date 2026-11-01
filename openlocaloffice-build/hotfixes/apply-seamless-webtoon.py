#!/usr/bin/env python3
"""Enforce edge-to-edge seamless comic pages without changing PDF page spacing."""
from pathlib import Path
css=Path("app/src/main/assets/style.css")
s=css.read_text()
s+="""

/* Seamless webtoon reading. Applied last to override older PDF and comic rules.
   Image-to-image joins must never expose whitespace, dividers, borders or shadows. */
.fg-pdf-scroll:has(.fg-comic-stack),
.fg-reader-scroll:has(.fg-comic-stack){
  padding:0!important;
}
.fg-comic-stack,
.fg-comic-stack .fg-pdf-container,
.fg-comic-stack .fg-comic-section,
.fg-comic-stack .fg-comic-page,
.fg-comic-stack .fg-archive-img{
  margin:0!important;padding:0!important;border:0!important;
  border-radius:0!important;box-shadow:none!important;outline:0!important;
}
.fg-comic-stack{width:100%!important;max-width:none!important}
.fg-comic-stack .fg-pdf-container{display:flex;flex-direction:column;gap:0!important}
.fg-comic-stack .fg-comic-section{
  width:100%!important;min-height:0!important;
  display:block!important;overflow:hidden;background:transparent!important;
  line-height:0!important;flex:none!important;
}
.fg-comic-stack .fg-comic-page{display:block!important;line-height:0!important}
.fg-comic-stack .fg-archive-img{
  display:block!important;width:100%!important;max-width:none!important;
  height:auto!important;object-fit:fill!important;
}
"""
css.write_text(s)
print("Seamless webtoon: zero gaps, margins, borders and shadows")

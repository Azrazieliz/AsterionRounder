#!/usr/bin/env python3
"""Unify actual Rounder launcher mark, controls, and preview feedback.
Runs after the approved-card preservation stage. Does not change card size,
layout, user selection or the functioning TeraBox/native reader pipeline.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

base=Path("app/src/main")
vector=base/"res/drawable/ic_launcher_foreground.xml"
assets=base/"assets"
lib=assets/"premium-library.js"
css=assets/"style.css"
media=base/"java/com/openlocal/office/core/FgMediaPlayer.java"
client=base/"java/com/openlocal/office/core/FgTeraboxClient.java"

# Use the REAL launcher vector as the only mark source. Never draw a new logo.
ns="{http://schemas.android.com/apk/res/android}"
tree=ET.parse(vector).getroot()
paths=[]
for path in tree.findall("path"):
    d=path.get(ns+"pathData","")
    if not d:continue
    attributes=['d="'+escape(d, {'"':'&quot;'})+'"']
    for android,svg in (("fillColor","fill"),("strokeColor","stroke"),
                        ("strokeWidth","stroke-width"),
                        ("strokeLineCap","stroke-linecap")):
        value=path.get(ns+android)
        if value is None:continue
        if android.endswith("Color") and value.startswith("#"):
            # Android #AARRGGBB -> SVG RGB + opacity.
            if len(value)==9:
                opacity=int(value[1:3],16)/255.0
                value="#"+value[3:]
                attributes.append(f'{svg}-opacity="{opacity:.4f}"')
        attributes.append(f'{svg}="{escape(value)}"')
    paths.append("<path "+" ".join(attributes)+"/>")
if len(paths)<3:raise AssertionError("Approved native vector not available")
mark=assets/"asterion-rounder-mark.svg"
mark.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" '
    'viewBox="0 0 108 108" aria-hidden="true">'+"\n".join(paths)+"</svg>\n",
    encoding="utf-8")

j=lib.read_text(encoding="utf-8")
def one(src,old,new,label):
    n=src.count(old)
    if n!=1:raise AssertionError(f"{label}: expected 1, got {n}")
    return src.replace(old,new,1)
j,n=re.subn(r"const monogram=E\('div','fg-lib-monogram',(?:'[^']*'|\"[^\"]*\")\);",
"""const monogram=E('div','fg-lib-monogram');
const sharedBrand=E('img','fg-lib-brand-image');
sharedBrand.src='asterion-rounder-mark.svg';
sharedBrand.alt='';sharedBrand.draggable=false;
monogram.append(sharedBrand);""",j,count=1)
if n!=1:raise AssertionError("Library must have exactly one brand mark")
icons=r"""
const iconDraw=(name)=>{
 const ns='http://www.w3.org/2000/svg';
 const svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox','0 0 24 24');
 svg.setAttribute('width','20');svg.setAttribute('height','20');
 svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');
 svg.setAttribute('stroke-width','2');svg.setAttribute('stroke-linecap','round');
 svg.setAttribute('stroke-linejoin','round');
 svg.setAttribute('aria-hidden','true');
 const commands={
  back:['M15 18 9 12 15 6'],
  grid:['M3 3h7v7H3z','M14 3h7v7h-7z','M3 14h7v7H3z','M14 14h7v7h-7z'],
  list:['M8 6h13','M8 12h13','M8 18h13','M3 6h.01','M3 12h.01','M3 18h.01']
 };
 for(const d of commands[name]||[]){
  const node=document.createElementNS(ns,'path');
  node.setAttribute('d',d);
  svg.append(node);
 }
 return svg;
};
"""
j=one(j,"const root=E('section','fg-library-root fg-lib-hidden');",
      icons+"const root=E('section','fg-library-root fg-lib-hidden');",
      "common navigation vectors")
j=one(j,"const back=b('‹','fg-lib-nav-back',()=>navigateBack());",
      "const back=b('','fg-lib-nav-back',()=>navigateBack());\nback.append(iconDraw('back'));",
      "replace font-specific back arrow")
j=one(j,"const layout=b('▦','fg-lib-icon',()=>{list=!list;layout.textContent=list?'☷':'▦';render();});",
"""const layout=b('','fg-lib-icon',()=>{
 list=!list;layout.replaceChildren(iconDraw(list?'list':'grid'));render();
});
layout.append(iconDraw('grid'));""","consistent grid/list navigation")
lib.write_text(j,encoding="utf-8")

# No card redesign: only solve the image/fallback overlay and mark consistency.
c=css.read_text(encoding="utf-8")
c+="""
/* Rounder identity and preview reliability. Existing cards preserved exactly. */
.fg-library-root .fg-lib-monogram{
 background:#0D1525!important;
 border:1px solid #D3A770!important;
 color:transparent!important;
 box-shadow:none!important;
 overflow:hidden!important;
 padding:2px!important;
 box-sizing:border-box!important;
 flex-shrink:0!important
}
.fg-library-root .fg-lib-monogram .fg-lib-brand-image{
 display:block!important;width:100%!important;height:100%!important;
 object-fit:contain!important;pointer-events:none!important
}
/* Image-ready state must not leave a generic glyph over valid artwork. */
.fg-library-root .fg-lib-cover.fg-lib-has-image > .fg-lib-fallback{
 visibility:hidden!important;opacity:0!important
}
.fg-library-root .fg-lib-cover.fg-lib-has-image > .fg-lib-cover-image{
 opacity:1!important
}
.fg-library-root .fg-lib-nav-back,.fg-library-root .fg-lib-icon{
 display:inline-flex!important;align-items:center!important;
 justify-content:center!important
}
.fg-library-root .fg-lib-nav-back svg,.fg-library-root .fg-lib-icon svg{
 display:block!important;width:19px!important;height:19px!important;
 stroke:currentColor!important;fill:none!important
}
.fg-library-root .fg-lib-nav-back svg{color:#e7cba5!important}
"""
css.write_text(c,encoding="utf-8")

# Show a nonblocking, actionable state when the TeraBox range stream stalls.
m=media.read_text(encoding="utf-8")
m=one(m,"        player.addListener(new Player.Listener(){",
"""        final int[] bufferingSequence={0};
        status.setOnClickListener(v->{
            if(closed||player.getPlaybackState()!=Player.STATE_BUFFERING)return;
            status.setClickable(false);
            showMessage("Retrying video stream…");
            try{
                if(teraboxDirect)playTeraboxRanges();
                else play(original);
            }catch(Exception retryError){
                showMessage("Video stream retry failed. Reopen the file.");
            }
        });
        status.setClickable(false);
        player.addListener(new Player.Listener(){""","buffer retry")
m=one(m,"                if(state==Player.STATE_READY){",
"""                bufferingSequence[0]++;
                if(state==Player.STATE_READY){
                    status.setClickable(false);""","ready resets buffer timer")
m=one(m,'                }else if(state==Player.STATE_BUFFERING)\n                    showMessage("Buffering video…");',
"""                }else if(state==Player.STATE_BUFFERING){
                    showMessage(teraboxDirect?"Connecting to TeraBox video…":"Loading video…");
                    final int sequence=bufferingSequence[0];
                    root.postDelayed(()->{
                        if(closed||bufferingSequence[0]!=sequence||
                           player.getPlaybackState()!=Player.STATE_BUFFERING)return;
                        showMessage(teraboxDirect?
                            "Video data has stalled. Tap here to retry TeraBox streaming.":
                            "Video data has stalled. Tap here to retry.");
                        status.setClickable(true);
                    },14000L);
                }""","bounded buffering feedback")
m=one(m,"            @Override public void onPlayerError(PlaybackException error){",
"""            @Override public void onPlayerError(PlaybackException error){
                bufferingSequence[0]++;
                status.setClickable(false);""","don't show stale buffering message after hard error")
# The existing native player transports stay functional; align their icons with
# the library's 24px vector language rather than asymmetric hand-drawn arrows.
transport=m.find("    private static final class VideoTransport extends View{")
if transport<0:raise AssertionError("Existing video transport missing")
draw=m.find("        @Override protected void onDraw(android.graphics.Canvas c){",transport)
stop=m.find("\n        }\n    }\n",draw)
if draw<0 or stop<0:raise AssertionError("Video transport drawing bounds changed")
new_draw="""        @Override protected void onDraw(android.graphics.Canvas c){
            super.onDraw(c);
            float cx=getWidth()/2f,cy=getHeight()/2f;
            float radius=Math.min(getWidth(),getHeight())*.48f;
            paint.setStyle(android.graphics.Paint.Style.FILL);
            paint.setColor(role==1?0xe01d2d43:0xd21b2a3f);
            c.drawCircle(cx,cy,radius,paint);
            paint.setColor(0xfff0d3aa);
            paint.setStrokeWidth(2.25f*dp);
            paint.setStrokeCap(android.graphics.Paint.Cap.ROUND);
            paint.setStrokeJoin(android.graphics.Paint.Join.ROUND);
            if(role==1){
                paint.setStyle(android.graphics.Paint.Style.FILL);
                if(playing){
                    c.drawRoundRect(cx-6*dp,cy-9*dp,cx-2*dp,cy+9*dp,1.3f*dp,1.3f*dp,paint);
                    c.drawRoundRect(cx+2*dp,cy-9*dp,cx+6*dp,cy+9*dp,1.3f*dp,1.3f*dp,paint);
                }else{
                    android.graphics.Path play=new android.graphics.Path();
                    play.moveTo(cx-5*dp,cy-9*dp);
                    play.lineTo(cx+9*dp,cy);
                    play.lineTo(cx-5*dp,cy+9*dp);
                    play.close();c.drawPath(play,paint);
                }
            }else{
                paint.setStyle(android.graphics.Paint.Style.STROKE);
                final float direction=role==0?-1f:1f;
                android.graphics.Path skip=new android.graphics.Path();
                skip.moveTo(cx-4*direction*dp,cy-8*dp);
                skip.lineTo(cx+4*direction*dp,cy);
                skip.lineTo(cx-4*direction*dp,cy+8*dp);
                c.drawPath(skip,paint);
                c.drawLine(cx+9*direction*dp,cy-9*dp,
                    cx+9*direction*dp,cy+9*dp,paint);
            }
        }"""
m=m[:draw]+new_draw+m[stop+len("\n        }"):]
media.write_text(m,encoding="utf-8")

# Recover once when signed TeraBox cover URLs expire. No full originals fetched.
s=client.read_text(encoding="utf-8")
start=s.index("public InputStream openThumbnail(String path,String folder,int page)")
end=s.index("    public void save(String path,OutputStream output)",start)
segment=s[start:end]
segment=one(segment,
"        // TeraBox may redirect thumbnails to a signed CDN.\n        for(int hop=0;hop<6;hop++){",
"""        // Refresh expired signed thumbnails once, without fetching originals.
        boolean refreshedSignedUrl=false;
        // TeraBox may redirect thumbnails to a signed CDN.
        for(int hop=0;hop<6;hop++){""","signed URL retry guard")
segment=one(segment,
"                int response=request.getResponseCode();",
"""                int response=request.getResponseCode();
                if((response==401||response==403||response==404)&&!refreshedSignedUrl){
                    refreshedSignedUrl=true;
                    try{
                        JSONObject current=fileDetails(safe);
                        JSONObject urls=current.optJSONObject("thumbs");
                        String fresh=urls==null?"":urls.optString(
                            "url3",urls.optString("url2",urls.optString("url1","")));
                        if(fresh.startsWith("https://")&&!fresh.equals(url.toString())){
                            thumbUrls.put(safe,fresh);
                            url=new URL(fresh);
                            continue;
                        }
                    }catch(Exception staleMetadata){
                        android.util.Log.i("FG_TERA","Signed image refresh unavailable");
                    }
                }""","refresh expired signed cover URL once")
s=s[:start]+segment+s[end:]
client.write_text(s,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
version=gradle.read_text(encoding="utf-8")
version,n=re.subn(r'(\\bversionCode\\s*=\\s*)45\\b',r'\\g<1>46',version,count=1)
if n!=1:raise AssertionError("Expected v0.15.23 source code 45")
version,n=re.subn(r'(\\bversionName\\s*=\\s*)"0\\.15\\.23"',r'\\g<1>"0.15.24"',version,count=1)
if n!=1:raise AssertionError("Expected v0.15.23 version name")
gradle.write_text(version,encoding="utf-8")
print("ROUNDER_UNIFIED_IDENTITY_PREVIEW_CONTROLS: launcher-shared mark, preserved cards, failed previews and buffering feedback handled")

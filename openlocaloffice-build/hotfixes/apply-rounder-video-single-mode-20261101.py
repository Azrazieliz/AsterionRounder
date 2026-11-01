#!/usr/bin/env python3
"""Single compact video playback mode control and Aloha-like fading chrome."""
from pathlib import Path
import re
root=Path("app/src/main")
f=root/"java/com/openlocal/office/core/FgMediaPlayer.java"
s=f.read_text(encoding="utf-8")
def one(old,new,label):
    global s
    if s.count(old)!=1:raise RuntimeError(label+" expected 1 got "+str(s.count(old)))
    s=s.replace(old,new,1)
# Compact geometry and no broad solid bar obscuring the video.
one("final LinearLayout transport=new LinearLayout(activity);",
"""final long[] lastChromeInteraction={android.os.SystemClock.uptimeMillis()};
            final LinearLayout transport=new LinearLayout(activity);""","chrome lifecycle")
one("footer.setPadding((int)(14*dp),(int)(7*dp),(int)(14*dp),(int)(6*dp));",
    "footer.setPadding((int)(8*dp),0,(int)(8*dp),(int)(5*dp));","footer margins")
one("footer.setBackgroundColor(0xbd101116);",
"""footer.setBackground(new android.graphics.drawable.GradientDrawable(
                android.graphics.drawable.GradientDrawable.Orientation.BOTTOM_TOP,
                new int[]{0xb8000000,0x00000000}));""","footer translucency")
one("footer.addView(timeline,new LinearLayout.LayoutParams(-1,(int)(43*dp)));",
    "footer.addView(timeline,new LinearLayout.LayoutParams(-1,(int)(45*dp)));",
    "compact timeline")
start=s.index("            final LinearLayout modes=new LinearLayout(activity);")
end=s.index("            root.addView(footer,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));",start)
mode=r'''            // One 42dp playback-type symbol at the far right of the timeline.
            // Tap cycles Play Next -> Replay -> Shuffle; no oversized options row.
            final TextView modeSymbol=new TextView(activity);
            modeSymbol.setText(playbackSymbol());
            modeSymbol.setTextSize(23);modeSymbol.setTextColor(0xffffffff);
            modeSymbol.setGravity(Gravity.CENTER);
            modeSymbol.setBackgroundColor(0x00000000);
            modeSymbol.setPadding(0,0,0,0);
            modeSymbol.setContentDescription("Playback mode: "+playbackModeName()+". Tap to change.");
            timeline.addView(modeSymbol,new LinearLayout.LayoutParams((int)(46*dp),(int)(43*dp)));
            modeSymbol.setOnClickListener(v->{
                lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                playbackMode=(playbackMode+1)%3;
                modeSymbol.setText(playbackSymbol());
                modeSymbol.setContentDescription("Playback mode: "+playbackModeName()+". Tap to change.");
                android.widget.Toast.makeText(activity,playbackModeName(),
                    android.widget.Toast.LENGTH_SHORT).show();
            });
'''
s=s[:start]+mode+s[end:]
one("timeline.addView(duration,new LinearLayout.LayoutParams((int)(64*dp),-2));",
    "timeline.addView(duration,new LinearLayout.LayoutParams((int)(54*dp),-2));",
    "right clock")
one("timeline.addView(elapsed,new LinearLayout.LayoutParams((int)(64*dp),-2));",
    "timeline.addView(elapsed,new LinearLayout.LayoutParams((int)(54*dp),-2));",
    "left clock")
one("pill.setColor(0xe5191c24);pill.setCornerRadius(24*dp);",
    "pill.setColor(0xc51b1e26);pill.setCornerRadius(999*dp);","circular transport")
one("lp.setMargins((int)(12*dp),0,(int)(12*dp),0);",
    "lp.setMargins((int)(7*dp),0,(int)(7*dp),0);","transport spacing")
one("(int)((b==toggle?70:55)*dp),(int)((b==toggle?70:55)*dp)",
    "(int)((b==toggle?60:49)*dp),(int)((b==toggle?60:49)*dp)",
    "transport size")
one("previous.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(-1,false);});",
    "previous.setOnClickListener(v->{lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();if(mediaNavigator!=null)mediaNavigator.navigate(-1,false);});",
    "prev action")
one("next.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(1,false);});",
    "next.setOnClickListener(v->{lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();if(mediaNavigator!=null)mediaNavigator.navigate(1,false);});",
    "next action")
one("toggle.setOnClickListener(v->{if(player.isPlaying())player.pause();else player.play();});",
    "toggle.setOnClickListener(v->{lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();if(player.isPlaying())player.pause();else player.play();});",
    "pause action")
one("                toggle.setText(player.isPlaying()?\"Ⅱ\":\"▶\");",
"""                toggle.setText(player.isPlaying()?"Ⅱ":"▶");
                if(player.isPlaying() && transport.getVisibility()==View.VISIBLE &&
                   android.os.SystemClock.uptimeMillis()-lastChromeInteraction[0]>3400){
                    transport.setVisibility(View.GONE);
                    heading.setVisibility(View.GONE);
                    footer.setVisibility(View.GONE);
                }""","video auto fade")
one("""                        int newVisibility=transport.getVisibility()==View.VISIBLE?""",
    """                        lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                        int newVisibility=transport.getVisibility()==View.VISIBLE?""",
    "video chrome tap")
one("""                        if(!player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))return true;""",
    """                        lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                        if(!player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))return true;""",
    "video seek double tap")
anchor="    private static void refreshPlaybackMode(Button[] buttons){"
assert s.count(anchor)==1
s=s.replace(anchor,'''    private static String playbackModeName(){
        return playbackMode==0?"Play Next":playbackMode==1?"Replay":"Shuffle";
    }
    private static String playbackSymbol(){
        // Drawable Unicode monochrome glyphs, not a word-sized button row.
        return playbackMode==0?"⇥":playbackMode==1?"↻":"⤨";
    }
'''+anchor,1)
f.write_text(s,encoding="utf-8")
gradle=Path("app/build.gradle.kts")
if not gradle.is_file():gradle=Path("app/build.gradle")
g=gradle.read_text(encoding="utf-8")
g,c=re.subn(r'(\bversionCode\s*(?:=\s*)?)31\b',r'\g<1>32',g,count=1)
if c!=1:raise RuntimeError("Expected code 31")
g,c=re.subn(r'(\bversionName\s*(?:=\s*)?)"0\.15\.9"',r'\g<1>"0.15.10"',g,count=1)
if c!=1:raise RuntimeError("Expected 0.15.9")
gradle.write_text(g,encoding="utf-8")
print("VIDEO_SINGLE_MODE_ICON_READY_AND_VERSION_0.15.10")

#!/usr/bin/env python3
"""Replace incomplete VideoView with Media3, bounded UI folder pages."""
from pathlib import Path
root=Path("app/src/main")
java=root/"java/com/openlocal/office/MainActivity.java"
s=java.read_text()
start=s.index("    private void showFgMedia(Uri uri,String name,boolean video){")
end=s.index("    private void openFolderImages(String uriText){",start)
assert 1800<end-start<5000
replacement=r'''    private com.openlocal.office.core.FgMediaPlayer fgMediaSession;
    private void showFgMedia(Uri uri,String name,boolean video){
        hideFgMedia();
        android.widget.FrameLayout host=findViewById(android.R.id.content);
        if(host==null)return;
        fgMediaSession=new com.openlocal.office.core.FgMediaPlayer(
            this,uri,name,video,this::hideFgMedia);
        android.view.View display=fgMediaSession.getView();
        host.addView(display,new android.widget.FrameLayout.LayoutParams(-1,-1));
        fgMediaPanel=(android.widget.FrameLayout)display;
        android.util.Log.i("FG_MEDIA","PLAYER_VISIBLE "+name);
    }
    private void hideFgMedia(){
        if(fgMediaSession!=null){
            fgMediaSession.close();
            fgMediaSession=null;
        }
        if(fgMediaPanel!=null){
            android.view.ViewParent parent=fgMediaPanel.getParent();
            if(parent instanceof android.view.ViewGroup)
                ((android.view.ViewGroup)parent).removeView(fgMediaPanel);
            fgMediaPanel=null;
        }
        js("window.FileGestionerLibrary?.show()");
    }
'''
s=s[:start]+replacement+s[end:]
s=s.replace('        if(fgMediaVideo!=null)fgMediaVideo.stopPlayback();',
            '        if(fgMediaSession!=null)fgMediaSession.close();')
# Preserve legacy field references from earlier hotfix for back navigation,
# but remove VideoView instance. Native player is now a Media3 PlayerView.
s=s.replace('    private android.widget.VideoView fgMediaVideo;','')
java.write_text(s)
gradle=Path("app/build.gradle.kts")
g=gradle.read_text()
anchor="dependencies {"
assert g.count(anchor)==1
g=g.replace(anchor,anchor+'''
    implementation("androidx.media3:media3-exoplayer:1.11.1")
    implementation("androidx.media3:media3-ui:1.11.1")''',1)
gradle.write_text(g)
print("ExoPlayer 1.11.1 integrated with cached SAF playback fallback")

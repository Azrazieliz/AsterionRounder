#!/usr/bin/env python3
"""Full-screen image reading without controls behind Android system navigation."""
from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
anchor='    private void openUri(Uri uri) {'
assert s.count(anchor)==1
methods='''    private boolean fgImageSystemUiActive=false;
    @android.webkit.JavascriptInterface public void fgImageImmersiveCompat(boolean active){
        setImageImmersiveInternal(active);
    }
    private void setImageImmersiveInternal(boolean active){
        runOnUiThread(()->{
            if(fgImageSystemUiActive==active)return;
            fgImageSystemUiActive=active;
            android.view.Window window=getWindow();
            if(android.os.Build.VERSION.SDK_INT>=30){
                android.view.WindowInsetsController controller=window.getInsetsController();
                if(controller!=null){
                    if(active){
                        controller.setSystemBarsBehavior(
                            android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                        controller.hide(android.view.WindowInsets.Type.navigationBars()|
                            android.view.WindowInsets.Type.statusBars());
                    }else controller.show(android.view.WindowInsets.Type.navigationBars()|
                        android.view.WindowInsets.Type.statusBars());
                }
            }else{
                android.view.View decor=window.getDecorView();
                decor.setSystemUiVisibility(active?
                    (android.view.View.SYSTEM_UI_FLAG_FULLSCREEN|
                    android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|
                    android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY|
                    android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE|
                    android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|
                    android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION):0);
            }
        });
    }
'''
s=s.replace(anchor,methods+anchor,1)
anchor='        @JavascriptInterface public String getRemoteToken(){'
assert s.count(anchor)==1
s=s.replace(anchor,'''        @JavascriptInterface public void setImageViewing(boolean active){
            MainActivity.this.setImageImmersiveInternal(active);
        }
'''+anchor,1)
main.write_text(s)
print("Image immersive system bars and per-file restoration wired to JavaScript")

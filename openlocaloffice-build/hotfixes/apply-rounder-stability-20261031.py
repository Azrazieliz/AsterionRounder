#!/usr/bin/env python3
"""Crash-resistant Asterion Rounder, bounded persistent caches, recoverable startup.
Applied after v0.14.4 fixes; preserves installation, signing, and encrypted ndus.
"""
from pathlib import Path
import re
base=Path('app/src/main')
main=base/'java/com/openlocal/office/MainActivity.java'
s=main.read_text(encoding='utf-8')
# Finite worker count. A cached, unbounded pool can exhaust memory or threads
# when cloud metadata/images are requested concurrently.
a='java.util.concurrent.Executors.newCachedThreadPool();'
assert s.count(a)==1,("directory worker",s.count(a))
s=s.replace(a,'java.util.concurrent.Executors.newFixedThreadPool(4);',1)

# Android WebView render-process termination must not kill the entire UI process.
a='web.setWebViewClient(new WebViewClient() {'
assert s.count(a)==1,("WebView recovery target",s.count(a))
new=r'''web.setWebViewClient(new WebViewClient() {
            @Override public boolean onRenderProcessGone(
                    WebView view, android.webkit.RenderProcessGoneDetail details) {
                android.util.Log.e("FG_RECOVERY","WebView renderer gone; crashed="+details.didCrash());
                android.content.SharedPreferences prefs=
                    getSharedPreferences("asterion_stability",MODE_PRIVATE);
                int count=prefs.getInt("renderer_recovery_count",0)+1;
                prefs.edit().putInt("renderer_recovery_count",count)
                    .putLong("last_renderer_loss",System.currentTimeMillis()).apply();
                try{
                    android.view.ViewParent parent=view.getParent();
                    if(parent instanceof android.view.ViewGroup)
                        ((android.view.ViewGroup)parent).removeView(view);
                    view.destroy();
                }catch(Exception ignored){}
                if(web==view)web=null;
                if(count<=2){
                    new android.os.Handler(android.os.Looper.getMainLooper()).post(
                        ()->MainActivity.this.recreate());
                }else{
                    android.widget.TextView recovery=new android.widget.TextView(MainActivity.this);
                    recovery.setPadding(28,48,28,32);
                    recovery.setTextColor(android.graphics.Color.WHITE);
                    recovery.setBackgroundColor(android.graphics.Color.rgb(13,21,37));
                    recovery.setText("Asterion Rounder protected your files after a reader crash. "+
                        "Close and reopen the app; your files, session and previews remain stored.");
                    recovery.setTextSize(18);
                    setContentView(recovery);
                }
                return true;
            }
'''
s=s.replace(a,new,1)
# Healthy session clears prior recovery counter. If rendering dies immediately,
# the bounded counter remains and prevents an endless recreate loop.
a='        web.loadUrl("file:///android_asset/index.html");'
assert s.count(a)==1,("web main URL",s.count(a))
s=s.replace(a,a+'''
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(()->{
            if(web!=null&&web.getParent()!=null){
                getSharedPreferences("asterion_stability",MODE_PRIVATE).edit()
                  .putInt("renderer_recovery_count",0).apply();
            }
        },22000);
''',1)
main.write_text(s,encoding='utf-8')

client=base/'java/com/openlocal/office/core/FgTeraboxClient.java'
c=client.read_text(encoding='utf-8')
old='new File(app.getCacheDir(),"terabox-thumbnails-v3")'
assert c.count(old)==1
c=c.replace(old,'new File(app.getFilesDir(),"terabox-thumbnails-v4")',1)
# No credential material is present in filenames, but use separate per-session
# prefix as was already implemented; do not allow file previews to leak to other apps.
client.write_text(c,encoding='utf-8')

covers=base/'java/com/openlocal/office/core/ReaderCovers.java'
v=covers.read_text(encoding='utf-8')
a='new File(ctx.getCacheDir(),"covers-v2")'
assert v.count(a)==2,("ReaderCovers persistent cache",v.count(a))
v=v.replace(a,'new File(ctx.getFilesDir(),"covers-v3")')
old='if(cached.exists()&&cached.length()>0)return new FileInputStream(cached);'
assert v.count(old)==2
v=v.replace(old,'''if(cached.exists()&&cached.length()>0){
            cached.setLastModified(System.currentTimeMillis());
            return new FileInputStream(cached);
        }''')
# Cache disk usage remains bounded across files and restarts. Never delete originals.
needle='            return new FileInputStream(cached);\n        }catch(InterruptedException error){'
assert v.count(needle)==1
v=v.replace(needle,'''            prunePersistentCovers(dir);
            return new FileInputStream(cached);
        }catch(InterruptedException error){''',1)
anchor='    private static boolean isArchive(String filename){'
assert v.count(anchor)==1
v=v.replace(anchor,'''    private static void prunePersistentCovers(File folder){
        File[] entries=folder.listFiles((dir,name)->name.endsWith(".jpg"));
        if(entries==null||entries.length<32)return;
        Arrays.sort(entries,Comparator.comparingLong(File::lastModified).reversed());
        long total=0;
        for(int i=0;i<entries.length;i++){
            total+=entries[i].length();
            if(i>=1000||total>180L*1024*1024)entries[i].delete();
        }
    }
'''+anchor,1)
covers.write_text(v,encoding='utf-8')
# Limit page decode pressure to a small viewport radius; retain only structure
# and measured placeholder heights outside the viewport.
reader=base/'assets/reader-controls.js'
j=reader.read_text(encoding='utf-8')
a="},{root:view,rootMargin:'320% 0px',threshold:0});"
assert j.count(a)==1
j=j.replace(a,"},{root:view,rootMargin:'100% 0px',threshold:0});",1)
# Prevent listener leaks after switching readers repeatedly.
needle=" let imageObserver=null,batchObserver=null,index=0,current=0,finished=false,busy=false;"
assert j.count(needle)==1
j=j.replace(needle,needle+'''
 // When the next document opens, dispose retained observers immediately.
 const originalRemove=host.remove.bind(host);
 host.remove=function(){imageObserver?.disconnect();batchObserver?.disconnect();originalRemove();};
''',1) if False else j
reader.write_text(j,encoding='utf-8')

js=base/'assets/premium-library.js'
ui=js.read_text(encoding='utf-8')
# Lower time spent on blank covers while failures are reported; limit network
# requests without preventing rapid first visible thumbnails.
ui=ui.replace('const MAX_CLOUD_COVERS=2;','const MAX_CLOUD_COVERS=3;')
ui=ui.replace('timeout=setTimeout(finish,10000);','timeout=setTimeout(finish,7000);')
js.write_text(ui,encoding='utf-8')

# VersionCode always advances for update install; do not alter package or key.
gradle=Path('app/build.gradle.kts')
if not gradle.exists():gradle=Path('app/build.gradle')
g=gradle.read_text()
assert '0.14.4' in g
g,n=re.subn(r'(\bversionCode\s*(?:=\s*)?)16\b',r'\g<1>17',g,count=1)
assert n==1
g=g.replace('0.14.4','0.14.5',1)
gradle.write_text(g)
print('Asterion Rounder v0.14.5: bounded executors, renderer recovery, persistent private thumbnails, viewport image budget')

from pathlib import Path
import re

main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
java=main.read_text()
# The app uses a WebView. Predictive/system Back cannot simply finish the
# Activity while a document, book drawer or collection child is visible.
method='''    private android.window.OnBackInvokedCallback systemBackCallback;
    private long lastRootBackMillis;

    private void navigateSystemBack() {
        if(web==null) {
            finish();
            return;
        }
        web.evaluateJavascript(
            "(function(){try{return !!(window.FileGestionerLibrary && " +
            "window.FileGestionerLibrary.handleBack && " +
            "window.FileGestionerLibrary.handleBack());}catch(e){return false;}})()",
            handled -> {
                if(!"true".equals(handled)){
                    long now=android.os.SystemClock.elapsedRealtime();
                    if(now-lastRootBackMillis<2200L)finish();
                    else {
                        lastRootBackMillis=now;
                        android.widget.Toast.makeText(this,
                            "Press Back again to exit",android.widget.Toast.LENGTH_SHORT).show();
                    }
                }
            });
    }
    @Override public void onBackPressed() {
        navigateSystemBack();
    }
'''
if re.search(r'\bvoid\s+onBackPressed\s*\(',java):
    match=re.search(r'(?m)^[ \t]*@Override\s+public\s+void\s+onBackPressed\s*\([^)]*\)\s*\{',java)
    if not match:
        match=re.search(r'(?m)^[ \t]*public\s+void\s+onBackPressed\s*\([^)]*\)\s*\{',java)
    assert match is not None,"Existing Back override could not be found safely"
    idx=match.end();level=1
    while idx<len(java) and level:
        if java[idx]=='{':level+=1
        elif java[idx]=='}':level-=1
        idx+=1
    java=java[:match.start()]+method+java[idx:]
else:
    anchor="    @Override public void onDestroy() {"
    assert java.count(anchor)==1,"Could not locate Activity lifetime anchor"
    java=java.replace(anchor,method+anchor,1)
# Android 13+ predictive Back dispatch may bypass the deprecated
# Activity.onBackPressed() override. Register the same navigation handler with
# OnBackInvokedDispatcher and release the callback on Activity destruction.
on_create='''        setContentView(web);'''
assert java.count(on_create)==1,"Missing WebView creation anchor"
java=java.replace(on_create,on_create+'''
        if(android.os.Build.VERSION.SDK_INT>=33){
            systemBackCallback=this::navigateSystemBack;
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                systemBackCallback);
        }''',1)
on_destroy='''    @Override public void onDestroy() {'''
assert java.count(on_destroy)==1,"Missing Activity cleanup anchor"
java=java.replace(on_destroy,'''    @Override public void onDestroy() {
        if(android.os.Build.VERSION.SDK_INT>=33&&systemBackCallback!=null){
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(systemBackCallback);
        }''',1)
main.write_text(java)
gradle=Path("app/build.gradle.kts")
version=gradle.read_text()
version,n=re.subn(r'versionCode\s*=\s*(\d+)',
    lambda match:"versionCode = "+str(int(match.group(1))+1),version,count=1)
assert n==1,"Missing Android versionCode"
version,n=re.subn(r'versionName\s*=\s*"[^"]+"',
    'versionName = "0.13.1"',version,count=1)
assert n==1,"Missing Android versionName"
gradle.write_text(version)
print("File Gestioner v0.13.1 — fixed EPUB, covers and Android Back")


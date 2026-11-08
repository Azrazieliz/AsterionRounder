#!/usr/bin/env python3
"""Rounder v0.15.19 — native signed updater bridge and Android installer grant.
Applied after existing premium organizer, before final UI patch.
"""
from pathlib import Path
import re
base=Path("app/src/main")
main=base/"java/com/openlocal/office/MainActivity.java"
s=main.read_text(encoding="utf-8")
def replace_once(source,needle,value,label):
    found=source.count(needle)
    if found!=1:raise AssertionError(f"{label}: expected 1 anchor, got {found}")
    return source.replace(needle,value,1)
s=replace_once(s,"    private volatile com.openlocal.office.core.FgRounderOrganizer fgOrganizer;",
'''    private volatile com.openlocal.office.core.FgRounderUpdater fgUpdater;
    private synchronized com.openlocal.office.core.FgRounderUpdater fgUpdater(){
        if(fgUpdater==null)
            fgUpdater=new com.openlocal.office.core.FgRounderUpdater(
                this,json->runOnUiThread(()->js(
                    "window.FileGestionerLibrary?.updaterStatus("+json+")")));
        return fgUpdater;
    }
    private volatile com.openlocal.office.core.FgRounderOrganizer fgOrganizer;''',
    "updater state")
s=replace_once(s,"        @JavascriptInterface public void organizerReview(){",
'''        @JavascriptInterface public void checkRounderUpdate(){
            fgUpdater().check();
        }
        @JavascriptInterface public void installRounderUpdate(){
            fgUpdater().install();
        }
        @JavascriptInterface public void organizerReview(){''',
    "updater actions")
main.write_text(s,encoding="utf-8")

manifest=base/"AndroidManifest.xml"
m=manifest.read_text(encoding="utf-8")
assert "FgRounderUpdateProvider" not in m
assert "android.permission.REQUEST_INSTALL_PACKAGES" not in m
m=replace_once(m,"</application>",
'''    <provider
        android:name="com.openlocal.office.core.FgRounderUpdateProvider"
        android:authorities="com.openlocal.office.rounderupdates"
        android:exported="false"
        android:grantUriPermissions="true" />
  </application>''',"private APK provider")
m=replace_once(m,"</manifest>",
'''  <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
</manifest>''',"update package installer permission")
manifest.write_text(m,encoding="utf-8")
print("Native updater bridge and restricted read-only provider wired")

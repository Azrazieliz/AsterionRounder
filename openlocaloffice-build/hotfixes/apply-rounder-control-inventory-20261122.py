#!/usr/bin/env python3
"""Wire read-only Control inventory into the existing signed Rounder assembly.

Runs after all established UI, cloud-file and two-column patches. Does not
alter TeraBox data, current reader engines, credentials, cards or signing.
"""
from pathlib import Path

base = Path("app/src/main")
main = base / "java/com/openlocal/office/MainActivity.java"
manifest = base / "AndroidManifest.xml"
library = base / "assets/premium-library.js"

def insert_once(src, anchor, addition, label):
    count = src.count(anchor)
    if count != 1:
        raise AssertionError(f"{label}: expected one assembly anchor, got {count}")
    return src.replace(anchor, addition + anchor, 1)

java = main.read_text(encoding="utf-8")
java = insert_once(java, "        @JavascriptInterface public void searchTeraboxIndex(",
'''        @JavascriptInterface public void allowControlInventory(String cloudFolder){
            // Never block WebView UI while verifying the selected TeraBox folder.
            fgDirectoryExecutor.execute(()->{
                try{
                    com.openlocal.office.core.FgRounderInventoryBridge.grant(
                        MainActivity.this,tb(),cloudFolder);
                    reportLibraryAction("inventory",true,
                        "Control access enabled for 30 minutes; selected-folder scan started");
                }catch(Exception error){
                    reportLibraryAction("inventory",false,
                        error.getMessage()==null?"Cannot share folder inventory":error.getMessage());
                }
            });
        }
        @JavascriptInterface public void revokeControlInventory(){
            try{
                com.openlocal.office.core.FgRounderInventoryBridge.revoke(MainActivity.this);
                reportLibraryAction("inventory",true,"Control folder access revoked");
            }catch(Exception error){
                reportLibraryAction("inventory",false,"Could not revoke Control folder access");
            }
        }
''', "Rounder native owner consent bridge")
main.write_text(java,encoding="utf-8")

xml=manifest.read_text(encoding="utf-8")
if 'FgRounderInventoryBridge' in xml:
    raise AssertionError("Inventory provider already declared")
xml=insert_once(xml,"</application>",
'''    <provider android:name="com.openlocal.office.core.FgRounderInventoryBridge"
        android:authorities="com.openlocal.office.asterion.bridge"
        android:exported="true" />
  ''',"Signed Asterion provider")
manifest.write_text(xml,encoding="utf-8")

js=library.read_text(encoding="utf-8")
start=js.index("function showFileActions(item){")
cloud=js.index("if(item.terabox){",start)
close=js.index("fileAction(sheet,'Close','',closeFileActions);",cloud)
if close<cloud or close>cloud+6000:
    raise AssertionError("TeraBox action sheet has changed")
js=js[:close]+'''if(item.folder){
     fileAction(sheet,'Allow Control inventory (30 min)',
        'Read-only recursive metadata access to this selected TeraBox folder',
        ()=>{closeFileActions();bridge()?.allowControlInventory?.(item.path);});
     fileAction(sheet,'Revoke Control inventory access',
        'Immediately stop access to the previously shared folder',
        ()=>{closeFileActions();bridge()?.revokeControlInventory?.();});
   }
   '''+js[close:]
library.write_text(js,encoding="utf-8")
print("CONTROL_INVENTORY_BRIDGE_WIRED: exact signer, opt-in folder, paginated read-only export")

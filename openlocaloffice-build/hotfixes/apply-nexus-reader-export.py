#!/usr/bin/env python3
"""Applied after the pinned Rounder source reconstruction. No donor storage is
modified by this patch; the resulting app adds an explicit metadata export."""
from pathlib import Path
import shutil

main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
manifest=Path("app/src/main/AndroidManifest.xml")
ui=Path("app/src/main/assets/premium-library.js")
source=Path("../additions/RounderMigrationExportActivity.java")
dest=Path("app/src/main/java/com/openlocal/office/core/RounderMigrationExportActivity.java")
shutil.copyfile(source,dest)

s=main.read_text()
anchor="@JavascriptInterface public void pickFile(){"
assert s.count(anchor)==1,"Expected existing native file picker"
s=s.replace(anchor,'''@JavascriptInterface public void exportNexusReaderMetadata(String json){
            com.openlocal.office.core.RounderMigrationExportActivity.request(MainActivity.this,json);
        }
        '''+anchor,1)
main.write_text(s)

s=manifest.read_text()
assert s.count("</application>")==1,"Expected original application declaration"
s=s.replace("</application>",'''<activity android:name="com.openlocal.office.core.RounderMigrationExportActivity" android:exported="false" />
    </application>''',1)
manifest.write_text(s)

s=ui.read_text()
anchor="toolbar.append(back,headBox,search,sortButton,layout);"
assert s.count(anchor)==1,"Expected actual Rounder library toolbar"
s=s.replace(anchor,anchor+'''
const nexusExport=b('Export reader metadata','fg-lib-action',()=>{
  try{
    const records=Object.create(null);
    const controls=new Set(['fg.controls.bg','fg.controls.ink','fg.controls.size','fg.controls.font',
      'fg.controls.mode:epub','fg.controls.mode:pdf','fg.controls.mode:comic','fg.controls.mode:text']);
    for(let i=0;i<localStorage.length;i++){
      const key=localStorage.key(i);
      if(key&&(key.startsWith('fg.book.preferences.v2.')||controls.has(key)||key==='asterion-rounder-recent-v1')){
        const value=localStorage.getItem(key);
        if(value!==null)records[key]=value;
      }
    }
    const payload=JSON.stringify({schema:'asterion.rounder.reader-export.v1',records});
    if(payload.length>4*1024*1024){window.showError?.('Reader export exceeds size limit');return;}
    if(typeof bridge()?.exportNexusReaderMetadata!=='function'){window.showError?.('Reader export unavailable');return;}
    bridge().exportNexusReaderMetadata(payload);
  }catch(error){window.showError?.('Cannot prepare reader metadata export');}
});
toolbar.append(nexusExport);
''',1)
ui.write_text(s)

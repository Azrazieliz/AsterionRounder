#!/usr/bin/env python3
"""Native file actions for the indexed SAF collection. No destructive work
without an explicit user request; provider write access is never assumed."""
from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=main.read_text()
anchor="        @JavascriptInterface public void openKoikatsu3d(){"
assert s.count(anchor)==1
addition=r'''        private boolean canManageLibrary(){
            Uri root=libraryTree;
            if(root==null)return false;
            for(android.content.UriPermission grant:
                    getContentResolver().getPersistedUriPermissions()){
                if(grant.isWritePermission()&&root.equals(grant.getUri()))
                    return true;
            }
            return false;
        }
        private void reportLibraryAction(String operation,boolean ok,String detail){
            try{
                String payload=new org.json.JSONObject()
                    .put("operation",operation).put("ok",ok)
                    .put("detail",detail==null?"":detail).toString();
                runOnUiThread(()->js("window.FileGestionerLibrary?.operationResult("+payload+")"));
            }catch(Exception e){android.util.Log.e("FG_FILE_ACTION","Result error",e);}
        }
        @JavascriptInterface public boolean canManageLibraryFiles(){
            return canManageLibrary();
        }
        @JavascriptInterface public void shareLibraryFile(String value){
            if(value==null||!allowedLibraryUris.contains(value))return;
            runOnUiThread(()->{
                try{
                    Uri uri=Uri.parse(value);
                    String mime=getContentResolver().getType(uri);
                    android.content.Intent intent=new android.content.Intent(
                        android.content.Intent.ACTION_SEND);
                    intent.setType(mime==null?"application/octet-stream":mime);
                    intent.putExtra(android.content.Intent.EXTRA_STREAM,uri);
                    intent.setClipData(android.content.ClipData.newUri(
                        getContentResolver(),"Shared file",uri));
                    intent.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(android.content.Intent.createChooser(intent,"Share file"));
                }catch(Exception e){reportLibraryAction("share",false,message(e));}
            });
        }
        @JavascriptInterface public void openLibraryExternally(String value){
            if(value==null||!allowedLibraryUris.contains(value))return;
            runOnUiThread(()->{
                try{
                    Uri uri=Uri.parse(value);
                    String mime=getContentResolver().getType(uri);
                    android.content.Intent intent=new android.content.Intent(
                        android.content.Intent.ACTION_VIEW);
                    intent.setDataAndType(uri,mime==null?"*/*":mime);
                    intent.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    intent.setClipData(android.content.ClipData.newUri(
                        getContentResolver(),"Open file",uri));
                    startActivity(android.content.Intent.createChooser(intent,"Open with"));
                }catch(Exception e){reportLibraryAction("external",false,message(e));}
            });
        }
        @JavascriptInterface public void renameLibraryFile(String value,String name){
            if(value==null||!allowedLibraryUris.contains(value))return;
            if(!canManageLibrary()){reportLibraryAction("rename",false,
                "This storage provider has not granted write access");return;}
            if(name==null||name.isBlank()||name.length()>240||
               name.contains("/")||name.contains("\\")||
               ".".equals(name)||"..".equals(name)){
                reportLibraryAction("rename",false,"Invalid file name");return;
            }
            fgDirectoryExecutor.execute(()->{
                try{
                    Uri result=android.provider.DocumentsContract.renameDocument(
                        getContentResolver(),Uri.parse(value),name);
                    if(result==null)throw new java.io.IOException(
                        "The storage provider refused to rename the file");
                    reportLibraryAction("rename",true,"Renamed to "+name);
                }catch(Exception e){reportLibraryAction("rename",false,message(e));}
            });
        }
        @JavascriptInterface public void deleteLibraryFile(String value){
            if(value==null||!allowedLibraryUris.contains(value))return;
            if(!canManageLibrary()){reportLibraryAction("delete",false,
                "This storage provider has not granted write access");return;}
            fgDirectoryExecutor.execute(()->{
                try{
                    if(!android.provider.DocumentsContract.deleteDocument(
                        getContentResolver(),Uri.parse(value)))
                        throw new java.io.IOException("The storage provider refused deletion");
                    reportLibraryAction("delete",true,"File deleted");
                }catch(Exception e){reportLibraryAction("delete",false,message(e));}
            });
        }
'''
s=s.replace(anchor,addition+anchor,1)
main.write_text(s)
print("Library SAF actions added: share, open-with, guarded rename/delete")

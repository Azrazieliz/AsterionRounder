#!/usr/bin/env python3
"""Streaming SAF copy/move with destination picker and verified move deletion.
No full-file buffering; never delete the source if destination cannot be verified.
"""
from pathlib import Path
p=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=p.read_text()
a="    private static final int REQ_KOIKATSU_PREVIEW = 2011;"
assert s.count(a)==1
s=s.replace(a,a+"\n    private static final int REQ_LIBRARY_TRANSFER = 2012;",1)
a="    private void selectKoikatsuPreview(){"
assert s.count(a)==1
s=s.replace(a,r'''    private volatile Uri fgTransferSource;
    private volatile boolean fgTransferMove;
    private final java.util.concurrent.atomic.AtomicBoolean fgTransferCancelled=
        new java.util.concurrent.atomic.AtomicBoolean();
    private final java.util.concurrent.atomic.AtomicBoolean fgTransferBusy=
        new java.util.concurrent.atomic.AtomicBoolean();

    private void selectTransferDestination(String original,boolean move){
        if(original==null || !allowedLibraryUris.contains(original))return;
        if(move && !new Bridge().canManageLibrary()){
            js("window.FileGestionerLibrary?.operationResult("+
                "{\"operation\":\"move\",\"ok\":false,\"detail\":\"Source is read-only\"})");
            return;
        }
        if(fgTransferBusy.get()){
            js("window.FileGestionerLibrary?.operationResult("+
                "{\"operation\":\"transfer\",\"ok\":false,\"detail\":\"A transfer is still running\"})");
            return;
        }
        fgTransferSource=Uri.parse(original);
        fgTransferMove=move;
        fgTransferCancelled.set(false);
        Intent picker=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION |
            Intent.FLAG_GRANT_WRITE_URI_PERMISSION |
            Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(picker,REQ_LIBRARY_TRANSFER);
    }
    private void transferFeedback(String operation,boolean ok,String msg){
        String json;
        try{
            json=new org.json.JSONObject().put("operation",operation)
                .put("ok",ok).put("detail",msg).toString();
        }catch(Exception e){return;}
        final String payload=json;
        runOnUiThread(()->js("window.FileGestionerLibrary?.operationResult("+payload+")"));
    }
    private void transferProgress(long transferred,long total){
        String payload="{\"transferred\":"+transferred+",\"total\":"+total+"}";
        runOnUiThread(()->js("window.FileGestionerLibrary?.transferProgress("+payload+")"));
    }
    private void transferSafFile(Uri destinationTree){
        final Uri source=fgTransferSource;
        final boolean move=fgTransferMove;
        if(source==null || !fgTransferBusy.compareAndSet(false,true))return;
        fgDirectoryExecutor.execute(()->{
            Uri created=null;
            long received=0;
            String operation=move?"move":"copy";
            try{
                String name=displayName(source);
                if(name==null||name.isBlank()||name.contains("/")||name.contains("\\"))
                    throw new IOException("Unsafe source filename");
                String mime=getContentResolver().getType(source);
                if(mime==null||mime.isBlank())mime="application/octet-stream";
                String targetId=android.provider.DocumentsContract.getTreeDocumentId(destinationTree);
                Uri parent=android.provider.DocumentsContract.buildDocumentUriUsingTree(
                    destinationTree,targetId);
                if(source.equals(parent))
                    throw new IOException("Source and destination are identical");
                long expected=displaySize(source);
                created=android.provider.DocumentsContract.createDocument(
                    getContentResolver(),parent,mime,name);
                if(created==null)throw new IOException(
                    "Destination provider cannot create files in this folder");
                try(InputStream input=getContentResolver().openInputStream(source);
                    java.io.OutputStream output=getContentResolver().openOutputStream(created,"w")){
                    if(input==null||output==null)
                        throw new IOException("Provider refused to open the transfer stream");
                    byte[] buffer=new byte[1024*256];
                    long lastNotice=android.os.SystemClock.elapsedRealtime();
                    for(int length;(length=input.read(buffer))!=-1;){
                        if(fgTransferCancelled.get())
                            throw new java.util.concurrent.CancellationException("Transfer cancelled");
                        output.write(buffer,0,length);
                        received+=length;
                        long now=android.os.SystemClock.elapsedRealtime();
                        if(now-lastNotice>350){transferProgress(received,expected);lastNotice=now;}
                    }
                    output.flush();
                }
                if(expected>=0 && received!=expected)
                    throw new IOException("Incomplete transfer: "+received+" / "+expected+" bytes");
                long copiedSize=displaySize(created);
                if(copiedSize>=0 && copiedSize!=received)
                    throw new IOException("Destination size mismatch: "+copiedSize+" / "+received);
                if(move){
                    // Never delete the source on unknown or unverified cloud
                    // destination size: finished upload is not proof of commit.
                    if(expected<0||copiedSize<0){
                        transferFeedback("copy",true,
                            "Copied "+received+" bytes. Original kept: remote destination not verifiable.");
                        return;
                    }
                    if(!new Bridge().canManageLibrary() ||
                        !android.provider.DocumentsContract.deleteDocument(
                            getContentResolver(),source)){
                        transferFeedback("copy",true,
                            "Copy verified; original kept because source cannot be deleted.");
                        return;
                    }
                }
                transferFeedback(operation,true,(move?"Moved ":"Copied ")+name+
                    " ("+received+" bytes)");
                android.util.Log.i("FG_TRANSFER",operation.toUpperCase()+"_SUCCESS bytes="+received+
                    " source="+source.getAuthority()+" dest="+destinationTree.getAuthority());
            }catch(Exception error){
                if(created!=null){
                    try{android.provider.DocumentsContract.deleteDocument(
                        getContentResolver(),created);}catch(Exception ignored){}
                }
                transferFeedback(operation,false,"Transfer failed; source preserved. "+message(error));
                android.util.Log.w("FG_TRANSFER","Failed after "+received+" bytes",error);
            }finally{
                fgTransferSource=null;
                fgTransferBusy.set(false);
                transferProgress(0,0);
            }
        });
    }
'''+a,1)
a="        if(requestCode==REQ_LIBRARY_TREE){"
assert s.count(a)==1
s=s.replace(a,'''        if(requestCode==REQ_LIBRARY_TRANSFER){
            try{
                try{
                    int flags=data.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|
                        Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                    getContentResolver().takePersistableUriPermission(uri,flags);
                }catch(Exception ignored){
                    // One-time picker grants still permit an immediate transfer.
                }
                transferSafFile(uri);
            }catch(Exception e){transferFeedback("transfer",false,message(e));}
            return;
        }
'''+a,1)
a="        private boolean canManageLibrary(){"
assert s.count(a)==1
s=s.replace(a,'''        @JavascriptInterface public void copyLibraryFile(String value){
            runOnUiThread(()->selectTransferDestination(value,false));
        }
        @JavascriptInterface public void moveLibraryFile(String value){
            runOnUiThread(()->selectTransferDestination(value,true));
        }
        @JavascriptInterface public void cancelLibraryTransfer(){
            fgTransferCancelled.set(true);
        }
'''+a,1)
p.write_text(s)
print("SAF copy/move: streaming, transfer picker, byte-length verification, and safe cancellation")

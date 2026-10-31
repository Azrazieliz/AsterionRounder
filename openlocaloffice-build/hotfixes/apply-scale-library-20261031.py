#!/usr/bin/env python3
"""SAF folder pagination + no synchronous all-file JSON construction."""
from pathlib import Path
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text()
start=s.index("    private void loadLibrary(String folder){")
end=s.index("    private volatile String fgFolderToken;",start)
assert 1000 < end-start < 7000
repl=r'''    private final java.util.concurrent.ExecutorService fgDirectoryExecutor=
        java.util.concurrent.Executors.newCachedThreadPool();
    private final java.util.concurrent.atomic.AtomicLong fgDirectoryVersion=
        new java.util.concurrent.atomic.AtomicLong();

    private void loadLibrary(String folder){
        final Uri root=libraryTree;
        if(root==null){runOnUiThread(()->
            js("window.FileGestionerLibrary?.missingCollection()"));return;}
        final long request=fgDirectoryVersion.incrementAndGet();
        fgDirectoryExecutor.execute(()->{
            final long started=android.os.SystemClock.elapsedRealtime();
            try {
                if(request!=fgDirectoryVersion.get())return;
                final java.util.concurrent.atomic.AtomicBoolean firstBatchLogged=
                    new java.util.concurrent.atomic.AtomicBoolean();
                allowedLibraryUris.clear();
                libraryCovers.clear();
                // Old collection scanner stopped at 500 and built an all-file
                // JSONArray before showing any files. Every bounded batch is
                // displayed as soon as its cursor rows are read.
                for(int attempt=0;attempt<3;attempt++){
                  try {
                    ReaderLibrary.Listing listing=ReaderLibrary.stream(this,root,folder,
                    (directory,batch,finished)->{
                        if(request!=fgDirectoryVersion.get())
                            throw new java.util.concurrent.CancellationException();
                        if(batch.length()>0 && firstBatchLogged.compareAndSet(false,true))
                            android.util.Log.i("FG_PERF","COLLECTION_FIRST_BATCH_ms="+
                                (android.os.SystemClock.elapsedRealtime()-started)+
                                " provider="+root.getAuthority()+
                                " rows="+batch.length());
                        for(int i=0;i<batch.length();i++){
                            org.json.JSONObject item=batch.getJSONObject(i);
                            String id=java.util.UUID.randomUUID().toString()
                                .replace("-","");
                            Uri file=Uri.parse(item.getString("uri"));
                            allowedLibraryUris.add(file.toString());
                            libraryCovers.put(id,new LibraryCover(file,
                                item.optString("name"),item.optLong("size",-1),
                                item.optLong("modified",0),item.optBoolean("folder")));
                            String name=item.optBoolean("folder")?"folder-cover.jpg":
                                item.optString("name");
                            String low=name.toLowerCase(java.util.Locale.ROOT);
                            boolean image=item.optBoolean("folder")||
                                low.endsWith(".epub")||low.endsWith(".cbz")||
                                low.endsWith(".zip")||low.endsWith(".pdf")||
                                low.endsWith(".jpg")||low.endsWith(".jpeg")||
                                low.endsWith(".png")||low.endsWith(".webp");
                            if(image){
                                item.put("cover","https://fg-assets.invalid/cover/"+id);
                                boolean cloud="de.felixnuesse.extract.vcp"
                                    .equals(file.getAuthority());
                                // Avoid thousands of filesystem checks during
                                // cloud enumeration; remote covers remain
                                // sequential on demand.
                                item.put("remoteCover",cloud);
                            }
                        }
                        final String json=new org.json.JSONObject()
                            .put("version",request).put("folder",directory)
                            .put("requestedFolder",folder==null?"":folder)
                            .put("finished",finished).put("items",batch).toString();
                        if(request==fgDirectoryVersion.get()){
                            runOnUiThread(()->{
                                if(request==fgDirectoryVersion.get())
                                    js("window.FileGestionerLibrary?.append("+json+")");
                            });
                        }
                    });
                android.util.Log.i("FG_PERF","COLLECTION_STREAM_DONE_ms="+
                    (android.os.SystemClock.elapsedRealtime()-started)+
                    " folder="+listing.folder);
                    break;
                  } catch(ReaderLibrary.PendingDirectoryException pending){
                    if(request!=fgDirectoryVersion.get())return;
                    android.util.Log.w("FG_FOLDER","ROUND_SYNC_RETRY attempt="+
                        (attempt+1)+" loading="+pending.loading+
                        " message="+pending.getMessage());
                    if(attempt==2)throw pending;
                    final int retry=attempt+2;
                    runOnUiThread(()->{
                        if(request==fgDirectoryVersion.get())
                            js("window.FileGestionerLibrary?.loadingStatus("+
                                q("RoundSync has not returned the folder contents. Retrying "+
                                    retry+"/3 without discarding images…")+")");
                    });
                    Thread.sleep(3000L);
                  }
                }
            }catch(java.util.concurrent.CancellationException ignored){
                android.util.Log.i("FG_PERF","COLLECTION_STREAM_CANCELLED");
            }catch(Throwable error){
                if(request==fgDirectoryVersion.get())
                    runOnUiThread(()->js("window.FileGestionerLibrary?.error("+
                        q(message(error))+")"));
            }
        });
    }
'''
s=s[:start]+repl+s[end:]
main.write_text(s)
print("Library SAF streams unlimited directory rows in batches; no all-files JSON or 500-file cutoff")

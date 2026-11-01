#!/usr/bin/env python3
"""Native Android reader extensions: Back, image folders, audio/video.
Works on top of existing EPUB/ZIP/PDF readers, not a new reader fork.
"""
from pathlib import Path
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text()
# The Android back handler should NEVER close the Activity from a document.
a='''    private void navigateSystemBack() {
        if(web==null) {
            finish();
            return;
        }'''
assert s.count(a)==1,"Android system-back implementation changed"
s=s.replace(a,'''    private void navigateSystemBack() {
        if(fgMediaPanel!=null){hideFgMedia();return;}
        if(web==null)return;''',1)
start=s.index('                if(!"true".equals(handled)){',s.index('private void navigateSystemBack()'))
end=s.index('            });',start)
assert 0<end-start<900
s=s[:start]+'''                if(!"true".equals(handled)){
                    // Root Back returns to the library; never exit the Activity.
                    js("window.FileGestionerLibrary?.show()");
                }
'''+s[end:]
# Android 13+ system back behavior must not bypass the registered handler.
manifest=root/"AndroidManifest.xml"
m=manifest.read_text()
if 'android:enableOnBackInvokedCallback' not in m:
    assert '<application' in m
    m=m.replace('<application','<application android:enableOnBackInvokedCallback="true"',1)
manifest.write_text(m)

# Allow image-directory reading from the same SAF permissions as the library.
anchor='''    private void openUri(Uri uri) {'''
assert s.count(anchor)==1
methods=r'''    private volatile String fgFolderToken;
    private volatile java.util.List<android.net.Uri> fgFolderUris=
        java.util.Collections.emptyList();
    private volatile java.util.List<String> fgFolderNames=
        java.util.Collections.emptyList();
    private android.widget.FrameLayout fgMediaPanel;
    private android.widget.VideoView fgMediaVideo;
    private static final class FolderPage{
        final Uri uri; final String name;
        FolderPage(Uri u,String n){uri=u;name=n;}
    }
    private void showFgMedia(Uri uri,String name,boolean video){
        hideFgMedia();
        android.widget.FrameLayout host=findViewById(android.R.id.content);
        if(host==null)return;
        android.widget.FrameLayout panel=new android.widget.FrameLayout(this);
        panel.setBackgroundColor(android.graphics.Color.rgb(9,12,19));
        android.widget.VideoView player=new android.widget.VideoView(this);
        android.widget.FrameLayout.LayoutParams videoParams=new android.widget.FrameLayout.LayoutParams(
            -1,video?-1:Math.round(160*getResources().getDisplayMetrics().density));
        videoParams.gravity=android.view.Gravity.CENTER;
        panel.addView(player,videoParams);
        android.widget.TextView title=new android.widget.TextView(this);
        title.setText(name);
        title.setTextColor(android.graphics.Color.WHITE);
        title.setTextSize(15);
        title.setPadding(18,13,110,13);
        title.setBackgroundColor(0x99202b44);
        android.widget.FrameLayout.LayoutParams titleParams=new android.widget.FrameLayout.LayoutParams(
            -1,-2,android.view.Gravity.TOP);
        panel.addView(title,titleParams);
        android.widget.Button close=new android.widget.Button(this);
        close.setText("Back");
        close.setOnClickListener(v->hideFgMedia());
        android.widget.FrameLayout.LayoutParams closeParams=new android.widget.FrameLayout.LayoutParams(
            -2,-2,android.view.Gravity.TOP|android.view.Gravity.RIGHT);
        panel.addView(close,closeParams);
        host.addView(panel,new android.widget.FrameLayout.LayoutParams(-1,-1));
        fgMediaPanel=panel;fgMediaVideo=player;
        android.widget.MediaController controls=new android.widget.MediaController(this);
        controls.setAnchorView(player);
        player.setMediaController(controls);
        player.setOnPreparedListener(mp->{
            mp.setLooping(false);
            player.start();
            controls.show(3500);
        });
        player.setOnErrorListener((mp,what,extra)->{
            android.widget.Toast.makeText(this,"Unable to play this media stream",
                android.widget.Toast.LENGTH_LONG).show();
            return true;
        });
        player.setVideoURI(uri);
        player.requestFocus();
        if(!video)title.setText("Audio • "+name);
    }
    private void hideFgMedia(){
        if(fgMediaVideo!=null){
            fgMediaVideo.stopPlayback();
            fgMediaVideo=null;
        }
        if(fgMediaPanel!=null){
            android.view.ViewParent parent=fgMediaPanel.getParent();
            if(parent instanceof android.view.ViewGroup)
                ((android.view.ViewGroup)parent).removeView(fgMediaPanel);
            fgMediaPanel=null;
        }
        js("window.FileGestionerLibrary?.show()");
    }
    private void openFolderImages(String uriText){
        if(uriText==null||!allowedLibraryUris.contains(uriText))return;
        final Uri directory=Uri.parse(uriText);
        collectionIo.execute(()->{
            try {
                Uri children=android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(
                    directory,android.provider.DocumentsContract.getDocumentId(directory));
                String[] fields={
                    android.provider.DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                    android.provider.DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                    android.provider.DocumentsContract.Document.COLUMN_MIME_TYPE};
                java.util.List<FolderPage> found=new java.util.ArrayList<>();
                try(android.database.Cursor cursor=getContentResolver().query(
                    children,fields,null,null,null)){
                    if(cursor==null)throw new java.io.IOException("Cannot list image folder");
                    while(cursor.moveToNext()&&found.size()<20000){
                        String id=cursor.getString(0),name=cursor.getString(1),
                            mime=cursor.getString(2);
                        if(id==null||name==null||name.startsWith("."))continue;
                        String lower=name.toLowerCase(java.util.Locale.ROOT);
                        boolean supported=lower.endsWith(".png")||lower.endsWith(".jpg")||
                            lower.endsWith(".jpeg")||lower.endsWith(".webp")||
                            lower.endsWith(".gif")||lower.endsWith(".avif");
                        if(!supported||android.provider.DocumentsContract.Document.MIME_TYPE_DIR.equals(mime))
                            continue;
                        found.add(new FolderPage(
                            android.provider.DocumentsContract.buildDocumentUriUsingTree(directory,id),
                            name));
                    }
                }
                if(found.isEmpty()){
                    // The selected folder isn't an image collection. Open as a
                    // normal folder rather than showing an empty comic.
                    runOnUiThread(()->js("window.FileGestionerLibrary?.enterFolder("+
                        q(android.provider.DocumentsContract.getDocumentId(directory))+")"));
                    return;
                }
                found.sort((a,b)->com.openlocal.office.core.ReaderLibrary.naturalCompare(
                    a.name,b.name));
                final String token=java.util.UUID.randomUUID().toString();
                java.util.List<Uri> urls=new java.util.ArrayList<>();
                java.util.List<String> names=new java.util.ArrayList<>();
                org.json.JSONArray images=new org.json.JSONArray();
                for(int i=0;i<found.size();i++){
                    FolderPage page=found.get(i);
                    urls.add(page.uri);names.add(page.name);
                    images.put(new org.json.JSONObject().put("name",page.name)
                        .put("url","https://fg-assets.invalid/folder-img/"+token+"/"+i));
                }
                fgFolderUris=java.util.Collections.unmodifiableList(urls);
                fgFolderNames=java.util.Collections.unmodifiableList(names);
                fgFolderToken=token;
                org.json.JSONObject payload=new org.json.JSONObject()
                    .put("name","Image folder").put("type","folderImages")
                    .put("pages",images);
                runOnUiThread(()->js("window.loadDocument("+payload.toString()+")"));
            }catch(Exception e){
                runOnUiThread(()->js("window.FileGestionerLibrary?.error("+
                    q("Cannot open image collection: "+message(e))+")"));
            }
        });
    }
'''
s=s.replace(anchor,methods+anchor,1)
# Route supported media through Android's native playback controls rather
# than the old deliberately unsupported-file error.
anchor='''                String quickType = detectType(uri, name);'''
assert s.count(anchor)==1,"File detection anchor changed"
s=s.replace(anchor,'''
                String lowerMediaName=name.toLowerCase(java.util.Locale.ROOT);
                if(lowerMediaName.endsWith(".mp3")||lowerMediaName.endsWith(".mp4")||
                   lowerMediaName.endsWith(".m4a")||lowerMediaName.endsWith(".webm")||
                   lowerMediaName.endsWith(".mkv")||lowerMediaName.endsWith(".mov")||
                   lowerMediaName.endsWith(".flac")||lowerMediaName.endsWith(".wav")||
                   lowerMediaName.endsWith(".ogg")||lowerMediaName.endsWith(".opus")){
                    final boolean isVideo=lowerMediaName.endsWith(".mp4")||
                        lowerMediaName.endsWith(".webm")||lowerMediaName.endsWith(".mkv")||
                        lowerMediaName.endsWith(".mov");
                    runOnUiThread(()->showFgMedia(uri,name,isVideo));
                    return;
                }
                String quickType = detectType(uri, name);''',1)
# WebView serves individual images on demand, never loading the folder into
# memory or downloading all pictures before page 1 is displayed.
anchor='''                    if(assetPath!=null&&assetPath.startsWith("/cover/")){'''
assert s.count(anchor)==1,"Asset route missing"
resource=r'''                    if(assetPath!=null&&assetPath.startsWith("/folder-img/")){
                        String[] part=assetPath.split("/");
                        if(part.length==4&&part[2].equals(fgFolderToken)){
                            try{
                                int index=Integer.parseInt(part[3]);
                                java.util.List<Uri> current=fgFolderUris;
                                java.util.List<String> names=fgFolderNames;
                                if(index>=0&&index<current.size()&&index<names.size()){
                                    String low=names.get(index).toLowerCase(java.util.Locale.ROOT);
                                    String mime=low.endsWith(".png")?"image/png":
                                        low.endsWith(".webp")?"image/webp":
                                        low.endsWith(".gif")?"image/gif":
                                        low.endsWith(".avif")?"image/avif":"image/jpeg";
                                    InputStream input=getContentResolver()
                                        .openInputStream(current.get(index));
                                    if(input!=null)return new WebResourceResponse(mime,null,input);
                                }
                            }catch(Exception e){
                                android.util.Log.w("FG_FOLDER","Image request failed",e);
                            }
                        }
                        return new WebResourceResponse("image/jpeg",null,
                            new ByteArrayInputStream(new byte[0]));
                    }
'''
s=s.replace(anchor,resource+anchor,1)
# Methods exposed to WebView must reside in the existing JavaScript bridge.
bridge_anchor="        @JavascriptInterface public void openKoikatsu3d(){"
assert s.count(bridge_anchor)==1
s=s.replace(bridge_anchor,'''        @JavascriptInterface public void openImageFolder(String uri){
            MainActivity.this.openFolderImages(uri);
        }
'''+bridge_anchor,1)
# VideoView uses the same Activity and its native playback lifecycle.
destroy='''    @Override public void onDestroy() {'''
assert s.count(destroy)==1
s=s.replace(destroy,destroy+'''
        if(fgMediaVideo!=null)fgMediaVideo.stopPlayback();''',1)
main.write_text(s)
reader=root/"java/com/openlocal/office/core/ReaderLibrary.java"
text=reader.read_text()
assert 'public static int naturalCompare' in text or 'private static int naturalCompare' in text
text=text.replace('private static int naturalCompare','public static int naturalCompare',1)
assert '".png",".webp",".avif",".gif",' in text
text=text.replace('".png",".webp",".avif",".gif",','".png",".webp",".avif",".gif",".mp3",".mp4",".m4a",".webm",',1)
reader.write_text(text)
print("Native: Android Back stays in app; image directories stream each image; MP3/MP4/M4A/WebM native media view.")

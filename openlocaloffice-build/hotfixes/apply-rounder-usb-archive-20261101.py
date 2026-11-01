#!/usr/bin/env python3
"""2026-11-01: recover secure USB-only PC pairing after release change; image decode fallbacks."""
from pathlib import Path
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text(encoding="utf-8")
old='''        @JavascriptInterface public String getRemoteToken(){
            return getSharedPreferences("fg_remote",MODE_PRIVATE)
                .getString("token","");
        }'''
new='''        // Authorized USB pair-once: ADB pushes the existing PC secret into
        // Android/data/<package>/files; only this app consumes and deletes it.
        // Never embed credentials in APK, repository, logs, or web resources.
        private String fgEnsureUsbPair(){
            android.content.SharedPreferences prefs=
                getSharedPreferences("fg_remote",MODE_PRIVATE);
            String existing=prefs.getString("token","");
            if(existing!=null&&!existing.isBlank())return existing;
            java.io.File folder=getExternalFilesDir(null);
            if(folder==null)return "";
            java.io.File once=new java.io.File(folder,"fg-usb-pair.token");
            if(!once.isFile())return "";
            try{
                if(once.length()<25||once.length()>256)return "";
                String candidate=new String(java.nio.file.Files.readAllBytes(once.toPath()),
                    java.nio.charset.StandardCharsets.US_ASCII).trim();
                if(!candidate.matches("[A-Za-z0-9_\\\\-]{32,256}"))return "";
                if(!prefs.edit().putString("token",candidate)
                    .putString("endpoint","http://127.0.0.1:39273").commit())
                    return "";
                android.util.Log.i("FG_REMOTE","USB_PAIR_STORED");
                return candidate;
            }catch(Exception issue){
                android.util.Log.w("FG_REMOTE","USB_PAIR_FAILED "+issue.getClass().getSimpleName());
                return "";
            }finally{once.delete();}
        }
        @JavascriptInterface public String getRemoteToken(){
            return fgEnsureUsbPair();
        }'''
assert s.count(old)==1,"remote getter missing"
s=s.replace(old,new,1)
old='''        @JavascriptInterface public String getRemoteEndpoint(){
            return getSharedPreferences("fg_remote",MODE_PRIVATE)
                .getString("endpoint","");
        }'''
new='''        @JavascriptInterface public String getRemoteEndpoint(){
            fgEnsureUsbPair();
            return getSharedPreferences("fg_remote",MODE_PRIVATE)
                .getString("endpoint","");
        }'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''                    String token=getSharedPreferences("fg_remote",MODE_PRIVATE)
                        .getString("token","");'''
assert s.count(old)==1
s=s.replace(old,'''                    String token=fgEnsureUsbPair();''',1)
old='''                    if(!remote.startsWith("https://"))
                        throw new IOException("Secure remote PC endpoint is not configured");'''
new='''                    if(!remote.startsWith("https://") &&
                       !remote.equals("http://127.0.0.1:39273"))
                        throw new IOException("Secure remote PC endpoint is not configured");'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''                    }catch(Exception ignored){}
                    return new WebResourceResponse("text/plain","UTF-8",
                        new ByteArrayInputStream(new byte[0]));
                }
                return super.shouldInterceptRequest(view,request);'''
new='''                    }catch(Exception failure){
                        android.util.Log.e("FG_IMAGE","BOOK_ASSET_FAILED path="+
                            (assetPath==null?"none":assetPath.replaceAll("[^a-zA-Z0-9/_\\\\.-]","_")),
                            failure);
                    }
                    return new WebResourceResponse("text/plain","UTF-8",
                        new ByteArrayInputStream(new byte[0]));
                }
                return super.shouldInterceptRequest(view,request);'''
assert s.count(old)==1,"resource fallback not found"
s=s.replace(old,new,1)
main.write_text(s,encoding="utf-8")
# Native decoder is used only after WebView reports that the original raster
# failed. Never endlessly retry one broken cloud stream.
app=root/"assets/universal-reader.js"
t=app.read_text(encoding="utf-8")
old='''       im.addEventListener('error',()=>{
         clearTimeout(watchdog);
         im.removeAttribute('src');'''
new='''       im.addEventListener('error',()=>{
         clearTimeout(watchdog);
         if(entry.streamed&&!im.dataset.fgSampled){
           const regular=bridge()?.getArchiveImageUrl?.(entry.name)||'';
           if(regular.includes('/book/')){
             im.dataset.fgSampled='yes';
             im.src=regular.replace('/book/','/book-fallback/');
             return;
           }
         }
         im.removeAttribute('src');'''
assert t.count(old)==1,"archive error handler not found"
app.write_text(t.replace(old,new,1),encoding="utf-8")
book=root/"assets/epub-reader.js"
t=book.read_text(encoding="utf-8")
old="      target.referrerPolicy='no-referrer';target.draggable=false;"
new="""      target.referrerPolicy='no-referrer';target.draggable=false;
      target.addEventListener('error',()=>{
        if(target.dataset.fgSampled||!target.src.includes('/book/'))return;
        target.dataset.fgSampled='yes';
        target.src=target.src.replace('/book/','/book-fallback/');
      });"""
assert t.count(old)==1
book.write_text(t.replace(old,new,1),encoding="utf-8")
print("USB_SECURE_PAIR_AND_ARCHIVE_IMAGE_FALLBACK_READY")

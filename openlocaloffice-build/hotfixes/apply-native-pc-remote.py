#!/usr/bin/env python3
"""Integrate native PC 3D UI and local authenticated upload into Android."""
from pathlib import Path
import re
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text()
anchor='        @JavascriptInterface public void openKoikatsu3d(){'
assert s.count(anchor)==1
method=r'''        @JavascriptInterface public boolean returnToExternalFile(){
            final Intent intent=getIntent();
            if(intent!=null&&Intent.ACTION_VIEW.equals(intent.getAction())){
                runOnUiThread(MainActivity.this::finish);
                return true;
            }
            return false;
        }
        @JavascriptInterface public String getRemoteToken(){
            return getSharedPreferences("fg_remote",MODE_PRIVATE)
                .getString("token","");
        }
        @JavascriptInterface public String getRemoteEndpoint(){
            return getSharedPreferences("fg_remote",MODE_PRIVATE)
                .getString("endpoint","");
        }
        @JavascriptInterface public boolean setRemoteEndpoint(String value){
            if(value==null||value.length()>512)return false;
            try{
                java.net.URI address=new java.net.URI(value.trim());
                if(!"https".equalsIgnoreCase(address.getScheme())||
                    address.getHost()==null||
                    address.getRawUserInfo()!=null||
                    address.getRawPath()!=null&&!address.getRawPath().isEmpty()||
                    address.getRawQuery()!=null||address.getRawFragment()!=null)
                    return false;
                String addressText=address.toASCIIString().replaceAll("/+$","");
                getSharedPreferences("fg_remote",MODE_PRIVATE)
                    .edit().putString("endpoint",addressText).apply();
                return true;
            }catch(Exception error){return false;}
        }
        @JavascriptInterface public void setRemoteToken(String token){
            if(token==null||token.length()>256)return;
            getSharedPreferences("fg_remote",MODE_PRIVATE).edit()
                .putString("token",token.trim()).apply();
        }
        @JavascriptInterface public void remoteOpen3D(String kind){
            if(!"cube".equals(kind)&&!"blend".equals(kind)&&
               !"koikatsu".equals(kind))return;
            final Uri source=currentUri;
            if(!"cube".equals(kind)){
                if(source==null)return;
                if("koikatsu".equals(kind)&&
                    !source.equals(fgVerifiedKoikatsuCard)){
                    runOnUiThread(()->js("window.FileGestionerRemoteViewer.onOpen("+
                       q("{\"error\":\"The selected PNG is not a native Koikatsu card\"}")+")"));
                    return;
                }
                if("blend".equals(kind)&&
                   !java.util.Arrays.asList("blend","blend1").contains(currentType)){
                    runOnUiThread(()->js("window.FileGestionerRemoteViewer.onOpen("+
                       q("{\"error\":\"Open a .blend file before connecting Blender\"}")+")"));
                    return;
                }
            }
            io.execute(()->{
                java.io.File staging=null;
                try {
                    String token=getSharedPreferences("fg_remote",MODE_PRIVATE)
                        .getString("token","");
                    if(token==null||token.isBlank())throw new IOException("This app needs PC authorization");
                    String remote=getSharedPreferences("fg_remote",MODE_PRIVATE)
                        .getString("endpoint","");
                    if(!remote.startsWith("https://"))
                        throw new IOException("Secure remote PC endpoint is not configured");
                    long size=0;
                    if(!"cube".equals(kind)){
                        staging=java.io.File.createTempFile("fg-remote-", ".bin",getCacheDir());
                        try(InputStream in=getContentResolver().openInputStream(source);
                            OutputStream out=new BufferedOutputStream(
                                new FileOutputStream(staging),128*1024)){
                            if(in==null)throw new IOException("Source cannot be read");
                            byte[] buffer=new byte[128*1024];int n;
                            while((n=in.read(buffer))!=-1){
                                size+=n;
                                if(size>256L*1024*1024)
                                    throw new IOException("Native remote source exceeds 256 MiB");
                                out.write(buffer,0,n);
                            }
                        }
                    }
                    java.net.HttpURLConnection request=(java.net.HttpURLConnection)
                        new java.net.URL(getSharedPreferences("fg_remote",MODE_PRIVATE)
                            .getString("endpoint","")+"/api/open?kind="+kind).openConnection();
                    request.setRequestMethod("POST");
                    request.setConnectTimeout(6000);
                    request.setReadTimeout(60000);
                    request.setRequestProperty("X-FG-Token",token);
                    request.setRequestProperty("Content-Type","application/octet-stream");
                    request.setDoOutput(true);
                    request.setFixedLengthStreamingMode(size);
                    try(OutputStream out=request.getOutputStream()){
                        if(staging!=null)try(InputStream in=new FileInputStream(staging)){
                            byte[] buffer=new byte[128*1024];int n;
                            while((n=in.read(buffer))!=-1)out.write(buffer,0,n);
                        }
                    }
                    java.io.InputStream responseStream=request.getResponseCode()<400?
                        request.getInputStream():request.getErrorStream();
                    String result;
                    try(InputStream input=responseStream){
                        result=input==null?"{\"error\":\"PC did not answer\"}":
                            new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);
                    }
                    request.disconnect();
                    final String payload=result;
                    runOnUiThread(()->js("window.FileGestionerRemoteViewer.onOpen("+q(payload)+")"));
                }catch(Exception e){
                    final String result="{\"error\":"+q("PC remote: "+message(e))+"}";
                    runOnUiThread(()->js("window.FileGestionerRemoteViewer.onOpen("+q(result)+")"));
                }finally{
                    if(staging!=null)staging.delete();
                }
            });
        }
'''
s=s.replace(anchor,method+anchor)
# Reuse the card classification done when the PNG was opened, not another
# full remote read merely to detect the same Koikatsu signature.
field='    private volatile Uri libraryTree;'
assert s.count(field)==1
s=s.replace(field,'    private volatile Uri fgVerifiedKoikatsuCard;\n'+field,1)
signature='boolean character=false; // Nonblocking: show image before validating Koikatsu payload'
assert s.count(signature)==1
s=s.replace(signature,signature+'''
                    fgVerifiedKoikatsuCard=null;
                    if("png".equals(quickType)||name.toLowerCase(java.util.Locale.ROOT).endsWith(".png"))
                        verifyKoikatsuInBackground(uri,imageStreamToken);''',1)
# The image must be displayed first; only the verified card gains 3D controls.
field2='    private volatile Uri fgVerifiedKoikatsuCard;'
assert s.count(field2)==1
s=s.replace(field2,field2+'''
    private void verifyKoikatsuInBackground(Uri uri,String token){
        io.execute(()->{
            boolean verified=KoikatsuCards.isCharacterCard(this,uri);
            if(!token.equals(imageStreamToken)||!uri.equals(currentUri))return;
            fgVerifiedKoikatsuCard=verified?uri:null;
            final boolean ok=verified;
            runOnUiThread(()->js("window.FileGestionerFolder?.koikatsuCard("+ok+")"));
            android.util.Log.i("FG_IMAGE","KOIKATSU_CHECK_DONE verified="+ok);
        });
    }
''',1)
main.write_text(s)
js=root/"assets/universal-reader.js"
s=js.read_text()
old="()=>bridge()?.openKoikatsu3d?.()"
assert old in s
s=s.replace(old,"()=>window.FileGestionerRemoteViewer?.open('koikatsu')")
js.write_text(s)
# Embed code after all other scripts to ensure the global object is ready.
html=root/"assets/index.html"
s=html.read_text()
assert "</body>" in s
s=s.replace("</body>",'<script src="fg-remote-ui.js"></script>\n</body>')
html.write_text(s)
css=root/"assets/style.css"
css.write_text(css.read_text()+r'''
/* Native PC 3D is independent of the offline 3D mesh viewer. */
.fg-pc-entry[hidden]{display:none!important}
.fg-pc-entry{position:fixed;bottom:calc(16px + env(safe-area-inset-bottom));
 right:15px;z-index:97;background:#506ce3;color:#fff;
 border:1px solid #7389ef;border-radius:13px;padding:12px;font:700 14px system-ui}
.fg-pc-overlay{position:fixed;inset:0;z-index:10000;display:flex;flex-direction:column;
 background:#0d1420;color:#eaf1ff;font:13px system-ui;
 padding:calc(7px + env(safe-area-inset-top)) 8px calc(8px + env(safe-area-inset-bottom))}
.fg-pc-head{display:flex;align-items:center;justify-content:space-between;padding:6px 3px}
.fg-pc-close,.fg-pc-action{background:#283958;color:white;border:1px solid #4a6091;
 border-radius:8px;padding:10px;font:600 13px system-ui}
.fg-pc-pair,.fg-pc-actions{display:flex;gap:6px;padding:5px 0}
.fg-pc-token{min-width:0;flex:1;color:white;background:#172438;border:1px solid #3c557a;
 border-radius:8px;padding:8px 10px;font:13px system-ui}
.fg-pc-viewport{position:relative;flex:1;min-height:120px;background:#101925;
 display:grid;place-items:center;touch-action:none;overflow:hidden}
.fg-pc-frame{width:100%;height:100%;object-fit:contain;pointer-events:none}
.fg-pc-frame[hidden]{display:none!important}
.fg-pc-placeholder{max-width:300px;text-align:center;color:#a3b5cf;
 font:500 13px/1.65 system-ui;padding:18px}
.fg-pc-placeholder[hidden]{display:none!important}
.fg-pc-status{font:12px/1.5 system-ui;color:#cbd7f2;min-height:30px;padding:6px}
''')
xml=root/"res/xml"
xml.mkdir(parents=True,exist_ok=True)
(xml/"fg_remote_network_security.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="false" />
  <domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="false">127.0.0.1</domain>
    <domain includeSubdomains="false">localhost</domain>
  </domain-config>
</network-security-config>
''')
manifest=root/"AndroidManifest.xml"
s=manifest.read_text()
if 'android.permission.INTERNET' not in s:
    s=s.replace('<application','<uses-permission android:name="android.permission.INTERNET"/>\n    <application',1)
assert 'android:networkSecurityConfig' not in s
s=s.replace('<application','<application android:networkSecurityConfig="@xml/fg_remote_network_security"',1)
manifest.write_text(s)
print("Native PC remote 3D integrated: Koikatsu PNG, independent Blender cube and .blend files")

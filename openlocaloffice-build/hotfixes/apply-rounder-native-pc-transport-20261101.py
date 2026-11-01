#!/usr/bin/env python3
"""Bridge native PC status/frames through Android; file WebView never fetches localhost."""
from pathlib import Path
root=Path("app/src/main")
main=root/"java/com/openlocal/office/MainActivity.java"
s=main.read_text(encoding="utf-8")
anchor='''                    String assetPath=u.getPath();
                    if(assetPath!=null&&assetPath.startsWith("/early/")){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''                    String assetPath=u.getPath();
                    if("/pc-frame".equals(assetPath))return fgAuthenticatedPcFrame(u);
                    if(assetPath!=null&&assetPath.startsWith("/early/")){''',1)
# Native transport uses the same approved encrypted/USB pairing settings;
# Java holds token, while the document WebView sees only image or status data.
anchor='''    private void closeTextStream() {'''
assert s.count(anchor)==1
helper=r'''    private java.net.HttpURLConnection fgNativePcConnection(String path)throws IOException{
        android.content.SharedPreferences prefs=getSharedPreferences("fg_remote",MODE_PRIVATE);
        String endpoint=prefs.getString("endpoint","");
        String token=prefs.getString("token","");
        if(token==null||token.length()<20)throw new IOException("PC pairing is missing");
        if(!"http://127.0.0.1:39273".equals(endpoint)&&
           !(endpoint!=null&&endpoint.startsWith("https://")))
            throw new IOException("PC endpoint is not configured");
        if(!path.startsWith("/api/status?")&&!path.startsWith("/api/frame?"))
            throw new IOException("Unsupported PC resource");
        java.net.HttpURLConnection connection=(java.net.HttpURLConnection)
            new java.net.URL(endpoint+path).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(6000);
        connection.setReadTimeout(135000);
        connection.setRequestProperty("X-FG-Token",token);
        connection.setUseCaches(false);
        return connection;
    }
    private WebResourceResponse fgAuthenticatedPcFrame(Uri uri){
        java.net.HttpURLConnection connection=null;
        try{
            String query=uri.getEncodedQuery();
            if(query==null||query.length()>320||
               !query.matches("[A-Za-z0-9_.%&=+\\\\-]+"))
                throw new IOException("Invalid native camera request");
            String session=uri.getQueryParameter("session");
            if(session==null||!session.matches("[0-9a-f]{24}"))
                throw new IOException("Invalid PC 3D session");
            connection=fgNativePcConnection("/api/frame?"+query);
            int code=connection.getResponseCode();
            if(code!=200)throw new IOException("PC frame status "+code);
            String type=connection.getContentType();
            if(type==null||(!type.startsWith("image/png")&&!type.startsWith("image/jpeg")))
                throw new IOException("PC did not send a native image");
            java.io.InputStream incoming=connection.getInputStream();
            final java.net.HttpURLConnection owned=connection;
            java.io.InputStream stream=new java.io.FilterInputStream(incoming){
                @Override public void close()throws IOException{
                    try{super.close();}finally{owned.disconnect();}
                }
            };
            java.util.Map<String,String> headers=new java.util.HashMap<>();
            headers.put("Access-Control-Allow-Origin","*");
            headers.put("Cache-Control","no-store");
            headers.put("Access-Control-Allow-Private-Network","true");
            return new WebResourceResponse(type.split(";")[0],null,
                200,"OK",headers,stream);
        }catch(Exception failure){
            if(connection!=null)connection.disconnect();
            android.util.Log.e("FG_REMOTE","PC_FRAME_PROXY_FAILED",failure);
            java.util.Map<String,String> headers=new java.util.HashMap<>();
            headers.put("Access-Control-Allow-Origin","*");
            headers.put("Cache-Control","no-store");
            return new WebResourceResponse("image/png",null,503,"Service Unavailable",
                headers,new java.io.ByteArrayInputStream(new byte[0]));
        }
    }
'''
s=s.replace(anchor,helper+anchor,1)
anchor='''        @JavascriptInterface public String getRemoteEndpoint(){'''
assert s.count(anchor)==1
native=r'''        @JavascriptInterface public String getNativePcStatus(String session){
            if(session==null||!session.matches("[0-9a-f]{24}"))
                return "{\"error\":\"Invalid native PC session\"}";
            fgEnsureUsbPair();
            java.net.HttpURLConnection connection=null;
            try{
                connection=fgNativePcConnection("/api/status?session="+session);
                int code=connection.getResponseCode();
                java.io.InputStream response=code<400?connection.getInputStream():
                    connection.getErrorStream();
                if(response==null)throw new IOException("PC status unavailable");
                byte[] data;
                try(java.io.InputStream input=response){data=input.readNBytes(8192);}
                String body=new String(data,java.nio.charset.StandardCharsets.UTF_8);
                if(code!=200)return "{\"error\":\"Native PC HTTP "+code+"\"}";
                return body;
            }catch(Exception error){
                android.util.Log.w("FG_REMOTE","PC_STATUS_PROXY_FAILED "+
                    error.getClass().getSimpleName());
                return "{\"error\":"+q("PC connection failed: "+error.getMessage())+"}";
            }finally{if(connection!=null)connection.disconnect();}
        }
'''
s=s.replace(anchor,native+anchor,1)
main.write_text(s,encoding="utf-8")
js=root/"assets/fg-remote-ui.js"
t=js.read_text(encoding="utf-8")
old="""async function api(path,opts={}){
  const auth=token();if(!auth)throw Error('PC authorization is not configured. Open Remote settings once.');
  const resp=await fetch(URL_ROOT()+path,{...opts,headers:{...(opts.headers||{}),'X-FG-Token':auth},cache:'no-store'});"""
new="""async function api(path,opts={}){
  const auth=token();if(!auth)throw Error('PC authorization is not configured. Open Remote settings once.');
  // File-backed WebViews block localhost fetch even when the native connection
  // and ADB reverse are healthy. Delegate authentication to Android instead.
  if(path.startsWith('/api/status?')&&bridge()?.getNativePcStatus){
    const sid=new URLSearchParams(path.split('?')[1]||'').get('session');
    const raw=bridge().getNativePcStatus(sid||'');
    return {ok:true,json:async()=>JSON.parse(raw)};
  }
  if(path.startsWith('/api/frame?')&&bridge()?.getNativePcStatus){
    const query=path.slice('/api/frame?'.length);
    const resp=await fetch('https://fg-assets.invalid/pc-frame?'+query,{cache:'no-store'});
    if(!resp.ok)throw Error('Native PC image bridge HTTP '+resp.status);
    return resp;
  }
  const resp=await fetch(URL_ROOT()+path,{...opts,headers:{...(opts.headers||{}),'X-FG-Token':auth},cache:'no-store'});"""
assert t.count(old)==1,"PC viewer API path missing"
t=t.replace(old,new,1)
start=t.index("    const data=await (await api(url)).blob();")
end=t.index("    if(retryTimer){clearTimeout(retryTimer);retryTimer=null;}",start)
t=t[:start]+r'''    // Image subresources work from file:///android_asset without unsafe
    // universal file URL access. Android transparently proxies each frame.
    const imageUrl='https://fg-assets.invalid/pc-frame?'+
      url.slice('/api/frame?'.length)+'&sequence='+at;
    const next=new Image();
    next.className='fg-pc-frame';
    next.alt='Remote native 3D scene';
    next.draggable=false;
    next.hidden=true;
    await new Promise((resolve,reject)=>{
      next.onload=resolve;
      next.onerror=()=>reject(Error('Native PC image proxy returned no frame'));
      next.src=imageUrl;
    });
    if(dead||at!==serial)return;
    const previous=frame;
    frame=next;
    viewport.appendChild(next);
    next.hidden=false;
    if(previous)previous.remove();
    const placeholder=overlay?.querySelector('.fg-pc-placeholder');
    if(placeholder)placeholder.hidden=true;
    setStatus('Drag: orbit camera · pinch: zoom · two-finger drag: pan');
    renderFailures=0;
'''+t[end:]
js.write_text(t,encoding="utf-8")
print("ANDROID_NATIVE_PC_STATUS_AND_FRAME_PROXY_READY")

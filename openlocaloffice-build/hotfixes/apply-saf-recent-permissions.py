from pathlib import Path
main=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
source=main.read_text()
old='    private String imageStreamToken;'
assert source.count(old)==1
source=source.replace(old,old+'''
    // Transient ACTION_VIEW grants last only for the current open
    // session; do not claim they are permanently reusable on a later launch.
    private Uri sessionRecentUri;
    private String sessionRecentName;
    private String sessionRecentMime;
''')
old='''    private void remember(Uri uri,String name,String mime){getSharedPreferences("recent",MODE_PRIVATE).edit().putString("uri",uri.toString()).putString("name",name).putString("mime",mime).apply();}
    private String recentJson(){android.content.SharedPreferences p=getSharedPreferences("recent",MODE_PRIVATE);String u=p.getString("uri",null),n=p.getString("name",null);return u==null?"null":"{\\"uri\\":"+q(u)+",\\"name\\":"+q(n)+"}";}'''
assert source.count(old)==1
source=source.replace(old,r'''    private boolean hasDurableReadGrant(Uri uri) {
        if(uri==null)return false;
        if("file".equals(uri.getScheme()))return true;
        if(!"content".equals(uri.getScheme()))return false;
        try {
            for(UriPermission grant:getContentResolver().getPersistedUriPermissions()){
                if(grant.isReadPermission() && grant.getUri().equals(uri))return true;
            }
        }catch(Exception ignored){}
        return false;
    }
    private void remember(Uri uri,String name,String mime){
        sessionRecentUri=uri;
        sessionRecentName=name;
        sessionRecentMime=mime;
        if(hasDurableReadGrant(uri)){
            getSharedPreferences("recent",MODE_PRIVATE).edit()
                .putString("uri",uri.toString()).putString("name",name)
                .putString("mime",mime).apply();
        }else{
            // Remove any stale reference to the just-opened ephemeral URI.
            android.content.SharedPreferences preferences=
                getSharedPreferences("recent",MODE_PRIVATE);
            if(uri.toString().equals(preferences.getString("uri",null)))
                preferences.edit().clear().apply();
        }
    }
    private String recentJson(){
        Uri active=sessionRecentUri;
        if(active!=null)return "{\"uri\":"+q(active.toString())+
            ",\"name\":"+q(sessionRecentName)+"}";
        android.content.SharedPreferences p=getSharedPreferences("recent",MODE_PRIVATE);
        String value=p.getString("uri",null),name=p.getString("name",null);
        if(value==null)return "null";
        Uri saved=Uri.parse(value);
        if(!hasDurableReadGrant(saved)){
            p.edit().clear().apply();
            return "null";
        }
        return "{\"uri\":"+q(value)+",\"name\":"+q(name)+"}";
    }''')
old='''        @JavascriptInterface public void openRecent(String uri){ runOnUiThread(() -> openUri(Uri.parse(uri))); }'''
assert source.count(old)==1
source=source.replace(old,r'''        @JavascriptInterface public void openRecent(String uri){
            runOnUiThread(() -> {
                Uri value=Uri.parse(uri);
                if((sessionRecentUri!=null&&sessionRecentUri.equals(value))||
                    hasDurableReadGrant(value)){
                    openUri(value);
                }else{
                    getSharedPreferences("recent",MODE_PRIVATE).edit().clear().apply();
                    js("window.showError("+q(
                        "The original file provider's access expired. Open this file again through the Android Files picker.")+")");
                }
            });
        }''')
main.write_text(source)
print("SAF Recent URI: session grants never persisted as durable links; no deleted cache URI referenced")

package com.openlocal.office.core;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Locale;

/** Explicit app-origin folders for deterministic TeraBox routing.
 * Folder location is configured by the owner. Filename extension is never
 * treated as proof of which Asterion application created a file.
 *
 * Downloader is ONE application. Historical names such as Kuroha/Kyora/
 * VideoFlow are NOT separate applications or default active source roots.
 */
public final class FgRounderSources {
    public static final String[] IDS={"downloader","art","sound","converter","koikatsu"};
    private static final String[] NAMES={
        "Asterion Downloader","Asterion Art","Asterion Sound",
        "Asterion 2D→3D","Asterion KK"
    };
    private static final String[] GENERIC={"/Incoming","/Downloads"};
    private final FgTeraboxSearchIndex index;
    private final SharedPreferences preferences;
    public static final class Route {
        public final String source,destination,reason;
        public final boolean auto;
        Route(String source,String destination,String reason,boolean auto){
            this.source=source;this.destination=destination;
            this.reason=reason;this.auto=auto;
        }
    }
    public FgRounderSources(Context context,FgTeraboxSearchIndex index){
        this.index=index;
        this.preferences=context.getApplicationContext()
            .getSharedPreferences("fg_rounder_sources_v2",Context.MODE_PRIVATE);
    }
    private String key(String id,String field){
        return "source_"+index.currentScope()+"_"+id+"_"+field;
    }
    private static int idIndex(String id){
        for(int i=0;i<IDS.length;i++)if(IDS[i].equals(id))return i;
        return -1;
    }
    private static boolean under(String path,String directory){
        return path!=null&&directory!=null&&!directory.isBlank()&&
            path.startsWith(directory+"/")&&path.length()>directory.length()+1;
    }
    public String root(String id){
        if(idIndex(id)<0||index.currentScope().isEmpty())return "";
        return preferences.getString(key(id,"root"),"");
    }
    public boolean sourceAutomatic(String id){
        return idIndex(id)>=0&&!root(id).isEmpty()&&
            preferences.getBoolean(key(id,"auto"),false);
    }
    /**
     * Owners register their ACTUAL app output/incoming folder, not guessed
     * paths or SDK package names. Reject broad collection roots.
     */
    public void configure(String id,String folder,boolean automatic){
        if(idIndex(id)<0||index.currentScope().isEmpty())
            throw new IllegalArgumentException("Invalid app or disconnected account");
        String path=folder==null?"":folder.trim();
        if(!path.isEmpty()){
            if(path.length()>240||!path.startsWith("/")||path.endsWith("/")||
               path.equals("/")||path.contains("//")||path.contains("\\")||
               path.contains("/../")||path.endsWith("/..")||
               path.contains("/./")||path.endsWith("/.")||
               path.contains("?")||path.contains("%")||path.contains("[")||
               path.contains("*"))
               throw new IllegalArgumentException("Invalid TeraBox source folder");
            String lower=path.toLowerCase(Locale.ROOT);
            for(String tooBroad:new String[]{"/art","/books","/apps","/videos",
                "/audio","/documents","/archives","/3d","/games","/music"}){
                if(lower.equals(tooBroad))
                    throw new IllegalArgumentException("Select the app's incoming/export subfolder, not an entire collection");
            }
            for(String other:IDS)
                if(!other.equals(id)){
                    String previous=root(other);
                    if(!previous.isBlank()&&
                        (path.equals(previous)||under(path,previous)||under(previous,path)))
                        throw new IllegalArgumentException("A source folder overlaps another app");
                }
        }
        preferences.edit().putString(key(id,"root"),path)
            .putBoolean(key(id,"auto"),!path.isEmpty()&&automatic).apply();
    }
    public JSONArray profiles()throws Exception{
        JSONArray items=new JSONArray();
        for(int i=0;i<IDS.length;i++){
            String root=root(IDS[i]);
            items.put(new JSONObject().put("id",IDS[i]).put("name",NAMES[i])
                .put("root",root).put("configured",!root.isEmpty())
                .put("auto",sourceAutomatic(IDS[i]))
                .put("note",IDS[i].equals("koikatsu")?
                    "Use a dedicated export folder. Cards/scenes require clear folder markers.":
                    "Choose the app's real TeraBox incoming/export folder."));
        }
        return items;
    }
    public ArrayList<String> roots(){
        ArrayList<String> values=new ArrayList<>();
        Collections.addAll(values,GENERIC);
        for(String id:IDS){
            String path=root(id);
            if(!path.isEmpty()&&!values.contains(path))values.add(path);
        }
        return values;
    }
    public static String classify(String name){
        String n=name.toLowerCase(Locale.ROOT);
        if(n.matches(".*\\.(png|jpe?g|webp|bmp|gif|avif|heif|heic|tiff?)$"))return "image";
        if(n.matches(".*\\.(mp4|webm|mkv|mov|avi|m4v|wmv)$"))return "video";
        if(n.matches(".*\\.(mp3|m4a|flac|wav|ogg|opus|aac)$"))return "audio";
        if(n.matches(".*\\.(epub|mobi|azw3)$"))return "book";
        if(n.matches(".*\\.(cbz|cbr|cb7)$"))return "comic";
        if(n.endsWith(".pdf"))return "pdf";
        if(n.matches(".*\\.(apk|apks|xapk|aab|exe|msi|deb|rpm)$"))return "app";
        if(n.matches(".*\\.(glb|gltf|fbx|obj|vrm|blend|pmx|pmd|usd|usdz|stl)$"))return "model";
        if(n.matches(".*\\.(docx?|xlsx?|pptx?|odt|ods|csv|txt|md|rtf)$"))return "document";
        if(n.matches(".*\\.(zip|7z|rar|tar|gz|bz2)$"))return "archive";
        if(n.endsWith(".mid")||n.endsWith(".midi"))return "midi";
        if(n.endsWith(".psd")||n.endsWith(".kra")||n.endsWith(".ora"))return "art-project";
        return "other";
    }
    private static String standardTarget(String kind){
        switch(kind){
            case "image":return "/Art/Downloads";
            case "book":case "comic":case "pdf":return "/Books/Downloads";
            case "app":return "/Apps/Downloads";
            case "video":return "/Videos/Downloads";
            case "audio":case "midi":return "/Audio/Downloads";
            case "document":return "/Documents/Downloads";
            case "model":return "/3D/Downloads";
            case "archive":return "/Archives/Downloads";
            default:return "";
        }
    }
    public Route route(String path){
        if(path==null||!path.startsWith("/")||path.endsWith("/")||
           path.contains("/../")||path.contains("/./")||path.contains("\\"))return null;
        String file=path.substring(path.lastIndexOf('/')+1);
        if(file.isBlank())return null;
        String type=classify(file);
        // Exact, user-chosen app export roots have priority over generic inboxes.
        for(int i=0;i<IDS.length;i++){
            String id=IDS[i],root=root(id);
            if(root.isBlank()||!under(path,root))continue;
            String dest="",reason=NAMES[i]+" export · "+type;
            String relative=path.substring(root.length()+1).toLowerCase(Locale.ROOT);
            switch(id){
                case "downloader":dest=standardTarget(type);break;
                case "art":
                    if(type.equals("image"))dest="/Art/Generated";
                    else if(type.equals("video"))dest="/Art/Animations";
                    else if(type.equals("art-project"))dest="/Art/Projects";
                    break;
                case "sound":
                    if(type.equals("audio"))dest="/Audio/AsterionSound";
                    else if(type.equals("midi"))dest="/Audio/MIDI";
                    break;
                case "converter":
                    if(type.equals("model"))dest="/3D/Models";
                    else if(type.equals("image")&&
                        (relative.contains("/textures/")||relative.startsWith("textures/")))
                        dest="/3D/Textures";
                    break;
                case "koikatsu":
                    // PNG character cards and studio scenes share an image format.
                    // Only actual path markers justify distinct destinations.
                    if(type.equals("image")&&
                        (relative.startsWith("chara/")||relative.startsWith("characters/")||
                         relative.startsWith("cards/")||relative.contains("/chara/")||
                         relative.contains("/characters/")||relative.contains("/cards/")))
                        dest="/Games/Koikatsu/Characters";
                    else if(type.equals("image")&&
                        (relative.startsWith("scenes/")||relative.startsWith("studio/")||
                         relative.contains("/scenes/")||relative.contains("/studio/")))
                        dest="/Games/Koikatsu/Scenes";
                    else if(type.equals("model")&&
                        (relative.startsWith("models/")||relative.contains("/models/")))
                        dest="/Games/Koikatsu/Models";
                    else if(type.equals("archive")&&
                        (relative.startsWith("mods/")||relative.contains("/mods/")))
                        dest="/Games/Koikatsu/Mods";
                    break;
            }
            if(dest.isEmpty())return null;
            return new Route(id,dest,reason,sourceAutomatic(id));
        }
        for(String generic:GENERIC)
            if(under(path,generic)){
                String dest=standardTarget(type);
                if(!dest.isEmpty())
                    return new Route("generic",dest,"General incoming folder · "+type,true);
            }
        return null;
    }
}

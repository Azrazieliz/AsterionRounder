#!/usr/bin/env python3
"""Add real TeraBox file-management APIs to existing Rounder release assembly.

Runs after the preview and video UI stages. Only modifies the assembled
Java client, MainActivity bridge, and existing cloud-file actions; does not
replace readers, authentication, signing identity, or local-file handling.
"""
from pathlib import Path

base=Path("app/src/main")
client=base/"java/com/openlocal/office/core/FgTeraboxClient.java"
main=base/"java/com/openlocal/office/MainActivity.java"
library=base/"assets/premium-library.js"
css=base/"assets/style.css"

def insert_once(source, anchor, addition, label):
    count=source.count(anchor)
    if count!=1:
        raise AssertionError("%s: expected one anchor, found %s" % (label,count))
    return source.replace(anchor,addition+anchor,1)

java_methods=r'''
    private static String checkedCloudName(String name) {
        if(name==null||name.isBlank()||name.length()>240||
           name.equals(".")||name.equals("..")||name.contains("/")||
           name.contains("\\")||name.indexOf('\n')>=0||
           name.indexOf('\r')>=0||name.indexOf((char)0)>=0)
            throw new IllegalArgumentException("Invalid TeraBox file name");
        return name;
    }
    private static String cloudParent(String path){
        int cut=path.lastIndexOf('/');
        return cut<=0?"/":path.substring(0,cut);
    }
    private static String cloudJoin(String folder,String name){
        return ("/".equals(folder)?"":folder)+"/"+checkedCloudName(name);
    }

    /** Invalidate only the modified folders, preserving huge account caches. */
    private void invalidateCloudFolder(String folder){
        String scope=metadataScope();
        if(scope.isEmpty())return;
        String prefix=scope+"|"+folder+"|";
        synchronized(hotPages){
            hotPages.keySet().removeIf(key->key.startsWith(prefix));
        }
        prefs.edit().putLong("directory_edit_"+cacheId(scope+"|"+folder),
            System.currentTimeMillis()).apply();
        synchronized(linkCache){linkCache.clear();}
    }
    private JSONObject manageCloudFile(String operation,JSONArray items)throws Exception{
        Map<String,String> query=new LinkedHashMap<>();
        query.put("opera",operation);
        query.put("onnest","fail");
        Map<String,String> form=new LinkedHashMap<>();
        form.put("async","0");form.put("ondup","fail");
        form.put("filelist",items.toString());
        JSONObject result=postCloud("/api/filemanager",query,form);
        JSONArray info=result.optJSONArray("info");
        if(info!=null)for(int i=0;i<info.length();i++){
            JSONObject row=info.optJSONObject(i);
            if(row!=null&&row.optInt("errno",0)!=0)
                throw new IOException("TeraBox "+operation+" failed for an item: "+
                    row.optInt("errno"));
        }
        return result;
    }
    public void renameCloud(String source,String newName)throws Exception {
        String from=safePath(source), name=checkedCloudName(newName);
        if("/".equals(from))throw new IllegalArgumentException("Cannot rename cloud root");
        String target=cloudJoin(cloudParent(from),name);
        if(from.equals(target))throw new IllegalArgumentException("Name is unchanged");
        long before=fileDetails(from).optLong("size",-1);
        JSONArray files=new JSONArray().put(new JSONObject().put("path",from)
            .put("newname",name));
        manageCloudFile("rename",files);
        invalidateCloudFolder(cloudParent(from));
        JSONObject changed=fileDetails(target);
        if(!target.equals(changed.optString("path",target))||
           (before>=0&&changed.optLong("size",-1)!=before))
            throw new IOException("Rename submitted but target verification failed");
    }
    public void transferCloud(String source,String destination,boolean copy)throws Exception{
        String from=safePath(source),dest=safePath(destination);
        if("/".equals(from))throw new IllegalArgumentException("Cannot transfer cloud root");
        String name=checkedCloudName(from.substring(from.lastIndexOf('/')+1));
        String target=cloudJoin(dest,name);
        if(from.equals(target)||dest.equals(from)||dest.startsWith(from+"/"))
            throw new IllegalArgumentException("Cannot transfer into the same path or child");
        long before=fileDetails(from).optLong("size",-1);
        JSONArray files=new JSONArray().put(new JSONObject().put("path",from)
            .put("dest",dest).put("newname",name));
        manageCloudFile(copy?"copy":"move",files);
        invalidateCloudFolder(cloudParent(from));
        invalidateCloudFolder(dest);
        JSONObject created=fileDetails(target);
        if(!target.equals(created.optString("path",target))||
           (before>=0&&created.optLong("size",-1)!=before))
            throw new IOException("Cloud transfer submitted but target verification failed");
    }
    public void deleteCloud(String path)throws Exception{
        String from=safePath(path);
        if("/".equals(from))throw new IllegalArgumentException("Cannot delete cloud root");
        fileDetails(from); // refuse removal of an already missing/stale path
        manageCloudFile("delete",new JSONArray().put(from));
        invalidateCloudFolder(cloudParent(from));
        // Provider reports an accepted operation; absence is checked afresh.
        try{
            JSONObject remaining=fileDetails(from);
            if(from.equals(remaining.optString("path",from)))
                throw new IOException("Cloud deletion unverified: source still exists");
        }catch(IOException failure){
            if(failure.getMessage()!=null&&failure.getMessage().startsWith(
                    "Cloud deletion unverified"))throw failure;
            // File metadata unavailable is expected after a successful removal.
            if(!"TeraBox file metadata unavailable".equals(failure.getMessage())&&
               !"TeraBox file is inaccessible".equals(failure.getMessage()))
                throw new IOException("Deletion submitted; verification needs refresh",failure);
        }
    }
    public void createCloudFolder(String destination,String name)throws Exception{
        String path=cloudJoin(safePath(destination),checkedCloudName(name));
        createDirectory(path);
        invalidateCloudFolder(safePath(destination));
        JSONObject created=fileDetails(path);
        if(created.optInt("isdir",0)!=1)
            throw new IOException("Folder creation unverified");
    }
    /** Folder picker: small paginated metadata requests, never enumerate account. */
    public JSONObject listCloudFolders(String folder,int page)throws Exception{
        String path=safePath(folder);
        if(page<1||page>100000)throw new IllegalArgumentException("Invalid folder page");
        JSONArray rows=listPage(path,page);
        JSONArray children=new JSONArray();
        for(int i=0;i<rows.length();i++){
            JSONObject item=rows.optJSONObject(i);
            if(item!=null&&item.optInt("isdir",0)==1){
                String child=item.optString("path","");
                if(child.startsWith("/")&&!child.equals(path))
                    children.put(new JSONObject().put("path",child)
                        .put("name",item.optString("server_filename",
                             child.substring(child.lastIndexOf('/')+1))));
            }
        }
        return new JSONObject().put("path",path).put("page",page)
            .put("hasMore",rows.length()>=PAGE).put("folders",children);
    }

'''
original=client.read_text(encoding="utf-8")
updated=insert_once(original,"    /** Fresh metadata for newest incoming items",java_methods,
                    "client cloud write methods")
# Each cached folder page is reused only if no writes occurred to that folder.
old_cache='if(saved.isFile()&&age>=0&&age<15L*60*1000L){'
new_cache=('if(saved.isFile()&&age>=0&&age<15L*60*1000L&&'
           'saved.lastModified()>=prefs.getLong('
           '"directory_edit_"+cacheId(scope+"|"+folder),0L)){')
updated=insert_once(updated,old_cache,new_cache,"stale cloud page guard")
# insert_once preserves anchor, so eliminate the old conditional once.
updated=updated.replace(new_cache+old_cache,new_cache,1)
client.write_text(updated,encoding="utf-8")

native=r'''
        private void rounderCloudResult(String action,boolean ok,String detail){
            reportLibraryAction(action,ok,detail);
        }
        @JavascriptInterface public void cloudFileOperation(
                String action,String path,String argument){
            if(!tb().configured()){rounderCloudResult(action,false,
                "Connect TeraBox before changing files");return;}
            if(action==null||!java.util.Arrays.asList(
                "rename","move","copy","delete","mkdir").contains(action))return;
            final String scope=tb().metadataScope();
            fgDirectoryExecutor.execute(()->{
                try{
                    if(scope.isEmpty()||!scope.equals(tb().metadataScope()))
                        throw new IOException("TeraBox account changed");
                    com.openlocal.office.core.FgTeraboxClient api=tb();
                    String from=path==null?"/":path;
                    String dest=null;
                    switch(action){
                        case "rename":
                            api.renameCloud(from,argument);
                            dest=(from.lastIndexOf('/')<=0?"":
                                from.substring(0,from.lastIndexOf('/')))+"/"+argument;
                            break;
                        case "move":
                        case "copy":
                            api.transferCloud(from,argument,"copy".equals(action));
                            dest=("/".equals(argument)?"":argument)+
                                from.substring(from.lastIndexOf('/'));
                            break;
                        case "delete":api.deleteCloud(from);break;
                        case "mkdir":api.createCloudFolder(from,argument);break;
                        default:throw new IllegalArgumentException("Unsupported cloud operation");
                    }
                    if(!scope.equals(tb().metadataScope()))
                        throw new IOException("TeraBox account changed during operation");
                    if("delete".equals(action)){
                        fgCloudIndex().noteDeleted(scope,from);
                    }else if(("move".equals(action)||"rename".equals(action))&&dest!=null){
                        fgCloudIndex().noteMoved(scope,from,dest);
                    }
                    rounderCloudResult(action,true,
                        "TeraBox "+action+" completed");
                }catch(Exception error){
                    rounderCloudResult(action,false,
                        error.getMessage()==null?"Cloud operation failed":error.getMessage());
                }
            });
        }
        @JavascriptInterface public void listCloudDestinationFolders(
                String folder,int page){
            if(!tb().configured())return;
            final String scope=tb().metadataScope();
            fgDirectoryExecutor.execute(()->{
                try{
                    org.json.JSONObject payload=tb().listCloudFolders(folder,page);
                    if(!scope.equals(tb().metadataScope()))return;
                    runOnUiThread(()->js(
                        "window.FileGestionerLibrary?.cloudFolderChoices("+
                        payload.toString()+")"));
                }catch(Exception error){
                    try{
                        org.json.JSONObject failure=new org.json.JSONObject()
                            .put("path",folder).put("page",page)
                            .put("error",error.getMessage()==null?
                                "Folder list unavailable":error.getMessage());
                        runOnUiThread(()->js(
                            "window.FileGestionerLibrary?.cloudFolderChoices("+
                            failure.toString()+")"));
                    }catch(Exception ignored){}
                }
            });
        }
'''
m=main.read_text(encoding="utf-8")
m=insert_once(m,"        @JavascriptInterface public void searchTeraboxIndex(",
              native,"native cloud bridge")
main.write_text(m,encoding="utf-8")

js_helpers=r'''
 const cloudFolderButton=b('New folder','fg-lib-secondary',()=>cloudCreateFolder());
 toolbar.append(cloudFolderButton);
 let cloudDestination=null;
 function cloudNameField(title,label,initial,action,source){
   const sheet=fileSheet(title,'Changes are applied directly to TeraBox.');
   const input=E('input','fg-file-name-input');
   input.value=initial||'';
   input.maxLength=240;
   input.setAttribute('aria-label',label);
   sheet.append(input);
   fileAction(sheet,'Cancel','',closeFileActions);
   fileAction(sheet,'Confirm','No existing files will be overwritten',()=>{
     const name=input.value.trim();
     if(!name||name==='.'||name==='..'||name.includes('/')||       name.includes(String.fromCharCode(92))||name.includes(String.fromCharCode(10))||       name.includes(String.fromCharCode(13)))return;
     if(action==='rename'&&name===initial)return;
     closeFileActions();
     bridge()?.cloudFileOperation?.(action,source,name);
   });
   input.focus();
 }
 function cloudCreateFolder(){
   if(!cloudMode)return;
   cloudNameField('Create TeraBox folder','Folder name','','mkdir',currentFolder||'/');
 }
 function cloudChooseDestination(item,action){
   cloudDestination={item,action,path:currentFolder||'/',page:1};
   cloudBrowseDestination(cloudDestination.path,1);
 }
 function cloudBrowseDestination(path,page){
   if(!cloudDestination)return;
   cloudDestination.path=path;cloudDestination.page=page;
   const sheet=fileSheet((cloudDestination.action==='copy'?'Copy':'Move')+' to folder',
     'Destination: '+path);
   sheet.append(E('p','fg-transfer-note','Loading TeraBox folders…'));
   bridge()?.listCloudDestinationFolders?.(path,page);
 }
 function cloudFolderChoices(data){
   const state=cloudDestination;
   if(!state||!operationDialog?.isConnected||!data||
      state.path!==data.path||state.page!==data.page)return;
   const sheet=fileSheet((state.action==='copy'?'Copy':'Move')+' to folder',
     'Destination: '+state.path);
   if(data.error){
     sheet.append(E('p','fg-file-write-note',data.error));
     fileAction(sheet,'Try again','',()=>cloudBrowseDestination(state.path,state.page));
   }else{
     fileAction(sheet,'Select this folder','No overwrites',()=>{
       const path=state.path;
       const source=state.item.path;
       const action=state.action;
       cloudDestination=null;
       closeFileActions();
       bridge()?.cloudFileOperation?.(action,source,path);
     });
     if(state.path!=='/'){
       fileAction(sheet,'↑ Parent folder','',()=>{
         const parent=state.path.substring(0,state.path.lastIndexOf('/'))||'/';
         cloudBrowseDestination(parent,1);
       });
     }
     for(const child of data.folders||[]){
       fileAction(sheet,'▸ '+child.name,'Open destination folder',()=>{
         cloudBrowseDestination(child.path,1);
       });
     }
     if(data.hasMore)
       fileAction(sheet,'More folders','Next 100 TeraBox entries',()=>{
         cloudBrowseDestination(state.path,state.page+1);
       });
   }
   fileAction(sheet,'Cancel','',()=>{cloudDestination=null;closeFileActions();});
 }
'''
j=library.read_text(encoding="utf-8")
j=insert_once(j,"function showFileActions(item){",js_helpers,
              "cloud file picker helpers")
actions=r'''    fileAction(sheet,'Properties','Cloud file metadata',()=>fileProperties(item));
    fileAction(sheet,'Rename','Change the cloud filename',()=>{
      cloudNameField('Rename '+item.name,'New file name',item.name,
                     'rename',item.path);
    });
    fileAction(sheet,'Copy to folder','Copy within TeraBox without downloading',()=>{
      cloudChooseDestination(item,'copy');
    });
    fileAction(sheet,'Move to folder','Move within TeraBox without downloading',()=>{
      cloudChooseDestination(item,'move');
    });
    fileAction(sheet,item.folder?'Delete folder':'Delete file',
      'Remove the selected original from TeraBox',()=>{
      const confirm=fileSheet('Delete from TeraBox?',
        'This may move the item to the provider recycle bin.');
      confirm.append(E('p','fg-file-delete-name',item.path));
      fileAction(confirm,'Cancel','',closeFileActions);
      fileAction(confirm,'Delete from TeraBox','Confirm cloud deletion',()=>{
        closeFileActions();
        bridge()?.cloudFileOperation?.('delete',item.path,'');
      },{danger:true});
    },{danger:true});
'''
start=j.index("function showFileActions(item){")
cloud_start=j.index("if(item.terabox){",start)
close=j.index("fileAction(sheet,'Close','',closeFileActions);",cloud_start)
if close<0:raise AssertionError("cloud sheet Close action missing")
j=j[:close]+actions+j[close:]
j=insert_once(j,"function request(){",
    "function request(){\n  cloudFolderButton.hidden=!cloudMode;\n",
    "cloud new folder on request")
if j.count("window.FileGestionerLibrary={")!=1:
    raise AssertionError("cloud folder callback anchor changed")
j=j.replace("window.FileGestionerLibrary={",
            "window.FileGestionerLibrary={\n  cloudFolderChoices,",1)
# A metadata refresh after any actual cloud modification must not reuse a
# 15-minute cached page or old same-collection cards.
old="if(result.ok&&['rename','delete','move','copy'].includes(result.operation))request();"
new=("if(result.ok&&['rename','delete','move','copy','mkdir'].includes(result.operation)){"
     "collectionCacheKey='';cloudDestination=null;request();}")
if j.count(old)!=1:raise AssertionError("cloud refresh result anchor changed")
j=j.replace(old,new,1)
library.write_text(j,encoding="utf-8")
css.write_text(css.read_text(encoding="utf-8")+"""
/* Native cloud-file management stays in existing Rounder action sheets. */
.fg-lib-toolbar button[hidden]{display:none!important}
.fg-file-sheet .fg-file-name-input{box-sizing:border-box;display:block;
 width:100%;padding:13px;margin:12px 0;color:inherit;
 background:#1b2b42;border:1px solid #62728b;border-radius:10px}
""",encoding="utf-8")
print("ROUNDER_CLOUD_FILE_ACTIONS_READY: rename/copy/move/delete/mkdir + picker")

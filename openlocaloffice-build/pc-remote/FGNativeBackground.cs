using BepInEx;
using UnityEngine;
using System;
using System.IO;

namespace FileGestioner.NativeRemote
{
    // Renders Unity's actual native Koikatsu Studio camera into an offscreen
    // GPU texture. Unlike the ordinary Unity window screenshot, this does not
    // depend on the user's active desktop or window visibility.
    [BepInPlugin("com.filegestioner.nativebackground","File Gestioner Native Background","1.1.0")]
    public sealed class NativeBackground : BaseUnityPlugin
    {
        // Studio inherits this path from the authenticated PC bridge.
        // Never fill Windows C: with hundreds of cloud-supplied character cards.
        private readonly string folder=
            !String.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("FG_NATIVE3D_ROOT"))?
                Environment.GetEnvironmentVariable("FG_NATIVE3D_ROOT"):
                Path.Combine(Path.Combine(
                    Environment.GetEnvironmentVariable("USERPROFILE"),".file-gestioner"),"native-3d");
        private string requestPath;
        private string framePath;
        private string errorPath;
        private int cooldown;

        private void Awake()
        {
            Application.runInBackground=true;
            Directory.CreateDirectory(folder);
            requestPath=Path.Combine(folder,"native-frame.request");
            framePath=Path.Combine(folder,"native-frame.png");
            errorPath=Path.Combine(folder,"native-frame.error");
            Logger.LogInfo("File Gestioner offscreen Koikatsu renderer initialized.");
        }
        private void Update()
        {
            Application.runInBackground=true;
            if(++cooldown%7!=0||!File.Exists(requestPath))return;
            string request=File.ReadAllText(requestPath);
            File.Delete(requestPath);
            try {
                string[] parts=request.Split(',');
                int width=Math.Max(240,Math.Min(1200,int.Parse(parts[0])));
                int height=Math.Max(240,Math.Min(1920,int.Parse(parts[1])));
                if(File.Exists(framePath))File.Delete(framePath);
                if(File.Exists(errorPath))File.Delete(errorPath);

                Camera[] cameras=Camera.allCameras;
                if(cameras.Length==0)throw new Exception("No Unity camera is available");
                RenderTexture before=RenderTexture.active;
                Texture2D capture=null;
                RenderTexture texture=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);
                string diagnostics="";
                int bestScore=-1;
                byte[] best=null;
                string bestCamera="";
                try {
                    texture.Create();
                    capture=new Texture2D(width,height,TextureFormat.RGB24,false);
                    foreach(Camera candidate in cameras){
                        if(candidate==null||!candidate.enabled||candidate.cullingMask==0)continue;
                        RenderTexture former=candidate.targetTexture;
                        try {
                            candidate.targetTexture=texture;
                            candidate.Render();
                            RenderTexture.active=texture;
                            capture.ReadPixels(new Rect(0,0,width,height),0,0);
                            capture.Apply(false);
                            Color32[] pixels=capture.GetPixels32();
                            int score=0;int nonBlack=0;
                            Color32 prev=pixels[0];
                            int step=Math.Max(1,pixels.Length/4096);
                            for(int i=step;i<pixels.Length;i+=step){
                                Color32 p=pixels[i];
                                if(p.r+p.g+p.b>48)nonBlack++;
                                if(Math.Abs((int)p.r-prev.r)+Math.Abs((int)p.g-prev.g)+
                                    Math.Abs((int)p.b-prev.b)>45)score++;
                                prev=p;
                            }
                            diagnostics+=candidate.name+"(depth="+candidate.depth+
                                ",mask="+candidate.cullingMask+",detail="+score+
                                ",lit="+nonBlack+"); ";
                            if(score>bestScore){
                                byte[] bytes=capture.EncodeToPNG();
                                if(bytes!=null&&bytes.Length>200){
                                    best=bytes;bestScore=score;bestCamera=candidate.name;
                                }
                            }
                        }catch(Exception error){
                            diagnostics+=candidate.name+": "+error.Message+"; ";
                        }finally{
                            candidate.targetTexture=former;
                            RenderTexture.active=before;
                        }
                    }
                    // A uniform black frame is not a rendered character.
                    // Reject it rather than falsely showing the user success.
                    if(best==null||bestScore<5)
                        throw new Exception("No camera rendered a 3D scene: "+diagnostics);
                    File.WriteAllBytes(framePath,best);
                    Logger.LogInfo("Native offscreen frame: "+best.Length+
                        " bytes, camera="+bestCamera+", detail="+bestScore+
                        ", cameras="+cameras.Length+"; "+diagnostics);
                }finally{
                    RenderTexture.active=before;
                    if(capture!=null)UnityEngine.Object.Destroy(capture);
                    texture.Release();UnityEngine.Object.Destroy(texture);
                }
            } catch(Exception exc) {
                File.WriteAllText(errorPath,exc.ToString());
                Logger.LogError("Native offscreen frame failed: "+exc);
            }
        }
    }
}

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
        private readonly string folder=Path.Combine(
            Path.Combine(Environment.GetEnvironmentVariable("USERPROFILE"),".file-gestioner"),
            "native-3d");
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
                int width=Math.Max(128,Math.Min(1024,int.Parse(parts[0])));
                int height=Math.Max(128,Math.Min(1024,int.Parse(parts[1])));
                if(File.Exists(framePath))File.Delete(framePath);
                if(File.Exists(errorPath))File.Delete(errorPath);

                Camera[] cameras=Camera.allCameras;
                Camera camera=Camera.main;
                if(camera==null||!camera.enabled||camera.cullingMask==0){
                    camera=null;
                    foreach(Camera candidate in cameras){
                        if(candidate==null||!candidate.enabled||candidate.cullingMask==0)continue;
                        if(camera==null||candidate.depth>camera.depth)camera=candidate;
                    }
                }
                if(camera==null)throw new Exception("No active 3D camera");
                RenderTexture texture=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);
                RenderTexture former=camera.targetTexture;
                RenderTexture before=RenderTexture.active;
                Texture2D capture=null;
                try {
                    texture.Create();
                    camera.targetTexture=texture;
                    camera.Render();
                    RenderTexture.active=texture;
                    capture=new Texture2D(width,height,TextureFormat.RGB24,false);
                    capture.ReadPixels(new Rect(0,0,width,height),0,0);
                    capture.Apply(false);
                    byte[] bytes=capture.EncodeToPNG();
                    if(bytes==null||bytes.Length<200)
                        throw new Exception("Unity camera rendered no pixels");
                    File.WriteAllBytes(framePath,bytes);
                    Logger.LogInfo("Native offscreen frame: "+bytes.Length+
                        " bytes, camera="+camera.name+
                        " cameras="+cameras.Length);
                } finally {
                    camera.targetTexture=former;
                    RenderTexture.active=before;
                    if(capture!=null)UnityEngine.Object.Destroy(capture);
                    texture.Release();
                    UnityEngine.Object.Destroy(texture);
                }
            } catch(Exception exc) {
                File.WriteAllText(errorPath,exc.ToString());
                Logger.LogError("Native offscreen frame failed: "+exc);
            }
        }
    }
}

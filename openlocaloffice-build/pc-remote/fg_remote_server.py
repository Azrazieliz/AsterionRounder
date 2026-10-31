"""File Gestioner native-PC render bridge (USB ADB reverse, loopback only).
No cloud uploads. PC native Koikatsu CharaStudio and headless Blender are
independent sessions. All authentication secrets stay on the paired PC.
"""
import base64,hashlib,hmac,json,math,os,pathlib,secrets,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs

ROOT=pathlib.Path.home()/".file-gestioner"/"native-3d"
ROOT.mkdir(parents=True,exist_ok=True)
BLENDER=pathlib.Path(r"D:\Tools\Blender-5.2.2-LTS\blender-5.2.2-windows-x64\blender.exe")
STUDIO=pathlib.Path(r"D:\Tools\Steam\steamapps\common\Koikatsu Party\CharaStudio.exe")
STUDIO_HELPER=pathlib.Path(__file__).with_name("fg_studio_background_window.py")
STUDIO_LAUNCH_LOCK=threading.Lock()
STUDIO_RUNNER=None
RENDER=pathlib.Path(__file__).with_name("fg_blender_frame.py")
KEYFILE=ROOT/"pair-token.txt"
if not KEYFILE.exists():
    KEYFILE.write_text(secrets.token_urlsafe(32),encoding="ascii")
    try:os.chmod(KEYFILE,0o600)
    except OSError:pass
TOKEN=KEYFILE.read_text(encoding="ascii").strip()
SESSIONS={}
GUARD=threading.RLock()
RENDER_LOCK=threading.Lock()
MAX_SOURCE=256*1024*1024

def is_koikatsu_card(payload):
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):return False
    i=8
    while i+12<=len(payload) and i<MAX_SOURCE:
        size=int.from_bytes(payload[i:i+4],"big");kind=payload[i+4:i+8]
        if size>MAX_SOURCE or i+12+size>len(payload):return False
        i+=size+12
        if kind==b"IEND":
            trailer=payload[i:i+256*1024]
            return any(marker in trailer for marker in
                       (b"KoiKatuChara",b"KoikatsuChara",
                        b"KoiKatuCharaSunshine",b"KoiKatuCharaFile"))
    return False

def studio_ws(data,timeout=12):
    # KKStudioSocket runs INSIDE native Koikatsu Studio and talks only to this
    # local process. Never forward the unsecured game WebSocket to the phone.
    sys.path.insert(0,str(ROOT/"vendor"))
    import websocket
    conn=websocket.create_connection("ws://127.0.0.1:8765/ws",timeout=timeout)
    try:
        conn.send(json.dumps(data))
        result=json.loads(conn.recv())
        if result.get("type")=="error":raise RuntimeError(result.get("message","Koikatsu failed"))
        return result
    finally:conn.close()

def studio_ready():
    try:return studio_ws({"type":"ping","message":"File Gestioner"}).get("type")=="pong"
    except Exception:return False

def ensure_studio_ready(timeout=38):
    """Launch the installed native Studio only when a character is requested.
    Offscreen renderer remains independent from the foreground desktop."""
    global STUDIO_RUNNER
    if studio_ready():return True
    if not STUDIO.is_file() or not STUDIO_HELPER.is_file():
        return False
    with STUDIO_LAUNCH_LOCK:
        if studio_ready():return True
        if STUDIO_RUNNER is None or STUDIO_RUNNER.poll() is not None:
            flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
            STUDIO_RUNNER=subprocess.Popen(
                [sys.executable,str(STUDIO_HELPER)],
                cwd=str(STUDIO.parent),creationflags=flags,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            print("FG_STUDIO_AUTOSTART requested",flush=True)
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if studio_ready():return True
        if STUDIO_RUNNER is not None and STUDIO_RUNNER.poll() is not None:
            print("FG_STUDIO_AUTOSTART helper stopped",flush=True)
            return False
        time.sleep(1.5)
    return False

def complete_studio_session(sid,source):
    """Load a real character on a worker; Android can show progress immediately."""
    try:
        if not ensure_studio_ready():
            raise RuntimeError("Native Koikatsu Studio is unavailable")
        response=studio_ws({"type":"add","command":"character",
            "sex":"female","path":str(source)},timeout=90)
        if response.get("type")!="success":
            raise RuntimeError("Native Koikatsu rejected card: "+str(response)[:220])
        with GUARD:
            if sid in SESSIONS:SESSIONS[sid]["ready"]=True
        print("FG_KOIKATSU_IMPORT_READY",sid,flush=True)
    except Exception as error:
        with GUARD:
            if sid in SESSIONS:SESSIONS[sid]["error"]=str(error)[:300]
        print("FG_KOIKATSU_IMPORT_FAILED",str(error)[:200],flush=True)

class Handler(BaseHTTPRequestHandler):
    server_version="FGNative3D/0.1"
    def log_message(self,fmt,*args):
        print(time.strftime("%H:%M:%S"),fmt%args,flush=True)
    def cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","X-FG-Token, Content-Type")
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
    def reply(self,code,payload,mime="application/json"):
        if isinstance(payload,dict):payload=json.dumps(payload).encode("utf-8")
        self.send_response(code);self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(payload)));self.cors()
        self.end_headers();self.wfile.write(payload)
    def do_OPTIONS(self):
        self.send_response(204);self.cors();self.end_headers()
    def authorized(self):
        if not hmac.compare_digest(self.headers.get("X-FG-Token",""),TOKEN):
            self.reply(403,{"error":"Pairing token is missing or incorrect"})
            return False
        return True
    def do_GET(self):
        if not self.authorized():return
        try:self.get_request()
        except Exception as exc:self.reply(503,{"error":str(exc)[:350]})
    def do_POST(self):
        if not self.authorized():return
        try:self.post_request()
        except Exception as exc:self.reply(400,{"error":str(exc)[:350]})
    def post_request(self):
        route=urlparse(self.path).path
        if route!="/api/open":return self.reply(404,{"error":"Unknown endpoint"})
        kind=parse_qs(urlparse(self.path).query).get("kind",[""])[0]
        n=int(self.headers.get("Content-Length","0"))
        if n<0 or n>MAX_SOURCE:return self.reply(413,{"error":"Source exceeds bounded upload limit"})
        if kind not in ("cube","blend","koikatsu"):return self.reply(400,{"error":"Unsupported session"})
        payload=self.rfile.read(n)
        if len(payload)!=n:raise ValueError("Incomplete source upload")
        if kind=="koikatsu" and not is_koikatsu_card(payload):
            return self.reply(415,{"error":"PNG has no authentic Koikatsu character payload"})
        if kind=="blend" and not payload.startswith(b"BLENDER"):
            return self.reply(415,{"error":"Not a Blender .blend source"})
        sid=secrets.token_hex(12)
        source=None
        if kind in ("koikatsu","blend"):
            sub=ROOT/("cards" if kind=="koikatsu" else "blends");sub.mkdir(exist_ok=True)
            digest=hashlib.sha256(payload).hexdigest()
            source=sub/(digest+(".png" if kind=="koikatsu" else ".blend"))
            if not source.exists():source.write_bytes(payload)
        with GUARD:
            SESSIONS[sid]={"kind":kind,"source":str(source or ""),
                "created":time.time(),"ready":kind!="koikatsu","error":None}
        if kind=="koikatsu":
            threading.Thread(target=complete_studio_session,
                args=(sid,source),daemon=True).start()
            return self.reply(202,{"session":sid,"kind":kind,"ready":False})
        return self.reply(200,{"session":sid,"kind":kind,"ready":True})
    def get_request(self):
        parsed=urlparse(self.path);route=parsed.path
        if route=="/api/status":
            q=parse_qs(parsed.query);sid=q.get("session",[""])[0]
            if sid:
                with GUARD:info=SESSIONS.get(sid)
                if not info:return self.reply(404,{"error":"Unknown 3D session"})
                return self.reply(200,{"session":sid,"ready":info.get("ready",False),
                    "error":info.get("error")})
            return self.reply(200,{"online":True,"blender":BLENDER.is_file(),
                "koikatsuStudio":STUDIO.is_file(),"studioConnected":studio_ready(),
                "transport":"usb-local"})
        if route!="/api/frame":return self.reply(404,{"error":"Unknown endpoint"})
        q=parse_qs(parsed.query)
        sid=q.get("session",[""])[0]
        with GUARD:info=SESSIONS.get(sid)
        if not info:return self.reply(404,{"error":"Unknown session"})
        yaw=max(-100,min(100,float(q.get("yaw",["0.4"])[0])))
        pitch=max(-1.3,min(1.3,float(q.get("pitch",["0.2"])[0])))
        distance=max(1.05,min(15,float(q.get("distance",["2.5"])[0])))
        if not all(map(math.isfinite,(yaw,pitch,distance))):
            return self.reply(400,{"error":"Invalid camera values"})
        if info["kind"]=="koikatsu":
            if not info.get("ready"):
                return self.reply(425,{"error":info.get("error") or "Koikatsu character is loading"})
            if not studio_ready():return self.reply(503,{"error":"CharaStudio native plugin disconnected"})
            # Camera controls and screenshot are handled inside Unity, no GLB.
            studio_ws({"type":"camera","command":"setview",
                "pos":[float(math.sin(yaw)*distance),1.25+pitch,float(math.cos(yaw)*distance)],
                "rot":[float(-pitch*45),float(yaw*180/math.pi),0],"fov":35})
            # KKStudioSocket already supports direct native Unity frame capture.
            # The old native-frame.request file had no consumer, so the PC
            # always timed out despite successful character import.
            with RENDER_LOCK:
                response=studio_ws({
                    "type":"screenshot","width":680,"height":800,
                    "transparency":False,"mark":False},timeout=60)
                payload=response.get("data") or {}
                encoded=payload.get("image","")
                if not isinstance(encoded,str) or len(encoded)>24*1024*1024:
                    raise RuntimeError("Studio supplied no valid encoded frame")
                raw=base64.b64decode(encoded,validate=True)
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise RuntimeError("Studio returned an invalid PNG frame")
                if len(raw)<200 or len(raw)>16*1024*1024:
                    raise RuntimeError("Studio frame size out of bounds")
                return self.reply(200,raw,"image/png")
        name=f"{sid}_{yaw:.2f}_{pitch:.2f}_{distance:.2f}.jpg"
        destination=ROOT/"frames"/name
        destination.parent.mkdir(exist_ok=True)
        if not destination.is_file():
            with RENDER_LOCK:
                if not destination.is_file():
                    args=[str(BLENDER),"--background","--factory-startup","--python",str(RENDER),
                          "--",info["kind"],info["source"],str(destination),
                          str(yaw),str(pitch),str(distance)]
                    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
                    out=subprocess.run(args,capture_output=True,text=True,timeout=120,
                        creationflags=flags)
                    if out.returncode or not destination.is_file():
                        raise RuntimeError("Blender render failed: "+(out.stderr or out.stdout)[-500:])
        return self.reply(200,destination.read_bytes(),"image/jpeg")

def main():
    print("File Gestioner bridge listening only on PC loopback. Token file:",KEYFILE,flush=True)
    print("USB transport: adb reverse tcp:39273 tcp:39273",flush=True)
    ThreadingHTTPServer(("127.0.0.1",39273),Handler).serve_forever()

if __name__=="__main__":main()

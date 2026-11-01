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
            # A failed/interrupted upload may leave a zero-byte file with the
            # expected name. Never treat mere existence as cache validity.
            valid=False
            if source.is_file() and source.stat().st_size==len(payload):
                with source.open("rb") as existing:
                    hash_check=hashlib.file_digest(existing,"sha256").hexdigest()
                valid=hash_check==digest
            if not valid:
                temporary=source.with_name(source.name+"."+secrets.token_hex(8)+".part")
                try:
                    with temporary.open("xb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary,source)
                finally:
                    if temporary.exists():temporary.unlink()
                if source.stat().st_size!=len(payload):
                    raise IOError("Stored PC asset does not match uploaded bytes")
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
        distance=max(1.25,min(15,float(q.get("distance",["3.2"])[0])))
        pan_x=max(-4,min(4,float(q.get("panx",["0"])[0])))
        pan_y=max(.25,min(3.5,float(q.get("pany",["1.25"])[0])))
        width=max(240,min(1200,int(q.get("width",["680"])[0])))
        height=max(240,min(1920,int(q.get("height",["800"])[0])))
        if not all(map(math.isfinite,(yaw,pitch,distance,pan_x,pan_y))):
            return self.reply(400,{"error":"Invalid camera values"})
        if info["kind"]=="koikatsu":
            if not info.get("ready"):
                return self.reply(425,{"error":info.get("error") or "Koikatsu character is loading"})
            if not studio_ready():return self.reply(503,{"error":"CharaStudio native plugin disconnected"})
            # Orbit ONLY the PC camera around a stationary character.
            # In Unity, yaw+180 turns the camera back toward the orbit target.
            # The vertical camera position and positive X tilt aim at pan_y.
            horizontal=distance*math.cos(pitch)
            camera_position=[
                pan_x+math.sin(yaw)*horizontal,
                pan_y+distance*math.sin(pitch),
                math.cos(yaw)*horizontal]
            camera_rotation=[math.degrees(pitch),180+math.degrees(yaw),0]
            studio_ws({"type":"camera","command":"setview",
                "pos":camera_position,"rot":camera_rotation,"fov":36})
            # Offscreen capture works without exposing Studio's desktop.
            # A hidden Studio window cannot reliably serve Unity screenshots.
            with RENDER_LOCK:
                output=ROOT/"native-frame.png"
                errors=ROOT/"native-frame.error"
                request=ROOT/"native-frame.request"
                for stale in (output,errors,request):
                    if stale.exists():stale.unlink()
                request.write_text(f"{width},{height}",encoding="ascii")
                deadline=time.monotonic()+35
                while time.monotonic()<deadline:
                    if errors.exists():
                        raise RuntimeError("Native offscreen capture: "+errors.read_text()[:450])
                    if output.exists() and output.stat().st_size>200:
                        raw=output.read_bytes()
                        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                            raise RuntimeError("Offscreen capture was not a PNG")
                        if len(raw)>16*1024*1024:
                            raise RuntimeError("Offscreen capture exceeds 16 MiB")
                        return self.reply(200,raw,"image/png")
                    time.sleep(.1)
                raise RuntimeError("Native Unity offscreen capture timed out")
        name=(f"{sid}_{yaw:.3f}_{pitch:.3f}_{distance:.3f}_"
              f"{pan_x:.2f}_{pan_y:.2f}_{width}x{height}.jpg")
        destination=ROOT/"frames"/name
        destination.parent.mkdir(exist_ok=True)
        if not destination.is_file():
            with RENDER_LOCK:
                if not destination.is_file():
                    args=[str(BLENDER),"--background","--factory-startup","--python",str(RENDER),
                          "--",info["kind"],info["source"],str(destination),
                          str(yaw),str(pitch),str(distance),
                          str(pan_x),str(pan_y),str(width),str(height)]
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

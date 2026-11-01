"""Run native CharaStudio with no foreground focus and a minimized window.
Uses normal Windows desktop so Unity graphics loop may continue.
Never sends input or switches desktops.
"""
import ctypes,ctypes.wintypes as w,pathlib,time
GAME=pathlib.Path(r"D:\Tools\Steam\steamapps\common\Koikatsu Party")
EXE=GAME/"CharaStudio.exe"
kernel=ctypes.WinDLL("kernel32",use_last_error=True)
user=ctypes.WinDLL("user32",use_last_error=True)
class STARTUPINFO(ctypes.Structure):
    _fields_=[("cb",w.DWORD),("lpReserved",w.LPWSTR),("lpDesktop",w.LPWSTR),
              ("lpTitle",w.LPWSTR),("dwX",w.DWORD),("dwY",w.DWORD),
              ("dwXSize",w.DWORD),("dwYSize",w.DWORD),
              ("dwXCountChars",w.DWORD),("dwYCountChars",w.DWORD),
              ("dwFillAttribute",w.DWORD),("dwFlags",w.DWORD),
              ("wShowWindow",w.WORD),("cbReserved2",w.WORD),
              ("lpReserved2",ctypes.c_void_p),("hStdInput",w.HANDLE),
              ("hStdOutput",w.HANDLE),("hStdError",w.HANDLE)]
class PROCESSINFO(ctypes.Structure):
    _fields_=[("hProcess",w.HANDLE),("hThread",w.HANDLE),
              ("dwProcessId",w.DWORD),("dwThreadId",w.DWORD)]
kernel.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,
  w.BOOL,w.DWORD,ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(STARTUPINFO),ctypes.POINTER(PROCESSINFO)]
kernel.CreateProcessW.restype=w.BOOL
si=STARTUPINFO()
si.cb=ctypes.sizeof(si);si.lpDesktop=None;si.dwFlags=1;si.wShowWindow=7
pi=PROCESSINFO()
cmd='"'+str(EXE)+'" -screen-width 854 -screen-height 480 -window-mode windowed'
if not kernel.CreateProcessW(str(EXE),ctypes.create_unicode_buffer(cmd),
    None,None,False,0x00000010,None,str(GAME),ctypes.byref(si),ctypes.byref(pi)):
    raise OSError(ctypes.get_last_error(),"Could not start native background CharaStudio")
pid=pi.dwProcessId
kernel.CloseHandle(pi.hThread);kernel.CloseHandle(pi.hProcess)
print("FG_STUDIO_BACKGROUND_PID",pid,flush=True)
callbackType=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
user.IsWindowVisible.argtypes=[w.HWND]
user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,
                            ctypes.c_int,ctypes.c_int,w.UINT]
while True:
    @callbackType
    def check(hwnd,lparam):
        owner=w.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid and user.IsWindowVisible(hwnd):
            # Keep GPU renderable window mapped on the normal desktop, but
            # place it far outside visible monitors without ever activating it.
            user.ShowWindow(hwnd,8) # SW_SHOWNA
            user.SetWindowPos(hwnd,1,-16000,-16000,854,480,0x0010|0x0040)
        return True
    user.EnumWindows(check,0)
    time.sleep(1)

"""Start native Koikatsu CharaStudio on an independent Windows desktop.
This does not switch the user's active desktop or control mouse/keyboard.
"""
import ctypes,ctypes.wintypes as w, pathlib,subprocess,sys,time
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
user.CreateDesktopW.restype=w.HANDLE
user.CreateDesktopW.argtypes=[w.LPCWSTR,w.LPCWSTR,ctypes.c_void_p,w.DWORD,w.DWORD,ctypes.c_void_p]
desktop=user.CreateDesktopW("FileGestionerNativeStudio",None,None,0,0x10000000,None)
if not desktop:raise OSError(ctypes.get_last_error(),"CreateDesktopW failed")
si=STARTUPINFO();si.cb=ctypes.sizeof(si)
si.lpDesktop="WinSta0\\FileGestionerNativeStudio"
si.dwFlags=1;si.wShowWindow=7
pi=PROCESSINFO()
cmd='"'+str(EXE)+'" -screen-width 854 -screen-height 480 -window-mode windowed'
kernel.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,
    w.BOOL,w.DWORD,ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(STARTUPINFO),ctypes.POINTER(PROCESSINFO)]
kernel.CreateProcessW.restype=w.BOOL
ok=kernel.CreateProcessW(str(EXE),ctypes.create_unicode_buffer(cmd),None,None,False,
    0x00000010,None,str(GAME),ctypes.byref(si),ctypes.byref(pi))
if not ok:raise OSError(ctypes.get_last_error(),"CreateProcessW failed")
pid=pi.dwProcessId
kernel.CloseHandle(pi.hThread);kernel.CloseHandle(pi.hProcess)
print("FG_HIDDEN_STUDIO_STARTED",pid,flush=True)
# Hold desktop handle open while Unity game uses it. Never SwitchDesktop.
while True:time.sleep(10)

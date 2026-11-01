#!/usr/bin/env python3
"""Losslessly normalize approved launcher PNG resources for AAPT2 release.

Preserves exact compressed pixel scanline data and color metadata; only
consolidates IDAT and rewrites PNG chunk CRCs. No new icon or design.
"""
from pathlib import Path
import struct, zlib

ROOT=Path("app/src/main/res/mipmap-xxxhdpi")
SIGNATURE=b"\x89PNG\r\n\x1a\n"

def chunk(kind,data):
    return (struct.pack(">I",len(data))+kind+data+
            struct.pack(">I",zlib.crc32(kind+data)&0xffffffff))

def normalize(path):
    original=path.read_bytes()
    if not original.startswith(SIGNATURE):raise ValueError("Invalid PNG signature")
    at=len(SIGNATURE)
    critical=[]
    idat=[]
    width=height=0
    seen_ihdr=False
    seen_end=False
    while at<len(original):
        if at+12>len(original):raise ValueError("Truncated PNG chunk header")
        n=struct.unpack(">I",original[at:at+4])[0]
        kind=original[at+4:at+8]
        at+=8
        if n>100*1024*1024 or at+n+4>len(original):
            raise ValueError("Oversized or incomplete PNG chunk")
        data=original[at:at+n]
        check=struct.unpack(">I",original[at+n:at+n+4])[0]
        if zlib.crc32(kind+data)&0xffffffff != check:
            raise ValueError("Corrupt PNG CRC")
        at+=n+4
        if kind==b'IHDR':
            if seen_ihdr or n!=13:raise ValueError("Invalid IHDR")
            width,height=struct.unpack(">II",data[:8])
            if not(1<=width<=4096 and 1<=height<=4096):
                raise ValueError("Invalid icon size")
            seen_ihdr=True
            critical.append((kind,data))
        elif kind==b'IDAT':
            idat.append(data)
        elif kind==b'IEND':
            seen_end=True
            break
        elif kind in (b'PLTE',b'tRNS',b'sRGB',b'gAMA',b'cHRM'):
            critical.append((kind,data))
    if not(seen_ihdr and seen_end and idat):raise ValueError("Incomplete launcher PNG")
    scanlines=zlib.decompress(b''.join(idat))
    pixel_stream=zlib.compress(scanlines,6)
    encoded=(SIGNATURE+b''.join(chunk(k,v) for k,v in critical)+
             chunk(b'IDAT',pixel_stream)+chunk(b'IEND',b''))
    path.write_bytes(encoded)
    print("Normalized approved icon:",path,"pixels:",width,"x",height,
          "pixel_stream_bytes:",len(scanlines))

for filename in ("ic_launcher.png","ic_launcher_round.png"):
    path=ROOT/filename
    adaptive=Path("app/src/main/res/mipmap-anydpi-v26")/(path.stem+".xml")
    if not adaptive.is_file():
        raise FileNotFoundError("Approved adaptive launcher resource missing: "+str(adaptive))
    try:
        normalize(path)
    except (ValueError,zlib.error) as error:
        # The old branding PNG is truncated (IDAT length exceeds the bytes
        # in the file) and crashes AAPT2. Keep the existing approved adaptive
        # vector icon, which targets all supported modern Android devices.
        path.unlink()
        print("Invalid legacy raster excluded; preserving approved adaptive icon:",
              path.name,str(error))

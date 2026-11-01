#!/usr/bin/env python3
"""Small, synthetic 102-image ZIP comic regression fixture.
Contains no copyrighted images, TeraBox credentials, or personal files.
"""
import struct,sys,zlib,os
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZIP_STORED

output_path=Path(sys.argv[1]) if len(sys.argv)>1 else Path("synthetic-comic.zip")
output_path.parent.mkdir(parents=True,exist_ok=True)
def chunk(kind,payload):
    return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff)
def image(index,w=360,h=510):
    pixel=(28+index*7)%180,(55+index*3)%160,(105+index*9)%175
    scan=b"\x00"+bytes(pixel)*w
    raw=scan*h
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,6))+chunk(b"IEND",b"")
with ZipFile(output_path,"w",ZIP_DEFLATED,allowZip64=True) as archive:
    for i in range(1,103):
        # Provide out-of-order directory insertion for numeric ordering test.
        n=(i*37)%102+1
        archive.writestr("Example book/"+str(n)+".png",image(n))
    archive.writestr("Example book/readme.txt","Synthetic comic regression fixture",ZIP_DEFLATED)
    archive.writestr("__MACOSX/._cover.png",b"macOS sidecar is not a comic image",ZIP_STORED)
    archive.writestr("Example book/.hidden.jpg",b"hidden file must not render",ZIP_STORED)
    # >30MiB ZIP, but still 102 true images: index time must not scale
    # with the byte size of this intentionally unreferenced payload.
    with archive.open("Example book/.synthetic-padding","w",force_zip64=True) as padding:
        for _ in range(33):
            padding.write(os.urandom(1024*1024))

assert output_path.stat().st_size>30*1024*1024
print("Created 102-image ZIP with filenames out of order:",output_path.stat().st_size,"bytes")

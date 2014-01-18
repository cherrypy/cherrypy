import struct
import time

from cherrypy.lib.compat import BytesIO


def compress(body, compress_level):
    """Compress 'body' at the given compress_level."""
    import zlib

    # See http://www.gzip.org/zlib/rfc-gzip.html
    yield b'\x1f\x8b'       # ID1 and ID2: gzip marker
    yield b'\x08'           # CM: compression method
    yield b'\x00'           # FLG: none set
    # MTIME: 4 bytes
    yield struct.pack("<L", int(time.time()) & int('FFFFFFFF', 16))
    yield b'\x02'           # XFL: max compression, slowest algo
    yield b'\xff'           # OS: unknown

    crc = zlib.crc32(b"")
    size = 0
    zobj = zlib.compressobj(compress_level,
                            zlib.DEFLATED, -zlib.MAX_WBITS,
                            zlib.DEF_MEM_LEVEL, 0)
    for line in body:
        size += len(line)
        crc = zlib.crc32(line, crc)
        yield zobj.compress(line)
    yield zobj.flush()

    # CRC32: 4 bytes
    yield struct.pack("<L", crc & int('FFFFFFFF', 16))
    # ISIZE: 4 bytes
    yield struct.pack("<L", size & int('FFFFFFFF', 16))


def decompress(body):
    import gzip

    zbuf = BytesIO()
    zbuf.write(body)
    zbuf.seek(0)
    zfile = gzip.GzipFile(mode='rb', fileobj=zbuf)
    data = zfile.read()
    zfile.close()
    return data

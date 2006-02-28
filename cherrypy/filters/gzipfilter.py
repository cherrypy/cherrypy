import struct
import time
import zlib

import cherrypy
from basefilter import BaseFilter

class GzipFilter(BaseFilter):
    """Filter that gzips the response."""
    
    def before_finalize(self):
        if not cherrypy.config.get('gzip_filter.on', False):
            return
        
        response = cherrypy.response
        if not response.body:
            # Response body is empty (might be a 304 for instance)
            return
        
        def zipit():
            # Return a generator that compresses the page
            varies = response.headers.get("Vary", "")
            varies = [x.strip() for x in varies.split(",") if x.strip()]
            if "Accept-Encoding" not in varies:
                varies.append("Accept-Encoding")
            response.headers['Vary'] = ", ".join(varies)
            
            response.headers['Content-Encoding'] = 'gzip'
            level = cherrypy.config.get('gzip_filter.compresslevel', 9)
            response.body = self.zip_body(response.body, level)
        
        from cherrypy.lib import httptools
        acceptable = cherrypy.request.headers.elements('Accept-Encoding')
        if not acceptable:
            # If no Accept-Encoding field is present in a request,
            # the server MAY assume that the client will accept any
            # content coding. In this case, if "identity" is one of
            # the available content-codings, then the server SHOULD use
            # the "identity" content-coding, unless it has additional
            # information that a different content-coding is meaningful
            # to the client.
            return
        
        ct = response.headers.get('Content-Type').split(';')[0]
        ct = ct in cherrypy.config.get('gzip_filter.mime_types', ['text/html', 'text/plain'])
        for coding in acceptable:
            if coding.value == 'identity' and coding.qvalue != 0:
                return
            if coding.value in ('gzip', 'x-gzip'):
                if coding.qvalue == 0:
                    return
                if ct:
                    zipit()
                return
        cherrypy.HTTPError(406, "identity, gzip").set_response()
    
    def write_gzip_header(self):
        """Adapted from the gzip.py standard module code"""
        
        header = '\037\213'      # magic header
        header += '\010'         # compression method
        header += '\0'
        header += struct.pack("<L", long(time.time()))
        header += '\002'
        header += '\377'
        return header
    
    def write_gzip_trailer(self, crc, size):
        footer = struct.pack("<l", crc)
        footer += struct.pack("<L", size & 0xFFFFFFFFL)
        return footer
    
    def zip_body(self, body, compress_level):
        # Compress page
        yield self.write_gzip_header()
        crc = zlib.crc32("")
        size = 0
        zobj = zlib.compressobj(compress_level,
                                zlib.DEFLATED, -zlib.MAX_WBITS,
                                zlib.DEF_MEM_LEVEL, 0)
        for line in body:
            size += len(line)
            crc = zlib.crc32(line, crc)
            yield zobj.compress(line)
        yield zobj.flush()
        yield self.write_gzip_trailer(crc, size)

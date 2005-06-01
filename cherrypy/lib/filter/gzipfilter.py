"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import zlib
import struct
import time
from basefilter import BaseFilter

class GzipFilter(BaseFilter):
    """Filter that gzips the response."""
    
    def onStartResource(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg
        from cherrypy import cpg
        cpg.threadData.gzipFilterOn = cpg.config.get('gzipFilter.on', False)
        cpg.threadData.gzipFilterMimeTypeList = cpg.config.get('gzipFilter.mimeTypeList', ['text/html'])
        cpg.threadData.gzipFilterCompressLevel = cpg.config.get('gzipFilter.compresslevel', 9)
    
    def beforeFinalize(self):
        if not cpg.threadData.gzipFilterOn:
            return
        
        if not cpg.response.body:
            # Response body is empty (might be a 304 for instance)
            return
        
        ct = cpg.response.headerMap.get('Content-Type').split(';')[0]
        ae = cpg.request.headerMap.get('Accept-Encoding', '')
        if (ct in cpg.threadData.gzipFilterMimeTypeList) and ('gzip' in ae):
            cpg.response.headerMap['Content-Encoding'] = 'gzip'
            # Return a generator that compresses the page
            cpg.response.body = self.zip_body(cpg.response.body)

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

    def zip_body(self, body):
        # Compress page
        yield self.write_gzip_header()
        crc = zlib.crc32("")
        size = 0
        zobj = zlib.compressobj(cpg.threadData.gzipFilterCompressLevel,
                                zlib.DEFLATED, -zlib.MAX_WBITS,
                                zlib.DEF_MEM_LEVEL, 0)
        for line in body:
            size += len(line)
            crc = zlib.crc32(line, crc)
            yield zobj.compress(line)
        yield zobj.flush()
        yield self.write_gzip_trailer(crc, size)

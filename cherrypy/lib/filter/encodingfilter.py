"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from basefilter import BaseOutputFilter
from cherrypy import cpg
import types

class EncodingFilter(BaseOutputFilter):
    """
    Filter that automatically encodes the response.
    """

    def __init__(self, encoding = 'utf-8', mimeTypeList = ['text/html']):
        self.encoding = encoding
        self.mimeTypeList = mimeTypeList

    def beforeResponse(self):
        ct = cpg.response.headerMap.get('Content-Type').split(';')[0]
        if (ct in self.mimeTypeList):
            # Add "charset=..." to response Content-Type header
            contentType = cpg.response.headerMap.get("Content-Type")
            if contentType and 'charset' not in contentType:
                cpg.response.headerMap["Content-Type"] += ";charset=%s" % self.encoding
            # Return a generator that encodes the sequence
            cpg.response.body = self.encode_body(cpg.response.body)

    def encode_body(self, body):
        for line in body:
            yield line.encode(self.encoding)

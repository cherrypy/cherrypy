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
import helper, gzip, StringIO

code = r"""
from cherrypy import cpg
europoundUnicode = u'\x80\xa3'
class Root:
    def index(self):
        yield u"Hello,"
        yield u"world"
        yield europoundUnicode
    index.exposed = True
cpg.root = Root()
cpg.config.update({
    '/': {
        'server.socketPort': 8000,
        'server.environment': 'production',
        'gzipFilter.on': True,
        'encodingFilter.on': True,
    }
})
cpg.server.start()
"""
config = ""
europoundUnicode = u'\x80\xa3'
expectedResult = (u"Hello," + u"world" + europoundUnicode).encode('utf-8')
zbuf = StringIO.StringIO()
zfile = gzip.GzipFile(mode='wb', fileobj = zbuf, compresslevel = 9)
zfile.write(expectedResult)
zfile.close()

testList = [
    ('/', '%s in cpg.response.body' % repr(zbuf.getvalue()[:3])),
]

def test(infoMap, failedList, skippedList):
    print "    Testing combined filters ...",
    # Gzip compression doesn't always return the same exact result !
    # So we just check that the first few bytes are the same
    helper.checkPageResult('combined filters', infoMap, code, testList, failedList, extraRequestHeader = [("Accept-Encoding", "gzip")])

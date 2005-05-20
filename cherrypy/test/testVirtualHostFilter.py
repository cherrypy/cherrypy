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
from cherrypy.lib.filter import basefilter, virtualhostfilter

siteMap = {
    'site1': '/site1',
    'site2': '/site2'
}

class Site1Filter(basefilter.BaseOutputFilter):
    def beforeResponse(self):
        cpg.response.body += 'Site1Filter'
class Site2Filter(basefilter.BaseOutputFilter):
    def beforeResponse(self):
        cpg.response.body += 'Site2Filter'

class Root:
    _cpFilterList = [virtualhostfilter.VirtualHostFilter(siteMap)]

class Site1:
    _cpFilterList = [Site1Filter()]
    def index(self):
        return "SITE1"
    index.exposed = True
class Site2:
    _cpFilterList = [Site2Filter()]
    def index(self):
        return "SITE2"
    index.exposed = True

cpg.root = Root()
cpg.root.site1 = Site1()
cpg.root.site2 = Site2()
cpg.config.update(file = 'testsite.cfg')
cpg.server.start()
"""

test1List = [
    ('/', "cpg.response.body == 'SITE1Site1Filter'"),
]
test2List = [
    ('/', "cpg.response.body == 'SITE2Site2Filter'"),
]

def test(infoMap, failedList, skippedList):
    print "    Testing VirtualHostFilter (1) ...",
    helper.checkPageResult('VirtualHostFilter', infoMap, code, test1List,
        failedList, extraRequestHeader = [("X-Forwarded-Host", "site1")])
    print "    Testing VirtualHostFilter (2) ...",
    helper.checkPageResult('VirtualHostFilter', infoMap, code, test2List,
        failedList, extraRequestHeader = [("X-Forwarded-Host", "site2")])

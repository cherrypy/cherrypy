"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Regression test suite for CherryPy

import sys,os,os.path
sys.path.insert(0,os.path.normpath(os.path.join(os.getcwd(),'../../')))
if not os.path.exists(os.path.join(os.curdir,'buildInfoMap.py')):
    print "Run the test form the test directory (cherrypy/test)from the cherrypy you wish to test."
    print "In no python executables are found, change this file (test.py) near line 31"
    sys.exit(1)
if len(sys.argv) == 2 and sys.argv[1] in ('-h', '--help'):
    print "Usage: unittest.py [testName+]"
    print "Run from the test directory from within cherrypy"
    sys.exit(0)

python2={}
python2[3]={}    # Infos about python-2.3
python2[4]={}    # Infos about python-2.4

# Edit these lines to match your setup
if sys.platform=="win32":
    python2[3]['path']="c:\\python23\\python.exe"
    python2[4]['path']="c:\\python24\\python.exe"
else:
    python2[3]['path']="python2.3"
    python2[4]['path']="python2.4"

print "Checking that port 8000 is free...",
try:
    import socket
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 8000))
    s.close()
    print "\n### Error: port 8000 is busy. This port must be free to run this test script"
    sys.exit(-1)
except socket.error:
    print "OK"

print

print "Examining your system..."
print
print "Python version used to run this test script:", sys.version.split()[0]
print
import buildInfoMap
python2 = buildInfoMap.buildInfoMap(python2)

print
print "Checking CherryPy version..."
import os
try:
    import cherrypy
except ImportError:
    print "Error: couln't find CherryPy !"
    os._exit(-1)

print "    Found version " + cherrypy.__version__
print

print "Testing CherryPy..."
failedList=[]
skippedList=[]

tutorialTestList = [
    ('01', [('/', "cpg.response.body == 'Hello world!'")]),
    ('02', [('/showMessage', "cpg.response.body == 'Hello world!'")]),
    ('03', [('/greetUser?name=Bob',
            '''cpg.response.body == "Hey Bob, what's up?"''')]),
    ('04', [('/links/extra/', r"""cpg.response.body == '\n            <p>Here are some extra useful links:</p>\n\n            <ul>\n                <li><a href="http://del.icio.us">del.icio.us</a></li>\n                <li><a href="http://www.mornography.de">Hendrik\'s weblog</a></li>\n            </ul>\n\n            <p>[<a href="../">Return to links page</a>]</p>\n        '""")]),
    ('05', [('/another/', r"""cpg.response.body == '\n            <html>\n            <head>\n                <title>Another Page</title>\n            <head>\n            <body>\n            <h2>Another Page</h2>\n        \n            <p>\n            And this is the amazing second page!\n            </p>\n        \n            </body>\n            </html>\n        '""")]),
    ('06', [('/', r"""cpg.response.body == '\n            <html>\n            <head>\n                <title>Tutorial 6 -- Aspect Powered!</title>\n            <head>\n            <body>\n            <h2>Tutorial 6 -- Aspect Powered!</h2>\n        \n            <p>\n            Isn\'t this exciting? There\'s\n            <a href="./another/">another page</a>, too!\n            </p>\n        \n            </body>\n            </html>\n        '""")]),
    ('07', [('/hendrik', r"""cpg.response.body == 'Hendrik Mans, CherryPy co-developer & crazy German (<a href="./">back</a>)'""")]),
    ('08', [('/', r'''cpg.response.body == "\n            During your current session, you've viewed this\n            page 1 times! Your life is a patio of fun!\n        "'''), ('/', r'''cpg.response.body == "\n            During your current session, you've viewed this\n            page 2 times! Your life is a patio of fun!\n        "''')]), 
    ('09', [('/', r"""cpg.response.body == '<html><body><h2>Generators rule!</h2><h3>List of users:</h3>Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/></body></html>'""")]),
]

testList = [
    'testObjectMapping',
    'testFilter1',
    'testVirtualHostFilter',
]

if len(sys.argv) > 1:
    # Some specific tests were specified on the command line
    # Limit the tests to these ones
    newTutorialTestList = []
    newTestList = []
    for number, myTestList in tutorialTestList:
        if "tutorial%s" % number in sys.argv[1:]:
            newTutorialTestList.append((number, myTestList))
    for t in testList:
        if t in sys.argv[1:]:
            newTestList.append(t)
    tutorialTestList = newTutorialTestList
    testList = newTestList

import helper

for version, infoMap in python2.items():
    print
    print "Running tests for python %s..."%infoMap['exactVersionShort']

    # Run tests based on tutorials
    for number, myTestList in tutorialTestList:
        code = open('../tutorial/tutorial%s.py' % number, 'r').read()
        code = code.replace('tutorial.conf', 'testsite.cfg')
        print "    Testing tutorial %s..." % number,
        #if ((version == 1 and number in ('06', '09')) or
        #        (version == 2 and number in ('09'))):
        #    print "skipped"
        #    skippedList.append("Tutorial %s for python2.%s" % (number, version))
        #    continue
           
        helper.checkPageResult('Tutorial %s' % number, infoMap, code, myTestList, failedList)

    # Running actual unittests
    for test in testList:
        exec("import "+test)
        eval(test+".test(infoMap, failedList, skippedList)")

print
print
print "#####################################"
print "#####################################"
print "###          TEST RESULT          ###"
print "#####################################"
print "#####################################"
if skippedList:
    print
    print "*** THE FOLLOWING TESTS WERE SKIPPED:"
    for skipped in skippedList: print skipped

    print "**** THE ABOVE TESTS WERE SKIPPED"
    print

if failedList:
    print
    print "*** THE FOLLOWING TESTS FAILED:"
    for failed in failedList: print failed

    print "**** THE ABOVE TESTS FAILED"
    print
    print "**** Some errors occured: please add a ticket in our Trac system (http://trac.cherrypy.org/cgi-bin/trac.cgi/newticket) with the output of this test script"

else:
    print
    print "**** NO TEST FAILED: EVERYTHING LOOKS OK ****"

############"
# Ideas for future tests:
#    - test if tabs and whitespaces are handled correctly in source file (option -W)
#    - test if absolute pathnames work fine on windows
#    - test sessions
#    - test threading server
#    - test forking server
#    - test process pooling server
#    - test SSL
#    - test compilator errors
#    - test abstract classes
#    - test hidden classes
#    ...

raw_input('hit enter')

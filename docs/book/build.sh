#!/bin/bash
#
# build.sh
#
# Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of CherryPy Team nor the names of its contributors 
#       may be used to endorse or promote products derived from this software 
#       without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# Thanks to Antonio Cavedoni (aka verbosus) 
# for this building script
# 
# Version 0.2 : Got rid of the docbook directories, made them tarballs.
#               Added untarDocbook() function
# Version 0.1 : First release 
#

DOCBOOK_BASE_PATH=../../tools/docbook/
DOCBOOK_DTD_DIRECTORY=docbook4.5
DOCBOOK_XSL_DIRECTORY=docbook-xsl-1.68.1

untarDocbook() {
    current=`pwd`
    cd $DOCBOOK_BASE_PATH
    if [ ! -d $DOCBOOK_DTD_DIRECTORY ]
	then
	tar zxf docbook-4.5b1.tgz
    fi
    
    if [ ! -d $DOCBOOK_XSL_DIRECTORY ]
	then
	tar zxf docbook-xsl-1.68.1.tar.gz
    fi
    cd "$current"
}

#
# Let's build the doc in one big file
#
rm -rf ./html
mkdir html
mkdir html/css
cp css/*.css html/css/
untarDocbook
xsltproc \
    --timing \
    --xinclude \
    --output html/index.html \
    xsl/html.xsl \
    $DOCBOOK_BASE_PATH$DOCBOOK_XSL_DIRECTORY/html/docbook.xsl \
    xml/cherrypy.xml 
 
#
# Let's chunk the doc in different files
#
rm -rf ./chunk
mkdir chunk
mkdir chunk/css
cp css/*.css chunk/css/
untarDocbook
xsltproc \
    --timing \
    --xinclude \
    --output chunk/index.html \
    xsl/chunked.xsl \
    $DOCBOOK_BASE_PATH$DOCBOOK_XSL_DIRECTORY/html/chunk.xsl \
    xml/cherrypy.xml 

exit

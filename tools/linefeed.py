#! /usr/bin/env python
"Replace CRLF with LF cherrypy files.  Print names of changed files."

import sys, os
import glob, os.path
import re

def main():
    scriptdir = os.path.split(sys.argv[0])[0]
    basepath = os.path.split(scriptdir)[0]
    filelist = []
    for directory in ['/tools','/cherrypy','/cherrypy/lib/filter','/',
                      '/cherrypy/filters','/cherrypy/lib','/cherrypy/test',
                      '/cherrypy/tutorial']:
        filelist.extend(glob.glob(basepath+directory+'/*.py'))
        filelist.extend(glob.glob(basepath+directory+'/*.conf'))
        filelist.extend(glob.glob(basepath+directory+'/*.txt'))
    for filename in filelist:
        if os.path.isdir(filename):
            print filename, "Directory!"
            continue
        data = open(filename, "rb").read()
        if '\0' in data:
            print filename, "Binary!"
            continue
        if os.path.splitext(filename)[1].lower() == '.txt':
            newdata = data.replace('\n','\r\n')
        else:
            newdata = data.replace('\r\n','\n')
        if newdata != data:
            print filename
            f = open(filename, "wb")
            f.write(newdata)
            f.close()

if __name__ == '__main__':
    main()

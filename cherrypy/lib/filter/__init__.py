import warnings
warnings.warn("cherrypy.lib.filter has been superseded by cherrypy.filters and will be removed in CP 2.3")

from cherrypy.filters import *

import sys
builtin_filters = ("basefilter", "baseurlfilter", "cachefilter",
                   "decodingfilter", "encodingfilter", "gzipfilter",
                   "logdebuginfofilter", "nsgmlsfilter",
                   "responseheadersfilter", "sessionauthenticatefilter",
                   "sessionfilter", "staticfilter", "tidyfilter",
                   "virtualhostfilter", "xmlrpcfilter")
for name in builtin_filters:
    newlocation = "cherrypy.filters." + name
    m = __import__(newlocation, globals(), locals(), [''])
    sys.modules["cherrypy.lib.filter." + name] = m
    globals()[name] = m

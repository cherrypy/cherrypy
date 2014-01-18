import datetime

import cherrypy
from cherrypy.lib import httputil


def expires(secs=0, force=False, debug=False):
    """Tool for influencing cache mechanisms using the 'Expires' header.

    secs
        Must be either an int or a datetime.timedelta, and indicates the
        number of seconds between response.time and when the response should
        expire. The 'Expires' header will be set to response.time + secs.
        If secs is zero, the 'Expires' header is set one year in the past, and
        the following "cache prevention" headers are also set:

            * Pragma: no-cache
            * Cache-Control': no-cache, must-revalidate

    force
        If False, the following headers are checked:

            * Etag
            * Last-Modified
            * Age
            * Expires

        If any are already present, none of the above response headers are set.

    """

    response = cherrypy.serving.response
    headers = response.headers

    cacheable = False
    if not force:
        # some header names that indicate that the response can be cached
        for indicator in ('Etag', 'Last-Modified', 'Age', 'Expires'):
            if indicator in headers:
                cacheable = True
                break

    if not cacheable and not force:
        if debug:
            cherrypy.log('request is not cacheable', 'TOOLS.EXPIRES')
    else:
        if debug:
            cherrypy.log('request is cacheable', 'TOOLS.EXPIRES')
        if isinstance(secs, datetime.timedelta):
            secs = (86400 * secs.days) + secs.seconds

        if secs == 0:
            if force or ("Pragma" not in headers):
                headers["Pragma"] = "no-cache"
            if cherrypy.serving.request.protocol >= (1, 1):
                if force or "Cache-Control" not in headers:
                    headers["Cache-Control"] = "no-cache, must-revalidate"
            # Set an explicit Expires date in the past.
            expiry = httputil.HTTPDate(1169942400.0)
        else:
            expiry = httputil.HTTPDate(response.time + secs)
        if force or "Expires" not in headers:
            headers["Expires"] = expiry

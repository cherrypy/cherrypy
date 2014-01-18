import cherrypy


def proxy(base=None, local='X-Forwarded-Host', remote='X-Forwarded-For',
          scheme='X-Forwarded-Proto', debug=False):
    """Change the base URL (scheme://host[:port][/path]).

    For running a CP server behind Apache, lighttpd, or other HTTP server.

    For Apache and lighttpd, you should leave the 'local' argument at the
    default value of 'X-Forwarded-Host'. For Squid, you probably want to set
    tools.proxy.local = 'Origin'.

    If you want the new request.base to include path info (not just the host),
    you must explicitly set base to the full base path, and ALSO set 'local'
    to '', so that the X-Forwarded-Host request header (which never includes
    path info) does not override it. Regardless, the value for 'base' MUST
    NOT end in a slash.

    cherrypy.request.remote.ip (the IP address of the client) will be
    rewritten if the header specified by the 'remote' arg is valid.
    By default, 'remote' is set to 'X-Forwarded-For'. If you do not
    want to rewrite remote.ip, set the 'remote' arg to an empty string.
    """

    request = cherrypy.serving.request

    if scheme:
        s = request.headers.get(scheme, None)
        if debug:
            cherrypy.log('Testing scheme %r:%r' % (scheme, s), 'TOOLS.PROXY')
        if s == 'on' and 'ssl' in scheme.lower():
            # This handles e.g. webfaction's 'X-Forwarded-Ssl: on' header
            scheme = 'https'
        else:
            # This is for lighttpd/pound/Mongrel's 'X-Forwarded-Proto: https'
            scheme = s
    if not scheme:
        scheme = request.base[:request.base.find("://")]

    if local:
        lbase = request.headers.get(local, None)
        if debug:
            cherrypy.log('Testing local %r:%r' % (local, lbase), 'TOOLS.PROXY')
        if lbase is not None:
            base = lbase.split(',')[0]
    if not base:
        port = request.local.port
        if port == 80:
            base = '127.0.0.1'
        else:
            base = '127.0.0.1:%s' % port

    if base.find("://") == -1:
        # add http:// or https:// if needed
        base = scheme + "://" + base

    request.base = base

    if remote:
        xff = request.headers.get(remote)
        if debug:
            cherrypy.log('Testing remote %r:%r' % (remote, xff), 'TOOLS.PROXY')
        if xff:
            if remote == 'X-Forwarded-For':
                # See
                # http://bob.ippoli.to/archives/2005/09/23/apache-x-forwarded-for-caveat/
                xff = xff.split(',')[-1].strip()
            request.remote.ip = xff

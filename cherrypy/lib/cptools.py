"""Functions for builtin CherryPy tools."""

import cherrypy
import http as _http


#                     Conditional HTTP request support                     #

def validate_etags(autotags=False):
    """Validate the current ETag against If-Match, If-None-Match headers."""
    # Guard against being run twice.
    if hasattr(cherrypy.response, "ETag"):
        return
    
    etag = cherrypy.response.headers.get('ETag')
    
    if (not etag) and autotags:
        import md5
        etag = '"%s"' % md5.new(cherrypy.response.collapse_body()).hexdigest()
        cherrypy.response.headers['ETag'] = etag
    
    if etag:
        cherrypy.response.ETag = etag
        
        status, reason, msg = _http.validStatus(cherrypy.response.status)
        
        conditions = cherrypy.request.headers.elements('If-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions and not (conditions == ["*"] or etag in conditions):
            if (status >= 200 and status < 299) or status == 412:
                raise cherrypy.HTTPError(412)
        
        conditions = cherrypy.request.headers.elements('If-None-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions == ["*"] or etag in conditions:
            if (status >= 200 and status < 299) or status == 304:
                if cherrypy.request.method in ("GET", "HEAD"):
                    raise cherrypy.HTTPRedirect([], 304)
                else:
                    raise cherrypy.HTTPError(412)

def validate_since():
    """Validate the current Last-Modified against If-Modified-Since headers."""
    lastmod = cherrypy.response.headers.get('Last-Modified')
    if lastmod:
        status, reason, msg = _http.validStatus(cherrypy.response.status)
        
        since = cherrypy.request.headers.get('If-Unmodified-Since')
        if since and since != lastmod:
            if (status >= 200 and status < 299) or status == 412:
                raise cherrypy.HTTPError(412)
        
        since = cherrypy.request.headers.get('If-Modified-Since')
        if since and since == lastmod:
            if (status >= 200 and status < 299) or status == 304:
                if cherrypy.request.method in ("GET", "HEAD"):
                    raise cherrypy.HTTPRedirect([], 304)
                else:
                    raise cherrypy.HTTPError(412)


#                                Tool code                                #

def proxy(base=None, local='X-Forwarded-Host', remote='X-Forwarded-For'):
    """Change the base URL (scheme://host[:port]).
    
    Useful when running a CP server behind Apache.
    """
    
    request = cherrypy.request
    
    if base is None:
        port = str(cherrypy.config.get('server.socket_port', '80'))
        if port == "80":
            base = 'http://localhost'
        else:
            base = 'http://localhost:%s' % port
    
    if local:
        base = request.headers.get(local, base)
    
    if base.find("://") == -1:
        # add http:// or https:// if needed
        base = request.base[:request.base.find("://") + 3] + base
    
    request.base = base
    
    if remote:
        xff = request.headers.get(remote)
        if xff:
            if remote == 'X-Forwarded-For':
                # See http://bob.pythonmac.org/archives/2005/09/23/apache-x-forwarded-for-caveat/
                xff = xff.split(',')[-1].strip()
            request.remote_host = xff


def response_headers(headers=None, force=True):
    """Set headers on the response."""
    for name, value in (headers or []):
        if force or (name not in cherrypy.response.headers):
            cherrypy.response.headers[name] = value


_login_screen = """<html><body>
Message: %(error_msg)s
<form method="post" action="do_login">
    Login: <input type="text" name="login" value="%(login)s" size="10" /><br />
    Password: <input type="password" name="password" size="10" /><br />
    <input type="hidden" name="from_page" value="%(from_page)s" /><br />
    <input type="submit" />
</form>
</body></html>"""

def session_auth(check_login_and_password=None, not_logged_in=None,
                 load_user_by_username=None, session_key='username',
                 on_login=None, on_logout=None, login_screen=None):
    """Assert that the user is logged in."""
    
    if login_screen is None:
        login_screen = _login_screen
    
    request = cherrypy.request
    tdata = cherrypy.thread_data
    sess = getattr(cherrypy, "session", None)
    if sess is None:
        # Shouldn't this raise an error (if the sessions tool isn't enabled)?
        return False
    
    request.user = None
    tdata.user = None
    
##    conf = cherrypy.config.get
##    if conf('tools.staticfile.on', False) or conf('tools.staticdir.on', False):
##        return
    if request.path.endswith('login_screen'):
        return False
    elif request.path.endswith('do_logout'):
        login = sess.get(session_key)
        sess[session_key] = None
        request.user = None
        tdata.user = None
        if login and on_logout:
            on_logout(login)
        from_page = request.params.get('from_page', '..')
        raise cherrypy.HTTPRedirect(from_page)
    elif request.path.endswith('do_login'):
        from_page = request.params.get('from_page', '..')
        login = request.params['login']
        password = request.params['password']
        error_msg = check_login_and_password(login, password)
        if error_msg:
            kw = {"from_page": from_page,
                  "login": login, "error_msg": error_msg}
            cherrypy.response.body = login_screen % kw
            return True
        
        sess[session_key] = login
        if on_login:
            on_login(login)
        raise cherrypy.HTTPRedirect(from_page or "/")
    
    # Check if user is logged in
    temp_user = None
    if (not sess.get(session_key)) and not_logged_in:
        # Call not_logged_in so that applications where anonymous user
        #   is OK can handle it
        temp_user = not_logged_in()
    if (not sess.get(session_key)) and not temp_user:
        kw = {"from_page": request.browser_url, "login": "", "error_msg": ""}
        cherrypy.response.body = login_screen % kw
        return True
    
    # Everything is OK: user is logged in
    if load_user_by_username and not tdata.user:
        username = temp_user or sess[session_key]
        request.user = load_user_by_username(username)
        tdata.user = request.user
    
    return False

def virtual_host(use_x_forwarded_host=True, **domains):
    """Redirect internally based on the Host header.
    
    Useful when running multiple sites within one CP server.
    
    From http://groups.google.com/group/cherrypy-users/browse_thread/thread/f393540fe278e54d:
    
    For various reasons I need several domains to point to different parts of a
    single website structure as well as to their own "homepage"   EG
    
    http://www.mydom1.com  ->  root
    http://www.mydom2.com  ->  root/mydom2/
    http://www.mydom3.com  ->  root/mydom3/
    http://www.mydom4.com  ->  under construction page
    
    but also to have  http://www.mydom1.com/mydom2/  etc to be valid pages in
    their own right.
    """
    if hasattr(cherrypy.request, "virtual_prefix"):
        return
    
    domain = cherrypy.request.headers.get('Host', '')
    if use_x_forwarded_host:
        domain = cherrypy.request.headers.get("X-Forwarded-Host", domain)
    
    cherrypy.request.virtual_prefix = prefix = domains.get(domain, "")
    if prefix:
        raise cherrypy.InternalRedirect(_http.urljoin(prefix, cherrypy.request.path_info))

def log_traceback():
    """Write the last error's traceback to the cherrypy error log."""
    from cherrypy import _cperror
    cherrypy.log(_cperror.format_exc(), "HTTP")

def log_request_headers():
    """Write request headers to the cherrypy error log."""
    h = ["  %s: %s" % (k, v) for k, v in cherrypy.request.header_list]
    cherrypy.log('\nRequest Headers:\n' + '\n'.join(h), "HTTP")

def redirect(url=''):
    """Raise cherrypy.HTTPRedirect to the given url."""
    raise cherrypy.HTTPRedirect(url)

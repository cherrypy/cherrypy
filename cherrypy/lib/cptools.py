"""Functions for builtin CherryPy tools."""

import re

import cherrypy
from cherrypy.lib import http as _http


#                     Conditional HTTP request support                     #

def validate_etags(autotags=False):
    """Validate the current ETag against If-Match, If-None-Match headers.
    
    If autotags is True, an ETag response-header value will be provided
    from an MD5 hash of the response body (unless some other code has
    already provided an ETag header). If False, the ETag will not be
    automatic, and if no other code has provided an ETag value, then no
    checks will be performed against If-Match or If-None-Match headers.
    """
    response = cherrypy.response
    
    # Guard against being run twice.
    if hasattr(response, "ETag"):
        return
    
    etag = response.headers.get('ETag')
    
    if (not etag) and autotags:
        import md5
        etag = '"%s"' % md5.new(response.collapse_body()).hexdigest()
        response.headers['ETag'] = etag
    
    if etag:
        response.ETag = etag
        
        status, reason, msg = _http.valid_status(response.status)
        
        request = cherrypy.request
        
        conditions = request.headers.elements('If-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions and not (conditions == ["*"] or etag in conditions):
            if status >= 200 and status < 299:
                raise cherrypy.HTTPError(412)
        
        conditions = request.headers.elements('If-None-Match') or []
        conditions = [str(x) for x in conditions]
        if conditions == ["*"] or etag in conditions:
            if status >= 200 and status < 299:
                if request.method in ("GET", "HEAD"):
                    raise cherrypy.HTTPRedirect([], 304)
                else:
                    raise cherrypy.HTTPError(412)

def validate_since():
    """Validate the current Last-Modified against If-Modified-Since headers.
    
    If no code has set the Last-Modified response header, then no validation
    will be performed.
    """
    response = cherrypy.response
    lastmod = response.headers.get('Last-Modified')
    if lastmod:
        status, reason, msg = _http.valid_status(response.status)
        
        request = cherrypy.request
        
        since = request.headers.get('If-Unmodified-Since')
        if since and since != lastmod:
            if (status >= 200 and status < 299) or status == 412:
                raise cherrypy.HTTPError(412)
        
        since = request.headers.get('If-Modified-Since')
        if since and since == lastmod:
            if (status >= 200 and status < 299) or status == 304:
                if request.method in ("GET", "HEAD"):
                    raise cherrypy.HTTPRedirect([], 304)
                else:
                    raise cherrypy.HTTPError(412)


#                                Tool code                                #

def proxy(base=None, local='X-Forwarded-Host', remote='X-Forwarded-For',
          scheme='X-Forwarded-Proto'):
    """Change the base URL (scheme://host[:port][/path]).
    
    For running a CP server behind Apache, lighttpd, or other HTTP server.
    
    If you want the new request.base to include path info (not just the host),
    you must explicitly set base to the full base path, and ALSO set 'local'
    to '', so that the X-Forwarded-Host request header (which never includes
    path info) does not override it.
    
    cherrypy.request.remote.ip (the IP address of the client) will be
    rewritten if the header specified by the 'remote' arg is valid.
    By default, 'remote' is set to 'X-Forwarded-For'. If you do not
    want to rewrite remote.ip, set the 'remote' arg to an empty string.
    """
    
    request = cherrypy.request
    
    if scheme:
        scheme = request.headers.get(scheme, None)
    if not scheme:
        scheme = request.base[:request.base.find("://")]
    
    if local:
        base = request.headers.get(local, base)
    if not base:
        port = cherrypy.request.local.port
        if port == 80:
            base = 'localhost'
        else:
            base = 'localhost:%s' % port
    
    if base.find("://") == -1:
        # add http:// or https:// if needed
        base = scheme + "://" + base
    
    request.base = base
    
    if remote:
        xff = request.headers.get(remote)
        if xff:
            if remote == 'X-Forwarded-For':
                # See http://bob.pythonmac.org/archives/2005/09/23/apache-x-forwarded-for-caveat/
                xff = xff.split(',')[-1].strip()
            request.remote.ip = xff


def ignore_headers(headers=('Range',)):
    """Delete request headers whose field names are included in 'headers'.
    
    This is a useful tool for working behind certain HTTP servers;
    for example, Apache duplicates the work that CP does for 'Range'
    headers, and will doubly-truncate the response.
    """
    request = cherrypy.request
    for name in headers:
        if name in request.headers:
            del request.headers[name]


def response_headers(headers=None):
    """Set headers on the response."""
    for name, value in (headers or []):
        cherrypy.response.headers[name] = value
response_headers.failsafe = True


def referer(pattern, accept=True, accept_missing=False, error=403,
            message='Forbidden Referer header.'):
    """Raise HTTPError if Referer header does not pass our test.
    
    pattern: a regular expression pattern to test against the Referer.
    accept: if True, the Referer must match the pattern; if False,
        the Referer must NOT match the pattern.
    accept_missing: if True, permit requests with no Referer header.
    error: the HTTP error code to return to the client on failure.
    message: a string to include in the response body on failure.
    """
    try:
        match = bool(re.match(pattern, cherrypy.request.headers['Referer']))
        if accept == match:
            return
    except KeyError:
        if accept_missing:
            return
    
    raise cherrypy.HTTPError(error, message)


class SessionAuth(object):
    """Assert that the user is logged in."""
    
    session_key = "username"
    
    def check_username_and_password(self, username, password):
        pass
    
    def anonymous(self):
        """Provide a temporary user name for anonymous users."""
        pass
    
    def on_login(self, username):
        pass
    
    def on_logout(self, username):
        pass
    
    def on_check(self, username):
        pass
    
    def login_screen(self, from_page='..', username='', error_msg=''):
        return """<html><body>
Message: %(error_msg)s
<form method="post" action="do_login">
    Login: <input type="text" name="username" value="%(username)s" size="10" /><br />
    Password: <input type="password" name="password" size="10" /><br />
    <input type="hidden" name="from_page" value="%(from_page)s" /><br />
    <input type="submit" />
</form>
</body></html>""" % {'from_page': from_page, 'username': username,
                     'error_msg': error_msg}
    
    def do_login(self, username, password, from_page='..'):
        """Login. May raise redirect, or return True if request handled."""
        error_msg = self.check_username_and_password(username, password)
        if error_msg:
            body = self.login_screen(from_page, username, error_msg)
            cherrypy.response.body = body
            if cherrypy.response.headers.has_key("Content-Length"):
                # Delete Content-Length header so finalize() recalcs it.
                del cherrypy.response.headers["Content-Length"]
            return True
        else:
            cherrypy.session[self.session_key] = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")
    
    def do_logout(self, from_page='..'):
        """Logout. May raise redirect, or return True if request handled."""
        sess = cherrypy.session
        username = sess.get(self.session_key)
        sess[self.session_key] = None
        if username:
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page)
    
    def do_check(self):
        """Assert username. May raise redirect, or return True if request handled."""
        sess = cherrypy.session
        request = cherrypy.request
        
        username = sess.get(self.session_key)
        if not username:
            sess[self.session_key] = username = self.anonymous()
        if not username:
            cherrypy.response.body = self.login_screen(cherrypy.url(qs=request.query_string))
            if cherrypy.response.headers.has_key("Content-Length"):
                # Delete Content-Length header so finalize() recalcs it.
                del cherrypy.response.headers["Content-Length"]
            return True
        
        self.on_check(username)
    
    def run(self):
        request = cherrypy.request
        path = request.path_info
        if path.endswith('login_screen'):
            return self.login_screen(**request.params)
        elif path.endswith('do_login'):
            return self.do_login(**request.params)
        elif path.endswith('do_logout'):
            return self.do_logout(**request.params)
        else:
            return self.do_check()


def session_auth(**kwargs):
    sa = SessionAuth()
    for k, v in kwargs.iteritems():
        setattr(sa, k, v)
    return sa.run()


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
    request = cherrypy.request
    
    # Guard against running twice.
    if hasattr(request, "virtual_prefix"):
        return
    
    domain = request.headers.get('Host', '')
    if use_x_forwarded_host:
        domain = request.headers.get("X-Forwarded-Host", domain)
    
    request.virtual_prefix = prefix = domains.get(domain, "")
    if prefix:
        raise cherrypy.InternalRedirect(_http.urljoin(prefix, request.path_info))

def log_traceback():
    """Write the last error's traceback to the cherrypy error log."""
    from cherrypy import _cperror
    cherrypy.log(_cperror.format_exc(), "HTTP")

def log_request_headers():
    """Write request headers to the cherrypy error log."""
    h = ["  %s: %s" % (k, v) for k, v in cherrypy.request.header_list]
    cherrypy.log('\nRequest Headers:\n' + '\n'.join(h), "HTTP")

def redirect(url='', internal=True):
    """Raise InternalRedirect or HTTPRedirect to the given url."""
    if internal:
        raise cherrypy.InternalRedirect(url)
    else:
        raise cherrypy.HTTPRedirect(url)

def trailing_slash(missing=True, extra=False):
    """Redirect if path_info has (missing|extra) trailing slash."""
    request = cherrypy.request
    pi = request.path_info
    
    if request.is_index is True:
        if missing:
            if pi[-1:] != '/':
                new_url = cherrypy.url(pi + '/', request.query_string)
                raise cherrypy.HTTPRedirect(new_url)
    elif request.is_index is False:
        if extra:
            # If pi == '/', don't redirect to ''!
            if pi[-1:] == '/' and pi != '/':
                new_url = cherrypy.url(pi[:-1], request.query_string)
                raise cherrypy.HTTPRedirect(new_url)


"""Tools which both CherryPy and application developers may invoke."""

import inspect
import os
import sys
import time

import cherrypy



def decorate(func, decorator):
    """
    Return the decorated func. This will automatically copy all
    non-standard attributes (like exposed) to the newly decorated function.
    """
    newfunc = decorator(func)
    for (k,v) in inspect.getmembers(func):
        if not hasattr(newfunc, k):
            setattr(newfunc, k, v)
    return newfunc

def decorateAll(obj, decorator):
    """
    Recursively decorate all exposed functions of obj and all of its children,
    grandchildren, etc. If you used to use aspects, you might want to look
    into these. This function modifies obj; there is no return value.
    """
    obj_type = type(obj)
    for (k,v) in inspect.getmembers(obj):
        if hasattr(obj_type, k): # only deal with user-defined attributes
            continue
        if callable(v) and getattr(v, "exposed", False):
            setattr(obj, k, decorate(v, decorator))
        decorateAll(v, decorator)


class ExposeItems:
    """
    Utility class that exposes a getitem-aware object. It does not provide
    index() or default() methods, and it does not expose the individual item
    objects - just the list or dict that contains them. User-specific index()
    and default() methods can be implemented by inheriting from this class.
    
    Use case:
    
    from cherrypy.lib.cptools import ExposeItems
    ...
    cherrypy.root.foo = ExposeItems(mylist)
    cherrypy.root.bar = ExposeItems(mydict)
    """
    exposed = True
    def __init__(self, items):
        self.items = items
    def __getattr__(self, key):
        return self.items[key]


def fileGenerator(input, chunkSize=65536):
    """Yield the given input (a file object) in chunks (default 64k)."""
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()


def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        mod = sys.modules[modulePath]
        if mod is None:
            raise KeyError()
    except KeyError:
        # The last [''] is important.
        mod = __import__(modulePath, globals(), locals(), [''])
    return mod

def attributes(fullAttributeName):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    lastDot = fullAttributeName.rfind(u".")
    attrName = fullAttributeName[lastDot + 1:]
    modPath = fullAttributeName[:lastDot]
    
    aMod = modules(modPath)
    # Let an AttributeError propagate outward.
    try:
        attr = getattr(aMod, attrName)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (modPath, attrName))
    
    # Return a reference to the attribute.
    return attr


# public domain "unrepr" implementation, found on the web and then improved.
import compiler

def getObj(s):
    s = "a=" + s
    p = compiler.parse(s)
    return p.getChildren()[1].getChildren()[0].getChildren()[1]


class UnknownType(Exception):
    pass


class Builder:
    
    def build(self, o):
        m = getattr(self, 'build_' + o.__class__.__name__, None)
        if m is None:
            raise UnknownType(o.__class__.__name__)
        return m(o)
    
    def build_CallFunc(self, o):
        callee, args, starargs, kwargs = map(self.build, o.getChildren())
        return callee(args, *(starargs or ()), **(kwargs or {}))
    
    def build_List(self, o):
        return map(self.build, o.getChildren())
    
    def build_Const(self, o):
        return o.value
    
    def build_Dict(self, o):
        d = {}
        i = iter(map(self.build, o.getChildren()))
        for el in i:
            d[el] = i.next()
        return d
    
    def build_Tuple(self, o):
        return tuple(self.build_List(o))
    
    def build_Name(self, o):
        if o.name == 'None':
            return None
        if o.name == 'True':
            return True
        if o.name == 'False':
            return False
        
        # See if the Name is a package or module
        try:
            return modules(o.name)
        except ImportError:
            pass
        
        raise UnknownType(o.name)
    
    def build_Add(self, o):
        real, imag = map(self.build_Const, o.getChildren())
        try:
            real = float(real)
        except TypeError:
            raise UnknownType('Add')
        if not isinstance(imag, complex) or imag.real != 0.0:
            raise UnknownType('Add')
        return real+imag
    
    def build_Getattr(self, o):
        parent = self.build(o.expr)
        return getattr(parent, o.attrname)
    
    def build_NoneType(self, o):
        return None


def unrepr(s):
    if not s:
        return s
    return Builder().build(getObj(s))


# Old filter code

def base_url(base=None, use_x_forwarded_host=True):
    """Change the base URL.
    
    Useful when running a CP server behind Apache.
    """
    
    request = cherrypy.request
    
    if base is None:
        port = str(cherrypy.config.get('server.socket_port', '80'))
        if port == "80":
            base = 'http://localhost'
        else:
            base = 'http://localhost:%s' % port
    
    if use_x_forwarded_host:
        base = request.headers.get("X-Forwarded-Host", base)
    
    if base.find("://") == -1:
        # add http:// or https:// if needed
        base = request.base[:request.base.find("://") + 3] + base
    
    request.base = base


def response_headers(headers=None):
    """Set headers on the response."""
    for name, value in headers or []:
        if name not in cherrypy.response.headers:
            cherrypy.response.headers[name] = value


class SessionAuthenticator:
    
    login_screen = """<html><body>
    Message: %(error_msg)s
    <form method="post" action="do_login">
        Login: <input type="text" name="login" value="%(login)s" size="10" /><br />
        Password: <input type="password" name="password" size="10" /><br />
        <input type="hidden" name="from_page" value="%(from_page)s" /><br />
        <input type="submit" />
    </form>
</body></html>"""
    
    def __call__(check_login_and_password, not_logged_in,
                 load_user_by_username, session_key = 'username',
                 on_login = None, on_logout = None,
                 login_screen = None):
        
        if login_screen is None:
            login_screen = self.login_screen
        
        cherrypy.request.user = None
        cherrypy.thread_data.user = None
        
        conf = cherrypy.config.get
        if conf('static_filter.on', False):
            return
        if cherrypy.request.path.endswith('login_screen'):
            return
        elif cherrypy.request.path.endswith('do_logout'):
            login = cherrypy.session.get(session_key)
            cherrypy.session[session_key] = None
            cherrypy.request.user = None
            cherrypy.thread_data.user = None
            if login and on_logout:
                on_logout(login)
            from_page = cherrypy.request.params.get('from_page', '..')
            raise cherrypy.HTTPRedirect(from_page)
        elif cherrypy.request.path.endswith('do_login'):
            from_page = cherrypy.request.params.get('from_page', '..')
            login = cherrypy.request.params['login']
            password = cherrypy.request.params['password']
            error_msg = check_login_and_password(login, password)
            if error_msg:
                kw = {"from_page": from_page,
                      "login": login, "error_msg": error_msg}
                cherrypy.response.body = login_screen % kw
                cherrypy.request.execute_main = False
            else:
                cherrypy.session[session_key] = login
                if on_login:
                    on_login(login)
                if not from_page:
                    from_page = '/'
                raise cherrypy.HTTPRedirect(from_page)
            return

        # Check if user is logged in
        temp_user = None
        if (not cherrypy.session.get(session_key)) and not_logged_in:
            # Call not_logged_in so that applications where anynymous user
            #   is OK can handle it
            temp_user = not_logged_in()
        if (not cherrypy.session.get(session_key)) and not temp_user:
            kw = {"from_page": cherrypy.request.browser_url,
                  "login": "", "error_msg": ""}
            cherrypy.response.body = login_screen % kw
            cherrypy.request.execute_main = False
            return
        
        # Everything is OK: user is logged in
        if load_user_by_username and not cherrypy.thread_data.user:
            username = temp_user or cherrypy.session[session_key]
            cherrypy.request.user = load_user_by_username(username)
            cherrypy.thread_data.user = cherrypy.request.user


def virtual_host(use_x_forwarded_host=True, **domains):
    """Change the object_path based on the Host.
    
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
    
    domain = cherrypy.request.headers.get('Host', '')
    if use_x_forwarded_host:
        domain = cherrypy.request.headers.get("X-Forwarded-Host", domain)
    
    prefix = domains.get(domain, "")
    if prefix:
        cherrypy.request.object_path = prefix + "/" + cherrypy.request.object_path



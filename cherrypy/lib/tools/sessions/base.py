import binascii
import datetime
import os
import time

from magicbus.plugins.tasks import Monitor

import cherrypy
from cherrypy.lib.tools import Tool
from cherrypy.lib import httputil, is_iterator

missing = object()


class Session(object):
    """A CherryPy dict-like Session object (one per request)."""

    _id = None

    id_observers = None
    "A list of callbacks to which to pass new id's."

    @property
    def id(self):
        """The current session ID."""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        for o in self.id_observers:
            o(value)

    timeout = 60
    "Number of minutes after which to delete session data."

    locked = False
    """
    If True, this session instance has exclusive read/write access
    to session data."""

    loaded = False
    """
    If True, data has been retrieved from storage. This should happen
    automatically on the first attempt to access session data."""

    clean_thread = None
    "Class-level Monitor which calls self.clean_up."

    clean_freq = 5
    "The poll rate for expired session cleanup in minutes."

    originalid = None
    "The session id passed by the client. May be missing or unsafe."

    missing = False
    "True if the session requested by the client did not exist."

    regenerated = False
    """
    True if the application called session.regenerate(). This is not set by
    internal calls to regenerate the session id."""

    debug = False
    "If True, log debug information."

    # --------------------- Session management methods --------------------- #

    def __init__(self, id=None, **kwargs):
        self.id_observers = []
        self._data = {}

        for k, v in kwargs.items():
            setattr(self, k, v)

        self.originalid = id
        self.missing = False
        if id is None:
            if self.debug:
                cherrypy.log('No id given; making a new one', 'TOOLS.SESSIONS')
            self._regenerate()
        else:
            self.id = id
            if self._exists():
                if self.debug:
                    cherrypy.log('Set id to %s.' % id, 'TOOLS.SESSIONS')
            else:
                if self.debug:
                    cherrypy.log('Expired or malicious session %r; '
                                 'making a new one' % id, 'TOOLS.SESSIONS')
                # Expired or malicious session. Make a new one.
                # See https://bitbucket.org/cherrypy/cherrypy/issue/709.
                self.id = None
                self.missing = True
                self._regenerate()

    def now(self):
        """Generate the session specific concept of 'now'.

        Other session providers can override this to use alternative,
        possibly timezone aware, versions of 'now'.
        """
        return datetime.datetime.now()

    def regenerate(self):
        """Replace the current session (with a new id)."""
        self.regenerated = True
        self._regenerate()

    def _regenerate(self):
        if self.id is not None:
            if self.debug:
                cherrypy.log(
                    'Deleting the existing session %r before '
                    'regeneration.' % self.id,
                    'TOOLS.SESSIONS')
            self.delete()

        old_session_was_locked = self.locked
        if old_session_was_locked:
            self.release_lock()
            if self.debug:
                cherrypy.log('Old lock released.', 'TOOLS.SESSIONS')

        self.id = None
        while self.id is None:
            self.id = self.generate_id()
            # Assert that the generated id is not already stored.
            if self._exists():
                self.id = None
        if self.debug:
            cherrypy.log('Set id to generated %s.' % self.id,
                         'TOOLS.SESSIONS')

        if old_session_was_locked:
            self.acquire_lock()
            if self.debug:
                cherrypy.log('Regenerated lock acquired.', 'TOOLS.SESSIONS')

    def clean_up(self):
        """Clean up expired sessions."""
        pass

    def generate_id(self):
        """Return a new session id."""
        return binascii.hexlify(os.urandom(20)).decode('ascii')

    def save(self):
        """Save session data."""
        try:
            # If session data has never been loaded then it's never been
            #   accessed: no need to save it
            if self.loaded:
                t = datetime.timedelta(seconds=self.timeout * 60)
                expiration_time = self.now() + t
                if self.debug:
                    cherrypy.log('Saving session %r with expiry %s' %
                                 (self.id, expiration_time),
                                 'TOOLS.SESSIONS')
                self._save(expiration_time)
            else:
                if self.debug:
                    cherrypy.log(
                        'Skipping save of session %r (no session loaded).' %
                        self.id, 'TOOLS.SESSIONS')
        finally:
            if self.locked:
                # Always release the lock if the user didn't release it
                self.release_lock()
                if self.debug:
                    cherrypy.log('Lock released after save.', 'TOOLS.SESSIONS')

    def load(self):
        """Copy stored session data into this session instance."""
        data = self._load()
        # data is either None or a tuple (session_data, expiration_time)
        if data is None or data[1] < self.now():
            if self.debug:
                cherrypy.log('Expired session %r, flushing data.' % self.id,
                             'TOOLS.SESSIONS')
            self._data = {}
        else:
            if self.debug:
                cherrypy.log('Data loaded for session %r.' % self.id,
                             'TOOLS.SESSIONS')
            self._data = data[0]
        self.loaded = True

        # Stick the clean_thread in the class, not the instance.
        # The instances are created and destroyed per-request.
        cls = self.__class__
        if self.clean_freq and not cls.clean_thread:
            # clean_up is an instancemethod and not a classmethod,
            # so that tool config can be accessed inside the method.
            t = Monitor(cherrypy.engine, self.clean_up, self.clean_freq * 60,
                        name='Session cleanup')
            t.subscribe()
            cls.clean_thread = t
            t.start()
            if self.debug:
                cherrypy.log('Started cleanup thread.', 'TOOLS.SESSIONS')

    def delete(self):
        """Delete stored session data."""
        self._delete()
        if self.debug:
            cherrypy.log('Deleted session %s.' % self.id,
                         'TOOLS.SESSIONS')

    # -------------------- Application accessor methods -------------------- #

    def __getitem__(self, key):
        if not self.loaded:
            self.load()
        return self._data[key]

    def __setitem__(self, key, value):
        if not self.loaded:
            self.load()
        self._data[key] = value

    def __delitem__(self, key):
        if not self.loaded:
            self.load()
        del self._data[key]

    def pop(self, key, default=missing):
        """Remove the specified key and return the corresponding value.
        If key is not found, default is returned if given,
        otherwise KeyError is raised.
        """
        if not self.loaded:
            self.load()
        if default is missing:
            return self._data.pop(key)
        else:
            return self._data.pop(key, default)

    def __contains__(self, key):
        if not self.loaded:
            self.load()
        return key in self._data

    if hasattr({}, 'has_key'):
        def has_key(self, key):
            """D.has_key(k) -> True if D has a key k, else False."""
            if not self.loaded:
                self.load()
            return key in self._data

    def get(self, key, default=None):
        """D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None."""
        if not self.loaded:
            self.load()
        return self._data.get(key, default)

    def update(self, d):
        """D.update(E) -> None.  Update D from E: for k in E: D[k] = E[k]."""
        if not self.loaded:
            self.load()
        self._data.update(d)

    def setdefault(self, key, default=None):
        """D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D."""
        if not self.loaded:
            self.load()
        return self._data.setdefault(key, default)

    def clear(self):
        """D.clear() -> None.  Remove all items from D."""
        if not self.loaded:
            self.load()
        self._data.clear()

    def keys(self):
        """D.keys() -> list of D's keys."""
        if not self.loaded:
            self.load()
        return self._data.keys()

    def items(self):
        """D.items() -> list of D's (key, value) pairs, as 2-tuples."""
        if not self.loaded:
            self.load()
        return self._data.items()

    def values(self):
        """D.values() -> list of D's values."""
        if not self.loaded:
            self.load()
        return self._data.values()


# Hook functions (for CherryPy tools)

def save():
    """Save any changed session data."""

    if not hasattr(cherrypy.serving, "session"):
        return
    request = cherrypy.serving.request
    response = cherrypy.serving.response

    # Guard against running twice
    if hasattr(request, "_sessionsaved"):
        return
    request._sessionsaved = True

    if response.stream:
        # If the body is being streamed, we have to save the data
        #   *after* the response has been written out
        request.hooks.attach('on_end_request', cherrypy.session.save)
    else:
        # If the body is not being streamed, we save the data now
        # (so we can release the lock).
        if is_iterator(response.body):
            response.collapse_body()
        cherrypy.session.save()
save.failsafe = True


def close():
    """Close the session object for this request."""
    sess = getattr(cherrypy.serving, "session", None)
    if getattr(sess, "locked", False):
        # If the session is still locked we release the lock
        sess.release_lock()
        if sess.debug:
            cherrypy.log('Lock released on close.', 'TOOLS.SESSIONS')
close.failsafe = True
close.priority = 90


def find_storage_class(storage_type):
    # FIXME: this is too magical. Implement a pluggable session register.
    storage_class = storage_type.title() + 'Session'
    import cherrypy.lib.tools.sessions
    return getattr(cherrypy.lib.tools.sessions, storage_class)


def init(storage_type='ram', path=None, path_header=None, name='session_id',
         timeout=60, domain=None, secure=False, clean_freq=5,
         persistent=True, httponly=False, debug=False, **kwargs):
    """Initialize session object (using cookies).

    storage_type
        One of 'ram', 'file', 'postgresql', 'memcached'. This will be
        used to look up the corresponding class in cherrypy.lib.sessions
        globals. For example, 'file' will use the FileSession class.

    path
        The 'path' value to stick in the response cookie metadata.

    path_header
        If 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].

    name
        The name of the cookie.

    timeout
        The expiration timeout (in minutes) for the stored session data.
        If 'persistent' is True (the default), this is also the timeout
        for the cookie.

    domain
        The cookie domain.

    secure
        If False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).

    clean_freq (minutes)
        The poll rate for expired session cleanup.

    persistent
        If True (the default), the 'timeout' argument will be used
        to expire the cookie. If False, the cookie will not have an expiry,
        and the cookie will be a "session cookie" which expires when the
        browser is closed.

    httponly
        If False (the default) the cookie 'httponly' value will not be set.
        If True, the cookie 'httponly' value will be set (to 1).

    Any additional kwargs will be bound to the new Session instance,
    and may be specific to the storage type. See the subclass of Session
    you're using for more information.
    """

    request = cherrypy.serving.request

    # Guard against running twice
    if hasattr(request, "_session_init_flag"):
        return
    request._session_init_flag = True

    # Check if request came with a session ID
    id = None
    if name in request.cookie:
        id = request.cookie[name].value
        if debug:
            cherrypy.log('ID obtained from request.cookie: %r' % id,
                         'TOOLS.SESSIONS')

    # Find the storage class and call setup (first time only).
    storage_class = find_storage_class(storage_type)
    if not hasattr(cherrypy, "session"):
        if hasattr(storage_class, "setup"):
            storage_class.setup(**kwargs)

    # Create and attach a new Session instance to cherrypy.serving.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    kwargs['timeout'] = timeout
    kwargs['clean_freq'] = clean_freq
    cherrypy.serving.session = sess = storage_class(id, **kwargs)
    sess.debug = debug

    def update_cookie(id):
        """Update the cookie every time the session id changes."""
        cherrypy.serving.response.cookie[name] = id
    sess.id_observers.append(update_cookie)

    # Create cherrypy.session which will proxy to cherrypy.serving.session
    if not hasattr(cherrypy, "session"):
        cherrypy.session = cherrypy._ThreadLocalProxy('session')

    if persistent:
        cookie_timeout = timeout
    else:
        # See http://support.microsoft.com/kb/223799/EN-US/
        # and http://support.mozilla.com/en-US/kb/Cookies
        cookie_timeout = None
    set_response_cookie(path=path, path_header=path_header, name=name,
                        timeout=cookie_timeout, domain=domain, secure=secure,
                        httponly=httponly)


def set_response_cookie(path=None, path_header=None, name='session_id',
                        timeout=60, domain=None, secure=False, httponly=False):
    """Set a response cookie for the client.

    path
        the 'path' value to stick in the response cookie metadata.

    path_header
        if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].

    name
        the name of the cookie.

    timeout
        the expiration timeout for the cookie. If 0 or other boolean
        False, no 'expires' param will be set, and the cookie will be a
        "session cookie" which expires when the browser is closed.

    domain
        the cookie domain.

    secure
        if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).

    httponly
        If False (the default) the cookie 'httponly' value will not be set.
        If True, the cookie 'httponly' value will be set (to 1).

    """
    # Set response cookie
    cookie = cherrypy.serving.response.cookie
    cookie[name] = cherrypy.serving.session.id
    cookie[name]['path'] = (
        path or
        cherrypy.serving.request.headers.get(path_header) or
        '/'
    )

    # We'd like to use the "max-age" param as indicated in
    # http://www.faqs.org/rfcs/rfc2109.html but IE doesn't
    # save it to disk and the session is lost if people close
    # the browser. So we have to use the old "expires" ... sigh ...
    ##    cookie[name]['max-age'] = timeout * 60
    if timeout:
        e = time.time() + (timeout * 60)
        cookie[name]['expires'] = httputil.HTTPDate(e)
    if domain is not None:
        cookie[name]['domain'] = domain
    if secure:
        cookie[name]['secure'] = 1
    if httponly:
        if not cookie[name].isReservedKey('httponly'):
            raise ValueError("The httponly cookie token is not supported.")
        cookie[name]['httponly'] = 1


def expire():
    """Expire the current session cookie."""
    name = cherrypy.serving.request.config.get(
        'tools.sessions.name', 'session_id')
    one_year = 60 * 60 * 24 * 365
    e = time.time() - one_year
    cherrypy.serving.response.cookie[name]['expires'] = httputil.HTTPDate(e)


class SessionTool(Tool):
    """Session Tool for CherryPy.

    sessions.locking
        When 'implicit' (the default), the session will be locked for you,
        just before running the page handler.

        When 'early', the session will be locked before reading the request
        body. This is off by default for safety reasons; for example,
        a large upload would block the session, denying an AJAX
        progress meter
        (`issue <https://bitbucket.org/cherrypy/cherrypy/issue/630>`_).

        When 'explicit' (or any other value), you need to call
        cherrypy.session.acquire_lock() yourself before using
        session data.
    """

    def __init__(self):
        # _sessions.init must be bound after headers are read
        Tool.__init__(self, 'before_request_body', init)

    def _lock_session(self):
        cherrypy.serving.session.acquire_lock()

    def _setup(self):
        """Hook this tool into cherrypy.request.

        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        hooks = cherrypy.serving.request.hooks

        conf = self._merged_args()

        p = conf.pop("priority", None)
        if p is None:
            p = getattr(self.callable, "priority", self._priority)

        hooks.attach(self._point, self.callable, priority=p, **conf)

        locking = conf.pop('locking', 'implicit')
        if locking == 'implicit':
            hooks.attach('before_handler', self._lock_session)
        elif locking == 'early':
            # Lock before the request body (but after _sessions.init runs!)
            hooks.attach('before_request_body', self._lock_session,
                         priority=60)
        else:
            # Don't lock
            pass

        hooks.attach('before_finalize', save)
        hooks.attach('on_end_request', close)

    def regenerate(self):
        """Drop the current session and make a new one (with a new id)."""
        sess = cherrypy.serving.session
        sess.regenerate()

        # Grab cookie-relevant tool args
        conf = dict([(k, v) for k, v in self._merged_args().items()
                     if k in ('path', 'path_header', 'name', 'timeout',
                              'domain', 'secure')])
        set_response_cookie(**conf)

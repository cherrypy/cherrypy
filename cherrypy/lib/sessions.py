"""Session implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.session to store these variables.
"""

import datetime
import os
try:
    import cPickle as pickle
except ImportError:
    import pickle
import random
import sha
import time
import threading
import types
from warnings import warn

import cherrypy
from cherrypy.lib import http


missing = object()

class Session(object):
    """A CherryPy dict-like Session object (one per request)."""
    
    __metaclass__ = cherrypy._AttributeDocstrings
    
    id = None
    id__doc = "The current session ID."
    
    timeout = 60
    timeout__doc = "Number of minutes after which to delete session data."
    
    locked = False
    locked__doc = """
    If True, this session instance has exclusive read/write access
    to session data."""
    
    loaded = False
    loaded__doc = """
    If True, data has been retrieved from storage. This should happen
    automatically on the first attempt to access session data."""
    
    clean_thread = None
    clean_thread__doc = "Class-level Monitor which calls self.clean_up."
    
    clean_freq = 5
    clean_freq__doc = "The poll rate for expired session cleanup in minutes."
    
    def __init__(self, id=None, **kwargs):
        self._data = {}
        
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        
        self.id = id
        while self.id is None:
            self.id = self.generate_id()
            # Assert that the generated id is not already stored.
            if self._load() is not None:
                self.id = None
    
    def clean_up(self):
        """Clean up expired sessions."""
        pass
    
    try:
        os.urandom(20)
    except (AttributeError, NotImplementedError):
        # os.urandom not available until Python 2.4. Fall back to random.random.
        def generate_id(self):
            """Return a new session id."""
            return sha.new('%s' % random.random()).hexdigest()
    else:
        def generate_id(self):
            """Return a new session id."""
            return os.urandom(20).encode('hex')
    
    def save(self):
        """Save session data."""
        try:
            # If session data has never been loaded then it's never been
            #   accessed: no need to delete it
            if self.loaded:
                t = datetime.timedelta(seconds = self.timeout * 60)
                expiration_time = datetime.datetime.now() + t
                self._save(expiration_time)
            
        finally:
            if self.locked:
                # Always release the lock if the user didn't release it
                self.release_lock()
    
    def load(self):
        """Copy stored session data into this session instance."""
        data = self._load()
        # data is either None or a tuple (session_data, expiration_time)
        if data is None or data[1] < datetime.datetime.now():
            # Expired session: flush session data (but keep the same id)
            self._data = {}
        else:
            self._data = data[0]
        self.loaded = True
        
        # Stick the clean_thread in the class, not the instance.
        # The instances are created and destroyed per-request.
        cls = self.__class__
        if not cls.clean_thread:
            # clean_up is in instancemethod and not a classmethod,
            # so tool config can be accessed inside the method.
            from cherrypy import restsrv
            t = restsrv.plugins.Monitor(cherrypy.engine, self.clean_up,
                                        "CP Session Cleanup")
            t.frequency = self.clean_freq
            cls.clean_thread = t
            t.start()
    
    def delete(self):
        """Delete stored session data."""
        self._delete()
    
    def __getitem__(self, key):
        if not self.loaded: self.load()
        return self._data[key]
    
    def __setitem__(self, key, value):
        if not self.loaded: self.load()
        self._data[key] = value
    
    def __delitem__(self, key):
        if not self.loaded: self.load()
        del self._data[key]
    
    def pop(self, key, default=missing):
        if not self.loaded: self.load()
        if default is missing:
            return self._data.pop(key)
        else:
            return self._data.pop(key, default)
    
    def __contains__(self, key):
        if not self.loaded: self.load()
        return key in self._data
    
    def has_key(self, key):
        if not self.loaded: self.load()
        return self._data.has_key(key)
    
    def get(self, key, default=None):
        if not self.loaded: self.load()
        return self._data.get(key, default)
    
    def update(self, d):
        if not self.loaded: self.load()
        self._data.update(d)
    
    def setdefault(self, key, default=None):
        if not self.loaded: self.load()
        return self._data.setdefault(key, default)
    
    def clear(self):
        if not self.loaded: self.load()
        self._data.clear()
    
    def keys(self):
        if not self.loaded: self.load()
        return self._data.keys()
    
    def items(self):
        if not self.loaded: self.load()
        return self._data.items()
    
    def values(self):
        if not self.loaded: self.load()
        return self._data.values()


class RamSession(Session):
    
    # Class-level objects. Don't rebind these!
    cache = {}
    locks = {}
    
    def clean_up(self):
        """Clean up expired sessions."""
        now = datetime.datetime.now()
        for id, (data, expiration_time) in self.cache.items():
            if expiration_time < now:
                try:
                    del self.cache[id]
                except KeyError:
                    pass
                try:
                    del self.locks[id]
                except KeyError:
                    pass
    
    def _load(self):
        return self.cache.get(self.id)
    
    def _save(self, expiration_time):
        self.cache[self.id] = (self._data, expiration_time)
    
    def _delete(self):
        del self.cache[self.id]
    
    def acquire_lock(self):
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()
    
    def release_lock(self):
        self.locks[self.id].release()
        self.locked = False


class FileSession(Session):
    """ Implementation of the File backend for sessions
    
    storage_path: the folder where session data will be saved. Each session
        will be saved as pickle.dump(data, expiration_time) in its own file;
        the filename will be self.SESSION_PREFIX + self.id.
    """
    
    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    
    def setup(self):
        # Warn if any lock files exist at startup.
        lockfiles = [fname for fname in os.listdir(self.storage_path)
                     if (fname.startswith(self.SESSION_PREFIX)
                         and fname.endswith(self.LOCK_SUFFIX))]
        if lockfiles:
            plural = ('', 's')[len(lockfiles) > 1]
            warn("%s session lockfile%s found at startup. If you are "
                 "only running one process, then you may need to "
                 "manually delete the lockfiles found at %r."
                 % (len(lockfiles), plural,
                    os.path.abspath(self.storage_path)))
    
    def _get_file_path(self):
        return os.path.join(self.storage_path, self.SESSION_PREFIX + self.id)
    
    def _load(self, path=None):
        if path is None:
            path = self._get_file_path()
        try:
            f = open(path, "rb")
            try:
                return pickle.load(f)
            finally:
                f.close()
        except (IOError, EOFError):
            return None
    
    def _save(self, expiration_time):
        f = open(self._get_file_path(), "wb")
        try:
            pickle.dump((self._data, expiration_time), f)
        finally:
            f.close()
    
    def _delete(self):
        try:
            os.unlink(self._get_file_path())
        except OSError:
            pass
    
    def acquire_lock(self, path=None):
        if path is None:
            path = self._get_file_path()
        path += self.LOCK_SUFFIX
        while True:
            try:
                lockfd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
            except OSError:
                time.sleep(0.1)
            else:
                os.close(lockfd) 
                break
        self.locked = True
    
    def release_lock(self, path=None):
        if path is None:
            path = self._get_file_path()
        os.unlink(path + self.LOCK_SUFFIX)
        self.locked = False
    
    def clean_up(self):
        """Clean up expired sessions."""
        now = datetime.datetime.now()
        # Iterate over all session files in self.storage_path
        for fname in os.listdir(self.storage_path):
            if (fname.startswith(self.SESSION_PREFIX)
                and not fname.endswith(self.LOCK_SUFFIX)):
                # We have a session file: lock and load it and check
                #   if it's expired. If it fails, nevermind.
                path = os.path.join(self.storage_path, fname)
                self.acquire_lock(path)
                try:
                    contents = self._load(path)
                    # _load returns None on IOError
                    if contents is not None:
                        data, expiration_time = contents
                        if expiration_time < now:
                            # Session expired: deleting it
                            os.unlink(path)
                finally:
                    self.release_lock(path)


class PostgresqlSession(Session):
    """ Implementation of the PostgreSQL backend for sessions. It assumes
        a table like this:

            create table session (
                id varchar(40),
                data text,
                expiration_time timestamp
            )
    
    You must provide your own get_db function.
    """
    
    def __init__(self):
        self.db = self.get_db()
        self.cursor = self.db.cursor()
    
    def __del__(self):
        if self.cursor:
            self.cursor.close()
        self.db.commit()
    
    def _load(self):
        # Select session data from table
        self.cursor.execute('select data, expiration_time from session '
                            'where id=%s', (self.id,))
        rows = self.cursor.fetchall()
        if not rows:
            return None
        
        pickled_data, expiration_time = rows[0]
        data = pickle.loads(pickled_data)
        return data, expiration_time
    
    def _save(self, expiration_time):
        pickled_data = pickle.dumps(self._data)
        self.cursor.execute('update session set data = %s, '
                            'expiration_time = %s where id = %s',
                            (pickled_data, expiration_time, self.id))
    
    def _delete(self):
        self.cursor.execute('delete from session where id=%s', (self.id,))
   
    def acquire_lock(self):
        # We use the "for update" clause to lock the row
        self.locked = True
        self.cursor.execute('select id from session where id=%s for update',
                            (self.id,))
    
    def release_lock(self):
        # We just close the cursor and that will remove the lock
        #   introduced by the "for update" clause
        self.cursor.close()
        self.locked = False
    
    def clean_up(self):
        """Clean up expired sessions."""
        self.cursor.execute('delete from session where expiration_time < %s',
                            (datetime.datetime.now(),))


# Hook functions (for CherryPy tools)

def save():
    """Save any changed session data."""
    if not hasattr(cherrypy, "session"):
        return
    
    # Guard against running twice
    if hasattr(cherrypy.request, "_sessionsaved"):
        return
    cherrypy.request._sessionsaved = True
    
    if cherrypy.response.stream:
        # If the body is being streamed, we have to save the data
        #   *after* the response has been written out
        cherrypy.request.hooks.attach('on_end_request', cherrypy.session.save)
    else:
        # If the body is not being streamed, we save the data now
        # (so we can release the lock).
        if isinstance(cherrypy.response.body, types.GeneratorType):
            cherrypy.response.collapse_body()
        cherrypy.session.save()
save.failsafe = True

def close():
    """Close the session object for this request."""
    sess = getattr(cherrypy, "session", None)
    if sess and sess.locked:
        # If the session is still locked we release the lock
        sess.release_lock()
close.failsafe = True
close.priority = 90


def init(storage_type='ram', path=None, path_header=None, name='session_id',
         timeout=60, domain=None, secure=False, clean_freq=5, **kwargs):
    """Initialize session object (using cookies).
    
    storage_type: one of 'ram', 'file', 'postgresql'. This will be used
        to look up the corresponding class in cherrypy.lib.sessions
        globals. For example, 'file' will use the FileSession class.
    path: the 'path' value to stick in the response cookie metadata.
    path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    name: the name of the cookie.
    timeout: the expiration timeout for the cookie.
    domain: the cookie domain.
    secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    clean_freq (minutes): the poll rate for expired session cleanup.
    
    Any additional kwargs will be bound to the new Session instance,
    and may be specific to the storage type. See the subclass of Session
    you're using for more information.
    """
    
    request = cherrypy.request
    
    # Guard against running twice
    if hasattr(request, "_session_init_flag"):
        return
    request._session_init_flag = True
    
    # Check if request came with a session ID
    id = None
    if name in request.cookie:
        id = request.cookie[name].value
    
    # Create and attach a new Session instance to cherrypy._serving.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    storage_class = storage_type.title() + 'Session'
    kwargs['timeout'] = timeout
    kwargs['clean_freq'] = clean_freq
    cherrypy._serving.session = sess = globals()[storage_class](id, **kwargs)
    
    # Create cherrypy.session which will proxy to cherrypy._serving.session
    if not hasattr(cherrypy, "session"):
        cherrypy.session = cherrypy._ThreadLocalProxy('session')
        if hasattr(sess, "setup"):
            sess.setup()
    
    # Set response cookie
    cookie = cherrypy.response.cookie
    cookie[name] = sess.id
    cookie[name]['path'] = path or request.headers.get(path_header) or '/'
    
    # We'd like to use the "max-age" param as indicated in
    # http://www.faqs.org/rfcs/rfc2109.html but IE doesn't
    # save it to disk and the session is lost if people close
    # the browser. So we have to use the old "expires" ... sigh ...
##    cookie[name]['max-age'] = timeout * 60
    if timeout:
        cookie[name]['expires'] = http.HTTPDate(time.time() + (timeout * 60))
    if domain is not None:
        cookie[name]['domain'] = domain
    if secure:
        cookie[name]['secure'] = 1


def expire():
    """Expire the current session cookie."""
    name = cherrypy.request.config.get('tools.sessions.name', 'session_id')
    one_year = 60 * 60 * 24 * 365
    exp = time.gmtime(time.time() - one_year)
    t = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", exp)
    cherrypy.response.cookie[name]['expires'] = t


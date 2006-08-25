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

import cherrypy
from cherrypy.lib import http


class Session(object):
    """A CherryPy dict-like Session object (one per request).
    
    id: current session ID.
    expiration_time (datetime): when the current session will expire.
    timeout (minutes): used to calculate expiration_time from now.
    clean_freq (minutes): the poll rate for expired session cleanup.
    locked: If True, this session instance has exclusive read/write access
        to session data.
    loaded: If True, data has been retrieved from storage. This should
        happen automatically on the first attempt to access session data.
    """
    
    clean_thread = None
    
    def __init__(self, id=None, **kwargs):
        self.locked = False
        self.loaded = False
        self._data = {}
        
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        
        self.id = id
        while self.id is None:
            self.id = self.generate_id()
            # Assert that the generated id is not already stored.
            if self._load() is not None:
                self.id = None
    
    def clean_cycle(self):
        """Clean up expired sessions at regular intervals."""
        # clean_thread is both a cancelable Timer and a flag.
        if self.clean_thread:
            self.clean_up()
            t = threading.Timer(self.clean_freq, self.clean_cycle)
            self.__class__.clean_thread = t
            t.start()
    
    def clean_interrupt(cls):
        """Stop the expired-session cleaning cycle."""
        if cls.clean_thread:
            cls.clean_thread.cancel()
            cls.clean_thread = None
    clean_interrupt = classmethod(clean_interrupt)
    
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
        # If session data has never been loaded then it's never been
        #   accessed: no need to delete it
        if self.loaded:
            t = datetime.timedelta(seconds = self.timeout * 60)
            expiration_time = datetime.datetime.now() + t
            self._save(expiration_time)
        
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
        
        cls = self.__class__
        if not cls.clean_thread:
            cherrypy.engine.on_stop_engine_list.append(cls.clean_interrupt)
            # Use the instance to call clean_cycle so tool config
            # can be accessed inside the method.
            cls.clean_thread = t = threading.Timer(self.clean_freq,
                                                   self.clean_cycle)
            t.start()
    
    def __getitem__(self, key):
        if not self.loaded: self.load()
        return self._data[key]
    
    def __setitem__(self, key, value):
        if not self.loaded: self.load()
        self._data[key] = value
    
    def __delitem__(self, key):
        if not self.loaded: self.load()
        del self._data[key]
    
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
    
    def _load(self):
        return self.cache.get(self.id)
    
    def _save(self, expiration_time):
        self.cache[self.id] = (self._data, expiration_time)
    
    def acquire_lock(self):
        self.locked = True
        self.locks.setdefault(self.id, threading.Semaphore()).acquire()
    
    def release_lock(self):
        self.locks[self.id].release()
        self.locked = False


class FileSession(Session):
    """ Implementation of the File backend for sessions """
    
    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    
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
        self.cursor.execute('delete from session where id=%s', (self.id,))
        pickled_data = pickle.dumps(self._data)
        self.cursor.execute(
            'insert into session (id, data, expiration_time) values (%s, %s, %s)',
            (self.id, pickled_data, expiration_time))
    
    def acquire_lock(self):
        # We use the "for update" clause to lock the row
        self.cursor.execute('select id from session where id=%s for update',
                            (self.id,))
    
    def release_lock(self):
        # We just close the cursor and that will remove the lock
        #   introduced by the "for update" clause
        self.cursor.close()
    
    def clean_up(self):
        """Clean up expired sessions."""
        self.cursor.execute('delete from session where expiration_time < %s',
                            (datetime.datetime.now(),))


# Hook functions (for CherryPy tools)

def save():
    """Save any changed session data."""
    def wrap_body(body):
        """Response.body wrapper which saves session data."""
        if isinstance(body, types.GeneratorType):
            # If the body is a generator, we have to save the data
            #   *after* the generator has been consumed
            for line in body:
                yield line
            cherrypy.session.save()
        else:
            # If the body is not a generator, we save the data
            #   before the body is returned (so we can release the lock).
            cherrypy.session.save()
            for line in body:
                yield line
    cherrypy.response.body = wrap_body(cherrypy.response.body)

def close():
    """Close the session object for this request."""
    sess = cherrypy.session
    if sess.locked:
        # If the session is still locked we release the lock
        sess.release_lock()
close.failsafe = True


_def_session = RamSession()

def init(storage_type='ram', path=None, path_header=None, name='session_id',
         timeout=60, domain=None, secure=False, locking='implicit',
         clean_freq=5, **kwargs):
    """Initialize session object (using cookies).
    
    Any additional kwargs will be bound to the new Session instance.
    """
    
    request = cherrypy.request
    
    # Check if request came with a session ID
    id = None
    if name in request.simple_cookie:
        id = request.simple_cookie[name].value
    
    if not hasattr(cherrypy, "session"):
        cherrypy.session = cherrypy._ThreadLocalProxy('session', _def_session)
    
    # Create and attach a new Session instance to cherrypy.request.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    storage_class = storage_type.title() + 'Session'
    kwargs['timeout'] = timeout
    kwargs['clean_freq'] = clean_freq
    cherrypy.serving.session = sess = globals()[storage_class](id, **kwargs)
    
    if locking == 'implicit':
        sess.acquire_lock()
    
    # Set response cookie
    cookie = cherrypy.response.simple_cookie
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


"""Session implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.request._session to store these variables.

Global variables (RAM backend only):
    - _session_lock_dict: dictionary containing the locks for all session_id
    - _session_data_holder: dictionary containing the data for all sessions

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
import thread
import threading
import types

import cherrypy

_session_last_clean_up_time = datetime.datetime.now()
_session_data_holder = {} # Needed for RAM sessions only
_session_lock_dict = {} # Needed for RAM sessions only


def generate_id():
    """Return a new session id"""
    return sha.new('%s' % random.random()).hexdigest()


def noop(data): pass

class Session:
    """A CherryPy Session object (one per request).
    
    timeout: timeout delay for the session
    locking: mechanism used to lock the session ('implicit' or 'explicit')
    storage (instance of the class implementing the backend)
    data: dictionary containing the actual session data
    id: current session ID
    expiration_time: date/time when the current session will expire
    """
    
    timeout = 60
    locking = 'explicit'
    deadlock_timeout = 30
    clean_up_delay = 5
    storage_type = 'Ram'
    storage_class = None
    cookie_name = 'session_id'
    cookie_domain = None
    cookie_secure = False
    cookie_path = None
    cookie_path_from_header = None
    
    def __init__(self):
        self.storage = None
        self.locked = False
        self.loaded = False
        self.saved = False
        
        self.generate_id = generate_id
        self.on_create = noop
        self.on_renew = noop
        self.on_delete = noop
    
    def init(self):
        # People can set their own custom class
        #   through tools.sessions.storage_class
        if self.storage_class is None:
            self.storage_class = globals()[self.storage_type.title() + 'Storage']
        self.storage = self.storage_class()
        
        now = datetime.datetime.now()
        # Check if we need to clean up old sessions
        global _session_last_clean_up_time
        clean_up_delay = datetime.timedelta(seconds = self.clean_up_delay * 60)
        if _session_last_clean_up_time + clean_up_delay < now:
            _session_last_clean_up_time = now
            # Run clean_up in other thread to avoid blocking this request
            thread.start_new_thread(self.storage.clean_up, (self,))
        
        self.data = {}
        
        if self.cookie_path is None:
            if self.cookie_path_from_header is not None:
                geth = cherrypy.request.headers.get
                self.cookie_path = geth(self.cookie_path_from_header, None)
            if self.cookie_path is None:
                self.cookie_path = '/'
        
        # Check if request came with a session ID
        if self.cookie_name in cherrypy.request.simple_cookie:
            # It did: we mark the data as needing to be loaded
            self.id = cherrypy.request.simple_cookie[self.cookie_name].value
            
            # If using implicit locking, acquire lock
            if self.locking == 'implicit':
                self.data['_id'] = self.id
                self.storage.acquire_lock()
        else:
            # No id yet
            self.id = self.generate_id()
            self.data['_id'] =  self.id
            self.on_create(self.data)
        
        # Set response cookie
        cookie = cherrypy.response.simple_cookie
        cookie[self.cookie_name] = self.id
        cookie[self.cookie_name]['path'] = self.cookie_path
        # We'd like to use the "max-age" param as
        #   http://www.faqs.org/rfcs/rfc2109.html indicates but IE doesn't
        #   save it to disk and the session is lost if people close
        #   the browser
        #   So we have to use the old "expires" ... sigh ...
        #cookie[cookie_name]['max-age'] = self.timeout * 60
        gmt_expiration_time = time.gmtime(time.time() + (self.timeout * 60))
        cookie[self.cookie_name]['expires'] = time.strftime(
                "%a, %d-%b-%Y %H:%M:%S GMT", gmt_expiration_time)
        if self.cookie_domain is not None:
            cookie[self.cookie_name]['domain'] = self.cookie_domain
        if self.cookie_secure is True:
            cookie[self.cookie_name]['secure'] = 1
    
    def save(self):
        """Save session data"""
        # If session data has never been loaded then it's never been
        #   accessed: no need to delete it
        if self.loaded:
            t = datetime.timedelta(seconds = self.timeout * 60)
            expiration_time = datetime.datetime.now() + t
            self.storage.save(self.id, self.data, expiration_time)
        
        if self.locked:
            # Always release the lock if the user didn't release it
            self.storage.release_lock()
        
        self.saved = True


class SessionDeadlockError(Exception):
    """The session could not acquire a lock after a certain time"""
    pass


class SessionNotEnabledError(Exception):
    """User forgot to set tools.sessions.on to True"""
    pass

class SessionStoragePathError(Exception):
    """User set storage_type to file but forgot to set the storage_path"""
    pass


class RamStorage:
    """ Implementation of the RAM backend for sessions """
    
    def load(self, id):
        return _session_data_holder.get(id)
    
    def save(self, id, data, expiration_time):
        _session_data_holder[id] = (data, expiration_time)
    
    def acquire_lock(self):
        sess = cherrypy.request._session
        id = cherrypy.session.id
        lock = _session_lock_dict.get(id)
        if lock is None:
            lock = threading.Lock()
            _session_lock_dict[id] = lock
        startTime = time.time()
        while True:
            if lock.acquire(False):
                break
            if time.time() - startTime > sess.deadlock_timeout:
                raise SessionDeadlockError()
            time.sleep(0.5)
        sess.locked = True
    
    def release_lock(self):
        _session_lock_dict[cherrypy.session['_id']].release()
        cherrypy.request._session.locked = False
    
    def clean_up(self, sess):
        to_be_deleted = []
        now = datetime.datetime.now()
        for id, (data, expiration_time) in _session_data_holder.iteritems():
            if expiration_time < now:
                to_be_deleted.append(id)
        for id in to_be_deleted:
            try:
                deleted_session = _session_data_holder[id]
                del _session_data_holder[id]
                sess.on_delete(deleted_session)
            except KeyError:
                # The session probably got deleted by a concurrent thread
                #   Safe to ignore this case
                pass


class FileStorage:
    """ Implementation of the File backend for sessions """
    
    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    
    def load(self, id):
        file_path = self._get_file_path(id)
        try:
            f = open(file_path, "rb")
            data = pickle.load(f)
            f.close()
            return data
        except (IOError, EOFError):
            return None
    
    def save(self, id, data, expiration_time):
        file_path = self._get_file_path(id)
        f = open(file_path, "wb")
        pickle.dump((data, expiration_time), f)
        f.close()
    
    def acquire_lock(self):
        file_path = self._get_file_path(cherrypy.session.id)
        self._lock_file(file_path + self.LOCK_SUFFIX)
        cherrypy.request._session.locked = True
    
    def release_lock(self):
        file_path = self._get_file_path(cherrypy.session.id)
        self._unlock_file(file_path + self.LOCK_SUFFIX)
        cherrypy.request._session.locked = False
    
    def clean_up(self, sess):
        storage_path = getattr(sess, "storage_path")
        if storage_path is None:
            return
        now = datetime.datetime.now()
        # Iterate over all files in the dir/ and exclude non session files
        #   and lock files
        for fname in os.listdir(storage_path):
            if (fname.startswith(self.SESSION_PREFIX)
                and not fname.endswith(self.LOCK_SUFFIX)):
                # We have a session file: try to load it and check
                #   if it's expired. If it fails, nevermind.
                file_path = os.path.join(storage_path, fname)
                try:
                    f = open(file_path, "rb")
                    data, expiration_time = pickle.load(f)
                    f.close()
                    if expiration_time < now:
                        # Session expired: deleting it
                        id = fname[len(self.SESSION_PREFIX):]
                        sess.on_delete(data)
                        os.unlink(file_path)
                except:
                    # We can't access the file ... nevermind
                    pass
    
    def _get_file_path(self, id):
        storage_path = getattr(cherrypy.request._session, "storage_path")
        if storage_path is None:
            raise SessionStoragePathError()
        fileName = self.SESSION_PREFIX + id
        file_path = os.path.join(storage_path, fileName)
        return file_path
    
    def _lock_file(self, path):
        timeout = cherrypy.request._session.deadlock_timeout
        startTime = time.time()
        while True:
            try:
                lockfd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
            except OSError:
                if time.time() - startTime > timeout:
                    raise SessionDeadlockError()
                time.sleep(0.5)
            else:
                os.close(lockfd) 
                break
    
    def _unlock_file(self, path):
        os.unlink(path)


class PostgreSQLStorage:
    """ Implementation of the PostgreSQL backend for sessions. It assumes
        a table like this:

            create table session (
                id varchar(40),
                data text,
                expiration_time timestamp
            )
    """
    
    def __init__(self):
        self.db = cherrypy.request._session.get_db()
        self.cursor = self.db.cursor()
    
    def __del__(self):
        if self.cursor:
            self.cursor.close()
        self.db.commit()
    
    def load(self, id):
        # Select session data from table
        self.cursor.execute(
            'select data, expiration_time from session where id=%s',
            (id,))
        rows = self.cursor.fetchall()
        if not rows:
            return None
        pickled_data, expiration_time = rows[0]
        # Unpickle data
        data = pickle.loads(pickled_data)
        return (data, expiration_time)
    
    def save(self, id, data, expiration_time):
        # Try to delete session if it was already there
        self.cursor.execute(
            'delete from session where id=%s',
            (id,))
        # Pickle data
        pickled_data = pickle.dumps(data)
        # Insert new session data
        self.cursor.execute(
            'insert into session (id, data, expiration_time) values (%s, %s, %s)',
            (id, pickled_data, expiration_time))
    
    def acquire_lock(self):
        # We use the "for update" clause to lock the row
        self.cursor.execute(
            'select id from session where id=%s for update',
            (cherrypy.session.id,))
    
    def release_lock(self):
        # We just close the cursor and that will remove the lock
        #   introduced by the "for update" clause
        self.cursor.close()
        self.cursor = None
    
    def clean_up(self, sess):
        now = datetime.datetime.now()
        self.cursor.execute(
            'select data from session where expiration_time < %s',
            (now,))
        rows = self.cursor.fetchall()
        for row in rows:
            sess.on_delete(row[0])
        self.cursor.execute(
            'delete from session where expiration_time < %s',
            (now,))


# Users access sessions through cherrypy.session, but we want this
#   to be thread-specific so we use a special wrapper that forwards
#   calls to cherrypy.session to a thread-specific dictionary called
#   cherrypy.request._session.data
class SessionWrapper:
    
    def __getattr__(self, name):
        sess = getattr(cherrypy.request, "_session", None)
        if sess is None:
            raise SessionNotEnabledError()
        
        # Create thread-specific dictionary if needed
        if name == 'acquire_lock':
            return sess.storage.acquire_lock
        elif name == 'release_lock':
            return sess.storage.release_lock
        elif name == 'id':
            return sess.id
        
        if not sess.loaded:
            data = sess.storage.load(sess.id)
            # data is either None or a tuple (session_data, expiration_time)
            if data is None or data[1] < datetime.datetime.now():
                # Expired session:
                # flush session data (but keep the same id)
                sess.data = {'_id': sess.id}
                if not (data is None):
                    sess.on_renew(sess.data)
            else:
                sess.data = data[0]
            sess.loaded = True

        return getattr(sess.data, name)


# The actual hook functions

def save():
    # Save the session either before or after the body is returned
    if not isinstance(cherrypy.response.body, types.GeneratorType):
        cherrypy.request._session.save()

def cleanup():
    sess = cherrypy.request._session
    if not sess.saved:
        sess.save()
    
    if sess.locked:
        # If the session is still locked we release the lock
        sess.storage.release_lock()
    if sess.storage:
        sess.storage = None

def wrap(*args, **kwargs):
    """Make a decorator for this tool."""
    def deco(f):
        def wrapper(*a, **kw):
            result = f(*a, **kw)
            save(*args, **kwargs)
            cherrypy.request.hooks.attach('on_end_request', cleanup)
            return result
        return wrapper
    return deco

def setup(conf):
    """Hook this tool into cherrypy.request using the given conf.
    
    The standard CherryPy request object will automatically call this
    method when the tool is "turned on" in config.
    """
    def wrapper():
        s = cherrypy.request._session = Session()
        for k, v in conf.iteritems():
            setattr(s, str(k), v)
        s.init()
        
        if not hasattr(cherrypy, "session"):
            cherrypy.session = SessionWrapper()
    
    cherrypy.request.hooks.attach('before_request_body', wrapper)
    cherrypy.request.hooks.attach('before_finalize', save)
    cherrypy.request.hooks.attach('on_end_request', cleanup)

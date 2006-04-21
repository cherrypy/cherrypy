"""Session implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.request._session to store these variables.

Global variables (RAM backend only):
    - cherrypy._session_lock_dict: dictionary containing the locks for all session_id
    - cherrypy._session_data_holder: dictionary containing the data for all sessions

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


def generate_id():
    """Return a new session id"""
    return sha.new('%s' % random.random()).hexdigest()


class Session:
    """A CherryPy Session object (one per request).
    
    timeout: timeout delay for the session
    locking: mechanism used to lock the session ('implicit' or 'explicit')
    storage (instance of the class implementing the backend)
    data: dictionary containing the actual session data
    id: current session ID
    expiration_time: date/time when the current session will expire
    """
    
    def __init__(self):
        conf = cherrypy.config.get
        
        self.storage = None
        self.locked = False
        self.loaded = True
        
        self.timeout = conf('session_filter.timeout', 60)
        self.locking = conf('session_filter.locking', 'explicit')
        self.on_create = conf('session_filter.on_create', lambda data: None)
        self.on_renew = conf('session_filter.on_renew', lambda data: None)
        self.on_delete = conf('session_filter.on_delete', lambda data: None)
        gen_id = conf('session_filter.generate_id', generate_id)
        self.deadlock_timeout = conf('session_filter.deadlock_timeout', 30)
        
        clean_up_delay = conf('session_filter.clean_up_delay', 5)
        clean_up_delay = datetime.timedelta(seconds = clean_up_delay * 60)
        
        storage = conf('session_filter.storage_type', 'Ram').title()
        
        # People can set their own custom class
        #   through session_filter.storage_class
        cls = conf('session_filter.storage_class', None)
        if cls is None:
            cls = globals()[storage + 'Storage']
        self.storage = cls()
        
        now = datetime.datetime.now()
        # Check if we need to clean up old sessions
        if cherrypy._session_last_clean_up_time + clean_up_delay < now:
            cherrypy._session_last_clean_up_time = now
            # Run clean_up in other thread to avoid blocking this request
            thread.start_new_thread(self.storage.clean_up, (self,))
        
        self.data = {}
        
        # Check if request came with a session ID
        cookie_name = conf('session_filter.cookie_name', 'session_id')
        cookie_domain = conf('session_filter.cookie_domain', None)
        cookie_secure = conf('session_filter.cookie_secure', False)
        cookie_path = conf('session_filter.cookie_path', None)
        if cookie_path is None:
            cookie_path_header = conf('session_filter.cookie_path_from_header', None)
            if cookie_path_header is not None:
                cookie_path = cherrypy.request.headers.get(cookie_path_header, None)
            if cookie_path is None:
                cookie_path = '/'
        if cookie_name in cherrypy.request.simple_cookie:
            # It did: we mark the data as needing to be loaded
            self.id = cherrypy.request.simple_cookie[cookie_name].value
            
            # If using implicit locking, acquire lock
            if self.locking == 'implicit':
                self.data['_id'] = self.id
                self.storage.acquire_lock()
        else:
            # No id yet
            self.id = gen_id()
            self.data['_id'] =  self.id
            self.on_create(self.data)
        
        # Set response cookie
        cookie = cherrypy.response.simple_cookie
        cookie[cookie_name] = self.id
        cookie[cookie_name]['path'] = cookie_path
        # We'd like to use the "max-age" param as
        #   http://www.faqs.org/rfcs/rfc2109.html indicates but IE doesn't
        #   save it to disk and the session is lost if people close
        #   the browser
        #   So we have to use the old "expires" ... sigh ...
        #cookie[cookie_name]['max-age'] = self.timeout * 60
        gmt_expiration_time = time.gmtime(time.time() + (self.timeout * 60))
        cookie[cookie_name]['expires'] = time.strftime(
                "%a, %d-%b-%Y %H:%M:%S GMT", gmt_expiration_time)
        if cookie_domain is not None:
            cookie[cookie_name]['domain'] = cookie_domain
        if cookie_secure is True:
            cookie[cookie_name]['secure'] = 1
    
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


class SessionDeadlockError(Exception):
    """The session could not acquire a lock after a certain time"""
    pass


class SessionNotEnabledError(Exception):
    """User forgot to set session_filter.on to True"""
    pass

class SessionStoragePathNotConfiguredError(Exception):
    """User set storage_type to file but forgot to set the storage_path"""
    pass


class SessionFilter(basefilter.BaseFilter):
    
    def before_request_body(self):
        if cherrypy.config.get('session_filter.on', False):
            cherrypy.request._session = Session()
    
    def before_finalize(self):
        sess = getattr(cherrypy.request, "_session", None)
        if sess:
            # Make a wrapper around the body in order to save the session
            #   either before or after the body is returned
            def save_session_data(body, sess):
                if isinstance(body, types.GeneratorType):
                    for line in body:
                        yield line
                    sess.save()
                else:
                    sess.save()
                    for line in body:
                        yield line
            cherrypy.response.body = save_session_data(cherrypy.response.body, sess)
    
    def on_end_request(self):
        sess = getattr(cherrypy.request, "_session", None)
        if sess:
            if sess.locked:
                # If the session is still locked we release the lock
                sess.storage.release_lock()
            if sess.storage:
                sess.storage = None


class RamStorage:
    """ Implementation of the RAM backend for sessions """
    
    def load(self, id):
        return cherrypy._session_data_holder.get(id)
    
    def save(self, id, data, expiration_time):
        cherrypy._session_data_holder[id] = (data, expiration_time)
    
    def acquire_lock(self):
        sess = cherrypy.request._session
        id = cherrypy.session.id
        lock = cherrypy._session_lock_dict.get(id)
        if lock is None:
            lock = threading.Lock()
            cherrypy._session_lock_dict[id] = lock
        startTime = time.time()
        while True:
            if lock.acquire(False):
                break
            if time.time() - startTime > sess.deadlock_timeout:
                raise SessionDeadlockError()
            time.sleep(0.5)
        sess.locked = True
    
    def release_lock(self):
        sess = cherrypy.request._session
        id = cherrypy.session['_id']
        cherrypy._session_lock_dict[id].release()
        sess.locked = False
    
    def clean_up(self, sess):
        to_be_deleted = []
        now = datetime.datetime.now()
        for id, (data, expiration_time) in cherrypy._session_data_holder.iteritems():
            if expiration_time < now:
                to_be_deleted.append(id)
        for id in to_be_deleted:
            try:
                deleted_session = cherrypy._session_data_holder[id]
                del cherrypy._session_data_holder[id]
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
        sess = cherrypy.request._session
        file_path = self._get_file_path(cherrypy.session.id)
        lock_file_path = file_path + self.LOCK_SUFFIX
        self._lock_file(lock_file_path)
        sess.locked = True
    
    def release_lock(self):
        sess = cherrypy.request._session
        file_path = self._get_file_path(cherrypy.session.id)
        lock_file_path = file_path + self.LOCK_SUFFIX
        self._unlock_file(lock_file_path)
        sess.locked = False
    
    def clean_up(self, sess):
        storage_path = cherrypy.config.get('session_filter.storage_path')
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
        storage_path = cherrypy.config.get('session_filter.storage_path')
        if storage_path is None:
            raise SessionStoragePathNotConfiguredError()
        fileName = self.SESSION_PREFIX + id
        file_path = os.path.join(storage_path, fileName)
        return file_path
    
    def _lock_file(self, path):
        sess = cherrypy.request._session
        startTime = time.time()
        while True:
            try:
                lockfd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
            except OSError:
                if time.time() - startTime > sess.deadlock_timeout:
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
        self.db = cherrypy.config.get('session_filter.get_db')()
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


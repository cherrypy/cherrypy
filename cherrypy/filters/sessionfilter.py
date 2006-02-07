""" Session implementation for CherryPy.
We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a dummy object called
cherrypy.request._session (sess) to store these variables.

Variables used to store config options:
    - sess.session_timeout: timeout delay for the session
    - sess.session_locking: mechanism used to lock the session ('implicit' or 'explicit')

Variables used to store temporary variables:
    - sess.session_storage (instance of the class implementing the backend)


Variables used to store the session for the current request:
    - sess.session_data: dictionary containing the actual session data
    - sess.session_id: current session ID
    - sess.expiration_time: date/time when the current session will expire

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
import threading
import types

import cherrypy
import basefilter


class EmptyClass:
    """ An empty class """
    pass


class SessionDeadlockError(Exception):
    """ The session could not acquire a lock after a certain time """
    pass


class SessionNotEnabledError(Exception):
    """ User forgot to set session_filter.on to True """
    pass


class SessionFilter(basefilter.BaseFilter):

    def on_start_resource(self):
        cherrypy.request._session = EmptyClass()
    
    def before_request_body(self):
        conf = cherrypy.config.get
        
        sess = cherrypy.request._session
        # Dont enable session if session_filter is off or if this is a
        #   request for static data
        if ((not conf('session_filter.on', False))
              or conf('static_filter.on', False)):
            sess.session_storage = None
            return

        sess.locked = False # Not locked by default
        sess.to_be_loaded = True
        
        # Read config options
        sess.session_timeout = conf('session_filter.timeout', 60)
        sess.session_locking = conf('session_filter.locking', 'explicit')
        sess.on_create_session = conf('session_filter.on_create_session',
                lambda data: None)
        sess.on_delete_session = conf('session_filter.on_delete_session',
                lambda data: None)
        sess.generate_session_id = conf('session_filter.on_delete_session',
                generate_session_id)
        
        clean_up_delay = conf('session_filter.clean_up_delay', 5)
        clean_up_delay = datetime.timedelta(seconds = clean_up_delay * 60)
        
        cookie_name = conf('session_filter.cookie_name', 'session_id')
        cookie_domain = conf('session_filter.cookie_domain', None)
        cookie_secure = conf('session_filter.cookie_secure', False)
        cookie_path = conf('session_filter.cookie_path', None)

        if cookie_path is None:
            cookie_path_header = conf('session_filter.cookie_path_from_header', None)
            if cookie_path_header is not None:
                cookie_path = cherrypy.request.headerMap.get(cookie_path_header, None)
            if cookie_path is None:
                cookie_path = '/'

        sess.deadlock_timeout = conf('session_filter.deadlock_timeout', 30)
        
        storage = conf('session_filter.storage_type', 'Ram')
        storage = storage[0].upper() + storage[1:]
        
        # People can set their own custom class
        #   through session_filter.storage_class
        sess.session_storage = conf('session_filter.storage_class', None)
        if sess.session_storage is None:
            sess.session_storage = globals()[storage + 'Storage']()
        else:
            sess.session_storage = sess.session_storage()
        
        # Check if we need to clean up old sessions
        if cherrypy._session_last_clean_up_time + clean_up_delay < \
                datetime.datetime.now():
            sess.session_storage.clean_up()
        
        # Check if request came with a session ID
        if cookie_name in cherrypy.request.simple_cookie:
            # It did: we mark the data as needing to be loaded
            sess.session_id = cherrypy.request.simple_cookie[cookie_name].value
            
            # If using implicit locking, acquire lock
            if sess.session_locking == 'implicit':
                sess.session_data = {'_id': sess.session_id}
                sess.session_storage.acquire_lock()
            
            sess.to_be_loaded = True

        else:
            # No session_id yet
            sess.session_id = sess.generate_session_id()
            sess.session_data = {'_id': sess.session_id}
            sess.on_create_session(sess.session_data)
        # Set response cookie
        cookie = cherrypy.response.simple_cookie
        cookie[cookie_name] = sess.session_id
        cookie[cookie_name]['path'] = cookie_path
        cookie[cookie_name]['max-age'] = sess.session_timeout * 60
        cookie[cookie_name]['version'] = 1
        if cookie_domain is not None:
            cookie[cookie_name]['domain'] = cookie_domain
        if cookie_secure is True:
            cookie[cookie_name]['secure'] = 1
    
    def before_finalize(self):
        def saveData(body, sess):
            # If the body is a generator, we have to save the data
            #   *after* the generator has been consumed
            if isinstance(body, types.GeneratorType):
                for line in body:
                    yield line
            
            # Save session data
            if sess.to_be_loaded is False:
                t = datetime.timedelta(seconds = sess.session_timeout * 60)
                expiration_time = datetime.datetime.now() + t
                sess.session_storage.save(sess.session_id,
                        sess.session_data, expiration_time)
            else:
                # If session data has never been loaded then it's never been
                #   accesses: not need to delete it
                pass
            if sess.locked:
                # Always release the lock if the user didn't release it
                sess.session_storage.release_lock()
            
            # If the body is not a generator, we save the data
            #   before the body is returned
            if not isinstance(body, types.GeneratorType):
                for line in body:
                    yield line
        
        sess = cherrypy.request._session
        if not getattr(sess, 'session_storage', None):
            # Sessions are not enabled: do nothing
            return
        
        # Make a wrapper around the body in order to save the session
        #   either before or after the body is returned
        cherrypy.response.body = saveData(cherrypy.response.body, sess)
    
    def on_end_request(self):
        sess = cherrypy.request._session
        if not getattr(sess, 'session_storage', None):
            # Sessions are not enabled: do nothing
            return
        if getattr(sess, 'locked', None):
            # If the session is still locked we release the lock
            sess.session_storage.release_lock()
        if getattr(sess, 'session_storage', None):
            del sess.session_storage


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
    
    def clean_up(self):
        sess = cherrypy.request._session
        to_be_deleted = []
        now = datetime.datetime.now()
        for id, (data, expiration_time) in cherrypy._session_data_holder.iteritems():
            if expiration_time < now:
                to_be_deleted.append(id)
        for id in to_be_deleted:
            try:
                deleted_session = cherrypy._session_data_holder[id]
                del cherrypy._session_data_holder[id]
                sess.on_delete_session(deleted_session)
            except KeyError:
                # The session probably got deleted by a concurrent thread
                #   Safe to ignore this case
                pass


class FileStorage:
    """ Implementation of the File backend for sessions """
    
    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    
    def load(self, id):
        filePath = self._getFilePath(id)
        try:
            f = open(filePath, "rb")
            data = pickle.load(f)
            f.close()
            return data
        except (IOError, EOFError):
            return None
    
    def save(self, id, data, expiration_time):
        filePath = self._getFilePath(id)
        f = open(filePath, "wb")
        pickle.dump((data, expiration_time), f)
        f.close()
    
    def acquire_lock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session.id)
        lockFilePath = filePath + self.LOCK_SUFFIX
        self._lockFile(lockFilePath)
        sess.locked = True
    
    def release_lock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session.id)
        lockFilePath = filePath + self.LOCK_SUFFIX
        self._unlockFile(lockFilePath)
        sess.locked = False
    
    def clean_up(self):
        sess = cherrypy.request._session
        storagePath = cherrypy.config.get('session_filter.storage_path')
        now = datetime.datetime.now()
        # Iterate over all files in the dir/ and exclude non session files
        #   and lock files
        for fname in os.listdir(storagePath):
            if (fname.startswith(self.SESSION_PREFIX)
                and not fname.endswith(self.LOCK_SUFFIX)):
                # We have a session file: try to load it and check
                #   if it's expired. If it fails, nevermind.
                filePath = os.path.join(storagePath, fname)
                try:
                    f = open(filePath, "rb")
                    data, expiration_time = pickle.load(f)
                    f.close()
                    if expiration_time < now:
                        # Session expired: deleting it
                        id = fname[len(self.SESSION_PREFIX):]
                        sess.on_delete_session(data)
                        os.unlink(filePath)
                except:
                    # We can't access the file ... nevermind
                    pass
    
    def _getFilePath(self, id):
        storagePath = cherrypy.config.get('session_filter.storage_path')
        fileName = self.SESSION_PREFIX + id
        filePath = os.path.join(storagePath, fileName)
        return filePath
    
    def _lockFile(self, path):
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
    
    def _unlockFile(self, path):
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
    
    def clean_up(self):
        sess = cherrypy.request._session
        now = datetime.datetime.now()
        self.cursor.execute(
            'select data from session where expiration_time < %s',
            (now,))
        rows = self.cursor.fetchall()
        for row in rows:
            sess.on_delete_session(row[0])
        self.cursor.execute(
            'delete from session where expiration_time < %s',
            (now,))


def generate_session_id():
    """ Return a new session_id """
    return sha.new('%s' % random.random()).hexdigest()


# Users access sessions through cherrypy.session, but we want this
#   to be thread-specific so we use a special wrapper that forwards
#   calls to cherrypy.session to a thread-specific dictionary called
#   cherrypy.request._session.session_data
class SessionWrapper:
    
    def __getattr__(self, name):
        sess = cherrypy.request._session
        if sess.session_storage is None:
            raise SessionNotEnabledError()
        # Create thread-specific dictionary if needed
        session_data = getattr(sess, 'session_data', None)
        if session_data is None:
            sess.session_data = {}
        if name == 'acquire_lock':
            return sess.session_storage.acquire_lock
        elif name == 'release_lock':
            return sess.session_storage.release_lock
        elif name == 'id':
            return sess.session_id

        if sess.to_be_loaded:
            data = sess.session_storage.load(sess.session_id)
            # data is either None or a tuple (session_data, expiration_time)
            if data is None or data[1] < datetime.datetime.now():
                # Expired session:
                # flush session data (but keep the same session_id)
                sess.session_data = {'_id': sess.session_id}
            else:
                sess.session_data = data[0]
            sess.to_be_loaded = False

        return getattr(sess.session_data, name)


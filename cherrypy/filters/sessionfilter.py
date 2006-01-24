""" Session implementation for CherryPy.
We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a dummy object called
cherrypy.request._session (sess) to store these variables.

Variables used to store config options:
    - sess.sessionTimeout: timeout delay for the session
    - sess.sessionLocking: mechanism used to lock the session ('implicit' or 'explicit')

Variables used to store temporary variables:
    - sess.sessionStorage (instance of the class implementing the backend)


Variables used to store the session for the current request:
    - sess.sessionData: dictionary containing the actual session data
    - sess.sessionID: current session ID
    - sess.expirationTime: date/time when the current session will expire

Global variables (RAM backend only):
    - cherrypy._session_lock_dict: dictionary containing the locks for all sessionIDs
    - cherrypy._sessionHolder: dictionary containing the data for all sessions

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
        now = datetime.datetime.now()
        # Dont enable session if session_filter is off or if this is a
        #   request for static data
        if ((not conf('session_filter.on', False))
              or conf('static_filter.on', False)):
            sess.sessionStorage = None
            return
        
        sess.locked = False # Not locked by default
        
        # Read config options
        sess.sessionTimeout = conf('session_filter.timeout', 60)
        sess.sessionLocking = conf('session_filter.locking', 'explicit')
        sess.onCreateSession = conf('session_filter.on_create_session',
                lambda data: None)
        sess.onDeleteSession = conf('session_filter.on_delete_session',
                lambda data: None)
        sess.generate_session_id = conf('session_filter.on_delete_session',
                generate_session_id)
        
        cleanUpDelay = conf('session_filter.clean_up_delay', 5)
        cleanUpDelay = datetime.timedelta(seconds = cleanUpDelay * 60)
        
        cookieName = conf('session_filter.cookie_name', 'sessionID')
        cookieDomain = conf('session_filter.cookie_domain', None)
        cookieSecure = conf('session_filter.cookie_secure', False)
        cookiePath = conf('session_filter.cookie_path', None)

        if cookiePath is None:
            cookiePathHeader = conf('session_filter.cookie_path_from_header', None)
            if cookiePathHeader is not None:
                cookiePath = cherrypy.request.headerMap.get(cookiePathHeader, None)
            if cookiePath is None:
                cookiePath = '/'

        sess.deadlockTimeout = conf('session_filter.deadlock_timeout', 30)
        
        storage = conf('session_filter.storage_type', 'Ram')
        storage = storage[0].upper() + storage[1:]
        
        # People can set their own custom class
        #   through session_filter.storage_class
        sess.sessionStorage = conf('session_filter.storage_class', None)
        if sess.sessionStorage is None:
            sess.sessionStorage = globals()[storage + 'Storage']()
        else:
            sess.sessionStorage = sess.sessionStorage()
        
        # Check if we need to clean up old sessions
        if cherrypy._session_last_clean_up_time + cleanUpDelay < now:
            sess.sessionStorage.clean_up()
        
        # Check if request came with a session ID
        if cookieName in cherrypy.request.simpleCookie:
            # It did: we try to load the session data
            sess.sessionID = cherrypy.request.simpleCookie[cookieName].value
            
            # If using implicit locking, acquire lock
            if sess.sessionLocking == 'implicit':
                sess.sessionData = {'_id': sess.sessionID}
                sess.sessionStorage.acquire_lock()
            
            data = sess.sessionStorage.load(sess.sessionID)
            # data is either None or a tuple (sessionData, expirationTime)
            if data is None or data[1] < now:
                # Expired session:
                # flush session data (but keep the same sessionID)
                sess.sessionData = {'_id': sess.sessionID}
            else:
                sess.sessionData = data[0]
        else:
            # No sessionID yet
            sess.sessionID = sess.generate_session_id()
            sess.sessionData = {'_id': sess.sessionID}
            sess.onCreateSession(sess.sessionData)
        # Set response cookie
        cookie = cherrypy.response.simpleCookie
        cookie[cookieName] = sess.sessionID
        cookie[cookieName]['path'] = cookiePath
        cookie[cookieName]['max-age'] = sess.sessionTimeout * 60
        cookie[cookieName]['version'] = 1
        if cookieDomain is not None:
            cookie[cookieName]['domain'] = cookieDomain
        if cookieSecure is True:
            cookie[cookieName]['secure'] = 1
    
    def before_finalize(self):
        def saveData(body, sess):
            # If the body is a generator, we have to save the data
            #   *after* the generator has been consumed
            if isinstance(body, types.GeneratorType):
                for line in body:
                    yield line
            
            # Save session data
            t = datetime.timedelta(seconds = sess.sessionTimeout * 60)
            expirationTime = datetime.datetime.now() + t
            sess.sessionStorage.save(sess.sessionID, sess.sessionData,
                                     expirationTime)
            if sess.locked:
                # Always release the lock if the user didn't release it
                sess.sessionStorage.release_lock()
            
            # If the body is not a generator, we save the data
            #   before the body is returned
            if not isinstance(body, types.GeneratorType):
                for line in body:
                    yield line
        
        sess = cherrypy.request._session
        if not getattr(sess, 'sessionStorage', None):
            # Sessions are not enabled: do nothing
            return
        
        # Make a wrapper around the body in order to save the session
        #   either before or after the body is returned
        cherrypy.response.body = saveData(cherrypy.response.body, sess)
    
    def on_end_request(self):
        sess = cherrypy.request._session
        if not getattr(sess, 'sessionStorage', None):
            # Sessions are not enabled: do nothing
            return
        if getattr(sess, 'locked', None):
            # If the session is still locked we release the lock
            sess.sessionStorage.release_lock()
        if getattr(sess, 'sessionStorage', None):
            del sess.sessionStorage


class RamStorage:
    """ Implementation of the RAM backend for sessions """
    
    def load(self, id):
        return cherrypy._session_data_holder.get(id)
    
    def save(self, id, data, expirationTime):
        cherrypy._session_data_holder[id] = (data, expirationTime)
    
    def acquire_lock(self):
        sess = cherrypy.request._session
        id = cherrypy.session['_id']
        lock = cherrypy._session_lock_dict.get(id)
        if lock is None:
            lock = threading.Lock()
            cherrypy._session_lock_dict[id] = lock
        startTime = time.time()
        while True:
            if lock.acquire(False):
                break
            if time.time() - startTime > sess.deadlockTimeout:
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
        toBeDeleted = []
        now = datetime.datetime.now()
        for id, (data, expirationTime) in cherrypy._session_data_holder.iteritems():
            if expirationTime < now:
                toBeDeleted.append(id)
        for id in toBeDeleted:
            sess.onDeleteSession(cherrypy._session_data_holder[id])
            del cherrypy._session_data_holder[id]


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
        except IOError:
            return None
    
    def save(self, id, data, expirationTime):
        filePath = self._getFilePath(id)
        f = open(filePath, "wb")
        pickle.dump((data, expirationTime), f)
        f.close()
    
    def acquire_lock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session['_id'])
        lockFilePath = filePath + self.LOCK_SUFFIX
        self._lockFile(lockFilePath)
        sess.locked = True
    
    def release_lock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session['_id'])
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
                    data, expirationTime = pickle.load(f)
                    f.close()
                    if expirationTime < now:
                        # Session expired: deleting it
                        id = fname[len(self.SESSION_PREFIX):]
                        sess.onDeleteSession(data)
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
                if time.time() - startTime > sess.deadlockTimeout:
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
        pickled_data, expirationTime = rows[0]
        # Unpickle data
        data = pickle.loads(pickled_data)
        return (data, expirationTime)
    
    def save(self, id, data, expirationTime):
        # Try to delete session if it was already there
        self.cursor.execute(
            'delete from session where id=%s',
            (id,))
        # Pickle data
        pickled_data = pickle.dumps(data)
        # Insert new session data
        self.cursor.execute(
            'insert into session (id, data, expiration_time) values (%s, %s, %s)',
            (id, pickled_data, expirationTime))
    
    def acquire_lock(self):
        # We use the "for update" clause to lock the row
        self.cursor.execute(
            'select id from session where id=%s for update',
            (cherrypy.session['_id'],))
    
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
            sess.onDeleteSession(row[0])
        self.cursor.execute(
            'delete from session where expiration_time < %s',
            (now,))


def generate_session_id():
    """ Return a new sessionID """
    return sha.new('%s' % random.random()).hexdigest()


# Users access sessions through cherrypy.session, but we want this
#   to be thread-specific so we use a special wrapper that forwards
#   calls to cherrypy.session to a thread-specific dictionary called
#   cherrypy.request._session.sessionData
class SessionWrapper:
    
    def __getattr__(self, name):
        sess = cherrypy.request._session
        if sess.sessionStorage is None:
            raise SessionNotEnabledError()
        # Create thread-specific dictionary if needed
        sess.sessionData = getattr(sess, 'sessionData', {})
        if name == 'acquire_lock':
            return sess.sessionStorage.acquire_lock
        elif name == 'release_lock':
            return sess.sessionStorage.release_lock
        return getattr(sess.sessionData, name)


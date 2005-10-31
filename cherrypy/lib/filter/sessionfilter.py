"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

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
    - cherrypy._sessionLockDict: dictionary containing the locks for all sessionIDs
    - cherrypy._sessionHolder: dictionary containing the data for all sessions

"""

import datetime
import os
import pickle
import random
import sha
import StringIO
import time
import threading
import types

import basefilter


class EmptyClass:
    """ An empty class """
    pass


class SessionDeadlockError(Exception):
    """ The session could not acquire a lock after a certain time """
    pass


class SessionNotEnabledError(Exception):
    """ User forgot to set sessionFilter.on to True """
    pass


class SessionFilter(basefilter.BaseFilter):
    
    def beforeRequestBody(self):
        # We have to dynamically import cherrypy because Python can't handle
        #   circular module imports :-(
        global cherrypy
        import cherrypy
        conf = cherrypy.config.get
        
        cherrypy.request._session = EmptyClass()
        sess = cherrypy.request._session
        sess.toBeCleaned = True
        now = datetime.datetime.now()
        # Dont enable session if sessionFilter is off or if this is a
        #   request for static data
        if ((not conf('sessionFilter.on', False))
              or conf('staticFilter.on', False)):
            sess.sessionStorage = None
            return
        
        sess.locked = False # Not locked by default
        
        # Read config options
        sess.sessionTimeout = conf('sessionFilter.timeout', 60)
        sess.sessionLocking = conf('sessionFilter.locking', 'explicit')
        sess.onCreateSession = conf('sessionFilter.onCreateSession',
                                    lambda data: None)
        sess.onDeleteSession = conf('sessionFilter.onDeleteSession',
                                    lambda data: None)
        
        cleanUpDelay = conf('sessionFilter.cleanUpDelay', 5)
        cleanUpDelay = datetime.timedelta(seconds = cleanUpDelay * 60)
        
        cookieName = conf('sessionFilter.cookieName', 'sessionID')
        sess.deadlockTimeout = conf('sessionFilter.deadlockTimeout', 30)
        
        storage = conf('sessionFilter.storageType', 'Ram')
        storage = storage[0].upper() + storage[1:]
        
        # People can set their own custom class
        #   through sessionFilter.storageClass
        sess.sessionStorage = conf('sessionFilter.storageClass', None)
        if sess.sessionStorage is None:
            sess.sessionStorage = globals()[storage + 'Storage']()
        else:
            sess.sessionStorage = sess.sessionStorage()
        
        # Check if we need to clean up old sessions
        if cherrypy._sessionLastCleanUpTime + cleanUpDelay < now:
            sess.sessionStorage.cleanUp()
        
        # Check if request came with a session ID
        if cookieName in cherrypy.request.simpleCookie:
            # It did: we try to load the session data
            sess.sessionID = cherrypy.request.simpleCookie[cookieName].value
            
            # If using implicit locking, acquire lock
            if sess.sessionLocking == 'implicit':
                sess.sessionData = {'_id': sess.sessionID}
                sess.sessionStorage.acquireLock()
            
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
            sess.sessionID = generateSessionID()
            sess.sessionData = {'_id': sess.sessionID}
            sess.onCreateSession(sess.sessionData)
        # Set response cookie
        cookie = cherrypy.response.simpleCookie
        cookie[cookieName] = sess.sessionID
        cookie[cookieName]['path'] = '/'
        cookie[cookieName]['max-age'] = sess.sessionTimeout * 60
        cookie[cookieName]['version'] = 1
    
    def beforeFinalize(self):
        def saveData(body, sess):
            try:
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
                    sess.sessionStorage.releaseLock()
                
                # If the body is not a generator, we save the data
                #   before the body is returned
                if not isinstance(body, types.GeneratorType):
                    for line in body:
                        yield line
            except:
                # Can't use try/finally because of yield
                self._clean()
                raise
            self._clean()
        
        sess = cherrypy.request._session
        if not getattr(sess, 'sessionStorage', None):
            # Sessions are not enabled: do nothing
            return
        
        # Make a wrapper around the body in order to save the session
        #   either before or after the body is returned
        cherrypy.response.body = saveData(cherrypy.response.body, sess)
        sess.toBeCleaned = False

    def onEndResource(self):
        # If RequestHandled is raised, beforeFinalize and afterErrorResponse
        #   are not called, so we release the session here
        sess = cherrypy.request._session
        if sess.toBeCleaned:
            self._clean()

    def afterErrorResponse(self):
        self._clean()
    
    def _clean(self):
        sess = cherrypy.request._session
        if not getattr(sess, 'sessionStorage', None):
            # Sessions are not enabled: do nothing
            return
        if getattr(sess, 'locked', None):
            # If the session is still locked we release the lock
            sess.sessionStorage.releaseLock()
        if getattr(sess, 'sessionStorage', None):
            del sess.sessionStorage


class RamStorage:
    """ Implementation of the RAM backend for sessions """
    
    def load(self, id):
        return cherrypy._sessionDataHolder.get(id)
    
    def save(self, id, data, expirationTime):
        cherrypy._sessionDataHolder[id] = (data, expirationTime)
    
    def acquireLock(self):
        sess = cherrypy.request._session
        id = cherrypy.session['_id']
        lock = cherrypy._sessionLockDict.get(id)
        if lock is None:
            lock = threading.Lock()
            cherrypy._sessionLockDict[id] = lock
        startTime = time.time()
        while True:
            if lock.acquire(False):
                break
            if time.time() - startTime > sess.deadlockTimeout:
                raise SessionDeadlockError()
            time.sleep(0.5)
        sess.locked = True
    
    def releaseLock(self):
        sess = cherrypy.request._session
        id = cherrypy.session['_id']
        cherrypy._sessionLockDict[id].release()
        sess.locked = False
    
    def cleanUp(self):
        sess = cherrypy.request._session
        toBeDeleted = []
        now = datetime.datetime.now()
        for id, (data, expirationTime) in cherrypy._sessionDataHolder.iteritems():
            if expirationTime < now:
                toBeDeleted.append(id)
        for id in toBeDeleted:
            sess.onDeleteSession(cherrypy._sessionDataHolder[id])
            del cherrypy._sessionDataHolder[id]


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
    
    def acquireLock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session['_id'])
        lockFilePath = filePath + self.LOCK_SUFFIX
        self._lockFile(lockFilePath)
        sess.locked = True
    
    def releaseLock(self):
        sess = cherrypy.request._session
        filePath = self._getFilePath(cherrypy.session['_id'])
        lockFilePath = filePath + self.LOCK_SUFFIX
        self._unlockFile(lockFilePath)
        sess.locked = False
    
    def cleanUp(self):
        sess = cherrypy.request._session
        storagePath = cherrypy.config.get('sessionFilter.storagePath')
        now = datetime.datetime.now()
        # Iterate over all files in the dir/ and exclude non session files
        #   and lock files
        for fname in os.listdir(storagePath):
            if (fname.startswith(self.SESSION_PREFIX)
                and not fname.endswith(self.LOCK_SUFFIX)):
                # We have a session file: lock it, load it and check
                #   if it's expired
                filePath = os.path.join(storagePath, fname)
                lockFilePath = filePath + self.LOCK_SUFFIX
                self._lockFile(lockFilePath)
                try:
                    f = open(filePath, "rb")
                    data, expirationTime = pickle.load(f)
                    f.close()
                    if expirationTime < now:
                        # Session expired: deleting it
                        id = fname[len(self.SESSION_PREFIX):]
                        sess.onDeleteSession(data)
                        os.unlink(filePath)
                except IOError:
                    # We can't access the file ... nevermind
                    pass
                self._unlockFile(lockFilePath)
    
    def _getFilePath(self, id):
        storagePath = cherrypy.config.get('sessionFilter.storagePath')
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
        self.db = cherrypy.config.get('sessionFilter.getDB')()
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
        data, expirationTime = rows[0]
        # Unpickle data
        f = StringIO.StringIO(data)
        data = pickle.load(f)
        return (data, expirationTime)
    
    def save(self, id, data, expirationTime):
        # Try to delete session if it was already there
        self.cursor.execute(
            'delete from session where id=%s',
            (id,))
        # Pickle data
        f = StringIO.StringIO()
        pickle.dump(data, f)
        # Insert new session data
        self.cursor.execute(
            'insert into session (id, data, expiration_time) values (%s, %s, %s)',
            (id, f.getvalue(), expirationTime))
    
    def acquireLock(self):
        # We use the "for update" clause to lock the row
        self.cursor.execute(
            'select id from session where id=%s for update',
            (cherrypy.session['_id'],))
    
    def releaseLock(self):
        # We just close the cursor and that will remove the lock
        #   introduced by the "for update" clause
        self.cursor.close()
        self.cursor = None
    
    def cleanUp(self):
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


def generateSessionID():
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
        if name == 'acquireLock':
            return sess.sessionStorage.acquireLock
        elif name == 'releaseLock':
            return sess.sessionStorage.releaseLock
        return getattr(sess.sessionData, name)


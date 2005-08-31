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
We use cherrypy.threadData (td) to store some convenient variables as
well as data about the session for the current request.

Variables used to store config options:
    - td._sessionTimeout: timeout delay for the session
    - td._sessionLocking: mechanism used to lock the session ('implicit' or 'explicit')

Variables used to store temporary variables:
    - td._sessionStorage (instance of the class implementing the backend)


Variables used to store the session for the current request:
    - td._sessionData: dictionnary containing the actual session data
    - td._sessionID: current session ID
    - td._expirationTime: time when the current session will expire

Global variables (RAM backend only):
    - cherrypy._sessionLockDict: dictionnary containing the locks for all sessionIDs
    - cherrypy._sessionHolder: dictionnary containing the data for all sessions

"""

import sha
import os
import pickle
import random
import threading
import time

import basefilter

# TODO: Clean up old sessions
# TODO: Release stale locks after a certain time

class SessionFilter(basefilter.BaseFilter):
    def beforeRequestBody(self):
        # We have to dynamically import cherrypy because Python can't handle
        #   circular module imports :-(
        global cherrypy, td
        import cherrypy
        td = cherrypy.threadData
        if not cherrypy.config.get('sessionFilter.on', False):
            td._sessionStorage = None
            return

        # Read config options
        td._sessionTimeout = \
            cherrypy.config.get('sessionFilter.timeout', 60)

        td._sessionLocking = \
            cherrypy.config.get('sessionFilter.locking', 'implicit')

        cookieName = \
            cherrypy.config.get('sessionFilter.cookieName', 'sessionID')

        storage = cherrypy.config.get('sessionFilter.storageType', 'Ram')
        storage = storage.capitalize()
        # TODO: support custom storage types
        td._sessionStorage = globals()[storage + 'Storage']()

        # Check if request came with a session ID
        if cookieName in cherrypy.request.simpleCookie:
            # It did: we try to load the session data
            td._sessionID = cherrypy.request.simpleCookie[cookieName].value
            data = td._sessionStorage.load(td._sessionID)
            # data is either None or a tuple (sessionData, expirationTime)
            if data is None or data[1] < time.time():
                # Expired session: flush session data (but keep the same
                #   sessionID)
                td._sessionData = {}
            else:
                td._sessionData = data[0]
        else:
            # No sessionID yet
            td._sessionID = generateSessionID()
            td._sessionData = {}
        td._sessionData['_id'] = td._sessionID
        # Set response cookie
        cherrypy.response.simpleCookie[cookieName] = td._sessionID
        cherrypy.response.simpleCookie[cookieName]['path'] = '/'
        cherrypy.response.simpleCookie[cookieName]['max-age'] = \
            td._sessionTimeout * 60
        cherrypy.response.simpleCookie[cookieName]['version'] = 1

        # If using implicit locking, acquire lock
        if td._sessionLocking == 'implicit':
            td._sessionStorage.acquireLock()

    def beforeFinalize(self):
        if not td._sessionStorage:
            return
        # Save session data
        expirationTime = time.time() + td._sessionTimeout * 60
        td._sessionStorage.save(
                td._sessionID, (td._sessionData, expirationTime))
        try:
            # Always try to release the lock at the end
            td._sessionStorage.releaseLock()
        except:
            pass

    def onEndResource(self):
        try:
            # Try to release the lock one more time at the very end (in
            #   case there was an error while processing the request
            #   or something)
            td._sessionStorage.releaseLock()
        except:
            pass

class RamStorage:
    """ Implementation of the RAM backend for sessions """
    def __init__(self):
        try:
            cherrypy._sessionDataHolder
        except:
            cherrypy._sessionDataHolder = {}
        try:
            cherrypy._sessionLockDict
        except:
            cherrypy._sessionLockDict = {}

    def load(self, id):
        return cherrypy._sessionDataHolder.get(id)
    def save(self, id, data):
        cherrypy._sessionDataHolder[id] = data
    def acquireLock(self):
        id = cherrypy.session['_id']
        lock = cherrypy._sessionLockDict.get(id)
        if lock is None:
            lock = threading.Lock()
            cherrypy._sessionLockDict[id] = lock
        lock.acquire()
    def releaseLock(self):
        id = cherrypy.session['_id']
        cherrypy._sessionLockDict[id].release()

class FileStorage:
    """ Implementation of the File backend for sessions """
    def load(self, id):
        filePath = self._getFilePath(id)
        try:
            f = open(filePath, "rb")
            data = pickle.load(f)
            f.close()
            return data
        except:
            return (None, None)
    def save(self, id, data):
        filePath = self._getFilePath(id)
        f = open(filePath, "wb")
        pickle.dump(data, f)
        f.close()
    def acquireLock(self):
        # Use the OS to acquire a lock on the file.
        # This means that if we have multiple CP processes it'll still
        # work fine
        filePath = self._getFilePath(cherrypy.session['_id'])
        lockFilePath = filePath + '.lock'
        while True:
            try:
                lockfd = os.open(lockFilePath, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
            except OSError:
                pass
            else:
                os.close(lockfd) 
                break

    def releaseLock(self):
        filePath = self._getFilePath(cherrypy.session['_id'])
        lockFilePath = filePath + '.lock'
        os.unlink(lockFilePath)

    def _getFilePath(self, id):
        storagePath = cherrypy.config.get('sessionFilter.storagePath')
        fileName = 'sessionFile-' + id
        filePath = os.path.join(storagePath, fileName)
        return filePath


def generateSessionID():
        """ Function to return a new sessionID """
        return sha.new('%s' % random.random()).hexdigest()

# Users access sessions through cherrypy.session, but we want this
#   to be thread-specific so we use a special wrapper that forwards
#   calls to cherrypy.session to a thread-specific dictionnary called
#   cherrypy.threadData._sessionData
class SessionWrapper(object):
    def __getattribute__(self, name):
        # Create thread-specific dictionnary if needed
        try:
            td._sessionData
        except:
            td._sessionData = {}
        if name == 'acquireLock':
            return td._sessionStorage.acquireLock
        elif name == 'releaseLock':
            return td._sessionStorage.releaseLock
        return td._sessionData.__getattribute__(name)
    def __getitem__(self, *a, **b):
        return td._sessionData.__getitem__(*a, **b)
    def __setitem__(self, *a, **b):
        return td._sessionData.__setitem__(*a, **b)

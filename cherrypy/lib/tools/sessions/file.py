import datetime
import os
import sys
import time
import cherrypy
from cherrypy.lib import lockfile, locking
from cherrypy.lib.tools.sessions.base import Session
from cherrypy.lib.compat import pickle


class FileSession(Session):
    """Implementation of the File backend for sessions

    storage_path
        The folder where session data will be saved. Each session
        will be saved as pickle.dump(data, expiration_time) in its own file;
        the filename will be self.SESSION_PREFIX + self.id.

    lock_timeout
        A timedelta or numeric seconds indicating how long
        to block acquiring a lock. If None (default), acquiring a lock
        will block indefinitely.
    """

    SESSION_PREFIX = 'session-'
    LOCK_SUFFIX = '.lock'
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, id=None, **kwargs):
        # The 'storage_path' arg is required for file-based sessions.
        kwargs['storage_path'] = os.path.abspath(kwargs['storage_path'])
        kwargs.setdefault('lock_timeout', None)

        Session.__init__(self, id=id, **kwargs)

        # validate self.lock_timeout
        if isinstance(self.lock_timeout, (int, float)):
            self.lock_timeout = datetime.timedelta(seconds=self.lock_timeout)
        if not isinstance(self.lock_timeout, (datetime.timedelta, type(None))):
            raise ValueError("Lock timeout must be numeric seconds or "
                             "a timedelta instance.")

    @classmethod
    def setup(cls, **kwargs):
        """Set up the storage system for file-based sessions.

        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        # The 'storage_path' arg is required for file-based sessions.
        kwargs['storage_path'] = os.path.abspath(kwargs['storage_path'])

        for k, v in kwargs.items():
            setattr(cls, k, v)

    def _get_file_path(self):
        f = os.path.join(self.storage_path, self.SESSION_PREFIX + self.id)
        if not os.path.abspath(f).startswith(self.storage_path):
            raise cherrypy.HTTPError(400, "Invalid session id in cookie.")
        return f

    def _exists(self):
        path = self._get_file_path()
        return os.path.exists(path)

    def _load(self, path=None):
        assert self.locked, ("The session load without being locked.  "
                             "Check your tools' priority levels.")
        if path is None:
            path = self._get_file_path()
        try:
            f = open(path, "rb")
            try:
                return pickle.load(f)
            finally:
                f.close()
        except (IOError, EOFError):
            e = sys.exc_info()[1]
            if self.debug:
                cherrypy.log("Error loading the session pickle: %s" %
                             e, 'TOOLS.SESSIONS')
            return None

    def _save(self, expiration_time):
        assert self.locked, ("The session was saved without being locked.  "
                             "Check your tools' priority levels.")
        f = open(self._get_file_path(), "wb")
        try:
            pickle.dump((self._data, expiration_time), f, self.pickle_protocol)
        finally:
            f.close()

    def _delete(self):
        assert self.locked, ("The session deletion without being locked.  "
                             "Check your tools' priority levels.")
        try:
            os.unlink(self._get_file_path())
        except OSError:
            pass

    def acquire_lock(self, path=None):
        """Acquire an exclusive lock on the currently-loaded session data."""
        if path is None:
            path = self._get_file_path()
        path += self.LOCK_SUFFIX
        checker = locking.LockChecker(self.id, self.lock_timeout)
        while not checker.expired():
            try:
                self.lock = lockfile.LockFile(path)
            except lockfile.LockError:
                time.sleep(0.1)
            else:
                break
        self.locked = True
        if self.debug:
            cherrypy.log('Lock acquired.', 'TOOLS.SESSIONS')

    def release_lock(self, path=None):
        """Release the lock on the currently-loaded session data."""
        self.lock.release()
        self.lock.remove()
        self.locked = False

    def clean_up(self):
        """Clean up expired sessions."""
        now = self.now()
        # Iterate over all session files in self.storage_path
        for fname in os.listdir(self.storage_path):
            if (fname.startswith(self.SESSION_PREFIX)
                    and not fname.endswith(self.LOCK_SUFFIX)):
                # We have a session file: lock and load it and check
                #   if it's expired. If it fails, nevermind.
                path = os.path.join(self.storage_path, fname)
                self.acquire_lock(path)
                if self.debug:
                    # This is a bit of a hack, since we're calling clean_up
                    # on the first instance rather than the entire class,
                    # so depending on whether you have "debug" set on the
                    # path of the first session called, this may not run.
                    cherrypy.log('Cleanup lock acquired.', 'TOOLS.SESSIONS')

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

    def __len__(self):
        """Return the number of active sessions."""
        return len([fname for fname in os.listdir(self.storage_path)
                    if (fname.startswith(self.SESSION_PREFIX)
                        and not fname.endswith(self.LOCK_SUFFIX))])
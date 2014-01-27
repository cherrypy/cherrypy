import threading
from cherrypy.lib.compat import copyitems
from cherrypy.lib.tools.sessions.base import Session


class RamSession(Session):

    # Class-level objects. Don't rebind these!
    cache = {}
    locks = {}

    def clean_up(self):
        """Clean up expired sessions."""
        now = self.now()
        for id, (data, expiration_time) in copyitems(self.cache):
            if expiration_time <= now:
                try:
                    del self.cache[id]
                except KeyError:
                    pass
                try:
                    del self.locks[id]
                except KeyError:
                    pass

        # added to remove obsolete lock objects
        for id in list(self.locks):
            if id not in self.cache:
                self.locks.pop(id, None)

    def _exists(self):
        return self.id in self.cache

    def _load(self):
        return self.cache.get(self.id)

    def _save(self, expiration_time):
        self.cache[self.id] = (self._data, expiration_time)

    def _delete(self):
        self.cache.pop(self.id, None)

    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()

    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        self.locks[self.id].release()
        self.locked = False

    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)
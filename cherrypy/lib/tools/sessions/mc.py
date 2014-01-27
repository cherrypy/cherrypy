import threading
import time
import cherrypy
from cherrypy.lib.compat import unicodestr
from cherrypy.lib.tools.sessions.base import Session


class MemcachedSession(Session):

    # The most popular memcached client for Python isn't thread-safe.
    # Wrap all .get and .set operations in a single lock.
    mc_lock = threading.RLock()

    # This is a seperate set of locks per session id.
    locks = {}

    servers = ['127.0.0.1:11211']

    def setup(cls, **kwargs):
        """Set up the storage system for memcached-based sessions.

        This should only be called once per process; this will be done
        automatically when using sessions.init (as the built-in Tool does).
        """
        for k, v in kwargs.items():
            setattr(cls, k, v)

        import memcache
        cls.cache = memcache.Client(cls.servers)
    setup = classmethod(setup)

    @property
    def id(self):
        """The current session ID."""
        return self._id

    @id.setter
    def id(self, value):
        # This encode() call is where we differ from the superclass.
        # Memcache keys MUST be byte strings, not unicode.
        if isinstance(value, unicodestr):
            value = value.encode('utf-8')

        self._id = value
        for o in self.id_observers:
            o(value)

    def _exists(self):
        self.mc_lock.acquire()
        try:
            return bool(self.cache.get(self.id))
        finally:
            self.mc_lock.release()

    def _load(self):
        self.mc_lock.acquire()
        try:
            return self.cache.get(self.id)
        finally:
            self.mc_lock.release()

    def _save(self, expiration_time):
        # Send the expiration time as "Unix time" (seconds since 1/1/1970)
        td = int(time.mktime(expiration_time.timetuple()))
        self.mc_lock.acquire()
        try:
            if not self.cache.set(self.id, (self._data, expiration_time), td):
                raise AssertionError(
                    "Session data for id %r not set." % self.id)
        finally:
            self.mc_lock.release()

    def _delete(self):
        self.cache.delete(self.id)

    def acquire_lock(self):
        """Acquire an exclusive lock on the currently-loaded session data."""
        self.locked = True
        self.locks.setdefault(self.id, threading.RLock()).acquire()
        if self.debug:
            cherrypy.log('Lock acquired.', 'TOOLS.SESSIONS')

    def release_lock(self):
        """Release the lock on the currently-loaded session data."""
        self.locks[self.id].release()
        self.locked = False

    def __len__(self):
        """Return the number of active sessions."""
        raise NotImplementedError



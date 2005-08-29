
# write should lock out everyone
# read should only lock out writing

import threading

try:
    from threading import local
except ImportError:
    from cherrypy._cpthreadinglocal import local


class MROWLock(object):
    
    def __init__(self):
        self.local = local()
        # this is required so that multiple writers won't mess up writing event
        self.writelock = threading.RLock()
        # must wait() for this; it'll tell you when a write is over
        # (like a lock that you dont acquire, you just wait for)
        self.writing = threading.Event()
        # we are not writing to it right now
        self.writing.set()
        # list of all reader Events. when clear, they are reading.
        # must wait() for all of these to be sure no one is reading
        self.readers = []
        # lock for readers list so it is not changed while looping
        self.readerslock = threading.RLock()
    
    def lock_read(self):
        if not hasattr(self.local, "reader"):
            self.local.reader = threading.Event()
            self.local.reader.set()
            # lock the list so it won't mess up the loop in lock_write
            self.readerslock.acquire()
            self.readers.append(self.local.reader)
            self.readerslock.release()
        
        # only wait if the writing thread is not the thread same
        # which is requesting a read lock
        if not hasattr(self.local, 'writing'):
            # wait for any writes to finish
            self.writing.wait()
        
        # tell everyone we are reading
        self.local.reader.clear()
    
    def lock_write(self):
        # we set the writing attribute so we know if 
        # lock_write is being called by the same thread
        if not hasattr(self.local, 'writing'):
            self.local.writing = True
            # wait for any writes to finish
            # (this is a bit redundant with the next line)
            self.writing.wait()
            
        self.writelock.acquire()
        # lock out everyone reading from this dict
        self.writing.clear()
        self.readerslock.acquire()
        for reader in self.readers:
            reader.wait()
        self.readerslock.release()
        # at this point, all systems go
    
    def unlock_read(self):
        if hasattr(self.local, "reader"):
            self.local.reader.set()
    
    def unlock_write(self):
        # wake everyone else up.
        # TODO: what if one thread has the lock, and another calls this method?
        self.writing.set()
        self.writelock.release()


class MROWDict(dict):
    
    def __init__(self, auto_lock = False, auto_lock_safe = True, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._locks = {}
        self._lockslock = threading.RLock()
        # automatically acquire locks for getitem setitem (BAD IDEA)
        self._auto_lock = auto_lock
        # when autolocking, lock the whole dict (GOOD IDEA)
        self._auto_lock_safe = auto_lock_safe
    
    def _init_lock(self, key):
        self._lockslock.acquire()
        if key not in self._locks:
            self._locks[key] = MROWLock()
        self._lockslock.release()
    
    def lock_read(self, key = "__me__"):
        self._init_lock(key)
        return self._locks[key].lock_read()
    
    def lock_write(self, key = "__me__"):
        self._init_lock(key)
        return self._locks[key].lock_write()
    
    def unlock_read(self, key = "__me__"):
        return self._locks[key].unlock_read()
    
    def unlock_write(self, key = "__me__"):
        return self._locks[key].unlock_write()
    
    def __delitem__(self, key):
        if key in self._locks:
            self.unlock_read(key)
            self.unlock_write(key)
            del self._locks[key]
            dict.__delitem__(self, key)
    
    def __getitem__(self, key):
        if self._auto_lock:
            if self._auto_lock_safe:
                self.lock_read()
            else:
                self.lock_read(key)
        return dict.__getitem__(self, key)
    
    def __setitem__(self, key, value):
        if self._auto_lock:
            if self._auto_lock_safe:
                self.lock_write()
            else:
                self.lock_write(key)
        dict.__setitem__(self, key, value)
    
    def get(self, key):
        if self._auto_lock:
            if self._auto_lock_safe:
                self.lock_read()
            else:
                self.lock_read(key)
        return dict.get(self, key)
    
    def setdefault(self, key, value):
        if self._auto_lock:
            if self._auto_lock_safe:
                self.lock_write()
            else:
                self.lock_write(key)
        dict.setdefault(self, key, value)

    def update(self, values):
        if self._auto_lock:
            if self._auto_lock_safe:
                self.lock_write()
            else:
                self.lock_write(key)
        dict.update(self, values)


# test code
import time, thread

class MROWTest(object):
    
    def __init__(self):
        self.deadthreads = 0
        self.hitdict = {"hits": 0}
        self.lock = MROWLock()
        for i in xrange(0, 2):
            thread.start_new_thread(self.reader_thread, ())
        for i in range(0, 3):
            thread.start_new_thread(self.writer_thread, ())
        self.reader_thread()
    
    def writer_thread(self):
        for i in xrange(100):
            self.lock.lock_write()
            hits = self.hitdict["hits"] + 1
            time.sleep(.01)
            self.hitdict["hits"] = hits
            self.lock.unlock_write()
        self.deadthreads += 1
    
    def reader_thread(self):
        while True:
            self.lock.lock_read()
            try:
                hits = self.hitdict["hits"]
                if self.deadthreads == 3:
                    break
            finally:
                self.lock.unlock_read()
            time.sleep(.01)
        
        if hits != 300:
            print "omfg error", hits
        else:
            print "its all ok"


if __name__ == "__main__":
    while True:
        MROWTest()

del time, thread, MROWTest

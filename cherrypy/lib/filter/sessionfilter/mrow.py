                                                                                                                                                                                                                                                               
import threading

# write should lock out everyone
# read should only lock out writing

class MROWLock(object):
    def __init__(self):
        self.local = threading.local()
        self.writelock = threading.RLock() # this is required so that multiple writers won't mess up writing event
        self.writing = threading.Event() # must wait() for this; it'll tell you when a write is over (like a lock that you dont acquire, you just wiat for)
        self.writing.set() # we are not writing to it right now
        self.readers = [] # list of all reader Events. when clear, they are reading. must wait() for all of these to be sure no one is reading
        self.readerslock = threading.RLock() # lock for readers list so it is not changed while looping
    def lock_read(self):
        if not hasattr(self.local, "reader"):
            self.local.reader = threading.Event()
            self.local.reader.set()
            self.readerslock.acquire() # lock the list so it won't mess up the loop in lock_write
            self.readers.append(self.local.reader)
            self.readerslock.release()
        self.writing.wait() # wait for any writes to finish
        # tell everyone we are reading
        self.local.reader.clear()
    def lock_write(self):
        self.writing.wait() # wait for any writes to finish (this is a bit redundant with the next line)
        self.writelock.acquire()
        self.writing.clear() # lock out everyone reading from this dict
        self.readerslock.acquire()
        for reader in self.readers:
            reader.wait()
        self.readerslock.release()
        # at this point, all systems go
    def unlock_read(self):
        if hasattr(self.local, "reader"):
            self.local.reader.set()
    def unlock_write(self):
        self.writing.set() # wake everyone else up. TODO: what if one thread has the lock, and another calls this method?
        self.writelock.release()

class MROWDict(dict):
    def __init__(self, auto_lock = False, auto_lock_safe = True, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._locks = {}
        self._lockslock = threading.RLock()
        self._auto_lock = auto_lock # automatically acquire locks for getitem setitem (BAD IDEA)
        self._auto_lock_safe = auto_lock_safe # when autolocking, lock the whole dict (GOOD IDEA)
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

# test code
'''
import time, thread

deadthreads = 0

def writer_thread(d, l):
    global deadthreads
    for i in range(0, 100):
        l.lock_write()
        hits = d["hits"]
        hits = hits + 1
        time.sleep(.01)
        d["hits"] = hits
        l.unlock_write()
    deadthreads += 1

def reader_thread(d, l):
    while True:
        l.lock_read()
        try:
            hits = d["hits"]
            if deadthreads == 3:
                if d["hits"] != 300:
                    print "omfg error",d["hits"]
                    break
                else:
                    print "its all ok"
                    break
        finally:
            l.unlock_read()
        time.sleep(.01)

def main():
    global deadthreads
    deadthreads = 0
    d = {}
    d["hits"] = 0
    l = MROWLock()
    for i in range(0, 2):
        thread.start_new_thread(reader_thread, (d,l))
    for i in range(0, 3):
        thread.start_new_thread(writer_thread, (d,l))
    reader_thread(d, l)

if __name__ == "__main__":
    while True:
        main()
'''

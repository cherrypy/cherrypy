"""
Platform-independent file locking.
"""

import os

try:
    import msvcrt
except ImportError:
    pass

try:
    import fcntl
except ImportError:
    pass

class LockError(Exception):
    "Could not obtain a lock"

# first, a default, naive locking implementation
class LockFile(object):
    """
    A default, naive locking implementation. Always fails if the file
    already exists.
    """
    def __init__(self, path):
        self.path = path
        try:
            fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
        except OSError:
            raise LockError("Unable to lock %s" % self.path)
        os.close(fd)

    def release(self):
        os.remove(self.path)


class SystemLockFile(object):

    def __init__(self, path):
        self.path = path
        fp = open(path, 'w+')

        self._lock_file(fp)

        self.fp = fp
        fp.write(" %s\n" % os.getpid())
        fp.truncate()
        fp.flush()

    def release(self):
        if not hasattr(self, 'fp'):
            return
        self._unlock_file()
        self.fp.close()
        del self.fp

    def _unlock_file(self):
        pass


class WindowsLockFile(SystemLockFile):
    def _lock_file(self):
        # Lock just the first byte
        try:
            msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
        except IOError:
            raise LockError("Unable to lock %r" % self.fp.name)

    def _unlock_file(self):
        try:
            self.fp.seek(0)
            msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
        except IOError:
            raise LockError("Unable to unlock %r" % self.fp.name)

if 'msvcrt' in globals():
    LockFile = WindowsLockFile


class UnixLockFile(SystemLockFile):
    def _lock_file(self):
        flags = fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(self.fp.fileno(), flags)
        except IOError:
            raise LockError("Unable to lock %r" % self.fp.name)

    # no need to implement _unlock_file, it will be unlocked on close()

if 'fcntl' in globals():
    LockFile = UnixLockFile

# autoreloading launcher
# stolen a lot from Ian Bicking's WSGIKit (www.wsgikit.org)

import os
import sys
import time
import thread

RUN_RELOADER = True
reloadFiles = []

def reloader_thread(freq):
    mtimes = {}
    
    def fileattr(m):
        if hasattr(m, "__loader__"):
            if hasattr(m.__loader__, "archive"):
                return m.__loader__.archive
        return getattr(m, "__file__", None)
    
    while RUN_RELOADER:
        for filename in map(fileattr, sys.modules.values()) + reloadFiles:
            if filename:
                if filename.endswith(".pyc"):
                    filename = filename[:-1]
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    sys.exit(3) # force reload
                if filename not in mtimes:
                    mtimes[filename] = mtime
                    continue
                if mtime > mtimes[filename]:
                    sys.exit(3) # force reload
        time.sleep(freq)

def restart_with_reloader():
    while True:
        args = [sys.executable] + sys.argv
        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        exit_code = os.spawnve(os.P_WAIT, sys.executable, args, new_environ)
        if exit_code != 3:
            return exit_code

def main(main_func, args=None, kwargs=None, freq=1):
    if os.environ.get("RUN_MAIN") == "true":
        
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        thread.start_new_thread(main_func, args, kwargs)
        
        # If KeyboardInterrupt is raised within reloader_thread,
        # let it propagate out to the caller.
        reloader_thread(freq)
    else:
        # If KeyboardInterrupt is raised within restart_with_reloader,
        # let it propagate out to the caller.
        sys.exit(restart_with_reloader())

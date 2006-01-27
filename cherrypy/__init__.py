"""Global module that all modules developing with CherryPy should import."""

__version__ = '2.2.0beta'

import datetime
import sys
import types

from _cperror import *
import config

import _cptree
tree = _cptree.Tree()

# Legacy code may clobber this.
root = None

lowercase_api = False

import _cpserver
server = _cpserver.Server()

codecoverage = False

try:
    from threading import local
except ImportError:
    from cherrypy._cpthreadinglocal import local

# Create a threadlocal object to hold the request and response
# objects. In this way, we can easily dump those objects when
# we stop/start a new HTTP conversation, yet still refer to
# them as module-level globals in a thread-safe way.
serving = local()

class _ThreadLocalProxy:
    
    def __init__(self, attrname):
        self.__dict__["__attrname__"] = attrname
    
    def __getattr__(self, name):
        childobject = getattr(serving, self.__attrname__)
        return getattr(childobject, name)
    
    def __setattr__(self, name, value):
        childobject = getattr(serving, self.__attrname__)
        setattr(childobject, name, value)
    
    def __delattr__(self, name):
        childobject = getattr(serving, self.__attrname__)
        delattr(childobject, name)

# Create request and response object (the same objects will be used
#   throughout the entire life of the webserver, but will redirect
#   to the "serving" object)
request = _ThreadLocalProxy('request')
response = _ThreadLocalProxy('response')

# Create thread_data object as a thread-specific all-purpose storage
thread_data = local()
threadData = thread_data # Backward compatibility

# Create variables needed for session (see lib/sessionfilter.py for more info)
from filters import sessionfilter
session = sessionfilter.SessionWrapper()
_session_data_holder = {} # Needed for RAM sessions only
_session_lock_dict = {} # Needed for RAM sessions only
_session_last_clean_up_time = datetime.datetime.now()

def expose(func=None, alias=None):
    """Expose the function, optionally providing an alias or set of aliases."""
    
    def expose_(func):
        func.exposed = True
        if alias is not None:
            if isinstance(alias, basestring):
                parents[alias] = func
            else:
                for a in alias:
                    parents[a] = func
        return func
    
    parents = sys._getframe(1).f_locals
    if isinstance(func, (types.FunctionType, types.MethodType)):
        # expose is being called directly, before the method has been bound
        return expose_(func)
    else:
        # expose is being called as a decorator
        if alias is None:
            alias = func
        return expose_

def log(msg='', context='', severity=0, traceback=False):
    """Syntactic sugar for writing to the (error) log."""
    # Load _cputil lazily to avoid circular references, and
    # to allow profiler and coverage tools to work on it.
    import _cputil
    logfunc = _cputil.get_special_attribute('_cp_log_message', '_cpLogMessage')
    
    if traceback:
        msg += _cputil.formatExc()
    
    logfunc(msg, context, severity)

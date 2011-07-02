import sys
if sys.version_info < (3, 0):
    from wsgiserver2 import *
else:
    # Le sigh. Boo for backward-incompatible syntax.
    exec('from .wsgiserver3 import *')

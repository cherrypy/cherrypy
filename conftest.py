"""test configuration for pytest."""

import sys


collect_ignore = [
    # imports win32api, so not viable on some systems
    'cherrypy/process/win32.py',
]


if sys.version_info < (3, 6):
    # Modules in docs require Python 3.6
    collect_ignore.append('docs')

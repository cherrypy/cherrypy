"""Test configuration for pytest."""


collect_ignore = [
    # imports win32api, so not viable on some systems
    'cherrypy/process/win32.py',
]

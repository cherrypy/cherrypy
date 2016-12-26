"""
Used by Travis script to trigger deployment only on
one version of Python 2 and Python 3.
"""

import sys
short_ver = sys.version_info[:2]
msg = "yes" if short_ver in [(3, 5), (2, 7)] else "no"
print(msg)

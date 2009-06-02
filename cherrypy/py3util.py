"""
A simple module that helps unify the code between a python2 and python3 library.
"""
import sys

def py3print(*args, **kwargs):
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    file = kwargs.get('file', sys.stdout)
    output = sep.join(['%s' % arg for arg in args]) + end
    file.write(output)

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def sorted(lst):
    newlst = list(lst)
    newlst.sort()
    return newlst

def reversed(lst):
    newlst = list(lst)
    return iter(newlst[::-1])

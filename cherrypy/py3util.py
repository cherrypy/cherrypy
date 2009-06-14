"""
A simple module that helps unify the code between a python2 and python3 library.
"""
import sys

def sorted(lst):
    newlst = list(lst)
    newlst.sort()
    return newlst

def reversed(lst):
    newlst = list(lst)
    return iter(newlst[::-1])

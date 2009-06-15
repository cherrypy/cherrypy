"""
A simple module that helps unify the code between a python2 and python3 library.
"""
import sys

try:
    sorted = sorted
except NameError:
    def sorted(lst):
        newlst = list(lst)
        newlst.sort()
        return newlst

try:
    reversed = reversed
except NameError:
    def reversed(lst):
        newlst = list(lst)
        return iter(newlst[::-1])

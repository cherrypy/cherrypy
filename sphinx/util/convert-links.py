#!python
from __future__ import print_function
import sys
import re
import inspect

def replace_external_link(matcher):
	r"\[(?P<href>(?P<scheme>\w+)\://.+?) (?P<name>.+?)\]"
	return '`{name} <{href}>`_'.format(**matcher.groupdict())

filename = sys.argv[1]
text = open(filename).read()
pattern = re.compile(inspect.getdoc(replace_external_link))
new_text = pattern.sub(replace_external_link, text)

open(filename, 'w').write(new_text)
print("done")

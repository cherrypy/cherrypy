from __future__ import print_function
import sys
import inspect
import docutils.utils
import docutils.parsers.rst
from StringIO import StringIO


def print_with_line_numbers(block):
    stream = StringIO(block)
    for number, line in enumerate(stream):
        number += 1
        print(number, line.rstrip())

target_class_spec = sys.argv[1]
import cherrypy
target_class = eval(target_class_spec)
source = inspect.getdoc(target_class)
print_with_line_numbers(source)
parser = docutils.parsers.rst.Parser()
settings = None  # ?
document = docutils.utils.new_document(source, settings)
parser.parse(source, document)

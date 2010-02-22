#!python
from __future__ import print_function
import sys
import re
import inspect
import optparse

def get_options():
	parser = optparse.OptionParser()
	options, args = parser.parse_args()
	try:
		options.filename = args.pop()
	except IndexError:
		parser.error("Filename required")
	return options

# each of the replacement functions should have a docstring
#  which is a regular expression to be matched.

def replace_external_link(matcher):
	r"\[(?P<href>(?P<scheme>\w+)\://.+?) (?P<name>.+?)\]"
	return '`{name} <{href}>`_'.format(**matcher.groupdict())

def replace_wiki_link(matcher):
	r"\[wiki\:(?P<ref>.+?) (?P<name>.+?)\]"
	return '`{name} <TODO-fix wiki target {ref}>`_'.format(**matcher.groupdict())

replacements = [
	replace_external_link,
	replace_wiki_link,
	]

def convert_file(filename):
	text = open(filename).read()
	new_text = text
	for repl in replacements:
		pattern = re.compile(inspect.getdoc(repl))
		new_text = pattern.sub(repl, new_text)

	open(filename, 'w').write(new_text)
	print("done")


def handle_command_line():
	options = get_options()
	convert_file(options.filename)

if __name__ == '__main__':
	handle_command_line()

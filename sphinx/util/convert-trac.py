#!python
from __future__ import print_function
import sys
import re
import inspect
import optparse
import shutil

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

# character array indexed by level for characters
heading_characters = [None, '*', '=', '-', '^']

def replace_headings(matcher):
	r"^(?P<level>=+) (?P<name>.*) (?P=level)$"
	level = len(matcher.groupdict()['level'])
	char = heading_characters[level]
	name = matcher.groupdict()['name']
	return '\n'.join([name, char*len(name)])

replacements = [func for name, func in globals().items() if name.startswith('replace')]

def convert_file(filename):
	shutil.copy(filename, filename+'.bak')
	text = open(filename).read()
	new_text = text
	for repl in replacements:
		pattern = re.compile(inspect.getdoc(repl), re.MULTILINE)
		new_text = pattern.sub(repl, new_text)

	open(filename, 'w').write(new_text)
	print("done")


def handle_command_line():
	options = get_options()
	convert_file(options.filename)

if __name__ == '__main__':
	handle_command_line()

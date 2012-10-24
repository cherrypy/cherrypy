"""
This script will walk a developer through the process of cutting a release.

To cut a release, simply invoke this script at the changeset to be released.
"""

def check_status():
	"""
	Make sure there aren't outstanding changesets that are unpushed, maybe
	run the tests or ask the user if the tests are passing.
	"""
	raise NotImplementedError()

def bump_versions():
	"""
	Bump the versions in each of the places where it appears and commit.
	"""
	places = ('setup.py (twice)', 'cherrypy/__init__.py',
		'cherrypy/wsgiserver/wsgiserver\d')
	raise NotImplementedError()

def tag_release():
	"""
	Tag the release.
	"""
	raise NotImplementedError()

def build_and_upload():
	raise NotImplementedError()

def main():
	check_status()
	bump_versions()
	tag_release()
	build_and_upload()

if __name__ == '__main__':
	main()

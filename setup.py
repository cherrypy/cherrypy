from distutils.core import setup

import sys
# patch distutils if it can't cope with the "classifiers" keyword
if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

setup(name="CherryPy",
      version="2.0.0a2",
      description="Object-Oriented web development framework",
      long_description="""CherryPy is a pythonic, object-oriented web development framework.""",
      classifiers=["Development Status :: Alpha",
                   "Intended Audience :: Developers",
                   "License :: Freely Distributable",
                   "Programming Language :: Python",
                   "Topic :: Internet ",
                   "Topic :: Software Development :: Libraries :: Application Frameworks",
                   ],
      author="CherryPy Team",
      author_email="team@cherrypy.org",
      url="http://www.cherrypy.org",
      license="BSD",
      packages=["cherrypy", "cherrypy.lib", "cherrypy.lib.filter", "cherrypy.tutorial", "cherrypy.test"],
      download_url="http://trac.cherrypy.org/cgi-bin/trac.cgi/wiki/CherryPyDownload"
)


************
Installation
************

Prerequisites
=============

All you need is a working version of Python-2.3 or later on your computer.

Stable versions
===============

Download
--------

You may download this version from http://download.cherrypy.org/cherrypy/3.2.0rc1/

For other releases, browse our
`download index <http://download.cherrypy.org/ download index>`_.

Install
-------

* Download the latest CherryPy release from the
  `repository <http://download.cherrypy.org/cherrypy/>`_.
* Unzip/untar the files.
* Go to the directory created by the file extraction.
* Type "python setup.py install" to install the CherryPy module
* To run your first sample website, go to cherrypy/tutorial/ and type
  "python tut01_helloworld.py", and you'll have a running website on port 8080.
* Open your favorite browser and point it to http://localhost:8080 to see your
  first CherryPy-served page :-)

Now, you should try running some of the other tutorials found in the tutorial
directory and look at their source code to understand how to develop a website
with CherryPy.

Debian installation::

    $ apt-get install python python-dev
    $ python setup.py install

Development versions
====================

CherryPy's source code is managed using `Subversion <http://subversion.tigris.org>`_,
a source code control system.

You can access our Subversion repository using your favorite Subversion client
at http://svn.cherrypy.org

For Windows users, we recommend the wonderful Subversion client
`TortoiseSVN <http://tortoisesvn.tigris.org/>`_. Users of other operating
systems are advised to use multi-platform, Qt-based
`eSVN <http://esvn.umputun.com/>`_ or the command line tools provided by the
`core Subversion distribution <http://subversion.tigris.org/>`_.

Note: In some cases http access fails with the error 'Cannot checkout' even
though the web interface works fine. This is usually because of a proxy between
you and the server which doesn't support all the access methods that SVN needs.
Many ISPs insert a transparent proxy on all http traffic, causing this problem.
The solution is to switch to https access so the proxy cannot interfere.

You may also browse present and past versions of CherryPy source code,
inspect change sets, and even follow changes to specific trees/files using
RSS feeds. This web interface is located at http://www.cherrypy.org/browser/

Usage notes
-----------

* The repository is open for anonymous read-only access. CherryPy developers
  have write permissions. To obtain write permission, please contact fumanchu via
  email or IRC.
* The repository follows the standard trunk/branches/tags structure that is
  recommended in the Subversion documentation:

   * ``trunk`` contains the official development code. Please do not checkin
     any code on trunk that is untested, or that breaks the test suite.
   * ``branches`` contain experimental branches. Patches for complex tickets
     may also be developed and tested on a branch, to allow for easier
     collaboration during test of inherently unstable features.
   * ``tags`` contain frozen, known quality releases.

Configuring the Subversion client
---------------------------------

Popular Subversion clients, including TortoiseSVN and the standard command line
tools, are configurable by editing a standard ``config`` file. The file is
stored at:

  * **Linux**: ``~/.subversion/config``
  * **Windows XP, 2000, NT**: ``%APPDATA%\Subversion\config``
  * **Windows 98 (and possibly ME also)**: ``\Windows\Application Data\Subversion\config``

Configuration is necessary because line endings do matter for Subversion, and
different code editors and IDEs use different conventions. This problem can be
solved by telling Subversion to automatically map the line endings of the code
in the repository to the conventions of your local install. The configuration
file should contain the following entries::

    [miscellany]
    global-ignores = *.o *.lo *.la #*# .*.rej *.rej .*~ *~ .#* .DS_Store *.pyc
    enable-auto-props = yes

    [auto-props]
    *.py = svn:eol-style=native
    README.* = svn:eol-style=CRLF
    *.TXT = svn:eol-style=CRLF

The miscellany section contains two important settings: first, it tells
Subversion to ignore pyc files (in addition to the standard files it already
ignores); and also, it enables the auto-props section, which in turn provides
the standard line-ending convention.

Standalone WSGI server
----------------------

The WSGI server that comes bundled with CherryPy is available as a standalone
module.  Feel free to use it for all of your WSGI serving needs.


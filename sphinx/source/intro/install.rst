************
Installation
************

:ref:`prerequisites`

:ref:`stableversions`

:ref:`developmentversions`

.. _prerequisites:

Prerequisites
=============

All you need is a working version of Python-2.3 or later on your computer.

Get Python on Debian::

    $ apt-get install python python-dev


.. _stableversions:

Stable versions
===============

Download
--------

You may download this version from `here <http://download.cherrypy.org/cherrypy/3.2.3/>`_ 

For other releases, browse our
`download index <http://download.cherrypy.org/cherrypy>`_.

Windows Installation
--------------------

* Download the latest CherryPy release from the
  `repository <http://download.cherrypy.org/cherrypy/>`_.
  Select the file ending in ".exe"
* Run the downloaded file.

Unix/Mac Installation
---------------------

* Download the latest CherryPy release from the
  `repository <http://download.cherrypy.org/cherrypy/>`_.
* Unzip/untar the files
* Go to the directory created by the file extraction.
* Type "python setup.py install" to install the CherryPy module

Next Steps
----------

* To run your first sample website, go to cherrypy/tutorial/ and type
  "python tut01_helloworld.py", and you'll have a running website on port 8080.
* Open your favorite browser and point it to http://localhost:8080 to see your
  first CherryPy-served page :-)

Now, you should try running some of the other tutorials found in the tutorial
directory and look at their source code to understand how to develop a website
with CherryPy.

.. _developmentversions:

Development versions
====================

CherryPy's source code is managed using `Mercurial <http://mercurial.selenic.com/>`_,
a source code control system written in python.

You can access our Mercurial repository using your favorite
Mercurial client at `bitbucket <https://bitbucket.org/cherrypy/cherrypy>`_.

For Windows users, we recommend the wonderful Mercurial
client `TortoiseHg <http://tortoisehg.org/>`_. Users of
other operating systems are advised to use multi-platform
command line tools provided by the
`core Mercurial distribution <http://mercurial.selenic.com/downloads/>`_.

* To submit a patch fork the repository and submit your pull request.
  For further information please contact us via email or IRC
  (see `getting involved <http://bitbucket.org/cherrypy/cherrypy/wiki/CherryPyInvolved>`_).

Standalone WSGI server
----------------------

The WSGI server that comes bundled with CherryPy is available as a standalone
module.  Feel free to use it for all of your WSGI serving needs.

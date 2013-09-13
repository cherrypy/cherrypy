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
If you are running Max OS X or some Linux distribution (e.g. Ubuntu, Debian, Fedora)
you most likely already have python on you system, for a detailed instruction
on how to install python follow the instruction on the
`python wiki <http://wiki.python.org/moin/BeginnersGuide/Download>`_.

.. _stableversions:

Download Stable Versions 
========================

Using `pip` or `easy_install`
-----------------------------

Using pip::

    $ pip install CherryPy

or with easy_install::

    $ easy_install CherryPy

It is recommended to use `pip` instead of `easy_install`.
If you want to download and install CherryPy for yourself proceed to the 
next instructions depending on your platform. 

Unix/Mac
--------

You may download the most current version from `PyPI <https://pypi.python.org/pypi/CherryPy/3.2.3>`_  

For other releases, browse our
`download index <http://download.cherrypy.org/cherrypy>`_.

* Unzip/untar the files
* Enter the directory created by the file extraction.
* Type "python setup.py install" to install the CherryPy module


Windows
-------

You may download the most current version from `PyPI <https://pypi.python.org/pypi/CherryPy/3.2.3>`_. 

For other releases, browse our `download index <http://download.cherrypy.org/cherrypy>`_.  

* Select the file ending in ".exe".
* Run the downloaded file.


Next Steps
==========

To run your first sample website:

    1. In a command terminal or console go to cherrypy/tutorial/
    2. Type::

        $ python tut01_helloworld.py

      and you'll have a running website on port 8080.

    3. Open your favorite browser and point it to http://localhost:8080 to see your first CherryPy-served page :-)

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

* To submit a patch: fork the repository and submit your pull request.
  For further information please contact us via email or IRC
  (see `getting involved <http://bitbucket.org/cherrypy/cherrypy/wiki/CherryPyInvolved>`_).

Standalone WSGI server
----------------------

The WSGI server that comes bundled with CherryPy is available as a standalone
module.  Feel free to use it for all of your WSGI serving needs.

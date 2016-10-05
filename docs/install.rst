
Installation
------------

CherryPy is a pure Python library. This has various consequences:

 - It can run anywhere Python runs
 - It does not require a C compiler
 - It can run on various implementations of the Python language: `CPython <http://python.org/>`_,
   `IronPython <http://ironpython.net/>`_, `Jython <http://www.jython.org/>`_ and `PyPy <http://pypy.org/>`_

.. contents::
   :depth:  4

Requirements
############

CherryPy does not have any mandatory requirements. However certain features it comes with
will require you install certain packages. To simplify installing additional
dependencies CherryPy enables you to specify extras in your requirements (e.g.
``cherrypy[json,routes_dispatcher,ssl]``):
- doc -- for documentation related stuff
- json -- for custom `JSON processing library <https://github.com/simplejson/simplejson>`_ 
- routes_dispatcher -- `routes <http://routes.readthedocs.org/en/latest/>`_ for declarative URL mapping dispatcher
- ssl -- for `OpenSSL bindings <https://github.com/pyca/pyopenssl>`_, useful in Python environments not having the builtin :mod:`ssl` module
- test_tools
- memcached_session -- enables `memcached <https://github.com/linsomniac/python-memcached>`_ backend session
- xcgi


Supported python version
########################

CherryPy supports Python 2.7 through to 3.5.


Installing
##########

CherryPy can be easily installed via common Python package managers such as setuptools or pip.

.. code-block:: bash

   $ easy_install cherrypy


.. code-block:: bash

   $ pip install cherrypy

You may also get the latest CherryPy version by grabbing the source code from Github:

.. code-block:: bash

   $ git clone https://github.com/cherrypy/cherrypy
   $ cd cherrypy
   $ python setup.py install

Test your installation
^^^^^^^^^^^^^^^^^^^^^^

CherryPy comes with a set of simple tutorials that can be executed
once you have deployed the package.

.. code-block:: bash

   $ python -m cherrypy.tutorial.tut01_helloworld

Point your browser at http://127.0.0.1:8080 and enjoy the magic.

Once started the above command shows the following logs:

.. code-block:: bash

   [15/Feb/2014:21:51:22] ENGINE Listening for SIGHUP.
   [15/Feb/2014:21:51:22] ENGINE Listening for SIGTERM.
   [15/Feb/2014:21:51:22] ENGINE Listening for SIGUSR1.
   [15/Feb/2014:21:51:22] ENGINE Bus STARTING
   [15/Feb/2014:21:51:22] ENGINE Started monitor thread 'Autoreloader'.
   [15/Feb/2014:21:51:22] ENGINE Started monitor thread '_TimeoutMonitor'.
   [15/Feb/2014:21:51:22] ENGINE Serving on http://127.0.0.1:8080
   [15/Feb/2014:21:51:23] ENGINE Bus STARTED

We will explain what all those lines mean later on, but suffice
to know that once you see the last two lines, your server
is listening and ready to receive requests.

Run it
######

During development, the easiest path is to run your application as
follow:

.. code-block:: bash

   $ python myapp.py

As long as `myapp.py` defines a `"__main__"` section, it will
run just fine.

cherryd
^^^^^^^

Another way to run the application is through the ``cherryd`` script
which is installed along side CherryPy.

.. note::

   This utility command will not concern you if you embed your
   application with another framework.

Command-Line Options
~~~~~~~~~~~~~~~~~~~~

.. program:: cherryd

.. cmdoption:: -c, --config

   Specify config file(s)

.. cmdoption:: -d

   Run the server as a daemon

.. cmdoption:: -e, --environment

   Apply the given config environment (defaults to None)


.. index:: FastCGI

.. cmdoption:: -f

   Start a :ref:`FastCGI <fastcgi>` server instead of the default HTTP server


.. index:: SCGI

.. cmdoption:: -s

   Start a SCGI server instead of the default HTTP server


.. cmdoption:: -i, --import

   Specify modules to import


.. index:: PID file

.. cmdoption:: -p, --pidfile

   Store the process id in the given file (defaults to None)


.. cmdoption:: -P, --Path

   Add the given paths to sys.path


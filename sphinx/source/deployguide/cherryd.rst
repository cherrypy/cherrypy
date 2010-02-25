*******
cherryd
*******

The ``cherryd`` script is used to start CherryPy servers, whether the builtin
WSGI server, :doc:`FastCGI <fastcgi>`, or SCGI. Sites using mod_python don't
need to use ``cherryd``; Apache will spawn the CherryPy process in that case.

Command-Line Options
====================

.. program:: cherryd

.. cmdoption:: -c, --config

   Specify config file(s)

.. cmdoption:: -d

   Run the server as a daemon

.. cmdoption:: -e, --environment

   Apply the given config environment (defaults to None)


.. index:: FastCGI

.. cmdoption:: -f

   Start a :doc:`FastCGI <fastcgi>` server instead of the default HTTP server


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


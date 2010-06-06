*********
PID files
*********

The PIDFile :ref:`Engine Plugin<plugins>` is pretty straightforward: it writes
the process id to a file on start, and deletes the file on exit. You must
provide a 'pidfile' argument, preferably an absolute path::

    PIDFile(cherrypy.engine, '/var/run/myapp.pid').subscribe()

.. currentmodule:: cherrypy.process.plugins

Classes
=======

.. autoclass:: PIDFile
   :members:
   :show-inheritance:



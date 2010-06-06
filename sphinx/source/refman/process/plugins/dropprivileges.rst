***************
Drop privileges
***************

Use this :ref:`Engine Plugin<plugins>` to start your
CherryPy site as root (for example, to listen on a privileged port like 80)
and then reduce privileges to something more restricted.

This priority of this plugin's "start" listener is slightly higher than the
priority for ``server.start`` in order to facilitate the most common use:
starting on a low port (which requires root) and then dropping to another user.

Example::

    DropPrivileges(cherrypy.engine, '/var/run/myapp.pid').subscribe()

.. currentmodule:: cherrypy.process.plugins

Classes
=======

.. autoclass:: DropPrivileges
   :members:
   :show-inheritance:


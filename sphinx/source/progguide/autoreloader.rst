****************
Reload processes
****************

.. _autoreloader:

Autoreloader
============

The autoreload plugin restarts the process (via os.execv) if any of the files
it monitors change (or is deleted). By default, the autoreloader monitors all
imported modules; you can add to the set by adding to autoreloader.files::

    cherrypy.engine.autoreload.files.add(myFile)

If there are imported files you do *not* wish to monitor, you can adjust the
``match`` attribute, a regular expression. For example, to stop monitoring
cherrypy itself::

    cherrypy.engine.autoreload.match = r'^(?!cherrypy).+'

Like all Monitor plugins (:ref:`monitor`), the autoreload plugin takes a
``frequency`` argument. The default is 1 second; that is, the autoreloader
will examine files each second.


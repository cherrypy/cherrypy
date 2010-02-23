.. _threadmanager:

**************
Manage threads
**************

ThreadManager
=============

A manager for HTTP request threads. Creating an instance of this plugin causes
two new channels to be registered with the bus: ``acquire_thread`` and
``release_thread``.

If you have control over thread creation and destruction, publish to the
``acquire_thread`` and ``release_thread`` channels (for each thread). This will
register/unregister the current thread, and cause a publish to
``start_thread`` and ``stop_thread`` listeners on the bus as needed. If you're using
normal ``cherrypy.Applications`` (you probably are), then they will do all this for
you.

If threads are created and destroyed by code you do not control (e.g., Apache),
then, at the beginning of every HTTP request, publish to ``acquire_thread`` only.
You should not publish to ``release_thread`` since you do not know
whether the thread will be re-used or not. The bus will call ``stop_thread``
listeners for you when it stops.
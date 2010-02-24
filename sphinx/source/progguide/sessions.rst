********
Sessions
********

You need to edit your config file to use sessions. Here's an example::

	[/]
	tools.sessions.on = True
	tools.sessions.storage_type = "file"
	tools.sessions.storage_path = "/home/site/sessions"
	tools.sessions.timeout = 60


This sets the session to be stored in files in the directory /home/site/sessions, and the session timeout to 60 minutes. If you omit ``storage_type`` the sessions will be saved in RAM.  ``tools.sessions.on`` is the only required line for working sessions, the rest are optional. 

By default, the session ID is passed in a cookie, so the client's browser must have cookies enabled for your site.

To set data for the current session, use ``cherrypy.session['fieldname'] = 'fieldvalue'``, to get data use ``cherrypy.session.get('fieldname')``.

================
Locking sessions
================

By default, the ``'locking'`` mode of sessions is ``'implicit'``, which means the session is locked early and unlocked late. If you want to control when the session data is locked and unlocked, set ``tools.sessions.locking = 'explicit'``. Then call ``cherrypy.session.acquire_lock()`` and ``cherrypy.session.release_lock()``. Regardless of which mode you use, the session is guaranteed to be unlocked when the request is complete.

=================
Expiring Sessions
=================

You can force a session to expire with :func:`cherrypy.lib.sessions.expire`.  Simply call that function at the point you want the session to expire, and it will cause the session cookie to expire client-side.

===========================
Session Fixation Protection
===========================

If CherryPy receives, via a request cookie, a session id that it does not recognize, it will reject that id and create a new one to return in the response cookie. This `helps prevent session fixation attacks <http://en.wikipedia.org/wiki/Session_fixation#Regenerate_SID_on_each_request>`_. However, CherryPy "recognizes" a session id by looking up the saved session data for that id. Therefore, if you never save any session data, **you will get a new session id for every request**.

================
Sharing Sessions
================

If you run multiple instances of CherryPy (for example via mod_python behind Apache prefork), you most likely cannot use the RAM session backend, since each instance of CherryPy will have its own memory space. Use a different backend instead, and verify that all instances are pointing at the same file or db location. Alternately, you might try a load balancer which makes sessions "sticky". Google is your friend, there.

================
Expiration Dates
================

The response cookie will possess an expiration date to inform the client at which point to stop sending the cookie back in requests. If the server time and client time differ, expect sessions to be unreliable. **Make sure the system time of your server is accurate**.

CherryPy defaults to a 60-minute session timeout, which also applies to the cookie which is sent to the client. Unfortunately, some versions of Safari ("4 public beta" on Windows XP at least) appear to have a bug in their parsing of the GMT expiration date--they appear to interpret the date as one hour in the past. Sixty minutes minus one hour is pretty close to zero, so you may experience this bug as a new session id for every request, unless the requests are less than one second apart. To fix, try increasing the session.timeout.

On the other extreme, some users report Firefox sending cookies after their expiration date, although this was on a system with an inaccurate system time. Maybe FF doesn't trust system time.




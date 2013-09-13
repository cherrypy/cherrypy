********************************
Securing CherryPy
********************************

There are several settings that can be enabled to make CherryPy pages more secure. These include:

    Transmitting data:

        #. Use Secure Cookies

    Rendering pages:

        #. Set HttpOnly cookies
        #. Set XFrame options
        #. Enable XSS Protection
        #. Set the Content Security Policy

An easy way to accomplish this is to set headers with a :doc:`Tool </tutorial/tools>` and wrap your entire CherryPy application with it::

    import cherrypy

    def secureheaders():
        headers = cherrypy.response.headers
        headers['X-Frame-Options'] = 'DENY'
        headers['X-XSS-Protection'] = '1; mode=block'
        headers['Content-Security-Policy'] = "default-src='self'"

    # set the priority according to your needs if you are hooking something
    # else on the 'before_finalize' hook point.
    cherrypy.tools.secureheaders = \
        cherrypy.Tool('before_finalize', secureheaders, priority=60)


Then, in the :doc:`configuration file </tutorial/config>` (or any other place that you want to enable the tool)::

    [/]
    tools.secureheaders.on = True


If you use :doc:`sessions </refman/lib/sessions>` you can also enable these settings::

    [/]
    tools.sessions.on = True
    # increase security on sessions
    tools.sessions.secure = True
    tools.sessions.httponly = True


If you use SSL you can also enable Strict Transport Security::

    #add this to secureheaders():
    headers['Strict-Transport-Security'] = 'max-age=31536000' # one year



Further Security Resources
==========================

For an introduction to webserver security see `Dan Callahan's presentation from PyCon CA 2013 <http://pyvideo.org/video/2315/quick-wins-for-better-website-security>`_.

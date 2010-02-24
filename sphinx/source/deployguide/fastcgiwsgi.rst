************
FastCGI WSGI
************

This is a HOWTO. See :doc:`apache` for a higher-level discussion.

A very simple setup lets your cherry run with FastCGI (on apache in my 
setup). You need just a running apache server with ``mod_fastcgi`` and 
`flup <http://www.saddi.com/software/flup/>`_.

CherryPy code
=============

hello.py::

    #python
    #!/usr/bin/python
    
    import cherrypy
    
    class HelloWorld:
        """ Sample request handler class. """
        def index(self):
            return "Hello world!"
        index.exposed = True
    
    cherrypy.tree.mount(HelloWorld())
    # CherryPy autoreload must be disabled for the flup server to work
    cherrypy.config.update({'engine.autoreload_on':False})

Then run the shiny new cherryd with the '-f' arg::

    cherryd -c <myconfig> -d -f -i hello.py

Apache config
=============

At the top level in httpd.conf::

    FastCgiIpcDir /tmp
    FastCgiServer /path/to/cherry.fcgi -idle-timeout 120 -processes 4

And inside the relevant VirtualHost section::

    # FastCGI config
    AddHandler fastcgi-script .fcgi
    ScriptAliasMatch (.*$) /path/to/cherry.fcgi$1

Lighttpd config
===============

For `Lighttpd <http://www.lighttpd.net/>`_ you can follow these 
instructions. Within ``lighttpd.conf`` make sure ``mod_fastcgi`` is 
active within ``server.modules``. Then, within your ``$HTTP["host"]`` 
directive, configure your fastcgi script like the following::

    $HTTP["url"] =~ "" {
      fastcgi.server = (
        "/" => (
          "script.fcgi" => (
            "bin-path" => "/path/to/your/script.fcgi",
            "socket"          => "/tmp/script.sock",
            "check-local"     => "disable",
            "disable-time"    => 1,
            "min-procs"       => 1,
            "max-procs"       => 1, # adjust as needed
          ),
        ),
      )
    } # end of $HTTP["url"] =~ "^/"

Please see `Lighttpd FastCGI Docs 
<http://trac.lighttpd.net/trac/wiki/Docs:ModFastCGI>`_ for an explanation 
of the possible configuration options.

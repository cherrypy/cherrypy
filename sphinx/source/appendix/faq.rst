.. _faq:

**************************
Frequently Asked Questions
**************************

General
=======

:Q: How fast is CherryPy ?

:A: Have a look at :doc:`/appendix/cherrypyspeed`.

:Q: When will it be added to the standard python library?

:A: Probably never. The standard python library is not the place to distribute
    an application server.

:Q: Who uses CherryPy?

:A: See :ref:`SuccessStories`.


Server Features and Configuration
=================================

:Q: How do I serve multiple domains on one host?

:A: You can use the :class:`cherrypy._cpdispatch.VirtualHost` dispatcher.

:Q: Does CherryPy support https?

:A: CherryPy has built-in SSL support as of 3.0.0beta. See the `ssl_*`
    properties of :mod:`cherrypy._cpserver`.
    
    Earlier versions do not have built-in SSL support, but Tim Evans has
    written a module called `SslCherry <http://tools.cherrypy.org/wiki/SSLWithM2Crypto>`_
    that uses M2Crypto for https support.  It's not quite ready for production
    use, but it looks promising.

:Q: Does CherryPy prevent cross-site scripting?

:A: See `Malicious HTML Tags Embedded in Client Web Requests <http://www.cert.org/advisories/CA-2000-02.html>`_
    and `Understanding Malicious Content Mitigation for Web Developers <http://www.cert.org/tech_tips/malicious_code_mitigation.html>`_
    at `CERT <http://www.cert.org/>`_ for an overview of Cross-Site Scripting
    (XSS) issues. It is ultimately up to the developer to remove potential XSS
    vulnerabilities from their apps and sites.

:Q: Why does CherryPy take CPU/RAM even though it's not yet receiving requests?

:A: CherryPy runs some tasks in the background by default, and some when you
    turn on certain tools. To strip CherryPy down to nothing, you might have to:
    
    * Turn off the :ref:`timeoutmonitor`
      via ``cherrypy.engine.timeout_monitor.unsubscribe()``.
    * Turn off the :class:`Autoreloader <cherrypy.process.plugins.Autoreloader>`
      via ``cherrypy.engine.autoreload.unsubscribe()``.
    * Examine the number of worker threads that WSGIServer uses.
      See :attr:`cherrypy._cpserver.Server.thread_pool`.

Development Questions
=====================

:Q: I can browse pages from my local machine, but not from other machines. What gives?

:A: Set the config entry `server.socket_host` to either your server name/IP,
    or to '0.0.0.0' to listen on all interfaces.
    See :mod:`cherrypy._cpserver` for more details.

:Q: How do I serve URL's with dots in them, like "/path/to/report.xml"?

:A: Two ways: 1) Convert the dots to underscores for your page handler names,
    e.g. ``def report_xml(self)``
    (see :ref:`defaultdispatcher`) or 2) use a :ref:`default method<defaultmethods>`.

:Q: How do I upload BIG files? (Or what is the best thing to do if I have many
    concurrent users uploading files?)

:A: Please see :doc:`/progguide/files/uploading` for examples.

:Q: Can I perform HTTP based authentication (.htaccess)?

:A: There are two tools implementing :rfc:`2617`: :doc:`/refman/lib/auth_digest`
    and :doc:`/refman/lib/auth_basic`.

:Q: What templating systems does CherryPy support? 

:A: All of them! One of the core idea of CherryPy is to be templating
    language independent. It is important to us to let developers keep
    their habits and preferred tools. Hence CherryPy does not favor any
    templating language. But for some ideas, see
    :doc:`/progguide/choosingtemplate` and the
    `Tools wiki <http://tools.cherrypy.org/wiki/>`_.

:Q: My default handler throws an exception complaining about the number of
    arguments. How to handle this?

:A: Suppose you have the following handler class setup: ::
    
        class Root:
            def project(self, id):
                data = db.query("project", id)
                return "Details for project %d: %r" % (id, data)
    
    and you want to provide project information based on urls of the form ::
    
        /project/123
    
    Here, 123 is a project id to search in a database. The above project()
    method will do the trick, but, when someone adds more arguments than the
    method expects, e.g. ::
    
        /project/123/456/789?x=blah
    
    those extra elements are passed on to the project() method as parameters, which 
    is not able to handle the extra arguments and results in an exception being thrown.
    
    You can catch this by appending ``*args``, ``**kwargs`` to the default()
    method's parameter list. This way, the values 456 and 789 in the example
    will be placed in the 'args' list and the 'kwargs' dictionary will contain
    the string 'blah' for the key 'x'. In the following example, we just
    ignore any extra params: ::
    
        class Root:
            def project(self, id, *args, **kwargs):
                data = db.query("project", id)
                return "Details for project %d: %r" % (id, data)

:Q: How do I publish objects with reserved Python names?

:A: Example: ::
    
        class SomeClass(object):
            def __init__(self):
                setattr(self, 'print', self._print)
                setattr(self, 'class', self._class)
           
            def _print(self):
                ...
            _print.exposed = True
           
            def _class(self):
                ...
            _class.exposed = True 
    
    Object attributes can have reserved names as long as you dynamically
    bind them so the Python parser doesn't choke on them.

:Q: How does CherryPy compare to projects like mod_python, Twisted, and Django?

:A: mod_python requires you to be running `Apache <http://httpd.apache.org/>`_.
    See http://www.modpython.org for more info. Since CherryPy 2.1, you can
    use mod_python as an interface to bridge CherryPy and Apache.
    
    Twisted is, well, twisted. You really have to spend the time to understand
    how the twisted framework works. It is deep and very powerful, but has a
    steep learning curve. CherryPy is, arguably, simpler to understand, due to
    its more traditional approach. Part of this comes from it not trying to do
    all the things that twisted does (SMTP, IRC, NNTP, etc etc). See
    http://twistedmatrix.com for more info.
    
    For a 3rd party discussion, refer to the
    `PyWebOff blog <http://pyre.third-bit.com/pyweb/index.html>`_ which concluded:
  
      "In no time at all, I was finished the library program. It took me
      significantly less time than it did with either of Quixote or Webware,
      and I'm very happy with the code that was produced. CherryPy needs more
      documenting, but otherwise it gets two enthusiastic thumbs up."

:Q: When you run cherrypy and two dudes browse your website at the same time,
    does cherrypy create two instances of your root object? How does that work?
    I don't get it.

:A: No, just one instance. It's no different than having two threads in any
    other Python application call the same method at the same time: each
    thread has its own set of local variables so they don't stomp each other.

:Q: How do I get CherryPy to work if I don't have root?

:A: Just append it to the path.  Put the following at the top of the files
    you need CherryPy for: ::
    
        import sys
        sys.path.append("your local dir path")

:Q: Can I change my root class, refresh my web page and see what is changed
    without restarting the CherryPy server?

:A: See :class:`cherrypy.process.plugins.Autoreloader`. Note that this solution
    works properly only if the changes you make are syntactically correct.
    Re-compilation errors will exit the entire application.


.. _faq:

**************************
Frequently Asked Questions
**************************

General
=======

  * How fast is CherryPy ?
      Have a look at this page (CP 2.0): [wiki:CherryPySpeed CherryPy speed]

  * When will it be added to the standard python library?
      Probably never. The standard python library is not the place to distribute an application server.

  * Who uses CherryPy?
    See :ref:`SuccessStories`.

Server Features and Configuration
=================================

  * How do I serve multiple domains on one host?
      You can use the virtual host filter as described [wiki:VirtualPathFilter here].

  * Does CherryPy support https?
      CherryPy has built-in SSL support as of 3.0.0beta. See the `ssl_*` properties at http://www.cherrypy.org/wiki/ServerObject.

      Earlier versions do not have built-in SSL support, but Tim Evans has written a module called [http://tools.cherrypy.org/wiki/SSLWithM2Crypto SslCherry] that uses M2Crypto for https support.  It's not quite ready for production use, but it looks promising.

  * Does CherryPy prevent cross-site scripting ?
      See [http://www.cert.org/advisories/CA-2000-02.html Malicious HTML Tags Embedded in Client Web Requests] and [http://www.cert.org/tech_tips/malicious_code_mitigation.html Understanding Malicious Content Mitigation for Web Developers] at [http://www.cert.org/ CERT] for an overview of Cross-Site Scripting (XSS) issues. It is ultimately up to the developer to remove potential XSS vulnerabilities from their apps and sites. 

Development Questions
=====================

  * I can browse pages from my local machine, but not from other machines. What gives?
      Set the config entry `server.socket_host` to either your server name/IP, or to '0.0.0.0' to listen on all interfaces. See ServerObject#Properties for more details.

  * How do I serve URL's with dots in them, like "/path/to/report.xml"?
      Two ways: 1) Convert the dots to underscores for your page handler names, e.g. `def report_xml(self)` (see PageHandlers#DefaultDispatcher) or 2) use a `default` method.

  * How do I upload BIG files? (Or what is the best thing to do if I have many concurrent users uploading files?)
      Please see the FileUpload page for examples.

  * Can I perform HTTP based authentication (.htaccess)?
      There are two filters implementing RFC 2617 : [wiki:DigestAuthFilter DigestAuthFilter] and [wiki:BasicAuthFilter BasicAuthFilter]

  * What templating systems does CherryPy support? 
      All of them! One of the core idea of CherryPy is to be templating language independent. It is important to us to let developers keep their habits and preferred tools. Hence CherryPy does not favor any templating language. But for some ideas, see [wiki:ChoosingATemplatingLanguage] and the [http://tools.cherrypy.org/wiki/ Tools] site.

  * My default handler throws an exception complaining about the number of arguments. How to handle this? (I assume cherrypy 2.0b here)
      Suppose you have the following handler class setup: ::

        #!python
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

      You can catch this by appending ``*args``, ``**kwargs`` to the default() method's parameter list. This way, the values 456 and 789 in the example will be placed in the 'args' list and the 'kwargs' dictionary will contain the string 'blah' for the key 'x'. In the following example, we just ignore any extra params: ::

        #!python
        class Root:
            def project(self, id, *args, **kwargs):
                data = db.query("project", id)
                return "Details for project %d: %r" % (id, data)

  * How do I publish objects with reserved Python names?
      Example ::
  
        #!python
        class SomeClass(object):
            def __init__(self):
                setattr(self,'print',self._print)
                setattr(self,'class',self._class)
       
            def _print(self):
                ...
            _print.exposed = True
       
            def _class(self):
                ...
            _class.exposed = True 

     (From cherrypy-users, an email by Remco Boerma)

  * How does CherryPy compare to projects like mod_python, Twisted, and Nevow?
      mod_python requires you to be running [http://httpd.apache.org/ Apache]. See http://www.modpython.org for more info. Since CherryPy 2.1, you can use mod_python as an interface to bridge CherryPy and Apache.

      Twisted is, well, twisted. You really have to spend the time to understand how the twisted framework works. It is deep and very powerful, but has a steep learning curve. CherryPy is, arguably, simpler to understand, due to its more traditional approach. Part of this comes from it not trying to do all the things that twisted does (SMTP, IRC, NNTP, etc etc). See http://twistedmatrix.com for more info.

      See [http://nevow.com/ Nevow's site] for more info. (Anyone have any experience with Nevow so we can have a better comparison with CherryPy?)

      For a 3rd party discussion, refer to the [http://pyre.third-bit.com/pyweb/index.html PyWebOff blog] which concluded:

        ''"In no time at all, I was finished the library program. It took me significantly less time than it did with either of Quixote or Webware, and I'm very happy with the code that was produced. CherryPy needs more documenting, but otherwise it gets two enthusiastic thumbs up."''

  * When you run cherrypy and two dudes browse your website at the same time, does cherrypy create two instances of your root object? How does that work? I don't get it.
      No, just one instance. It's no different than having two threads in any other Python application call the same method at the same time: each thread has its own set of local variables so they don't stomp each other.

  * How do I get CherryPy to work if I don't have root?
      Just append it to the path.  Put the following at the top of the files you need CherryPy for: ::

        #!python
        import sys
        sys.path.append("your local dir path")

  * Can I change my root class, refresh my web page and see what is changed without restarting the CherryPy server?
      See AutoReload. Note that this solution works properly only if the changes you make are syntactically correct. Re-compilation errors will exit the entire application.

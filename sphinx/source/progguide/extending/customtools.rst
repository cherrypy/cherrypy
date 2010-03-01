************
Custom Tools
************

CherryPy is an extremely capable platform for web application and framework
development. One of the strengths of CherryPy is its modular design; CherryPy
separates key-but-not-core functionality out into "tools". This provides two
benefits: a slimmer, faster core system and a supported means of tying
additional functionality into the framework.

Tools can be enabled for any point of your CherryPy application: a certain
path, a certain class, or even individual methods using the 
:ref:`_cp_config <cp_config>` dictionary. Tools can also be used as decorators
which provide syntactic sugar for configuring a tool for a specific callable.
See :doc:`/intro/concepts/tools` for more information on how to use Tools.
This document will show you how to make your own.

Your First Custom Tool
======================

Let's look at a very simple authorization tool::

    import cherrypy

    def protect(users):
        if cherrypy.request.login not in users:
            raise cherrypy.HTTPError("401 Unauthorized")

    cherrypy.tools.protect = Tool('on_start_resource', protect)

We can now enable it in the standard ways: a config file or dict passed to an
application, a :ref:`_cp_config<cp_config>` dict on a particular class or
callable or via use of the tool as a decorator. Here's how to turn it on in 
a config file::

    [/path/to/protected/resource]
    tools.protect.on = True
    tools.protect.users = ['me', 'myself', 'I']

Now let's look at the example tool a bit more closely.
Working from the bottom up, the :class:`cherrypy.Tool<cherrypy._cptools.Tool>`
constructor takes 2 required and 2 optional arguments.

point
-----

First, we need to declare the point in the CherryPy request/response 
handling process where we want our tool to be triggered. Different request
attributes are obtained and set at different points in the request process.
In this example, we'll run at the first *hook point*, called "on_start_resource".

.. _hooks:

Hooks
^^^^^

Tools package up *hooks*. When we created a Tool instance above, the Tool
class registered our `protect` function to run at the 'on_start_resource'
*hookpoint*. You can write code that runs at hookpoints without using a Tool
to help you, but you probably shouldn't. The Tool system allows your function
to be turned on and configured both via the CherryPy config system and via the
Tool itself as a decorator. You can also write a Tool that runs code at multiple
hook points.

Here is a quick rundown of the "hook points" that you can hang your tools on:

 * on_start_resource - The earliest hook; the Request-Line and request headers
   have been processed and a dispatcher has set request.handler and request.config.
 * before_request_body - Tools that are hooked up here run right before the
   request body would be processed.
 * before_handler - Right before the request.handler (the "exposed" callable
   that was found by the dispatcher) is called.
 * before_finalize - This hook is called right after the page handler has been
   processed and before CherryPy formats the final response object. It helps
   you for example to check for what could have been returned by your page
   handler and change some headers if needed.
 * on_end_resource - Processing is complete - the response is ready to be
   returned. This doesn't always mean that the request.handler (the exposed
   page handler) has executed! It may be a generator. If your tool absolutely
   needs to run after the page handler has produced the response body, you
   need to either use on_end_request instead, or wrap the response.body in a
   generator which applies your tool as the response body is being generated
   (what a mouthful--see
   `caching tee.output <http://www.cherrypy.org/browser/trunk/cherrypy/lib/caching.py>`_
   for an example).
 * before_error_response - Called right before an error response
   (status code, body) is set.
 * after_error_response - Called right after the error response
   (status code, body) is set and just before the error response is finalized.
 * on_end_request - The request/response conversation is over, all data has
   been written to the client, nothing more to see here, move along.


callable
--------

Second, we need to provide the function that will be called back at that
hook point.  Here, we provide our ``protect`` callable.  The Tool
class will find all config entries related to our tool and pass them as
keyword arguments to our callback.  Thus, if::

    'tools.protect.on' = True
    'tools.protect.users' = ['me', 'myself', 'I']

is set in the config, the users list will get passed to the Tool's callable.
[The 'on' config entry is special; it's never passed as a keyword argument.]

The tool can also be invoked as a decorator like this::

    @cherrypy.expose
    @cherrypy.tools.protect(users=['me', 'myself', 'I'])
    def resource(self):
        return "Hello, %s!" % cherrypy.request.login

name
----

This argument is optional as long as you set the Tool onto a Toolbox. That is::


    def foo():
        cherrypy.request.foo = True
    cherrypy.tools.TOOLNAME = cherrypy.Tool('on_start_resource', foo)

The above will set the 'name' arg for you (to 'TOOLNAME'). The only time you
would need to provide this argument is if you're bypassing the toolbox in some way.

priority
--------

This specifies a priority order (from 0 - 100) that determines the order in
which callbacks in the same hook point are called.  The lower the priority
number, the sooner it will run (that is, we call .sort(priority) on the list).
The default priority for a tool is set to 50 and most built-in tools use that
default value.

Custom Toolboxes
================

All of the builtin CherryPy tools are collected into a Toolbox called
:attr:`cherrypy.tools`. It responds to config entries in the "tools"
:ref:`namespace<namespaces>`. You can add your own Tools to this Toolbox
as described above.

You can also make your own Toolboxes if you need more modularity. For example,
you might create multiple Tools for working with JSON, or you might publish
a set of Tools covering authentication and authorization from which everyone
could benefit (hint, hint). Creating a new Toolbox is as simple as::

    # cpstuff/newauth.py
    import cherrypy

    # Create a new Toolbox.
    newauthtools = cherrypy._cptools.Toolbox("newauth")

    # Add a Tool to our new Toolbox.
    def check_access(default=False):
        if not getattr(cherrypy.request, "userid", default):
            raise cherrypy.HTTPError(401)
    newauthtools.check_access = cherrypy.Tool('before_request_body', check_access)

Then, in your application, use it just like you would use ``cherrypy.tools``,
with the additional step of registering your toolbox with your app.
Note that doing so automatically registers the "newauth" config namespace;
you can see the config entries in action below::

    import cherrypy
    from cpstuff import newauth


    class Root(object):
        def default(self):
            return "Hello"
        default.exposed = True

    conf = {'/demo': {
        'newauth.check_access.on': True,
        'newauth.check_access.default': True,
        }}

    app = cherrypy.tree.mount(Root(), config=conf)
    if hasattr(app, 'toolboxes'):
        # CherryPy 3.1+
        app.toolboxes['newauth'] = newauth.newauthtools

Just the Beginning
==================

Hopefully that information is enough to get you up and running and create some
simple but useful CherryPy tools.  Much more than what you have seen in this
tutorial is possible.  Also, remember to take advantage of the fact that CherryPy
is open source!  Check out :doc:`/progguide/builtintools` and the
:doc:`libraries</refman/lib/index>` that they are built upon.

In closing, here is a slightly more complicated tool that acts as a
"traffic meter" and triggers a callback if a certain traffic threshold is
exceeded within a certain time frame.  It should probably launch its own
watchdog thread that actually checks the log and triggers the alerts rather
than waiting on a request to do so, but I wanted to
keep it simple for the purpose of example::

    # traffictool.py
    import time

    import cherrypy


    class TrafficAlert(cherrypy.Tool):
        
        def __init__(self, listclass=list):
            """Initialize the TrafficAlert Tool with the given listclass."""

            # A ring buffer subclass of list would probably be a more robust
            # choice than a standard Python list.
            
            self._point = "on_start_resource"
            self._name = None
            self._priority = 50
            # set the args of self.callable as attributes on self
            self._setargs()
            # a log for storing our per-path traffic data
            self._log = {}
            # a history of the last alert for a given path
            self._history = {}
            self.__doc__ = self.callable.__doc__
            self._struct = listclass
            
        def log_hit(self, path):
            """Log the time of a hit to a unique sublog for the path."""
            log = self._log.setdefault(path, self._struct())
            log.append(time.time())

        def last_alert(self, path):
            """Returns the time of the last alert for path."""
            return self._history.get(path, 0)
        
        def check_alert(self, path, window, threshhold, delay, callback=None):
            # set the bar
            now = time.time()
            bar = now - window
            hits = [t for t in self._log[path] if t > bar]
            num_hits = len(hits)
            if num_hits > threshhold:
                if self.last_alert(path) + delay < now:
                    self._history[path] = now
                    if callback:
                        callback(path, window, threshhold, num_hits)
                    else:
                        msg = '%s - %s hits within the last %s seconds.'
                        msg = msg % (path, num_hits, window)
                        cherrypy.log.error(msg, 'TRAFFIC')

        def callable(self, window=60, threshhold=100, delay=30, callback=None):
            """Alert when traffic thresholds are exceeded.

            window: the time frame within which the threshhold applies
            threshhold: the number of hits within the window that will trigger
                        an alert
            delay: the delay between alerts
            callback: a callback that accepts(path, window, threshhold, num_hits)
            """
            
            path = cherrypy.request.path_info
            self.log_hit(path)
            self.check_alert(path, window, threshhold, delay, callback)


    cherrypy.tools.traffic_alert = TrafficAlert()

    if __name__ == '__main__':
        class Root(object):
            @cherrypy.expose
            def index(self):
                return "Hi!!"

            @cherrypy.expose
            @cherrypy.tools.traffic_alert(threshhold=5)
            def popular(self):
                return "A popular page."

        cherrypy.quickstart(Root())


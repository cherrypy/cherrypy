.. _extend:

Extend
------

CherryPy is truly an open framework, you can extend and plug
new functions at will either server-side or on a per-requests basis.
Either way, CherryPy is made to help you build your
application and support your architecture via simple patterns.

.. contents::
   :depth:  4

Server-wide functions
#####################

CherryPy can be considered both as a HTTP library
as much as a web application framework. In that latter case,
its architecture provides mechanisms to support operations
across the whole server instance. This offers a powerful
canvas to perform persistent operations as server-wide
functions live outside the request processing itself. They
are available to the whole process as long as the bus lives.

Typical use cases:

- Keeping a pool of connection to an external server so that
  your need not to re-open them on each request (database connections
  for instance).
- Background processing (say you need work to be done without
  blocking the whole request itself).


Publish/Subscribe pattern
^^^^^^^^^^^^^^^^^^^^^^^^^

CherryPy's backbone consists of a bus system implementing
a simple `publish/subscribe messaging pattern <http://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern>`_.
Simply put, in CherryPy everything is controlled via that bus.
One can easily picture the bus as a sushi restaurant's belt as in
the picture below.

.. image:: _static/images/sushibelt.JPG
   :target:  http://en.wikipedia.org/wiki/YO!_Sushi


You can subscribe and publish to channels on a bus. A channel is
bit like a unique identifier within the bus. When a message is
published to a channel, the bus will dispatch the message to
all subscribers for that channel.

One interesting aspect of a pubsub pattern is that it promotes
decoupling between a caller and the callee. A published message
will eventually generate a response but the publisher does not
know where that response came from.

Thanks to that decoupling, a CherryPy application can easily
access functionalities without having to hold a reference to
the entity providing that functionality. Instead, the
application simply publishes onto the bus and will receive
the appropriate response, which is all that matter.

.. _buspattern:

Typical pattern
~~~~~~~~~~~~~~~

Let's take the following dummy application:

.. code-block:: python

   import cherrypy

   class ECommerce(object):
       def __init__(self, db):
           self.mydb = db

       @cherrypy.expose
       def save_kart(self, cart_data):
           cart = Cart(cart_data)
           self.mydb.save(cart)

   if __name__ == '__main__':
      cherrypy.quickstart(ECommerce(), '/')

The application has a reference to the database but
this creates a fairly strong coupling between the
database provider and the application.

Another approach to work around the coupling is by
using a pubsub workflow:

.. code-block:: python

   import cherrypy

   class ECommerce(object):
       @cherrypy.expose
       def save_kart(self, cart_data):
           cart = Cart(cart_data)
           cherrypy.engine.publish('db-save', cart)

   if __name__ == '__main__':
      cherrypy.quickstart(ECommerce(), '/')

In this example, we publish a `cart` instance to
`db-save` channel. One or many subscribers can then
react to that message and the application doesn't
have to know about them.

.. note::

   This approach is not mandatory and it's up to you to
   decide how to design your entities interaction.


Implementation details
~~~~~~~~~~~~~~~~~~~~~~

CherryPy's bus implementation is simplistic as it registers
functions to channels. Whenever a message is published to
a channel, each registered function is applied with that
message passed as a parameter.

The whole behaviour happens synchronously and, in that sense,
if a subscriber takes too long to process a message, the
remaining subscribers will be delayed.

CherryPy's bus is not an advanced pubsub messaging broker
system such as provided by `zeromq <http://zeromq.org/>`_ or
`RabbitMQ <https://www.rabbitmq.com/>`_.
Use it with the understanding that it may have a cost.

.. _cpengine:

Engine as a pubsub bus
~~~~~~~~~~~~~~~~~~~~~~

As said earlier, CherryPy is built around a pubsub bus. All
entities that the framework manages at runtime are working on
top of a single bus instance, which is named the `engine`.

The bus implementation therefore provides a set of common
channels which describe the application's lifecycle:

.. code-block:: text

                        O
                        |
                        V
       STOPPING --> STOPPED --> EXITING -> X
          A   A         |
          |    \___     |
          |        \    |
          |         V   V
        STARTED <-- STARTING

The states' transitions trigger channels to be published
to so that subscribers can react to them.

One good example is the HTTP server which will tranisition
from a `"STOPPED"` stated to a `"STARTED"` state whenever
a message is published to the `start` channel.

Built-in channels
~~~~~~~~~~~~~~~~~

In order to support its life-cycle, CherryPy defines a set
of common channels that will be published to at various states:

- **"start"**: When the bus is in the `"STARTING"` state
- **"main"**: Periodically from the CherryPy's mainloop
- **"stop"**: When the bus is in the `"STOPPING"` state
- **"graceful"**: When the bus requests a reload of subscribers
- **"exit"**: When the bus is in the `"EXITING"` state

This channel will be published to by the `engine` automatically.
Register therefore any subscribers that would need to react
to the transition changes of the `engine`.

In addition, a few other channels are also published to during
the request processing.

- **"before_request"**: right before the request is processed by CherryPy
- **"after_request"**: right after it has been processed

Also, from the :class:`cherrypy.process.plugins.ThreadManager` plugin:

- **"acquire_thread"**
- **"start_thread"**
- **"stop_thread"**
- **"release_thread"**

Bus API
~~~~~~~

In order to work with the bus, the implementation
provides the following simple API:

- :meth:`cherrypy.engine.publish(channel, *args) <cherrypy.process.wspbus.Bus.publish>`:

 - The `channel` parameter is a string identifying the channel to
   which the message should be sent to

 - `*args` is the message and may contain any valid Python values or
   objects.

- :meth:`cherrypy.engine.subscribe(channel, callable) <cherrypy.process.wspbus.Bus.subscribe>`:

 - The `channel` parameter is a string identifying the channel the
   `callable` will be registered to.

 - `callable` is a Python function or method which signature must
   match what will be published.

- :meth:`cherrypy.engine.unsubscribe(channel, callable) <cherrypy.process.wspbus.Bus.unsubscribe>`:

 - The `channel` parameter is a string identifying the channel the
   `callable` was registered to.

 - `callable` is the Python function or method which was registered.

.. _busplugins:

Plugins
^^^^^^^

Plugins, simply put, are entities that play with the bus, either by
publishing or subscribing to channels, usually both at the same time.

.. important::

   Plugins are extremely useful whenever you have functionalities:

   - Available across the whole application server
   - Associated to the application's life-cycle
   - You want to avoid being strongly coupled to the application

Create a plugin
~~~~~~~~~~~~~~~

A typical plugin looks like this:

.. code-block:: python

   import cherrypy
   from cherrypy.process import wspbus, plugins

   class DatabasePlugin(plugins.SimplePlugin):
       def __init__(self, bus, db_klass):
           plugins.SimplePlugin.__init__(self, bus)
           self.db = db_klass()

       def start(self):
           self.bus.log('Starting up DB access')
           self.bus.subscribe("db-save", self.save_it)

       def stop(self):
           self.bus.log('Stopping down DB access')
           self.bus.unsubscribe("db-save", self.save_it)

       def save_it(self, entity):
           self.db.save(entity)

The :class:`cherrypy.process.plugins.SimplePlugin` is a helper
class provided by CherryPy that will automatically subscribe
your `start` and `stop` methods to the related channels.

When the `start` and `stop` channels are published on, those
methods are called accordingly.

Notice then how our plugin subscribes to the `db-save`
channel so that the bus can dispatch messages to the plugin.

Enable a plugin
~~~~~~~~~~~~~~~

To enable the plugin, it has to be registered to the the
bus as follows:

.. code-block:: python

   DatabasePlugin(cherrypy.engine, SQLiteDB).subscribe()

The `SQLiteDB` here is a fake class that is used as our
database provider.

Disable a plugin
~~~~~~~~~~~~~~~~

You can also unregister a plugin as follows:

.. code-block:: python

   someplugin.unsubscribe()

This is often used when you want to prevent the default
HTTP server from being started by CherryPy, for instance
if you run on top of a different HTTP server (WSGI capable):

.. code-block:: python

   cherrypy.server.unsubscribe()

Let's see an example using this default application:

.. code-block:: python

   import cherrypy

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "hello world"

   if __name__ == '__main__':
       cherrypy.quickstart(Root())

For instance, this is what you would see when running
this application:

.. code-block:: python

   [27/Apr/2014:13:04:07] ENGINE Listening for SIGHUP.
   [27/Apr/2014:13:04:07] ENGINE Listening for SIGTERM.
   [27/Apr/2014:13:04:07] ENGINE Listening for SIGUSR1.
   [27/Apr/2014:13:04:07] ENGINE Bus STARTING
   [27/Apr/2014:13:04:07] ENGINE Started monitor thread 'Autoreloader'.
   [27/Apr/2014:13:04:08] ENGINE Serving on http://127.0.0.1:8080
   [27/Apr/2014:13:04:08] ENGINE Bus STARTED

Now let's unsubscribe the HTTP server:

.. code-block:: python

   import cherrypy

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "hello world"

   if __name__ == '__main__':
       cherrypy.server.unsubscribe()
       cherrypy.quickstart(Root())

This is what we get:

.. code-block:: python

   [27/Apr/2014:13:08:06] ENGINE Listening for SIGHUP.
   [27/Apr/2014:13:08:06] ENGINE Listening for SIGTERM.
   [27/Apr/2014:13:08:06] ENGINE Listening for SIGUSR1.
   [27/Apr/2014:13:08:06] ENGINE Bus STARTING
   [27/Apr/2014:13:08:06] ENGINE Started monitor thread 'Autoreloader'.
   [27/Apr/2014:13:08:06] ENGINE Bus STARTED

As you can see, the server is not started. The missing:

.. code-block:: python

   [27/Apr/2014:13:04:08] ENGINE Serving on http://127.0.0.1:8080

Per-request functions
#####################

One of the most common task in a web application development
is to tailor the request's processing to the runtime context.

Within CherryPy, this is performed via what are called `tools`.
If you are familiar with Django or WSGI middlewares,
CherryPy tools are similar in spirit.
They add functions that are applied during the
request/response processing.

.. _hookpoint:

Hook point
^^^^^^^^^^

A hook point is a point during the request/response processing.

Here is a quick rundown of the "hook points" that you can hang your tools on:

 * **"on_start_resource"** - The earliest hook; the Request-Line and request headers
   have been processed and a dispatcher has set request.handler and request.config.
 * **"before_request_body"** - Tools that are hooked up here run right before the
   request body would be processed.
 * **"before_handler"** - Right before the request.handler (the :term:`exposed` callable
   that was found by the dispatcher) is called.
 * **"before_finalize"** - This hook is called right after the page handler has been
   processed and before CherryPy formats the final response object. It helps
   you for example to check for what could have been returned by your page
   handler and change some headers if needed.
 * **"on_end_resource"** - Processing is complete - the response is ready to be
   returned. This doesn't always mean that the request.handler (the exposed
   page handler) has executed! It may be a generator. If your tool absolutely
   needs to run after the page handler has produced the response body, you
   need to either use on_end_request instead, or wrap the response.body in a
   generator which applies your tool as the response body is being generated.
 * **"before_error_response"** - Called right before an error response
   (status code, body) is set.
 * **"after_error_response"** - Called right after the error response
   (status code, body) is set and just before the error response is finalized.
 * **"on_end_request"** - The request/response conversation is over, all data has
   been written to the client, nothing more to see here, move along.

.. _tools:

Tools
^^^^^

A tool is a simple callable object (function, method, object
implementing a `__call__` method) that is attached to a
:ref:`hook point <hookpoint>`.

Below is a simple tool that is attached to the `before_finalize`
hook point, hence after the page handler was called:

.. code-block:: python

   @cherrypy.tools.register('before_finalize')
   def logit():
      print(cherrypy.request.remote.ip)

Tools can also be created and assigned manually.
The decorator registration is equivalent to:

.. code-block:: python

   cherrypy.tools.logit = cherrypy.Tool('before_finalize', logit)

Using that tool is as simple as follows:

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       @cherrypy.tools.logit()
       def index(self):
           return "hello world"

Obviously the tool may be declared the
:ref:`other usual ways <perappconf>`.

.. note::

   The name of the tool, technically the attribute set to `cherrypy.tools`,
   does not have to match the name of the callable. However, it is
   that name that will be used in the configuration to refer to that
   tool.

Stateful tools
~~~~~~~~~~~~~~

The tools mechanism is really flexible and enables
rich per-request functionalities.

Straight tools as shown in the previous section are
usually good enough. However, if your workflow
requires some sort of state during the request processing,
you will probably want a class-based approach:

.. code-block:: python

    import time

    import cherrypy

    class TimingTool(cherrypy.Tool):
        def __init__(self):
            cherrypy.Tool.__init__(self, 'before_handler',
                                   self.start_timer,
                                   priority=95)

        def _setup(self):
            cherrypy.Tool._setup(self)
            cherrypy.request.hooks.attach('before_finalize',
                                          self.end_timer,
                                          priority=5)

        def start_timer(self):
            cherrypy.request._time = time.time()

        def end_timer(self):
            duration = time.time() - cherrypy.request._time
            cherrypy.log("Page handler took %.4f" % duration)

    cherrypy.tools.timeit = TimingTool()

This tool computes the time taken by the page handler
for a given request. It stores the time at which the handler
is about to get called and logs the time difference
right after the handler returned its result.

The import bits is that the :class:`cherrypy.Tool <cherrypy._cptools.Tool>` constructor
allows you to register to a hook point but, to attach the
same tool to a different hook point, you must use the
:meth:`cherrypy.request.hooks.attach <cherrypy._cprequest.HookMap.attach>` method.
The :meth:`cherrypy.Tool._setup <cherrypy._cptools.Tool._setup>`
method is automatically called by CherryPy when the tool
is applied to the request.

Next, let's see how to use our tool:

.. code-block:: python

    class Root(object):
        @cherrypy.expose
        @cherrypy.tools.timeit()
        def index(self):
            return "hello world"

Tools ordering
~~~~~~~~~~~~~~

Since you can register many tools at the same hookpoint,
you may wonder in which order they will be applied.

CherryPy offers a deterministic, yet so simple, mechanism
to do so. Simply set the **priority** attribute to a value
from 1 to 100, lower values providing greater priority.

If you set the same priority for several tools, they will
be called in the order you declare them in your configuration.

Toolboxes
~~~~~~~~~

All of the builtin CherryPy tools are collected into a Toolbox called
:attr:`cherrypy.tools`. It responds to config entries in the ``"tools"``
:ref:`namespace<namespaces>`. You can add your own Tools to this Toolbox
as described above.

You can also make your own Toolboxes if you need more modularity. For example,
you might create multiple Tools for working with JSON, or you might publish
a set of Tools covering authentication and authorization from which everyone
could benefit (hint, hint). Creating a new Toolbox is as simple as:

.. code-block:: python

    import cherrypy

    # Create a new Toolbox.
    newauthtools = cherrypy._cptools.Toolbox("newauth")

    # Add a Tool to our new Toolbox.
    @newauthtools.register('before_request_body')
    def check_access(default=False):
        if not getattr(cherrypy.request, "userid", default):
            raise cherrypy.HTTPError(401)

Then, in your application, use it just like you would use ``cherrypy.tools``,
with the additional step of registering your toolbox with your app.
Note that doing so automatically registers the ``"newauth"`` config namespace;
you can see the config entries in action below:

.. code-block:: python

    import cherrypy

    class Root(object):
        @cherrypy.expose
        def default(self):
            return "Hello"

    conf = {
       '/demo': {
           'newauth.check_access.on': True,
           'newauth.check_access.default': True,
        }
    }

    app = cherrypy.tree.mount(Root(), config=conf)

Request parameters manipulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

HTTP uses strings to carry data between two endpoints.
However your application may make better use of richer
object types. As it wouldn't be really readable, nor
a good idea regarding maintenance, to let each page handler
deserialize data, it's a common pattern to delegate
this functions to tools.

For instance, let's assume you have a user id in the query-string
and some user data stored into a database. You could
retrieve the data, create an object and pass it on to the
page handler instead of the user id.


.. code-block:: python

    import cherrypy

    class UserManager(cherrypy.Tool):
        def __init__(self):
            cherrypy.Tool.__init__(self, 'before_handler',
                                   self.load, priority=10)

        def load(self):
            req = cherrypy.request

            # let's assume we have a db session
            # attached to the request somehow
            db = req.db

            # retrieve the user id and remove it
            # from the request parameters
            user_id = req.params.pop('user_id')
            req.params['user'] = db.get(int(user_id))

    cherrypy.tools.user = UserManager()


    class Root(object):
        @cherrypy.expose
        @cherrypy.tools.user()
        def index(self, user):
            return "hello %s" % user.name

In other words, CherryPy give you the power to:

- inject data, that wasn't part of the initial request, into the page handler
- remove data as well
- convert data into a different, more useful, object to remove that burden
  from the page handler itself

.. _dispatchers:

Tailored dispatchers
####################

Dispatching is the art of locating the appropriate page handler
for a given request. Usually, dispatching is based on the
request's URL, the query-string and, sometimes, the request's method
(GET, POST, etc.).

Based on this, CherryPy comes with various dispatchers already.

In some cases however, you will need a little more. Here is an example
of dispatcher that will always ensure the incoming URL leads
to a lower-case page handler.

.. code-block:: python

    import random
    import string

    import cherrypy
    from cherrypy._cpdispatch import Dispatcher

    class StringGenerator(object):
       @cherrypy.expose
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))

    class ForceLowerDispatcher(Dispatcher):
        def __call__(self, path_info):
            return Dispatcher.__call__(self, path_info.lower())

    if __name__ == '__main__':
        conf = {
            '/': {
                'request.dispatch': ForceLowerDispatcher(),
            }
        }
        cherrypy.quickstart(StringGenerator(), '/', conf)

Once you run this snippet, go to:

- http://localhost:8080/generate?length=8
- http://localhost:8080/GENerAte?length=8

In both cases, you will be led to the `generate` page
handler. Without our home-made dispatcher, the second
one would fail and return a 404 error (:rfc:`2616#sec10.4.5`).

Tool or dispatcher?
^^^^^^^^^^^^^^^^^^^

In the previous example, why not simply use a tool? Well, the sooner
a tool can be called is always after the page handler has been found.
In our example, it would be already too late as the default dispatcher
would have not even found a match for `/GENerAte`.

A dispatcher exists mostly to determine the best page
handler to serve the requested resource.

On the other hand, tools are there to adapt the request's processing
to the runtime context of the application and the request's content.

Usually, you will have to write a dispatcher only if you
have a very specific use case to locate the most adequate
page handler. Otherwise, the default ones will likely suffice.

Request body processors
#######################

Since its 3.2 release, CherryPy provides a really elegant
and powerful mechanism to deal with a request's body based
on its mimetype. Refer to the :mod:`cherrypy._cpreqbody` module
to understand how to implement your own processors.

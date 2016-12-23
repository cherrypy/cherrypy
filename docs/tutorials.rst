.. _tutorials:

Tutorials
---------


This tutorial will walk you through basic but complete CherryPy applications
that will show you common concepts as well as slightly more advanced ones.

.. contents::
   :depth:  4

Tutorial 1: A basic web application
###################################

The following example demonstrates the most basic application
you could write with CherryPy. It starts a server and hosts
an application that will be served at request reaching
http://127.0.0.1:8080/

.. code-block:: python
   :linenos:

   import cherrypy


   class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello world!"


   if __name__ == '__main__':
       cherrypy.quickstart(HelloWorld())

Store this code snippet into a file named `tut01.py` and
execute it as follows:

.. code-block:: bash

   $ python tut01.py

This will display something along the following:

.. code-block:: text
   :linenos:

   [24/Feb/2014:21:01:46] ENGINE Listening for SIGHUP.
   [24/Feb/2014:21:01:46] ENGINE Listening for SIGTERM.
   [24/Feb/2014:21:01:46] ENGINE Listening for SIGUSR1.
   [24/Feb/2014:21:01:46] ENGINE Bus STARTING
   CherryPy Checker:
   The Application mounted at '' has an empty config.

   [24/Feb/2014:21:01:46] ENGINE Started monitor thread 'Autoreloader'.
   [24/Feb/2014:21:01:46] ENGINE Started monitor thread '_TimeoutMonitor'.
   [24/Feb/2014:21:01:46] ENGINE Serving on http://127.0.0.1:8080
   [24/Feb/2014:21:01:46] ENGINE Bus STARTED

This tells you several things. The first three lines indicate
the server will handle :mod:`signal` for you. The next line tells you
the current state of the server, as that
point it is in `STARTING` stage. Then, you are notified your
application has no specific configuration set to it.
Next, the server starts a couple of internal utilities that
we will explain later. Finally, the server indicates it is now
ready to accept incoming communications as it listens on
the address `127.0.0.1:8080`. In other words, at that stage your
application is ready to be used.

Before moving on, let's discuss the message
regarding the lack of configuration. By default, CherryPy has
a feature which will review the syntax correctness of settings
you could provide to configure the application. When none are
provided, a warning message is thus displayed in the logs. That
log is harmless and will not prevent CherryPy from working. You
can refer to :ref:`the documentation above <perappconf>` to
understand how to set the configuration.

Tutorial 2: Different URLs lead to different functions
######################################################

Your applications will obviously handle more than a single URL.
Let's imagine you have an application that generates a random
string each time it is called:

.. code-block:: python
   :linenos:

   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return "Hello world!"

       @cherrypy.expose
       def generate(self):
           return ''.join(random.sample(string.hexdigits, 8))


   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut02.py` and run it as follows:

.. code-block:: bash

   $ python tut02.py

Go now to http://localhost:8080/generate and your browser
will display a random string.

Let's take a minute to decompose what's happening here. This is the
URL that you have typed into your browser: http://localhost:8080/generate

This URL contains various parts:

- `http://` which roughly indicates it's a URL using the HTTP protocol (see :rfc:`2616`).
- `localhost:8080` is the server's address. It's made of a hostname and a port.
- `/generate` which is the path segment of the URL. This is what CherryPy uses to
  locate an :term:`exposed` function or method to respond.

Here CherryPy uses the `index()` method to handle `/` and the
`generate()` method to handle `/generate`

.. _tut03:

Tutorial 3: My URLs have parameters
###################################

In the previous tutorial, we have seen how to create an application
that could generate a random string. Let's now assume you wish
to indicate the length of that string dynamically.

.. code-block:: python
   :linenos:

   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return "Hello world!"

       @cherrypy.expose
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))


   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut03.py` and run it as follows:

.. code-block:: bash

   $ python tut03.py

Go now to http://localhost:8080/generate?length=16 and your browser
will display a generated string of length 16. Notice how
we benefit from Python's default arguments' values to support
URLs such as http://localhost:8080/generate still.

In a URL such as this one, the section after `?` is called a
query-string. Traditionally, the query-string is used to
contextualize the URL by passing a set of (key, value) pairs. The
format for those pairs is `key=value`. Each pair being
separated by a `&` character.

Notice how we have to convert the given `length` value to
an integer. Indeed, values are sent out from the client
to our server as strings.

Much like CherryPy maps URL path segments to exposed functions,
query-string keys are mapped to those exposed function parameters.

.. _tut04:

Tutorial 4: Submit this form
############################

CherryPy is a web framework upon which you build web applications.
The most traditional shape taken by applications is through
an HTML user-interface speaking to your CherryPy server.

Let's see how to handle HTML forms via the following
example.

.. code-block:: python
   :linenos:

   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return """<html>
             <head></head>
             <body>
               <form method="get" action="generate">
                 <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
               </form>
             </body>
           </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))


   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut04.py` and run it as follows:

.. code-block:: bash

   $ python tut04.py

Go now to http://localhost:8080/ and your browser and this will
display a simple input field to indicate the length of the string
you want to generate.

Notice that in this example, the form uses the `GET` method and
when you pressed the `Give it now!` button, the form is sent using the
same URL as in the :ref:`previous <tut03>` tutorial. HTML forms also support the
`POST` method, in that case the query-string is not appended to the
URL but it sent as the body of the client's request to the server.
However, this would not change your application's exposed method because
CherryPy handles both the same way and uses the exposed's handler
parameters to deal with the query-string (key, value) pairs.

.. _tut05:

Tutorial 5: Track my end-user's activity
########################################

It's not uncommon that an application needs to follow the
user's activity for a while. The usual mechanism is to use
a `session identifier <http://en.wikipedia.org/wiki/Session_(computer_science)#HTTP_session_token>`_
that is carried during the conversation between the user and
your application.

.. code-block:: python
   :linenos:

   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return """<html>
             <head></head>
             <body>
               <form method="get" action="generate">
                 <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
               </form>
             </body>
           </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       @cherrypy.expose
       def display(self):
           return cherrypy.session['mystring']


   if __name__ == '__main__':
       conf = {
           '/': {
               'tools.sessions.on': True
           }
       }
       cherrypy.quickstart(StringGenerator(), '/', conf)

Save this into a file named `tut05.py` and run it as follows:

.. code-block:: bash

   $ python tut05.py

In this example, we generate the string as in the
:ref:`previous <tut04>` tutorial but also store it in the current
session. If you go to http://localhost:8080/, generate a
random string, then go to http://localhost:8080/display, you
will see the string you just generated.

The lines 30-34 show you how to enable the session support
in your CherryPy application. By default, CherryPy will save
sessions in the process's memory. It supports more persistent
:ref:`backends <basicsession>` as well.

Tutorial 6: What about my javascripts, CSS and images?
######################################################

Web applications are usually also made of static content such
as javascript, CSS files or images. CherryPy provides support
to serve static content to end-users.

Let's assume, you want to associate a stylesheet with your
application to display a blue background color (why not?).

First, save the following stylesheet into a file named `style.css`
and stored into a local directory `public/css`.

.. code-block:: css
   :linenos:

   body {
     background-color: blue;
   }

Now let's update the HTML code so that we link to the stylesheet
using the http://localhost:8080/static/css/style.css URL.

.. code-block:: python
   :linenos:

   import os, os.path
   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return """<html>
             <head>
               <link href="/static/css/style.css" rel="stylesheet">
             </head>
             <body>
               <form method="get" action="generate">
                 <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
               </form>
             </body>
           </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       @cherrypy.expose
       def display(self):
           return cherrypy.session['mystring']


   if __name__ == '__main__':
       conf = {
           '/': {
               'tools.sessions.on': True,
               'tools.staticdir.root': os.path.abspath(os.getcwd())
           },
           '/static': {
               'tools.staticdir.on': True,
               'tools.staticdir.dir': './public'
           }
       }
       cherrypy.quickstart(StringGenerator(), '/', conf)


Save this into a file named `tut06.py` and run it as follows:

.. code-block:: bash

   $ python tut06.py

Going to http://localhost:8080/, you should be greeted by a flashy blue color.

CherryPy provides support to serve a single file or a complete
directory structure. Most of the time, this is what you'll end
up doing so this is what the code above demonstrates. First, we
indicate the `root` directory of all of our static content. This
must be an absolute path for security reason. CherryPy will
complain if you provide only relative paths when looking for a
match to your URLs.

Then we indicate that all URLs which path segment starts with `/static`
will be served as static content. We map that URL to the `public`
directory, a direct child of the `root` directory. The entire
sub-tree of the `public` directory will be served as static content.
CherryPy will map URLs to path within that directory. This is why
`/static/css/style.css` is found in `public/css/style.css`.

Tutorial 7: Give us a REST
##########################

It's not unusual nowadays that web applications expose some sort
of datamodel or computation functions. Without going into
its details, one strategy is to follow the `REST principles
edicted by Roy T. Fielding
<http://www.ibm.com/developerworks/library/ws-restful/index.html>`_.

Roughly speaking, it assumes that you can identify a resource
and that you can address that resource through that identifier.

"What for?" you may ask. Well, mostly, these principles are there
to ensure that you decouple, as best as you can, the entities
your application expose from the way they are manipulated or
consumed. To embrace this point of view, developers will
usually design a web API that expose pairs of `(URL, HTTP method, data, constraints)`.

.. note::

   You will often hear REST and web API together. The former is
   one strategy to provide the latter. This tutorial will not go
   deeper in that whole web API concept as it's a much more
   engaging subject, but you ought to read more about it online.


Lets go through a small example of a very basic web API
mildly following REST principles.

.. code-block:: python
   :linenos:

   import random
   import string

   import cherrypy


   @cherrypy.expose
   class StringGeneratorWebService(object):

       @cherrypy.tools.accept(media='text/plain')
       def GET(self):
           return cherrypy.session['mystring']

       def POST(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       def PUT(self, another_string):
           cherrypy.session['mystring'] = another_string

       def DELETE(self):
           cherrypy.session.pop('mystring', None)


   if __name__ == '__main__':
       conf = {
           '/': {
               'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
               'tools.sessions.on': True,
               'tools.response_headers.on': True,
               'tools.response_headers.headers': [('Content-Type', 'text/plain')],
           }
       }
       cherrypy.quickstart(StringGeneratorWebService(), '/', conf)


Save this into a file named `tut07.py` and run it as follows:

.. code-block:: bash

   $ python tut07.py

Before we see it in action, let's explain a few things. Until now,
CherryPy was creating a tree of exposed methods that were used to
match URLs. In the case of our web API, we want to stress the role
played by the actual requests' HTTP methods. So we created
methods that are named after them and they are all exposed at once
by decorating the class itself with `cherrypy.expose`.

However, we must then switch from the default mechanism of matching
URLs to method for one that is aware of the whole HTTP method
shenanigan. This is what goes on line 27 where we create
a :class:`~cherrypy.dispatch.MethodDispatcher` instance.

Then we force the responses `content-type` to be `text/plain` and
we finally ensure that `GET` requests will only be responded to clients
that accept that `content-type` by having a `Accept: text/plain`
header set in their request. However, we do this only for that
HTTP method as it wouldn't have much meaning on the other methods.


For the purpose of this tutorial, we will be using a Python client
rather than your browser as we wouldn't be able to actually try
our web API otherwise.

Please install `requests <http://www.python-requests.org/en/latest/>`_
through the following command:

.. code-block:: bash

   $ pip install requests

Then fire up a Python terminal and try the following commands:

.. code-block:: pycon
   :linenos:

   >>> import requests
   >>> s = requests.Session()
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code
   500
   >>> r = s.post('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'04A92138')
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'04A92138')
   >>> r = s.get('http://127.0.0.1:8080/', headers={'Accept': 'application/json'})
   >>> r.status_code
   406
   >>> r = s.put('http://127.0.0.1:8080/', params={'another_string': 'hello'})
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'hello')
   >>> r = s.delete('http://127.0.0.1:8080/')
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code
   500

The first and last `500` responses stem from the fact that, in
the first case, we haven't yet generated a string through `POST` and,
on the latter case, that it doesn't exist after we've deleted it.

Lines 12-14 show you how the application reacted when our client requested
the generated string as a JSON format. Since we configured the
web API to only support plain text, it returns the appropriate
`HTTP error code <http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.7>`_.


.. note::

   We use the `Session <http://www.python-requests.org/en/latest/user/advanced/#session-objects>`_
   interface of `requests` so that it takes care of carrying the
   session id stored in the request cookie in each subsequent
   request. That is handy.

.. important::

   It's all about RESTful URLs these days, isn't it?

   It is likely your URL will be made of dynamic parts that you
   will not be able to match to page handlers. For example,
   ``/library/12/book/15`` cannot be directly handled by the
   default CherryPy dispatcher since the segments ``12`` and
   ``15`` will not be matched to any Python callable.

   This can be easily workaround with two handy CherryPy features
   explained in the :ref:`advanced section <restful>`.



.. _tut08:


Tutorial 8: Make it smoother with Ajax
######################################

In the recent years, web applications have moved away from the
simple pattern of "HTML forms + refresh the whole page". This
traditional scheme still works very well but users have become used
to web applications that don't refresh the entire page.
Broadly speaking, web applications carry code performed
client-side that can speak with the backend without having to
refresh the whole page.

This tutorial will involve a little more code this time around. First,
let's see our CSS stylesheet located in `public/css/style.css`.

.. code-block:: css
   :linenos:

   body {
     background-color: blue;
   }

   #the-string {
     display: none;
   }

We're adding a simple rule about the element that will display
the generated string. By default, let's not show it up.
Save the following HTML code into a file named `index.html`.

.. code-block:: html
   :linenos:

   <!DOCTYPE html>
   <html>
     <head>
       <link href="/static/css/style.css" rel="stylesheet">
       <script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
       <script type="text/javascript">
         $(document).ready(function() {

           $("#generate-string").click(function(e) {
             $.post("/generator", {"length": $("input[name='length']").val()})
              .done(function(string) {
               $("#the-string").show();
               $("#the-string input").val(string);
             });
             e.preventDefault();
           });

           $("#replace-string").click(function(e) {
             $.ajax({
               type: "PUT",
               url: "/generator",
               data: {"another_string": $("#the-string input").val()}
             })
             .done(function() {
               alert("Replaced!");
             });
             e.preventDefault();
           });

           $("#delete-string").click(function(e) {
             $.ajax({
               type: "DELETE",
               url: "/generator"
             })
             .done(function() {
               $("#the-string").hide();
             });
             e.preventDefault();
           });

         });
       </script>
     </head>
     <body>
       <input type="text" value="8" name="length"/>
       <button id="generate-string">Give it now!</button>
       <div id="the-string">
         <input type="text" />
         <button id="replace-string">Replace</button>
         <button id="delete-string">Delete it</button>
       </div>
     </body>
   </html>

We'll be using the `jQuery framework <http://jquery.com/>`_
out of simplicity but feel free to replace it with your
favourite tool. The page is composed of simple HTML elements
to get user input and display the generated string. It also
contains client-side code to talk to the backend API that
actually performs the hard work.

Finally, here's the application's code that serves the
HTML page above and responds to requests to generate strings.
Both are hosted by the same application server.

.. code-block:: python
   :linenos:

   import os, os.path
   import random
   import string

   import cherrypy


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return open('index.html')


   @cherrypy.expose
   class StringGeneratorWebService(object):

       @cherrypy.tools.accept(media='text/plain')
       def GET(self):
           return cherrypy.session['mystring']

       def POST(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       def PUT(self, another_string):
           cherrypy.session['mystring'] = another_string

       def DELETE(self):
           cherrypy.session.pop('mystring', None)


   if __name__ == '__main__':
       conf = {
           '/': {
               'tools.sessions.on': True,
               'tools.staticdir.root': os.path.abspath(os.getcwd())
           },
           '/generator': {
               'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
               'tools.response_headers.on': True,
               'tools.response_headers.headers': [('Content-Type', 'text/plain')],
           },
           '/static': {
               'tools.staticdir.on': True,
               'tools.staticdir.dir': './public'
           }
       }
       webapp = StringGenerator()
       webapp.generator = StringGeneratorWebService()
       cherrypy.quickstart(webapp, '/', conf)

Save this into a file named `tut08.py` and run it as follows:

.. code-block:: bash

   $ python tut08.py

Go to http://127.0.0.1:8080/ and play with the input and buttons
to generate, replace or delete the strings. Notice how the page
isn't refreshed, simply part of its content.

Notice as well how your frontend converses with the backend using
a straightfoward, yet clean, web service API. That same API
could easily be used by non-HTML clients.

.. _tut09:

Tutorial 9: Data is all my life
###############################

Until now, all the generated strings were saved in the
session, which by default is stored in the process memory. Though,
you can persist sessions on disk or in a distributed memory store,
this is not the right way of keeping your data on the long run.
Sessions are there to identify your user and carry as little
amount of data as necessary for the operation carried by the user.

To store, persist and query data you need a proper database server.
There exist many to choose from with various paradigm support:

- relational: PostgreSQL, SQLite, MariaDB, Firebird
- column-oriented: HBase, Cassandra
- key-store: redis, memcached
- document oriented: Couchdb, MongoDB
- graph-oriented: neo4j

Let's focus on the relational ones since they are the most common
and probably what you will want to learn first.

For the sake of reducing the number of dependencies for these
tutorials, we will go for the :mod:`sqlite` database which
is directly supported by Python.

Our application will replace the storage of the generated
string from the session to a SQLite database. The application
will have the same HTML code as :ref:`tutorial 08 <tut08>`.
So let's simply focus on the application code itself:

.. code-block:: python
   :linenos:

   import os, os.path
   import random
   import sqlite3
   import string
   import time

   import cherrypy

   DB_STRING = "my.db"


   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return open('index.html')


   @cherrypy.expose
   class StringGeneratorWebService(object):

       @cherrypy.tools.accept(media='text/plain')
       def GET(self):
           with sqlite3.connect(DB_STRING) as c:
               cherrypy.session['ts'] = time.time()
               r = c.execute("SELECT value FROM user_string WHERE session_id=?",
                             [cherrypy.session.id])
               return r.fetchone()

       def POST(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           with sqlite3.connect(DB_STRING) as c:
               cherrypy.session['ts'] = time.time()
               c.execute("INSERT INTO user_string VALUES (?, ?)",
                         [cherrypy.session.id, some_string])
           return some_string

       def PUT(self, another_string):
           with sqlite3.connect(DB_STRING) as c:
               cherrypy.session['ts'] = time.time()
               c.execute("UPDATE user_string SET value=? WHERE session_id=?",
                         [another_string, cherrypy.session.id])

       def DELETE(self):
           cherrypy.session.pop('ts', None)
           with sqlite3.connect(DB_STRING) as c:
               c.execute("DELETE FROM user_string WHERE session_id=?",
                         [cherrypy.session.id])


   def setup_database():
       """
       Create the `user_string` table in the database
       on server startup
       """
       with sqlite3.connect(DB_STRING) as con:
           con.execute("CREATE TABLE user_string (session_id, value)")


   def cleanup_database():
       """
       Destroy the `user_string` table from the database
       on server shutdown.
       """
       with sqlite3.connect(DB_STRING) as con:
           con.execute("DROP TABLE user_string")


   if __name__ == '__main__':
       conf = {
           '/': {
               'tools.sessions.on': True,
               'tools.staticdir.root': os.path.abspath(os.getcwd())
           },
           '/generator': {
               'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
               'tools.response_headers.on': True,
               'tools.response_headers.headers': [('Content-Type', 'text/plain')],
           },
           '/static': {
               'tools.staticdir.on': True,
               'tools.staticdir.dir': './public'
           }
       }

       cherrypy.engine.subscribe('start', setup_database)
       cherrypy.engine.subscribe('stop', cleanup_database)

       webapp = StringGenerator()
       webapp.generator = StringGeneratorWebService()
       cherrypy.quickstart(webapp, '/', conf)

Save this into a file named `tut09.py` and run it as follows:

.. code-block:: bash

   $ python tut09.py

Let's first see how we create two functions that create
and destroy the table within our database. These functions
are registered to the CherryPy's server on lines 85-86,
so that they are called when the server starts and stops.

Next, notice how we replaced all the session code with calls
to the database. We use the session id to identify the
user's string within our database. Since the session will go
away after a while, it's probably not the right approach.
A better idea would be to associate the user's login or
more resilient unique identifier. For the sake of our
demo, this should do.

.. important::

   In this example, we must still set the session to a dummy value
   so that the session is not `discarded <https://cherrypy.readthedocs.org/en/latest/pkg/cherrypy.lib.html?highlight=fixation#session-fixation-protection>`_
   on each request by CherryPy. Since we now use the database
   to store the generated string, we simply store a dummy
   timestamp inside the session.

.. note::

   Unfortunately, sqlite in Python forbids us
   to share a connection between threads. Since CherryPy is a
   multi-threaded server, this would be an issue. This is the
   reason why we open and close a connection to the database
   on each call. This is clearly not really production friendly,
   and it is probably advisable to either use a more capable
   database engine or a higher level library, such as
   `SQLAlchemy <http://sqlalchemy.readthedocs.org>`_, to better
   support your application's needs.

.. _tut10:

Tutorial 10: Make it a modern single-page application with React.js
###################################################################

In the recent years, client-side single-page applications (SPA) have
gradually eaten server-side generated content web applications's lunch.

This tutorial demonstrates how to integrate with
`React.js <https://facebook.github.io/react/>`_, a Javascript library
for SPA released by Facebook in 2013. Please refer to React.js
documentation to learn more about it.

To demonstrate it, let's use the code from :ref:`tutorial 09 <tut09>`.
However, we will be replacing the HTML and Javascript code.

First, let's see how our HTML code has changed:

.. code-block:: html
   :linenos:

    <!DOCTYPE html>
    <html>
       <head>
         <link href="/static/css/style.css" rel="stylesheet">
         <script src="https://cdnjs.cloudflare.com/ajax/libs/react/0.13.3/react.js"></script>
         <script src="http://code.jquery.com/jquery-2.1.1.min.js"></script>
         <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-core/5.8.23/browser.min.js"></script>
       </head>
       <body>
         <div id="generator"></div>
         <script type="text/babel" src="static/js/gen.js"></script>
       </body>
    </html>

Basically, we have removed the entire Javascript code that was using jQuery.
Instead, we load the React.js library as well as a new, local,
Javascript module, named ``gen.js`` and located in the ``public/js``
directory:

.. code-block:: javascript
   :linenos:

   var StringGeneratorBox = React.createClass({
     handleGenerate: function() {
       var length = this.state.length;
       this.setState(function() {
         $.ajax({
           url: this.props.url,
           dataType: 'text',
           type: 'POST',
           data: {
             "length": length
           },
           success: function(data) {
             this.setState({
               length: length,
               string: data,
               mode: "edit"
             });
           }.bind(this),
           error: function(xhr, status, err) {
             console.error(this.props.url,
               status, err.toString()
             );
           }.bind(this)
         });
       });
     },
     handleEdit: function() {
       var new_string = this.state.string;
       this.setState(function() {
         $.ajax({
           url: this.props.url,
           type: 'PUT',
           data: {
             "another_string": new_string
           },
           success: function() {
             this.setState({
               length: new_string.length,
               string: new_string,
               mode: "edit"
             });
           }.bind(this),
           error: function(xhr, status, err) {
             console.error(this.props.url,
               status, err.toString()
             );
           }.bind(this)
         });
       });
     },
     handleDelete: function() {
       this.setState(function() {
         $.ajax({
           url: this.props.url,
           type: 'DELETE',
           success: function() {
             this.setState({
               length: "8",
               string: "",
               mode: "create"
             });
           }.bind(this),
           error: function(xhr, status, err) {
             console.error(this.props.url,
               status, err.toString()
             );
           }.bind(this)
         });
       });
     },
     handleLengthChange: function(length) {
       this.setState({
         length: length,
         string: "",
         mode: "create"
       });
     },
     handleStringChange: function(new_string) {
       this.setState({
         length: new_string.length,
         string: new_string,
         mode: "edit"
       });
     },
     getInitialState: function() {
       return {
         length: "8",
         string: "",
         mode: "create"
       };
     },
     render: function() {
       return (
         <div className="stringGenBox">
               <StringGeneratorForm onCreateString={this.handleGenerate}
                                    onReplaceString={this.handleEdit}
                                    onDeleteString={this.handleDelete}
                                    onLengthChange={this.handleLengthChange}
                                    onStringChange={this.handleStringChange}
                                    mode={this.state.mode}
                                    length={this.state.length}
                                    string={this.state.string}/>
         </div>
       );
     }
   });

   var StringGeneratorForm = React.createClass({
     handleCreate: function(e) {
       e.preventDefault();
       this.props.onCreateString();
     },
     handleReplace: function(e) {
       e.preventDefault();
       this.props.onReplaceString();
     },
     handleDelete: function(e) {
       e.preventDefault();
       this.props.onDeleteString();
     },
     handleLengthChange: function(e) {
       e.preventDefault();
       var length = React.findDOMNode(this.refs.length).value.trim();
       this.props.onLengthChange(length);
     },
     handleStringChange: function(e) {
       e.preventDefault();
       var string = React.findDOMNode(this.refs.string).value.trim();
       this.props.onStringChange(string);
     },
     render: function() {
       if (this.props.mode == "create") {
         return (
           <div>
              <input  type="text" ref="length" defaultValue="8" value={this.props.length} onChange={this.handleLengthChange} />
              <button onClick={this.handleCreate}>Give it now!</button>
           </div>
         );
       } else if (this.props.mode == "edit") {
         return (
           <div>
              <input type="text" ref="string" value={this.props.string} onChange={this.handleStringChange} />
              <button onClick={this.handleReplace}>Replace</button>
              <button onClick={this.handleDelete}>Delete it</button>
           </div>
         );
       }

       return null;
     }
   });

   React.render(
     <StringGeneratorBox url="/generator" />,
     document.getElementById('generator')
   );

Wow! What a lot of code for something so simple, isn't it?
The entry point is the last few lines where we indicate that we
want to render the HTML code of the ``StringGeneratorBox`` React.js
class inside the ``generator`` div.

When the page is rendered, so is that component. Notice how it
is also made of another component that renders the form itself.

This might be a little over the top for such a simple example
but hopefully will get you started with React.js in the process.

There is not much to say and, hopefully, the meaning of that code
is rather clear. The component has an internal `state <https://facebook.github.io/react/docs/interactivity-and-dynamic-uis.html>`_
in which we store the current string as generated/modified by the user.

When the user `changes the content of the input boxes <https://facebook.github.io/react/docs/forms.html>`_,
the state is updated on the client side. Then, when a button is clicked,
that state is sent out to the backend server using the API endpoint
and the appropriate action takes places. Then, the state is updated and so is the view.


Tutorial 11: Organize my code
#############################

CherryPy comes with a powerful architecture
that helps you organizing your code in a way that should make
it easier to maintain and more flexible.

Several mechanisms are at your disposal, this tutorial will focus
on the three main ones:

- :ref:`dispatchers <dispatchers>`
- :ref:`tools <tools>`
- :ref:`plugins <busplugins>`

In order to understand them, let's imagine you are at a superstore:

- You have several tills and people queuing for each of them (those are your requests)
- You have various sections with food and other stuff (these are your data)
- Finally you have the superstore people and their daily tasks
  to make sure sections are always in order (this is your backend)

In spite of being really simplistic, this is not far from how your
application behaves. CherryPy helps you structure your application
in a way that mirrors these high-level ideas.

Dispatchers
^^^^^^^^^^^

Coming back to the superstore example, it is likely that you will
want to perform operations based on the till:

- Have a till for baskets with less than ten items
- Have a till for disabled people
- Have a till for pregnant women
- Have a till where you can only using the store card

To support these use-cases, CherryPy provides a mechanism called
a :ref:`dispatcher <dispatchers>`. A dispatcher is executed early
during the request processing in order to determine which piece of
code of your application will handle the incoming request. Or, to
continue on the store analogy, a dispatcher will decide which
till to lead a customer to.

Tools
^^^^^

Let's assume your store has decided to operate a discount spree but,
only for a specific category of customers. CherryPy will deal
with such use case via a mechanism called a :ref:`tool <tools>`.

A tool is a piece of code that runs on a per-request
basis in order to perform additional work. Usually a tool is a
simple Python function that is executed at a given point during
the process of the request by CherryPy.

Plugins
^^^^^^^

As we have seen, the store has a crew of people dedicated to manage
the stock and deal with any customers' expectation.

In the CherryPy world, this translates into having functions
that run outside of any request life-cycle. These functions should
take care of background tasks, long lived connections (such as
those to a database for instance), etc.

:ref:`Plugins <busplugins>` are called that way because
they work along with the CherryPy :ref:`engine <cpengine>`
and extend it with your operations.

**********************
Creating a RESTful API
**********************

`REST <http://en.wikipedia.org/wiki/Representational_state_transfer>`_ is an elegant architecture concept which is widely used nowadays.

The point is quite simple: rely on HTTP methods and statuses and associate them with actual data manipulations.

You can read more theory on the :doc:`../progguide/REST` page.

Overview
========

In this tutorial, we will create a RESTful backend for a song collection management web app.

A song is a *resource* with certain data (called *state*). Let's assume, every song has **title** and **artist**, and is identified by a unique **ID**.

There are also *methods* to view and change the state of a resource. The basic set of methods is called `CRUD <http://en.wikipedia.org/wiki/Create,_read,_update_and_delete>`_—Create, Read, Update, and Delete.

Let's assume that the frontend part is developed by someone else, and can interact with our backend part only with API requests. Our jobs is only to handle those requests, perform actions, and return the proper response.

Therefore, we will not take care about templating or page rendering.

We will also not use a database in this tutorial for the sake of concentrating solely on the RESTful API concept.

.. note::

    REST principles assume that a response status must always be meaningful. HTTP 1.1 specification already has all necessary error codes, and a developer should properly map erroneous backend events with according HTTP error codes.

    Fortunately, CherryPy has done it for us. For instance, if our backend app receives a request with wrong parameters, CherryPy will raise a ``400 Bad Request`` response automatically.

Download the :download:`complete example file <files/songs.py>`.

Getting Started
===============

Create a file called ``songs.py`` with the following content::

    import cherrypy

    songs = {
        '1': {
            'title': 'Lumberjack Song',
            'artist': 'Canadian Guard Choir'
        },

        '2': {
            'title': 'Always Look On the Bright Side of Life',
            'artist': 'Eric Idle'
        },

        '3': {
            'title': 'Spam Spam Spam',
            'artist': 'Monty Python'
        }
    }

    class Songs:

        exposed = True

    if __name__ == '__main__':

        cherrypy.tree.mount(
            Songs(), '/api/songs',
            {'/':
                {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
            }
        )

        cherrypy.engine.start()
        cherrypy.engine.block()

Let's go through this code line by line.

Import CherryPy::

    import cherrypy

Define the song "database", which is a simple Python dictionary::

    songs = {
        '1': {
            'title': 'Lumberjack Song',
            'artist': 'Canadian Guard Choir'
        },

        '2': {
            'title': 'Always Look On the Bright Side of Life',
            'artist': 'Eric Idle'
        },

        '3': {
            'title': 'Spam Spam Spam',
            'artist': 'Monty Python'
        }
    }

Note that we are using *strings* as dict keys, not *integers*. This is done only to avoid extra type convertings when we will parse the request parameters (which  are always strings.) Normally, the ID handling is performed by a database automatically, but since we do not use any, we have to deal with it manually.

Create a class to represent the *songs* resource::

    class Songs:

Expose all the (future) class methods at once::

    exposed = True

Standard Python check on whether the file is used directly or as module::

    if __name__ == '__main__':

Create an instance of the class (called a CherryPy application) and mount it to ``/api/songs``::

    cherrypy.tree.mount(
        Songs(), '/api/songs',

This means that this app will handle requests coming to the URLs starting with ``/api/songs``.

Now, here goes the interesting part.

CherryPy has a very helpful tool for creating RESTful APIs—the **MethodDispatcher**.

Learn it and love it.

Briefly speaking, it is a special sort of dispatcher which automatically connects the HTTP requests to the according handlers based on the request method. All you have to do is just name the handlers to correspond to the HTTP method names.

Long story short, just call the HTTP GET handler ``GET``, and the HTTP POST handle ``POST``.

Activate this dispatcher for our app::

        {'/':
            {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
        }
    )

Note that the ``/`` path in this config is relative to the application mount point (``/api/songs``), and will apply only to it.

The last 2 lines do just the same as the ``quickstart`` method, only written a bit more explicitly—run the server::

    cherrypy.engine.start()
    cherrypy.engine.block()

GET
===

Represents the Read method in CRUD.

Add a new method to the ``Songs`` class in ``songs.py``, called ``GET``::

    def GET(self, id=None):

        if id == None:
            return('Here are all the songs we have: %s' % songs)
        elif id in songs:
            song = songs[id]
            return('Song with the ID %s is called %s, and the artist is %s' % (id, song['title'], song['artist']))
        else:
            return('No song with the ID %s :-(' % id)

This method will return the whole song dictionary if the ID is not specified (``/api/songs``), a particular song data if the ID is specified and exists (``/api/songs/1`` ), and the message about a not existing song otherwise (``/api/songs/42``.)

Try it out in your browser by going to ``127.0.0.1:8080/api/songs/``, ``127.0.0.1:8080/api/songs/1``, or ``127.0.0.1:8080/api/songs/42``.

POST
====

Represents the Create method in CRUD.

Add a new method to the ``Songs`` class, called ``POST``::

    def POST(self, title, artist):

        id = str(max([int(_) for _ in songs.keys()]) + 1)

        songs[id] = {
            'title': title,
            'artist': artist
        }

        return ('Create a new song with the ID: %s' % id)

This method defines the next unique ID and adds an item to the ``songs`` dictionary.

Note that we do not validate the input arguments. CherryPy does it for us. If any parameter is missing or and extra one is provided, the 400 Bad Request error will be raised automatically.

.. note::

    Unlike GET request, POST, PUT, and DELETE requests cannot be sent via the browser URL promt.

    You will need to use some special software to do it.

    The recommendation here is to use `cURL <http://en.wikipedia.org/wiki/CURL>`_, which is available by default in most GNU/Linux distributions and is available for Windows and Mac.

    Basic cURL usage to send a request, applied in the examples below, is as follows:

    .. code-block:: bash

        curl -d <param1>=<value1> -d <param2>=<value2> -X <HTTPMethod> <URL>

    You can send GET requests with cURL too, but using a browser is easier.

Send a POST HTTP request to ``127.0.0.1:8080/api/songs/`` with cURL:

.. code-block:: bash

    curl -d title='Frozen' -d artist='Madonna' -X POST '127.0.0.1:8080/api/songs/'

You will see the response:

    Create a new song with the ID: 4%

Now, if you go to ``127.0.0.1:8080/api/songs/4`` in your browser you will se the following message:

    Song with the ID 4 is called Frozen, and the artist is Madonna

So it actually works!

PUT
===

Represents the Update method in CRUD.

Add a new method to the ``Songs`` class, called ``PUT``::

    def PUT(self, id, title=None, artist=None):
        if id in songs:
            song = songs['id']

            song['title'] = title or song['title']
            song['artist'] = artist or song['artist']

            return('Song with the ID %s is now called %s, and the artist is now %s' % (id, song['title'], song['artist']))
        else:
            return('No song with the ID %s :-(' % id)

This method checks whether the requested song exists and updates the fields that are provided. If some field is not specified, the corresponding value will not be updated.

Try sending some PUT HTTP requests to ``127.0.0.1:8080/api/songs/3`` via cURL, and check the result by requesting ``127.0.0.1:8080/api/songs/4`` in your browser:

*   .. code-block:: bash

        curl -d title='Yesterday' -X PUT '127.0.0.1:8080/api/songs/3'

    The response:

        Song with the ID 3 is now called Yesterday, and the artist is now Monty Python%

    What you'll see in the browser:

        Song with the ID 3 is called Yesterday, and the artist is Monty Python

*   .. code-block:: bash

        curl -d artist='Beatles' -X PUT '127.0.0.1:8080/api/songs/3'

    The response:

        Song with the ID 3 is now called Yesterday, and the artist is now Beatles%

    What you'll see in the browser:

        Song with the ID 3 is called Yesterday, and the artist is Beatles

DELETE
======

Represents the DELETE method in CRUD.

Add a new method to the ``Songs`` class, called ``DELETE``::

    def DELETE(self, id):
        if id in songs:
            songs.pop(id)

            return('Song with the ID %s has been deleted.' % id)
        else:
            return('No song with the ID %s :-(' % id)

This method, like the previous ones, check if the given ID point to an existing song and pops it out of the ``songs`` dictionary.

Send a DELETE HTTP request to ``127.0.0.1:8080/api/songs/2`` via cURL:

.. code-block:: bash

    curl -X DELETE '127.0.0.1:8080/api/songs/2'

The response:

    Song with the ID 2 has been deleted.%

And the browser output:

    No song with the ID 2 :-(

Multiple Resources
==================

You can have any number of resources represented this way. Each resource is a CherryPy application, i.e. a class.

For another resource, say, *users*, just create a class ``Users`` the same way you created ``Songs``, and mount it to ``/api/users`` with the same config.

Conclusion and Further Steps
============================

This is pretty much it about the logic of REST API in CherryPy.

You can now add actual database manipulations, parameter validation, and whatever your project may require.

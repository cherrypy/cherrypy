**********************
Creating a RESTful API
**********************

`REST <http://en.wikipedia.org/wiki/Representational_state_transfer>`_ is an elegant architecture concept which is widely used nowadays.

The point is quite simple: rely on HTTP methods and statuses and associate them with actual data manipulations.

You can read more theory on the :doc:`../progguide/REST` page.

Overview
========

In this tutorial, we will create a RESTful backend for a song collection management web app.

Let's assume that the frontend part is developed by someone else, and can interact with our backend part only with API requests. Our jobs is only to handle those requests, perform actions, and return the proper response.

Therefore, we will not take care about templating or page rendering.

.. note::

    REST principles assume that a response status must always be meaningful. HTTP 1.1 specification already has all necessary error codes, and a developer should properly map erroneous backend events with according HTTP error codes.

    Fortunately, CherryPy has done it for us. For instance, if our backend app receives a request with wrong parameters, CherryPy will raise a ``400 Bad Request`` response automatically.

Resource class, MethodDispatcher, and GET handler
=================================================

Create a file called ``songs.py`` with the following content::

    import cherrypy

    class Songs:

        exposed = True

        def GET(self, id=None):
            if id:
                return('Show info about the song with the ID %s' % id)
            else:
                return('Show info about all the available songs')

    if __name__ == '__main__':

        cherrypy.tree.mount(
            Songs(), '/api/songs',
            {'/':
                {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
            }
        )

        cherrypy.engine.start()
        cherrypy.engine.block()

Let's go through this code line by line:

Import CherryPy::

    import cherrypy

Create a class to represent the *songs* resource::

    class Songs:

Expose all the class methods at once::

    exposed = True

Create the GET method to handle HTTP GET requests::

    def GET(self, id=None):
        if id:
            return('Show info about the song with the ID %s' % id)
        else:
            return('Show info about all the available songs')

This method will show the first message when the URL ``/api/songs/<id>`` is requested, the second one—when the URL ``/api/songs`` is requested.

.. note:: The method name matters! Class methods must correspond to the actual HTTP methods. See the explanation below.

Standard Python direct check on whether the file is used directly or as module::

    if __name__ == '__main__':

Create an instance of the class (called a CherryPy application) and mount it to ``/api/songs``::

    cherrypy.tree.mount(
        Songs(), '/api/songs',


This means that this app will handle requests coming to the URLs starting with ``/api/songs``.

Now, here goes the interesting part.

CherryPy has a very helpful tool for creating RESTful APIs—the **MethodDispatcher**.

Briefly speaking, it is a special sort of dispatcher which automatically connects the HTTP requests with proper handlers based on the request method. All you have to do is just name the handlers accordingly, so the dispatcher can find it.

Long story short, just call the HTTP GET handler ``GET``, and the HTTP POST handle ``POST``.

Activate this dispatcher for our app::

        {'/':
            {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
        }
    )

Note that the ``/`` path in this config is relative to the application mount point (``/api/songs``), and will apply only to it.

The last 2 lines do just the same as ``.quickstart()``, only written a bit more explicitly—run the server::

    cherrypy.engine.start()
    cherrypy.engine.block()

Now, if you run this file on you local machine with Python, you will have a working GET request handler at ``127.0.0.1:8080/api/songs``!

Try it out in your browser by going to ``127.0.0.1:8080/api/songs/`` or ``127.0.0.1:8080/api/songs/42``.

It does not do much yet, but it already properly handles GET requests and responses with the correct HTTP status codes.

POST, PUT, and DELETE
=====================

In order to have a persistent system, we must have 4 basic actions implemented by our app—so called `CRUD <http://en.wikipedia.org/wiki/Create,_read,_update_and_delete>`_.

We already have GET to read. According to REST, now we need to add:

 * POST to create
 * PUT to update
 * DELETE to delete

Let's do so!

In the file ``songs.py``, add the following methods into the ``Songs`` class (you probably can guess the method names already)::

    def POST(self, **kwargs):
        return ('Create a new song with the following parameters: %s' % kwargs)

    def PUT(self, id, **kwargs):
        return ('Update the data of the song with the ID %s with the following parameters: %s' % (id, kwargs))

    def DELETE(self, id):
        return('Delete the song with the ID %s' % id)

Note that unlike the ``GET`` method, ``PUT`` and ``DELETE`` have the ``id`` argument mandatory (no ``id=None``). This is a good idea since we want to update and delete only a particular song, but not all of them.

Also note that ``POST`` does not have the ``id`` argument at all. It is not needed as there is logically no ID to relate to.

Now, if you use `cURL <http://en.wikipedia.org/wiki/CURL>`_ or any similar tool to send a POST, PUT, or DELETE request to the ``/api/songs/`` or ``/api/songs/<id>``, you will see that it is properly processed—valid requests are responded with status 200 and the according message, invalid requests are rejected.

Multiple resources
==================

You can have any number of resources represented this way. Each resource is a CherryPy application, i.e. a class.

For another resource, say, *users*, just create a class ``Users`` the same way you created ``Songs``, and mount it to ``/api/users`` with the same config.

Conclusion and further steps
============================

This is pretty much it about the logic of REST API in CherryPy.

You can now add actual database manipulations, parameter validation, and whatever your project may require.

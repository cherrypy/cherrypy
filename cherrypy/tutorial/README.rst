CherryPy Tutorials
------------------------------------------------------------------------

This is a series of tutorials explaining how to develop dynamic web
applications using CherryPy. A couple of notes:


- Each of these tutorials builds on the ones before it. If you're
  new to CherryPy, we recommend you start with 01_helloworld.py and
  work your way upwards. :)

- In most of these tutorials, you will notice that all output is done
  by returning normal Python strings, often using simple Python
  variable substitution. In most real-world applications, you will
  probably want to use a separate template package (like Cheetah,
  CherryTemplate or XML/XSL).

- For convinience cherrypy tutorials are provided in a docker container, if you
  are not familiar with docker go through the `Getting started guide
  https://docs.docker.com/get-started/`_ first, then come back and try the
  examples below. All commands must be run within the `cherrypy/tutorials`
  directory

To run docker from the latest image in docker hub run:

.. code-block:: bash

  $ docker run -p 8080:8080 cherrypy/cherrypy

By default tutorial 1 will be run within the container, you can pass the
filename of the tutorial you wish to run like this:

.. code-block:: bash

  $ docker run -p 8080:8080 cherrypy/cherrypy tut02_expose_methods.py

Now you can browse to `<http://localhost:8080>`

We also provide a docker-compose.yml so you can just run:

.. code-block:: bash

  $ docker-compose up

Compose is a tool for defining and running multi-container Docker
applications. To learn more about Compose refer to the `getting
started https://docs.docker.com/compose/gettingstarted/`_

 
CherryPy - A Minimalist Python Web Framework
============================================

.. toctree::
   :hidden:

   intro.rst
   install.rst
   tutorials.rst
   basics.rst
   advanced.rst
   extend.rst
   deploy.rst
   glossary.rst

CherryPy is a pythonic, object-oriented web framework.

CherryPy allows developers to build web applications in much the 
same way they would build any other object-oriented Python program. 
This results in smaller source code developed in less time.

CherryPy is now more than seven years old and it is has proven to 
be very fast and stable. It is being used in production by many 
sites, from the simplest to the most demanding.

A CherryPy application typically looks like this:

.. code-block:: python

   import cherrypy
   
   class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

   cherrypy.quickstart(HelloWorld())

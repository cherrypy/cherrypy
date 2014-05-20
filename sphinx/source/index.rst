 
CherryPy - A Minimalist Python Web Framework
============================================

.. toctree::
   :hidden:

   intro.rst
   install.rst
   tutorials.rst
   basics.rst
   advanced.rst
   config.rst
   extend.rst
   deploy.rst
   contribute.rst
   glossary.rst

`CherryPy <http://www.cherrypy.org>`_ is a pythonic, object-oriented web framework.

CherryPy allows developers to build web applications in much the 
same way they would build any other object-oriented Python program. 
This results in smaller source code developed in less time.

CherryPy is now more than ten years old and it is has proven to 
be fast and reliable. It is being used in production by many 
sites, from the simplest to the most demanding.

A CherryPy application typically looks like this:

.. code-block:: python

   import cherrypy
   
   class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

   cherrypy.quickstart(HelloWorld())

In order to make the most of CherryPy, you should start
with the :ref:`tutorials <tutorials>` that will lead you through the most common
aspects of the framework. Once done, you will probably want to 
browse through the :ref:`basics <basics>` and :ref:`advanced <advanced>` 
sections that will demonstrate how to implement certain operations. 
Finally, you will want to carefully read the configuration and 
:ref:`extend <extend>` sections that go in-depth regarding the 
powerful features provided by the framework.

Above all, have fun with your application!

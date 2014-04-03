
Glossary
--------

.. glossary:: 

   exposed
      A Python function or method which has an attribute called `exposed`
      set to `True`. This attribute can be set directly or via the 
      :func:`cherrypy.expose()` decorator.

      .. code-block:: python
		      
         @cherrypy.expose
	 def method(...):
	     ...

      is equivalent to:

      .. code-block:: python
		      
	 def method(...):
	     ...
         method.exposed = True
         
   page handler
      Name commonly given to an exposed method

   controller
      Name commonly given to a class owning at least one exposed method

******************
Extending CherryPy
******************

If you need to perform some work that doesn't fit in a page handler, there are
two ways to do it depending on the scope of the task. If your code needs to run
on each request, or for only some URL's in your application, use a Tool. If your
code needs to run elsewhere, such as process start/stop/restart/exit, or thread
start/stop, use an Engine Plugin.

.. toctree::
   
   customtools
   customplugins


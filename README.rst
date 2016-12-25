CherryPy
========

|CherryPy Build Status| |Codacy Badge|

Welcome to the GitHub-repository of `CherryPy <http://cherrypy.org/>`__!

CherryPy is a pythonic, object-oriented HTTP framework.

1. It allows building web applications in much the same way one would
   build any other object-oriented program.
2. This results in less and more readable code being developed faster.
   It's all just properties and methods.
3. It is now more than ten years old and has proven fast and very
   stable.
4. It is being used in production by many sites, from the simplest to
   the most demanding.
5. And perhaps most importantly, it is fun to work with :-)

Here's how easy it is to write "Hello World" in CherryPy:

.. code:: python

    import cherrypy

    class HelloWorld(object):
        @cherrypy.expose
        def index(self):
            return "Hello World!"

    cherrypy.quickstart(HelloWorld())

And it continues to work that intuitively when systems grow, allowing
for the Python object model to be dynamically presented as a web site
and/or API.

Table of contents
-----------------

.. raw:: html

   <!-- START doctoc generated TOC please keep comment here to allow auto update -->

.. raw:: html

   <!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

-  `Help <#help>`__

   -  `I don't understand the
      documentation <#i-dont-understand-the-documentation>`__
   -  `I have a question <#i-have-a-question>`__
   -  `I have found a bug <#i-have-found-a-bug>`__
   -  `I have a feature request <#i-have-a-feature-request>`__
   -  `I want to discuss CherryPy, reach out to developers or CherryPy
      users
      users <#i-want-to-discuss-cherrypy-reach-out-to-developers-or-cherrypy-users>`__

-  `Documentation <#documentation>`__
-  `Installation <#installation>`__
-  `Pip <#pip>`__
-  `Source <#source>`__
-  `Development <#development>`__
-  `Contributing <#contributing>`__
-  `Testing <#testing>`__

.. raw:: html

   <!-- END doctoc generated TOC please keep comment here to allow auto update -->

Help
====

What are my options if I feel I need help?

I don't understand the documentation
------------------------------------

While CherryPy is one of the easiest and most intuitive frameworks out
there, the prerequisite for understanding the `CherryPy
documentation <http://docs.cherrypy.org/en/latest/>`__ is that you have
a general understanding of Python and web development.

So if you have that, and still cannot understand the documentation, it
is probably not your fault. `Please create an
issue <https://github.com/cherrypy/cherrypy/issues/new>`__ in those
cases.

I have a question
-----------------

If you have a question and cannot find an answer for it in issues or the
the `documentation <http://docs.cherrypy.org/en/latest/>`__, `please
create an issue <https://github.com/cherrypy/cherrypy/issues/new>`__.

Questions and their answers have great value for the community, and a
tip is to really put the effort in and write a good explanation, you
will get better and quicker answers. Examples are strongly encouraged.

I have found a bug
------------------

If no one have already, `create an
issue <https://github.com/cherrypy/cherrypy/issues/new>`__. Be sure to
provide ample information, remember that any help won't be better than
your explanation.

Unless something is very obviously wrong, you are likely to be asked to
provide a working example, displaying the erroneous behaviour.

Note: While this might feel troublesome, a tip is to always make a
separate example that have the same dependencies as your project. It is
great for troubleshooting those annoying problems where you don't know
if the problem is at your end or the components. Also, you can then
easily fork and provide as an example. You will get answers and
resolutions way quicker. Also, many other open source projects require
it.

I have a feature request
------------------------

`Good stuff! Please create an
issue! <https://github.com/cherrypy/cherrypy/issues/new>`__\  Note:
Features are more likely to be added the more users they seem to
benefit.

I want to discuss CherryPy, reach out to developers or CherryPy users
---------------------------------------------------------------------

`The gitter page <https://gitter.im/cherrypy/cherrypy>`__ is good for
when you want to talk, but doesn't feel that the discussion has to be
indexed for posterity.

Documentation
=============

-  The official user documentation of CherryPy is at:
   http://docs.cherrypy.org/en/latest/
-  Tutorials are included in the repository:
   https://github.com/cherrypy/cherrypy/tree/master/cherrypy/tutorial
-  A general wiki at(will be moved to github):
   https://bitbucket.org/cherrypy/cherrypy/wiki/Home
-  Plugins are described at: http://tools.cherrypy.org/

Installation
============

To install CherryPy for use in your project, follow these instructions:

From the PyPI package
---------------------

.. code:: sh

    pip install cherrypy

or (for python 3)

.. code:: sh

    pip3 install cherrypy

From source
-----------

Change to the directory where setup.py is located and type (Python 2.6
or later needed):

.. code:: sh

    python setup.py install

Development
===========

Contributing
------------

Please follow the `contribution
guidelines <https://github.com/cherrypy/cherrypy/blob/master/CONTRIBUTING.txt>`__.
And by all means, `absorb the Zen of
CherryPy <https://bitbucket.org/cherrypy/cherrypy/wiki/ZenOfCherryPy>`__.

Testing
-------

-  To run the regression tests, first install tox:

   .. code:: sh

       pip install tox

   then run it

   .. code:: sh

       tox

-  To run individual tests type:

   .. code:: sh

       tox -- -k test_foo

.. |CherryPy Build Status| image:: https://travis-ci.org/cherrypy/cherrypy.svg?branch=master
   :target: https://travis-ci.org/cherrypy/cherrypy
.. |Codacy Badge| image:: https://api.codacy.com/project/badge/Grade/48b11060b5d249dc86e52dac2be2c715
   :target: https://www.codacy.com/app/webknjaz/cherrypy-upstream?utm_source=github.com&utm_medium=referral&utm_content=cherrypy/cherrypy&utm_campaign=Badge_Grade

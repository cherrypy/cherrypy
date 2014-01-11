****************
Deployment Guide
****************

CherryPy the application framework is quite flexible and can be deployed in a
wide variety of ways. CherryPy the server is a production-ready, performant
server that can be used to deploy any WSGI or CGI application.

Applications
============

An easy way to deploy a CherryPy application is using the standard
``quickstart()`` server. The ``cherryd`` script mentioned below wraps this same
server. It is a production-ready, performant server that can be quickly
configured for development or production use (or even somewhere in-between) by
setting an :ref:`environment <environments>` in the application config.

A CherryPy application can also be deployed using any WSGI-capable server. The
return from :py:class:`cherrypy.tree.mount <cherrypy._cptree.Tree>` is a
standard WSGI application.

Servers
=======

CherryPy ships with a fast, production-ready server that can be used to serve
applications independently of the CherryPy application framework.

.. toctree::
   :maxdepth: 2

   apache
   /refman/process/servers
   /refman/wsgiserver/init


Environment
===========

.. toctree::
   :maxdepth: 2

   cherryd
   /refman/process/plugins/daemonizer
   /refman/process/plugins/dropprivileges
   /refman/process/plugins/pidfile
   /refman/process/plugins/signalhandler



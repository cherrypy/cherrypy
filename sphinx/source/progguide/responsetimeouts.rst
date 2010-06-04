*****************
Response Timeouts
*****************

CherryPy responses include 3 attributes related to time:

 * ``response.time``: the :func:`time.time` at which the response began
 * ``response.timeout``: the number of seconds to allow responses to run
 * ``response.timed_out``: a boolean indicating whether the response has
   timed out (default False).

The request processing logic inspects the value of ``response.timed_out`` at
various stages; if it is ever True, then :class:`TimeoutError` is raised.
You are free to do the same within your own code.

Rather than calculate the difference by hand, you can call
``response.check_timeout`` to set ``timed_out`` for you.


.. _timeoutmonitor:

Timeout Monitor
===============

In addition, CherryPy includes a ``cherrypy.engine.timeout_monitor`` which
monitors all active requests in a separate thread; periodically, it calls
``check_timeout`` on them all. It is subscribed by default. To turn it off::

    [global]
    engine.timeout_monitor.on: False

or::

    cherrypy.engine.timeout_monitor.unsubscribe()

You can also change the interval (in seconds) at which the timeout monitor runs::

    [global]
    engine.timeout_monitor.frequency: 60 * 60

The default is once per minute. The above example changes that to once per hour.

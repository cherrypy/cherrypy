.. _monitor:

*************
Timer threads
*************

Monitor
=======

A generic plugin to periodically run a callback in its own thread. Some of the
other builtin plugins subclass this already.

 * callback: the function to call at intervals.
 * frequency: the time in seconds between callback runs.
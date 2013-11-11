.. _cherrypyspeed:

*********************
How fast is CherryPy?
*********************

Introduction
============

When people ask this question, they usually mean "how fast will my CherryPy-based application be?".

In 99% of the cases, the answer is "this depends on your actual application code, not on CherryPy itself".

The reason is that, for 99% of the real-world dynamic applications, most of the time spent to return a page will be spent in your actual application code, and the time actually spent in the CherryPy code will be negligible.

For instance, a typical page that requires a few database calls to be built might take in total 200ms to be served. Out of these 200ms, about 2ms will be spent by CherryPy itself, and 198ms will be spend in your actual database calls and page rendering...

So you can see that, if you want to optimize anything, you should really optimize your actual application code before you try to optimize CherryPy.


Raw speed of the CherryPy HTTP server
=====================================

Despite the real-life most common scenario explained in the introduction, some people still want to know the raw speed of the CherryPy HTTP server.

About the benchmark
-------------------

This benchmarking only makes sense on very small documents, otherwise we're no longer measuring the raw speed of the HTTP server, but also the speed of the application.

.. warning::

   This benchmark uses the ``ab`` tool from the Apache project, it's far from being a perfect tool nor does it provide a realistic user workflow. Take these results lightly and always perform real load/performance tests in your environment with better tools.

This benchmarking was performed on a laptop in the following environment:
 * Processor: Intel® Core™ i3-2330M CPU @ 2.20GHz × 4 
 * RAM: 4GB
 * Ubuntu 13.10
 * Python 2.7
 * CherryPy 3.2.4
 * Load testing tool: ab from Apache2

We used the following basic CherryPy app:


.. code-block:: python

    import cherrypy

    class Root(object):
        def index(self):
            return "OK"
        index.exposed = True

    if __name__ == "__main__":
        # remove the default CherryPy enabled tools 
        # to really check the speed of the request processing stack
        cherrypy.config.clear()

	# we don't need the logging for this test
        cherrypy.config.update({'log.screen': False})

        cherrypy.quickstart(Root())


Test 1: Dynamic content / no concurrent connections
---------------------------------------------------

.. code-block:: text

    $ ab -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        CherryPy/3.2.4
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      1
    Time taken for tests:   2.414 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      126000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    414.19 [#/sec] (mean)
    Time per request:       2.414 [ms] (mean)
    Time per request:       2.414 [ms] (mean, across all concurrent requests)
    Transfer rate:          50.96 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    0   0.0      0       1
    Processing:     1    2   0.6      2       8
    Waiting:        1    2   0.5      2       5
    Total:          1    2   0.6      2       8

    Percentage of the requests served within a certain time (ms)
      50%      2
      66%      2
      75%      2
      80%      2
      90%      3
      95%      3
      98%      4
      99%      5
     100%      8 (longest request)


Test 2: Dynamic content / concurrent connections / persistent connections
-------------------------------------------------------------------------

.. code-block:: text

    $ ab -k -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        CherryPy/3.2.4
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      1
    Time taken for tests:   0.626 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Keep-Alive requests:    1000
    Total transferred:      150000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    1597.89 [#/sec] (mean)
    Time per request:       0.626 [ms] (mean)
    Time per request:       0.626 [ms] (mean, across all concurrent requests)
    Transfer rate:          234.07 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    0   0.0      0       0
    Processing:     1    1   0.2      1       3
    Waiting:        1    1   0.2      1       3
    Total:          1    1   0.2      1       3

    Percentage of the requests served within a certain time (ms)
      50%      1
      66%      1
      75%      1
      80%      1
      90%      1
      95%      1
      98%      1
      99%      2
     100%      3 (longest request)

Test 3: Dynamic content / concurrent connections
------------------------------------------------

Now let's alo tell "ab" to simulate 10 concurrent users.

.. code-block:: text

    $ ab -c 10 -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        CherryPy/3.2.4
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      10
    Time taken for tests:   2.653 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      126000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    376.99 [#/sec] (mean)
    Time per request:       26.526 [ms] (mean)
    Time per request:       2.653 [ms] (mean, across all concurrent requests)
    Transfer rate:          46.39 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    2  44.7      0    1000
    Processing:     5   21  33.7     17     406
    Waiting:        4   20  33.7     16     406
    Total:          5   23  55.9     17    1020

    Percentage of the requests served within a certain time (ms)
      50%     17
      66%     19
      75%     20
      80%     21
      90%     23
      95%     25
      98%     31
      99%    286
     100%   1020 (longest request)


Test 4: Dynamic content / concurrent connections / persistent connections
-------------------------------------------------------------------------

In this use case, we tell ab to reuse connections as per HTTP/1.1.

.. code-block:: text

    $ ab -k -c 10 -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        CherryPy/3.2.4
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      10
    Time taken for tests:   1.944 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Keep-Alive requests:    1000
    Total transferred:      150000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    514.36 [#/sec] (mean)
    Time per request:       19.442 [ms] (mean)
    Time per request:       1.944 [ms] (mean, across all concurrent requests)
    Transfer rate:          75.35 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    1  31.6      0    1000
    Processing:     1   18  16.6     16     424
    Waiting:        1   14  15.6     12     418
    Total:          1   19  36.3     16    1040

    Percentage of the requests served within a certain time (ms)
      50%     16
      66%     21
      75%     24
      80%     26
      90%     32
      95%     38
      98%     47
      99%     51
     100%   1040 (longest request)


Test 5: Raw WSGI server / no concurrent connections
---------------------------------------------------
    
.. code-block:: text

    $ ab -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        sylvain-laptop
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      1
    Time taken for tests:   1.041 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      108000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    960.58 [#/sec] (mean)
    Time per request:       1.041 [ms] (mean)
    Time per request:       1.041 [ms] (mean, across all concurrent requests)
    Transfer rate:          101.31 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    0   0.0      0       0
    Processing:     0    1   0.3      1       4
    Waiting:        0    1   0.3      1       4
    Total:          0    1   0.3      1       4

    Percentage of the requests served within a certain time (ms)
      50%      1
      66%      1
      75%      1
      80%      1
      90%      1
      95%      1
      98%      2
      99%      2
     100%      4 (longest request)


Test 6: Raw WSGI server / concurrent connections
------------------------------------------------
    
.. code-block:: text

    $ ab -c 10 -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        sylvain-laptop
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      10
    Time taken for tests:   1.235 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      108000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    809.88 [#/sec] (mean)
    Time per request:       12.348 [ms] (mean)
    Time per request:       1.235 [ms] (mean, across all concurrent requests)
    Transfer rate:          85.42 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    1  31.5      0     996
    Processing:     2    8  19.4      7     341
    Waiting:        1    8  19.4      6     341
    Total:          2    9  37.0      7    1003

    Percentage of the requests served within a certain time (ms)
      50%      7
      66%      7
      75%      8
      80%      8
      90%     10
      95%     11
      98%     15
      99%     17
     100%   1003 (longest request)


Test 7: Raw WSGI server / concurrent connections / persistent connections
-------------------------------------------------------------------------
    
.. code-block:: text

    $ ab -k -c 10 -n 1000 http://localhost:8080/
    This is ApacheBench, Version 2.3 <$Revision: 1430300 $>
    Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Licensed to The Apache Software Foundation, http://www.apache.org/

    Benchmarking localhost (be patient)
    Completed 100 requests
    Completed 200 requests
    Completed 300 requests
    Completed 400 requests
    Completed 500 requests
    Completed 600 requests
    Completed 700 requests
    Completed 800 requests
    Completed 900 requests
    Completed 1000 requests
    Finished 1000 requests


    Server Software:        sylvain-laptop
    Server Hostname:        localhost
    Server Port:            8080

    Document Path:          /
    Document Length:        2 bytes

    Concurrency Level:      10
    Time taken for tests:   0.992 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Keep-Alive requests:    0
    Total transferred:      108000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    1008.08 [#/sec] (mean)
    Time per request:       9.920 [ms] (mean)
    Time per request:       0.992 [ms] (mean, across all concurrent requests)
    Transfer rate:          106.32 [Kbytes/sec] received

    Connection Times (ms)
              min  mean[+/-sd] median   max
    Connect:        0    0   0.1      0       1
    Processing:     1    7  22.8      6     345
    Waiting:        0    7  22.7      5     344
    Total:          1    7  22.8      6     345

    Percentage of the requests served within a certain time (ms)
      50%      6
      66%      7
      75%      7
      80%      7
      90%      9
      95%     10
      98%     11
      99%     13
     100%    345 (longest request)

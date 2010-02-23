.. _cherrypyspeed:

**********************
How fast is CherryPy ?
**********************

Introduction
============

When people ask this question, they usually mean "how fast will my CherryPy-based application be ?".

In 99% of the cases, the answer is "this depends on your actual application code, not on !CherryPy itself".

The reason is that, for 99% of the real-world dynamic applications, most of the time spent to return a page will be spent in your actual application code, and the time actually spent in the CherryPy code will be negligible.

For instance, a typical page that requires a few database calls to be built might take in total 200ms to be served. Out of these 200ms, about 2ms will be spent by CherryPy itself, and 198ms will be spend in your actual database calls and page rendering...

So you can see that, if you want to optimize anything, you should really optimize your actual application code before you try to optimize !CherryPy

Raw speed of the CherryPy HTTP server
=====================================

Despite the real-life most common scenario explained in the introduction, some people still want to know the raw speed of the CherryPy HTTP server.
So I sat down and did some benchmarking...

About the benchmark
-------------------

This benchmarking only makes sense on very small documents, otherwise we're no longer measuring the raw speed of the HTTP server, but also the speed of the application ...

This benchmarking was performed on a laptop in the following environment:
 * Processor: Pentium M 1.6 Ghz
 * RAM: 1GB
 * Windows XP 2
 * Load testing tool: ab from Apache2
 * CherryPy version: SVN snapshot on 2005/01/13

Note that "ab" was running on the same machine as the CherryPy server, so CherryPy is probably a bit faster than what we're getting.

Test 1: Dynamic content / single threaded server
------------------------------------------------

I used the following basic CherryPy app::

    #!python
    from cherrypy import cpg
    class Root:
        def index(self):
            return "OK"
        index.exposed = True
    
    cpg.root = Root()
    
    cpg.server.start(configMap = {'socketPort': 10000})

Here are the "ab" results::

    $ ./ab.exe -n 1000 http://localhost:10000/
    This is ApacheBench, Version 2.0.41-dev <$Revision: 1.121.2.12 $> apache-2.0
    Copyright (c) 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Copyright (c) 1998-2002 The Apache Software Foundation, http://www.apache.org/
    
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
    Finished 1000 requests
    
    
    Server Software:        CherryPy/2.0.0b
    Server Hostname:        localhost
    Server Port:            10000
    
    Document Path:          /
    Document Length:        2 bytes
    
    Concurrency Level:      1
    Time taken for tests:   1.789044 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      127000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    558.96 [#/sec] (mean)
    Time per request:       1.789 [ms] (mean)
    Time per request:       1.789 [ms] (mean, across all concurrent requests)
    Transfer rate:          69.31 [Kbytes/sec] received
    
    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   1.9      0      15
    Processing:     0    1   4.2      0      15
    Waiting:        0    0   0.8      0      15
    Total:          0    1   4.5      0      15
    
    Percentage of the requests served within a certain time (ms)
      50%      0
      66%      0
      75%      0
      80%      0
      90%     15
      95%     15
      98%     15
      99%     15
     100%     15 (longest request)

As you can see, CherryPy averaged 558 requests/second, which is pretty good ...

Test 2: Dynamic content / multi threaded server
-----------------------------------------------

I used the same code as test 1, but started CherryPy in thread-pool mode, with 10 threads.
I also told "ab" to simulate 10 concurrent users ...
Here are the "ab" results::

    $ ./ab.exe -c 10 -n 1000 http://localhost:10000/
    This is ApacheBench, Version 2.0.41-dev <$Revision: 1.121.2.12 $> apache-2.0
    Copyright (c) 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Copyright (c) 1998-2002 The Apache Software Foundation, http://www.apache.org/
    
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
    Finished 1000 requests
    
    
    Server Software:        CherryPy/2.0.0b
    Server Hostname:        localhost
    Server Port:            10000
    
    Document Path:          /
    Document Length:        2 bytes
    
    Concurrency Level:      10
    Time taken for tests:   2.327670 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      127000 bytes
    HTML transferred:       2000 bytes
    Requests per second:    429.61 [#/sec] (mean)
    Time per request:       23.277 [ms] (mean)
    Time per request:       2.328 [ms] (mean, across all concurrent requests)
    Transfer rate:          53.27 [Kbytes/sec] received
    
    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   2.3      0      15
    Processing:    15   21   8.9     15      47
    Waiting:        0   16   6.2     15      47
    Total:         15   22   9.0     15      47
    
    Percentage of the requests served within a certain time (ms)
      50%     15
      66%     31
      75%     31
      80%     31
      90%     31
      95%     31
      98%     47
      99%     47
     100%     47 (longest request)

As you can see, CherryPy averaged 429 requests/second, which is a bit less than test 1 (there is a small thread-switching overhead), but is still pretty good ...

Test 3: Static content / single threaded server
-----------------------------------------------

This time, I used CherryPy to serve a static file from disc.
The file was a simple text containing "OK".
Here was the config file for CherryPy::

    [server]
    socketPort = 10000
    
    [staticContent]
    static.html = static.html


Here are the "ab" results::

    $ ./ab.exe -n 1000 http://localhost:10000/static.html
    This is ApacheBench, Version 2.0.41-dev <$Revision: 1.121.2.12 $> apache-2.0
    Copyright (c) 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
    Copyright (c) 1998-2002 The Apache Software Foundation, http://www.apache.org/
    
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
    Finished 1000 requests
    
    
    Server Software:        CherryPy/2.0.0b
    Server Hostname:        localhost
    Server Port:            10000
    
    Document Path:          /static.html
    Document Length:        4 bytes
    
    Concurrency Level:      1
    Time taken for tests:   1.979130 seconds
    Complete requests:      1000
    Failed requests:        0
    Write errors:           0
    Total transferred:      175000 bytes
    HTML transferred:       4000 bytes
    Requests per second:    505.27 [#/sec] (mean)
    Time per request:       1.979 [ms] (mean)
    Time per request:       1.979 [ms] (mean, across all concurrent requests)
    Transfer rate:          85.90 [Kbytes/sec] received
    
    Connection Times (ms)
                  min  mean[+/-sd] median   max
    Connect:        0    0   2.2      0      15
    Processing:     0    1   4.3      0      15
    Waiting:        0    0   0.5      0      15
    Total:          0    1   4.8      0      15
    
    Percentage of the requests served within a certain time (ms)
      50%      0
      66%      0
      75%      0
      80%      0
      90%     15
      95%     15
      98%     15
      99%     15
     100%     15 (longest request)


As you can see, CherryPy averaged 505 requests/second. Again it is a little bit less than a dynamic page, but it is still pretty good ...

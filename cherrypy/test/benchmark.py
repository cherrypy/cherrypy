"""Benchmark tool for CherryPy."""

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import re
import sys
import time
import traceback

import cherrypy


MOUNT_POINT = "/cpbench/users/rdelon/apps/blog"

__all__ = ['ABSession', 'Root', 'print_chart', 'read_process',
           'run_standard_benchmarks', 'safe_threads',
           'size_chart', 'startup', 'thread_chart',
           ]

size_cache = {}

class Root:
    def index(self):
        return r"Hello, world\r\n"
    index.exposed = True
    
    def sizer(self, size):
        resp = size_cache.get(size, None)
        if resp is None:
            size_cache[size] = resp = "X" * int(size)
        return resp
    sizer.exposed = True


conf = {
    'global': {
        'server.log_to_screen': False,
##        'server.log_file': os.path.join(curdir, "bench.log"),
        'server.environment': 'production',
        'server.socket_host': 'localhost',
        'server.socket_port': 8080,
        },
    '/static': {
        'static_filter.on': True,
        'static_filter.dir': 'static',
        'static_filter.root': curdir,
        },
    }
cherrypy.tree.mount(Root(), MOUNT_POINT, conf)
cherrypy.lowercase_api = True


def read_process(cmd, args=""):
    pipein, pipeout = os.popen4("%s %s" % (cmd, args))
    output = pipeout.read()
    if (# Windows
        output.startswith("'%s' is not recognized" % cmd)
        # bash
        or re.match(r"bash: .*: No such file", output)
        ):
        raise IOError('%s must be on your system path.' % cmd)
    pipeout.close()
    return output


class ABSession:
    """A session of 'ab', the Apache HTTP server benchmarking tool.

Example output from ab:

This is ApacheBench, Version 2.0.40-dev <$Revision: 1.121.2.1 $> apache-2.0
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


Server Software:        CherryPy/2.2.0beta
Server Hostname:        localhost
Server Port:            8080

Document Path:          /static/index.html
Document Length:        14 bytes

Concurrency Level:      10
Time taken for tests:   9.643867 seconds
Complete requests:      1000
Failed requests:        0
Write errors:           0
Total transferred:      189000 bytes
HTML transferred:       14000 bytes
Requests per second:    103.69 [#/sec] (mean)
Time per request:       96.439 [ms] (mean)
Time per request:       9.644 [ms] (mean, across all concurrent requests)
Transfer rate:          19.08 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   2.9      0      10
Processing:    20   94   7.3     90     130
Waiting:        0   43  28.1     40     100
Total:         20   95   7.3    100     130

Percentage of the requests served within a certain time (ms)
  50%    100
  66%    100
  75%    100
  80%    100
  90%    100
  95%    100
  98%    100
  99%    110
 100%    130 (longest request)
Finished 1000 requests
"""
    
    parse_patterns = [('complete_requests', 'Completed',
                       r'^Complete requests:\s*(\d+)'),
                      ('failed_requests', 'Failed',
                       r'^Failed requests:\s*(\d+)'),
                      ('requests_per_second', 'req/sec',
                       r'^Requests per second:\s*([0-9.]+)'),
                      ('time_per_request_concurrent', 'msec/req',
                       r'^Time per request:\s*([0-9.]+).*concurrent requests\)$'),
                      ('transfer_rate', 'KB/sec',
                       r'^Transfer rate:\s*([0-9.]+)'),
                      ]
    
    def __init__(self, path=MOUNT_POINT + "/", requests=1000, concurrency=10):
        self.path = path
        self.requests = requests
        self.concurrency = concurrency
    
    def args(self):
        port = cherrypy.config.get('server.socket_port')
        assert self.concurrency > 0
        assert self.requests > 0
        return ("-n %s -c %s http://localhost:%s%s" %
                (self.requests, self.concurrency, port, self.path))
    
    def run(self):
        # Parse output of ab, setting attributes on self
        self.output = read_process("ab", self.args())
        for attr, name, pattern in self.parse_patterns:
            val = re.search(pattern, self.output, re.MULTILINE)
            if val:
                val = val.group(1)
                setattr(self, attr, val)


safe_threads = (25, 50, 100, 200, 400)
if sys.platform in ("win32",):
    # For some reason, ab crashes with > 50 threads on my Win2k laptop.
    safe_threads = (10, 20, 30, 40, 50)


def thread_chart(path=MOUNT_POINT + "/", concurrency=safe_threads):
    sess = ABSession(path)
    attrs, names, patterns = zip(*sess.parse_patterns)
    rows = [('threads',) + names]
    for c in concurrency:
        sess.concurrency = c
        sess.run()
        rows.append([c] + [getattr(sess, attr) for attr in attrs])
    return rows

def size_chart(sizes=(1, 10, 50, 100, 100000, 100000000),
               concurrency=50):
    sess = ABSession(concurrency=concurrency)
    attrs, names, patterns = zip(*sess.parse_patterns)
    rows = [('bytes',) + names]
    for sz in sizes:
        sess.path = "%s/sizer?size=%s" % (MOUNT_POINT, sz)
        sess.run()
        rows.append([sz] + [getattr(sess, attr) for attr in attrs])
    return rows

def print_chart(rows):
    widths = []
    for i in range(len(rows[0])):
        lengths = [len(str(row[i])) for row in rows]
        widths.append(max(lengths))
    for row in rows:
        print
        for i, val in enumerate(row):
            print str(val).rjust(widths[i]), "|",
    print


def run_standard_benchmarks():
    print
    print "Thread Chart (1000 requests, 14 byte response body):"
    print_chart(thread_chart())
    
    print
    print "Thread Chart (1000 requests, 14 bytes via static_filter):"
    print_chart(thread_chart("%s/static/index.html" % MOUNT_POINT))
    
    print
    print "Size Chart (1000 requests, 50 threads):"
    print_chart(size_chart())


started = False
def startup(req=None):
    """Start the CherryPy app server in 'serverless' mode (for WSGI)."""
    global started
    if not started:
        started = True
        cherrypy.server.start(init_only=True, server_class=None)
    return 0 # apache.OK


if __name__ == '__main__':
    if "-notests" in sys.argv:
        # Return without stopping the server, so that the pages
        # can be tested from a standard web browser.
        run = lambda x: x
    else:
        def run():
            end = time.time() - start
            print "Started in %s seconds" % end
            try:
                run_standard_benchmarks()
            finally:
                cherrypy.server.stop()
    
    print "Starting CherryPy app server..."
    start = time.time()
    
    if "-modpython" in sys.argv:
        try:
            mpconf = os.path.join(curdir, "bench_mp.conf")
            read_process("apache", "-k start -f %s" % mpconf)
            run()
        finally:
            os.popen("apache -k stop")
    else:
        # This will block
        cherrypy.server.start_with_callback(run)

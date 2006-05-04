"""
Script to simulate lots of concurrent requests to a site that uses sessions.
It then checks that the integrity of the session data has been kept


"""

import cherrypy
import httplib
import sys
import thread
import time

if len(sys.argv) == 1:
    print """Usage: test_session_concurrency [storage_type]
            [storage_path (for file sessions)]
            [# of server threads] [# of client threads] [# of requests]"""
    print "Example 1: test_session_concurrency ram"
    print "Example 2: test_session_concurrency file /tmp"
    sys.exit(0)

storage_type = sys.argv[1]
if storage_type == 'file':
    storage_path = sys.argv[2]
    i = 3
else:
    i = 2
    storage_path = 'dummy'

try:
    server_thread_count = sys.argv[i]
except IndexError:
    server_thread_count = 10
try:
    client_thread_count = sys.argv[i+1]
except IndexError:
    client_thread_count = 5
try:
    request_count = sys.argv[i+2]
except IndexError:
    request_count = 30

# Server code
class Root:
    def index(self):
        # If you remove the "acquire_lock" call the assert at the end
        #   of this script will fail
        cherrypy.session.acquire_lock()
        c = cherrypy.session.get('counter', 0) + 1
        time.sleep(0.1)
        cherrypy.session['counter'] = c
        return str(c)
    index.exposed = True

cherrypy.config.update({
    'server.environment': 'production',
    'server.log_to_screen': False,
    'server.thread_pool': server_thread_count,
    'session_filter.on': True,
    'session_filter.storage_type': storage_type,
    'session_filter.storage_path': storage_path,
})
cherrypy.root = Root()

# Client code
def run_client(cookie, request_count, data_dict, index):

    # Make other requests
    for i in xrange(request_count):
        conn = httplib.HTTPConnection('localhost:8080')
        conn.request("GET", "/", headers = {'Cookie': cookie})
        r = conn.getresponse()
        cookie = r.getheader('set-cookie').split(';')[0]
        data = r.read()
        conn.close()
    data_dict[index] = int(data)

# Start server
cherrypy.server.start()
thread.start_new_thread(cherrypy.engine.start, ())

# Start client
time.sleep(2)

# Make first request to get cookie
conn = httplib.HTTPConnection('localhost:8080')
conn.request("GET", "/")
r = conn.getresponse()
cookie = r.getheader('set-cookie').split(';')[0]
data = r.read()
conn.close()

data_dict = {}
# Simulate <request_count> concurrent requests from <client_thread_count>
# from the same client
for i in xrange(client_thread_count):
    data_dict[i] = 0
    thread.start_new_thread(run_client, (cookie, request_count, data_dict, i))
print "Please wait while test is running (default settings take about 30secs)"
while True:
    all_finished = True
    for data in data_dict.values():
        if data == 0:
            all_finished = False
            break
    if all_finished:
        break
    time.sleep(1)

cherrypy.server.stop()
cherrypy.engine.stop()

m = max(data_dict.values())
expected_m = 1 + (client_thread_count * request_count)
if m != expected_m:
    print "Problem, max is %s instead of %s (data_dict: %s)" % (
        m, expected_m, data_dict)
else:
    print "Everything OK"


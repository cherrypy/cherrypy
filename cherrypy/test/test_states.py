import httplib
import os
import sys
import threading
import time

from cherrypy.test import test
test.prefer_parent_path()

import cherrypy


class Root:
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def ctrlc(self):
        raise KeyboardInterrupt()
    ctrlc.exposed = True
    
    def restart(self):
        cherrypy.engine.restart()
        return "app was restarted succesfully"
    restart.exposed = True
    
    def block_explicit(self):
        while True:
            if cherrypy.response.timed_out:
                cherrypy.response.timed_out = False
                return "broken!"
            time.sleep(0.01)
    block_explicit.exposed = True
    
    def block_implicit(self):
        time.sleep(0.5)
        return "response.timeout = %s" % cherrypy.response.timeout
    block_implicit.exposed = True

cherrypy.tree.mount(Root())
cherrypy.config.update({
    'environment': 'test_suite',
    'engine.deadlock_poll_freq': 0.1,
    'response.timeout': 0.2,
    })

class Dependency:
    
    def __init__(self):
        self.running = False
        self.startcount = 0
        self.threads = {}
    
    def start(self):
        self.running = True
        self.startcount += 1
    
    def stop(self):
        self.running = False
    
    def startthread(self, thread_id):
        self.threads[thread_id] = None
    
    def stopthread(self, thread_id):
        del self.threads[thread_id]


from cherrypy.test import helper

class ServerStateTests(helper.CPWebCase):
    
    def test_0_NormalStateFlow(self):
        if not self.server_class:
            # Without having called "cherrypy.engine.start()", we should
            # get a 503 Service Unavailable response.
            self.getPage("/")
            self.assertStatus(503)
        
        # And our db_connection should not be running
        self.assertEqual(db_connection.running, False)
        self.assertEqual(db_connection.startcount, 0)
        self.assertEqual(len(db_connection.threads), 0)
        
        # Test server start
        cherrypy.server.quickstart(self.server_class)
        cherrypy.engine.start(blocking=False)
        self.assertEqual(cherrypy.engine.state, 1)
        
        if self.server_class:
            host = cherrypy.server.socket_host
            port = cherrypy.server.socket_port
            self.assertRaises(IOError, cherrypy._cpserver.check_port, host, port)
        
        # The db_connection should be running now
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, 1)
        self.assertEqual(len(db_connection.threads), 0)
        
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test engine stop
        cherrypy.engine.stop()
        self.assertEqual(cherrypy.engine.state, 0)
        
        # Verify that the on_stop_engine function was called
        self.assertEqual(db_connection.running, False)
        self.assertEqual(len(db_connection.threads), 0)
        
        if not self.server_class:
            # Once the engine has stopped, we should get a 503
            # error again. (If we were running an HTTP server,
            # then the connection should not even be processed).
            self.getPage("/")
            self.assertStatus(503)
        
        # Block the main thread now and verify that stop() works.
        def stoptest():
            self.getPage("/")
            self.assertBody("Hello World")
            cherrypy.engine.stop()
        cherrypy.engine.start_with_callback(stoptest)
        self.assertEqual(cherrypy.engine.state, 0)
        cherrypy.server.stop()
    
    def test_1_Restart(self):
        cherrypy.server.start()
        cherrypy.engine.start(blocking=False)
        
        # The db_connection should be running now
        self.assertEqual(db_connection.running, True)
        sc = db_connection.startcount
        
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from this thread
        cherrypy.engine.restart()
        self.assertEqual(cherrypy.engine.state, 1)
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, sc + 1)
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from inside a page handler
        self.getPage("/restart")
        self.assertEqual(cherrypy.engine.state, 1)
        self.assertBody("app was restarted succesfully")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, sc + 2)
        # Since we are requesting synchronously, is only one thread used?
        # Note that the "/restart" request has been flushed.
        self.assertEqual(len(db_connection.threads), 0)
        
        cherrypy.engine.stop()
        self.assertEqual(cherrypy.engine.state, 0)
        self.assertEqual(db_connection.running, False)
        self.assertEqual(len(db_connection.threads), 0)
        cherrypy.server.stop()
    
    def test_2_KeyboardInterrupt(self):
        if self.server_class:
            
            # Raise a keyboard interrupt in the HTTP server's main thread.
            # We must start the server in this, the main thread
            cherrypy.engine.start(blocking=False)
            cherrypy.server.start()
            cherrypy.server.httpservers.keys()[0].interrupt = KeyboardInterrupt
            while cherrypy.engine.state != 0:
                time.sleep(0.1)
            
            self.assertEqual(db_connection.running, False)
            self.assertEqual(len(db_connection.threads), 0)
            self.assertEqual(cherrypy.engine.state, 0)
            
            # Raise a keyboard interrupt in a page handler; on multithreaded
            # servers, this should occur in one of the worker threads.
            # This should raise a BadStatusLine error, since the worker
            # thread will just die without writing a response.
            cherrypy.engine.start(blocking=False)
            cherrypy.server.start()
            
            from httplib import BadStatusLine
            try:
                self.getPage("/ctrlc")
            except BadStatusLine:
                pass
            else:
                print self.body
                self.fail("AssertionError: BadStatusLine not raised")
            
            while cherrypy.engine.state != 0:
                time.sleep(0.1)
            self.assertEqual(db_connection.running, False)
            self.assertEqual(len(db_connection.threads), 0)
    
    def test_3_Deadlocks(self):
        cherrypy.engine.start(blocking=False)
        cherrypy.server.start()
        try:
            self.assertNotEqual(cherrypy.engine.monitor_thread, None)
            
            # Request a "normal" page.
            self.assertEqual(cherrypy.engine.servings, [])
            self.getPage("/")
            self.assertBody("Hello World")
            # request.close is called async.
            while cherrypy.engine.servings:
                time.sleep(0.01)
            
            # Request a page that explicitly checks itself for deadlock.
            # The deadlock_timeout should be 2 secs.
            self.getPage("/block_explicit")
            self.assertBody("broken!")
            
            # Request a page that implicitly breaks deadlock.
            # If we deadlock, we want to touch as little code as possible,
            # so we won't even call handle_error, just bail ASAP.
            self.getPage("/block_implicit")
            self.assertStatus(500)
            self.assertInBody("raise cherrypy.TimeoutError()")
        finally:
            cherrypy.engine.stop()
            cherrypy.server.stop()
    
    def test_4_Autoreload(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        # Start the demo script in a new process
        demoscript = os.path.join(os.getcwd(), os.path.dirname(__file__),
                                  "test_states_demo.py")
        host = cherrypy.server.socket_host
        port = cherrypy.server.socket_port
        cherrypy._cpserver.wait_for_free_port(host, port)
        
        args = [sys.executable, demoscript, host, str(port)]
        if self.scheme == "https":
            args.append('-ssl')
        pid = os.spawnl(os.P_NOWAIT, sys.executable, *args)
        pid = str(pid)
        cherrypy._cpserver.wait_for_occupied_port(host, port)
        
        try:
            self.getPage("/pid")
            assert self.body.isdigit(), self.body
            pid = self.body
            
            # Give the autoreloader time to cache the file time.
            time.sleep(2)
            
            # Touch the file
            f = open(demoscript, 'ab')
            f.write(" ")
            f.close()
            
            # Give the autoreloader time to re-exec the process
            time.sleep(2)
            cherrypy._cpserver.wait_for_occupied_port(host, port)
            
            self.getPage("/pid")
            assert self.body.isdigit(), self.body
            self.assertNotEqual(self.body, pid)
            pid = self.body
        finally:
            # Shut down the spawned process
            self.getPage("/stop")
        
        try:
            try:
                # Mac, UNIX
                print os.wait()
            except AttributeError:
                # Windows
                print os.waitpid(int(pid), 0)
        except OSError, x:
            if x.args != (10, 'No child processes'):
                raise

db_connection = None

def run(server, conf):
    helper.setConfig(conf)
    ServerStateTests.server_class = server
    suite = helper.CPTestLoader.loadTestsFromTestCase(ServerStateTests)
    try:
        global db_connection
        db_connection = Dependency()
        cherrypy.engine.on_start_engine_list.append(db_connection.start)
        cherrypy.engine.on_stop_engine_list.append(db_connection.stop)
        cherrypy.engine.on_start_thread_list.append(db_connection.startthread)
        cherrypy.engine.on_stop_thread_list.append(db_connection.stopthread)
        
        try:
            import pyconquer
        except ImportError:
            helper.CPTestRunner.run(suite)
        else:
            tr = pyconquer.Logger("cherrypy")
            tr.out = open(os.path.join(os.path.dirname(__file__), "state.log"), "wb")
            try:
                tr.start()
                helper.CPTestRunner.run(suite)
            finally:
                tr.stop()
                tr.out.close()
    finally:
        cherrypy.server.stop()
        cherrypy.engine.stop()


def run_all(host, port, ssl=False):
    conf = {'server.socket_host': host,
            'server.socket_port': port,
            'server.thread_pool': 10,
            'environment': "test_suite",
            }
    
    if ssl:
        localDir = os.path.dirname(__file__)
        serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
        conf['server.ssl_certificate'] = serverpem
        conf['server.ssl_private_key'] = serverpem
        ServerStateTests.scheme = "https"
        ServerStateTests.HTTP_CONN = httplib.HTTPSConnection
    
    def _run(server):
        print
        print "Testing %s on %s:%s..." % (server, host, port)
        run(server, conf)
    _run("cherrypy._cpwsgi.WSGIServer")


def run_localhosts(port):
    for host in ("", "127.0.0.1", "localhost"):
        conf = {'server.socket_host': host,
                'server.socket_port': port,
                'server.thread_pool': 10,
                'environment': "test_suite",
                }
        def _run(server):
            print
            print "Testing %s on %s:%s..." % (server, host, port)
            run(server, conf)
        _run("cherrypy._cpwsgi.WSGIServer")


if __name__ == "__main__":
    import sys
    host = '127.0.0.1'
    port = 8000
    ssl = False
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in [prefix + atom for atom in ("?", "h", "help")
                   for prefix in ("", "-", "--", "\\")]:
            print
            print "test_states.py -?                 -> this help page"
            print "test_states.py [host] [port]      -> run the tests on the given host/port"
            print "test_states.py -ssl [port]        -> run the tests using SSL on %s:port" % host
            print "test_states.py -localhosts [port] -> try various localhost strings"
            sys.exit(0)
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
        if cmd == "-localhosts":
            run_localhosts(port)
            sys.exit(0)
        if cmd == "-ssl":
            ssl = True
        else:
            host = cmd.strip("\"'")
    run_all(host, port, ssl)

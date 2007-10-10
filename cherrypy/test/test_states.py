import httplib
from httplib import BadStatusLine

import os
import sys
import threading
import time

from cherrypy.test import test
test.prefer_parent_path()

import cherrypy
engine = cherrypy.engine
thisdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
PID_file_path = os.path.join(thisdir,'pid_for_test_daemonize')

class Root:
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def ctrlc(self):
        raise KeyboardInterrupt()
    ctrlc.exposed = True
    
    def graceful(self):
        engine.graceful()
        return "app was (gracefully) restarted succesfully"
    graceful.exposed = True
    
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
    })

class Dependency:
    
    def __init__(self):
        self.running = False
        self.startcount = 0
        self.gracecount = 0
        self.threads = {}
    
    def start(self):
        self.running = True
        self.startcount += 1
    
    def stop(self):
        self.running = False
    
    def graceful(self):
        self.gracecount += 1
    
    def startthread(self, thread_id):
        self.threads[thread_id] = None
    
    def stopthread(self, thread_id):
        del self.threads[thread_id]


from cherrypy.test import helper

class ServerStateTests(helper.CPWebCase):
    
    def test_0_NormalStateFlow(self):
        if not self.server_class:
            # Without having called "engine.start()", we should
            # get a 503 Service Unavailable response.
            self.getPage("/")
            self.assertStatus(503)
        
        # And our db_connection should not be running
        self.assertEqual(db_connection.running, False)
        self.assertEqual(db_connection.startcount, 0)
        self.assertEqual(len(db_connection.threads), 0)
        
        # Test server start
        cherrypy.server.quickstart(self.server_class)
        engine.start()
        self.assertEqual(engine.state, engine.states.STARTED)
        
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
        
        # Test engine stop. This will also stop the HTTP server.
        engine.stop()
        self.assertEqual(engine.state, engine.states.STOPPED)
        
        # Verify that our custom stop function was called
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
            engine.stop()
        cherrypy.server.start()
        engine.start_with_callback(stoptest)
        engine.block()
        self.assertEqual(engine.state, engine.states.STOPPED)
    
    def test_1_Restart(self):
        cherrypy.server.start()
        engine.start()
        
        # The db_connection should be running now
        self.assertEqual(db_connection.running, True)
        grace = db_connection.gracecount
        
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from this thread
        engine.graceful()
        self.assertEqual(engine.state, engine.states.STARTED)
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.gracecount, grace + 1)
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from inside a page handler
        self.getPage("/graceful")
        self.assertEqual(engine.state, engine.states.STARTED)
        self.assertBody("app was (gracefully) restarted succesfully")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.gracecount, grace + 2)
        # Since we are requesting synchronously, is only one thread used?
        # Note that the "/graceful" request has been flushed.
        self.assertEqual(len(db_connection.threads), 0)
        
        engine.stop()
        self.assertEqual(engine.state, engine.states.STOPPED)
        self.assertEqual(db_connection.running, False)
        self.assertEqual(len(db_connection.threads), 0)
    
    def test_2_KeyboardInterrupt(self):
        if self.server_class:
            
            # Raise a keyboard interrupt in the HTTP server's main thread.
            # We must start the server in this, the main thread
            engine.start()
            cherrypy.server.start()
            
            self.persistent = True
            try:
                # Make the first request and assert there's no "Connection: close".
                self.getPage("/")
                self.assertStatus('200 OK')
                self.assertBody("Hello World")
                self.assertNoHeader("Connection")
                
                cherrypy.server.httpservers.keys()[0].interrupt = KeyboardInterrupt
                engine.block()
                
                self.assertEqual(db_connection.running, False)
                self.assertEqual(len(db_connection.threads), 0)
                self.assertEqual(engine.state, engine.states.STOPPED)
            finally:
                self.persistent = False
            
            # Raise a keyboard interrupt in a page handler; on multithreaded
            # servers, this should occur in one of the worker threads.
            # This should raise a BadStatusLine error, since the worker
            # thread will just die without writing a response.
            engine.start()
            cherrypy.server.start()
            
            try:
                self.getPage("/ctrlc")
            except BadStatusLine:
                pass
            else:
                print self.body
                self.fail("AssertionError: BadStatusLine not raised")
            
            engine.block()
            self.assertEqual(db_connection.running, False)
            self.assertEqual(len(db_connection.threads), 0)
    
    def test_3_Deadlocks(self):
        cherrypy.config.update({'response.timeout': 0.2})
        
        engine.start()
        cherrypy.server.start()
        try:
            self.assertNotEqual(cherrypy._timeout_monitor.thread, None)
            
            # Request a "normal" page.
            self.assertEqual(cherrypy._timeout_monitor.servings, [])
            self.getPage("/")
            self.assertBody("Hello World")
            # request.close is called async.
            while cherrypy._timeout_monitor.servings:
                print ".",
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
            engine.stop()
    
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
        cherrypy._cpserver.wait_for_occupied_port(host, port)
        
        try:
            self.getPage("/start")
            start = float(self.body)
            
            # Give the autoreloader time to cache the file time.
            time.sleep(2)
            
            # Touch the file
            os.utime(demoscript, None)
            
            # Give the autoreloader time to re-exec the process
            time.sleep(2)
            cherrypy._cpserver.wait_for_occupied_port(host, port)
            
            self.getPage("/pid")
            pid = int(self.body)
            
            self.getPage("/start")
            self.assert_(float(self.body) > start)
        finally:
            # Shut down the spawned process
            self.getPage("/stop")
        
        try:
            try:
                # Mac, UNIX
                print os.wait()
            except AttributeError:
                # Windows
                print os.waitpid(pid, 0)
        except OSError, x:
            if x.args != (10, 'No child processes'):
                raise

class DaemonizeTest(helper.CPWebCase):
    def test_0_Daemonize(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        if os.name not in ['posix']: 
            print "skipped (not on posix) ",
            return


        # Start the demo script in a new process
        demoscript = os.path.join(os.getcwd(), os.path.dirname(__file__),
                                  "test_states_demo.py")
        host = cherrypy.server.socket_host
        port = cherrypy.server.socket_port
        cherrypy._cpserver.wait_for_free_port(host, port)
        
        args = [sys.executable, demoscript, host, str(port), '-daemonize']
        if self.scheme == "https":
            args.append('-ssl')
        # Spawn the process and wait, when this returns, the original process
        # is finished.  If it daemonized properly, we should still be able
        # to access pages.
        exit_code = os.spawnl(os.P_WAIT, sys.executable, *args)
        cherrypy._cpserver.wait_for_occupied_port(host, port)

        # Give the server some time to start up
        time.sleep(2)

        # Get the PID from the file.
        pid = int(open(PID_file_path).read())
        try:
            # Just get the pid of the daemonization process.
            self.getPage("/pid")
            self.assertStatus(200)
            page_pid = int(self.body)
            self.assertEqual(page_pid, pid)
        finally:
            # Shut down the spawned process
            self.getPage("/stop")
        
        try:
            print os.waitpid(pid, 0)
        except OSError, x:
            if x.args != (10, 'No child processes'):
                raise

        # Wait until here to test the exit code because we want to ensure
        # that we wait for the daemon to finish running before we fail.
        if exit_code != 0:
            self.fail("Daemonized process failed to exit cleanly")
db_connection = None

def run(server, conf):
    helper.setConfig(conf)
    ServerStateTests.server_class = server
    DaemonizeTest.server_class = server
    suite = helper.CPTestLoader.loadTestsFromTestCase(ServerStateTests)
    daemon_suite = helper.CPTestLoader.loadTestsFromTestCase(DaemonizeTest)
    try:
        global db_connection
        db_connection = Dependency()
        engine.subscribe('start', db_connection.start)
        engine.subscribe('stop', db_connection.stop)
        engine.subscribe('graceful', db_connection.graceful)
        engine.subscribe('start_thread', db_connection.startthread)
        engine.subscribe('stop_thread', db_connection.stopthread)
        
        try:
            import pyconquer
        except ImportError:
            helper.CPTestRunner.run(suite)
            helper.CPTestRunner.run(daemon_suite)
        else:
            tr = pyconquer.Logger("cherrypy")
            tr.out = open(os.path.join(os.path.dirname(__file__), "state.log"), "wb")
            try:
                tr.start()
                helper.CPTestRunner.run(suite)
                helper.CPTestRunner.run(daemon_suite)
            finally:
                tr.stop()
                tr.out.close()
    finally:
        engine.stop()


def run_all(host, port, ssl=False):
    conf = {'server.socket_host': host,
            'server.socket_port': port,
            'server.thread_pool': 10,
            'environment': "test_suite",
            }
    
    if host:
        DaemonizeTest.HOST = ServerStateTests.HOST = host
    
    if port:
        DaemonizeTest.PORT = ServerStateTests.PORT = port
    
    if ssl:
        localDir = os.path.dirname(__file__)
        serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
        conf['server.ssl_certificate'] = serverpem
        conf['server.ssl_private_key'] = serverpem
        DaemonizeTest.scheme = ServerStateTests.scheme = "https"
        DaemonizeTest.HTTP_CONN = ServerStateTests.HTTP_CONN = httplib.HTTPSConnection
    
    def _run(server):
        print
        print "Testing %s on %s:%s..." % (server, host, port)
        run(server, conf)
    _run("cherrypy._cpwsgi.CPWSGIServer")

if __name__ == "__main__":
    import sys
    
    host = '127.0.0.1'
    port = 8000
    ssl = False
    
    argv = sys.argv[1:]
    if argv:
        help_args = [prefix + atom for atom in ("?", "h", "help")
                     for prefix in ("", "-", "--", "\\")]
        
        for arg in argv:
            if arg in help_args:
                print
                print "test_states.py -?                       -> this help page"
                print "test_states.py [-host=h] [-port=p]      -> run the tests on h:p"
                print "test_states.py -ssl [-host=h] [-port=p] -> run the tests using SSL on h:p"
                sys.exit(0)
            
            if arg == "-ssl":
                ssl = True
            elif arg.startswith("-host="):
                host = arg[6:].strip("\"'")
            elif arg.startswith("-port="):
                port = int(arg[6:].strip())
    
    run_all(host, port, ssl)

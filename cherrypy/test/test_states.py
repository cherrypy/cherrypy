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
    
    def __init__(self, bus):
        self.bus = bus
        self.running = False
        self.startcount = 0
        self.gracecount = 0
        self.threads = {}
    
    def subscribe(self):
        self.bus.subscribe('start', self.start)
        self.bus.subscribe('stop', self.stop)
        self.bus.subscribe('graceful', self.graceful)
        self.bus.subscribe('start_thread', self.startthread)
        self.bus.subscribe('stop_thread', self.stopthread)
    
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

db_connection = Dependency(engine)
db_connection.subscribe()



# ------------ Enough helpers. Time for real live test cases. ------------ #


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
        
        # Block the main thread now and verify that exit() works.
        def exittest():
            self.getPage("/")
            self.assertBody("Hello World")
            engine.exit()
        cherrypy.server.start()
        engine.start_with_callback(exittest)
        engine.block()
        self.assertEqual(engine.state, engine.states.EXITING)
    
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
                
                cherrypy.server.httpserver.interrupt = KeyboardInterrupt
                engine.block()
                
                self.assertEqual(db_connection.running, False)
                self.assertEqual(len(db_connection.threads), 0)
                self.assertEqual(engine.state, engine.states.EXITING)
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
            self.assertNotEqual(engine.timeout_monitor.thread, None)
            
            # Request a "normal" page.
            self.assertEqual(engine.timeout_monitor.servings, [])
            self.getPage("/")
            self.assertBody("Hello World")
            # request.close is called async.
            while engine.timeout_monitor.servings:
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
            engine.exit()
    
    def test_4_Autoreload(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        # Start the demo script in a new process
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'))
        p.write_conf()
        p.start(imports='cherrypy.test.test_states_demo')
        try:
            self.getPage("/start")
            start = float(self.body)
            
            # Give the autoreloader time to cache the file time.
            time.sleep(2)
            
            # Touch the file
            os.utime(os.path.join(thisdir, "test_states_demo.py"), None)
            
            # Give the autoreloader time to re-exec the process
            time.sleep(2)
            cherrypy._cpserver.wait_for_occupied_port(host, port)
            
            self.getPage("/start")
            self.assert_(float(self.body) > start)
        finally:
            # Shut down the spawned process
            self.getPage("/exit")
        p.join()
    
    def test_5_Start_Error(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        # If a process errors during start, it should stop the engine
        # and exit with a non-zero exit code.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'),
                             wait=True)
        p.write_conf(extra="starterror: True")
        p.start(imports='cherrypy.test.test_states_demo')
        if p.exit_code == 0:
            self.fail("Process failed to return nonzero exit code.")


class PluginTests(helper.CPWebCase):
    
    def test_daemonize(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        if os.name not in ['posix']: 
            print "skipped (not on posix) ",
            return
        
        # Spawn the process and wait, when this returns, the original process
        # is finished.  If it daemonized properly, we should still be able
        # to access pages.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'),
                             wait=True, daemonize=True)
        p.write_conf()
        p.start(imports='cherrypy.test.test_states_demo')
        try:
            # Just get the pid of the daemonization process.
            self.getPage("/pid")
            self.assertStatus(200)
            page_pid = int(self.body)
            self.assertEqual(page_pid, p.get_pid())
        finally:
            # Shut down the spawned process
            self.getPage("/exit")
        p.join()
        
        # Wait until here to test the exit code because we want to ensure
        # that we wait for the daemon to finish running before we fail.
        if p.exit_code != 0:
            self.fail("Daemonized parent process failed to exit cleanly.")


class SignalHandlingTests(helper.CPWebCase):
    
    def test_SIGHUP_tty(self):
        # When not daemonized, SIGHUP should shut down the server.
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        try:
            from signal import SIGHUP
        except ImportError:
            print "skipped (no SIGHUP) ",
            return
        
        # Spawn the process.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'))
        p.write_conf()
        p.start(imports='cherrypy.test.test_states_demo')
        # Send a SIGHUP
        os.kill(p.get_pid(), SIGHUP)
        # This might hang if things aren't working right, but meh.
        p.join()
    
    def test_SIGHUP_daemonized(self):
        # When daemonized, SIGHUP should restart the server.
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        try:
            from signal import SIGHUP
        except ImportError:
            print "skipped (no SIGHUP) ",
            return
        
        if os.name not in ['posix']: 
            print "skipped (not on posix) ",
            return
        
        # Spawn the process and wait, when this returns, the original process
        # is finished.  If it daemonized properly, we should still be able
        # to access pages.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'),
                             wait=True, daemonize=True)
        p.write_conf()
        p.start(imports='cherrypy.test.test_states_demo')
        
        pid = p.get_pid()
        try:
            # Send a SIGHUP
            os.kill(pid, SIGHUP)
            # Give the server some time to restart
            time.sleep(2)
            self.getPage("/pid")
            self.assertStatus(200)
            new_pid = int(self.body)
            self.assertNotEqual(new_pid, pid)
        finally:
            # Shut down the spawned process
            self.getPage("/exit")
        p.join()
    
    def test_SIGTERM(self):
        # SIGTERM should shut down the server whether daemonized or not.
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        try:
            from signal import SIGTERM
        except ImportError:
            print "skipped (no SIGTERM) ",
            return
        
        try:
            from os import kill
        except ImportError:
            print "skipped (no os.kill) ",
            return
        
        # Spawn a normal, undaemonized process.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'))
        p.write_conf()
        p.start(imports='cherrypy.test.test_states_demo')
        # Send a SIGTERM
        os.kill(p.get_pid(), SIGTERM)
        # This might hang if things aren't working right, but meh.
        p.join()
        
        if os.name in ['posix']: 
            # Spawn a daemonized process and test again.
            p = helper.CPProcess(ssl=(self.scheme.lower()=='https'),
                                 wait=True, daemonize=True)
            p.write_conf()
            p.start(imports='cherrypy.test.test_states_demo')
            # Send a SIGTERM
            os.kill(p.get_pid(), SIGTERM)
            # This might hang if things aren't working right, but meh.
            p.join()
    
    def test_signal_handler_unsubscribe(self):
        if not self.server_class:
            print "skipped (no server) ",
            return
        
        try:
            from signal import SIGTERM
        except ImportError:
            print "skipped (no SIGTERM) ",
            return
        
        try:
            from os import kill
        except ImportError:
            print "skipped (no os.kill) ",
            return
        
        # Spawn a normal, undaemonized process.
        p = helper.CPProcess(ssl=(self.scheme.lower()=='https'))
        p.write_conf(extra="unsubsig: True")
        p.start(imports='cherrypy.test.test_states_demo')
        # Send a SIGTERM
        os.kill(p.get_pid(), SIGTERM)
        # This might hang if things aren't working right, but meh.
        p.join()
        
        # Assert the old handler ran.
        target_line = open(p.error_log, 'rb').readlines()[-10]
        if not "I am an old SIGTERM handler." in target_line:
            self.fail("Old SIGTERM handler did not run.\n%r" % target_line)


cases = [v for v in globals().values()
         if isinstance(v, type) and issubclass(v, helper.CPWebCase)]

def run(server, conf):
    helper.setConfig(conf)
    for tc in cases:
        tc.server_class = server
    suites = [helper.CPTestLoader.loadTestsFromTestCase(tc) for tc in
              (ServerStateTests, PluginTests, SignalHandlingTests)]
    try:
        try:
            import pyconquer
        except ImportError:
            for suite in suites:
                helper.CPTestRunner.run(suite)
        else:
            tr = pyconquer.Logger("cherrypy")
            tr.out = open(os.path.join(os.path.dirname(__file__), "test_states_conquer.log"), "wb")
            try:
                tr.start()
                for suite in suites:
                    helper.CPTestRunner.run(suite)
            finally:
                tr.stop()
                tr.out.close()
    finally:
        engine.exit()


def run_all(host, port, ssl=False):
    conf = {'server.socket_host': host,
            'server.socket_port': port,
            'server.thread_pool': 10,
            'environment': "test_suite",
            }
    
    if host:
        for tc in cases:
            tc.HOST = host
    
    if port:
        for tc in cases:
            tc.PORT = port
    
    if ssl:
        localDir = os.path.dirname(__file__)
        serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
        conf['server.ssl_certificate'] = serverpem
        conf['server.ssl_private_key'] = serverpem
        for tc in cases:
            tc.scheme = "https"
            tc.HTTP_CONN = httplib.HTTPSConnection
    
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

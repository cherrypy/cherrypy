import test
test.prefer_parent_path()

import threading

import cherrypy


class Root:
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def ctrlc(self):
        raise KeyboardInterrupt()
    ctrlc.exposed = True
    
    def restart(self):
        cherrypy.server.restart()
        return "app was restarted succesfully"
    restart.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
    'global': {
        'server.log_to_screen': False,
        'server.environment': 'production',
    },
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


import helper

class ServerStateTests(helper.CPWebCase):
    
    def test_0_NormalStateFlow(self):
        # Without having called "cherrypy.server.start()", we should
        # get a NotReady error
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        
        # And our db_connection should not be running
        self.assertEqual(db_connection.running, False)
        self.assertEqual(db_connection.startcount, 0)
        self.assertEqual(len(db_connection.threads), 0)
        
        # Test server start
        cherrypy.server.start(True, self.serverClass)
        self.assertEqual(cherrypy.server.state, 1)
        
        if self.serverClass:
            host = cherrypy.config.get('server.socket_host')
            port = cherrypy.config.get('server.socket_port')
            self.assertRaises(IOError, cherrypy._cpserver.check_port, host, port)
        
        # The db_connection should be running now
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, 1)
        self.assertEqual(len(db_connection.threads), 0)
        
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server stop
        cherrypy.server.stop()
        self.assertEqual(cherrypy.server.state, 0)
        
        # Once the server has stopped, we should get a NotReady error again.
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        
        # Verify that the on_stop_server function was called
        self.assertEqual(db_connection.running, False)
        self.assertEqual(len(db_connection.threads), 0)
    
    def test_1_Restart(self):
        cherrypy.server.start(True, self.serverClass)
        
        # The db_connection should be running now
        self.assertEqual(db_connection.running, True)
        sc = db_connection.startcount
        
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from this thread
        cherrypy.server.restart()
        self.assertEqual(cherrypy.server.state, 1)
        self.getPage("/")
        self.assertBody("Hello World")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, sc + 1)
        self.assertEqual(len(db_connection.threads), 1)
        
        # Test server restart from inside a page handler
        self.getPage("/restart")
        self.assertEqual(cherrypy.server.state, 1)
        self.assertBody("app was restarted succesfully")
        self.assertEqual(db_connection.running, True)
        self.assertEqual(db_connection.startcount, sc + 2)
        # Since we are requesting synchronously, is only one thread used?
        # Note that the "/restart" request has been flushed.
        self.assertEqual(len(db_connection.threads), 0)
        
        cherrypy.server.stop()
        self.assertEqual(cherrypy.server.state, 0)
        self.assertEqual(db_connection.running, False)
        self.assertEqual(len(db_connection.threads), 0)
    
    def test_2_KeyboardInterrupt(self):
        if self.serverClass:
            
            # Raise a keyboard interrupt in the HTTP server's main thread.
            def interrupt():
                cherrypy.server.wait()
                cherrypy.server.httpserver.interrupt = KeyboardInterrupt
            threading.Thread(target=interrupt).start()
            
            # We must start the server in this, the main thread
            cherrypy.server.start(False, self.serverClass)
            # Time passes...
            self.assertEqual(cherrypy.server.httpserver, None)
            self.assertEqual(cherrypy.server.state, 0)
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")
            self.assertEqual(db_connection.running, False)
            self.assertEqual(len(db_connection.threads), 0)
            
            # Raise a keyboard interrupt in a page handler; on multithreaded
            # servers, this should occur in one of the worker threads.
            # This should raise a BadStatusLine error, since the worker
            # thread will just die without writing a response.
            def interrupt():
                cherrypy.server.wait()
                from httplib import BadStatusLine
                self.assertRaises(BadStatusLine, self.getPage, "/ctrlc")
            threading.Thread(target=interrupt).start()
            
            cherrypy.server.start(False, self.serverClass)
            # Time passes...
            self.assertEqual(cherrypy.server.httpserver, None)
            self.assertEqual(cherrypy.server.state, 0)
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")
            self.assertEqual(db_connection.running, False)
            self.assertEqual(len(db_connection.threads), 0)


db_connection = None

def run(server, conf):
    helper.setConfig(conf)
    ServerStateTests.serverClass = server
    suite = helper.CPTestLoader.loadTestsFromTestCase(ServerStateTests)
    try:
        global db_connection
        db_connection = Dependency()
        cherrypy.server.on_start_server_list.append(db_connection.start)
        cherrypy.server.on_stop_server_list.append(db_connection.stop)
        cherrypy.server.on_start_thread_list.append(db_connection.startthread)
        cherrypy.server.on_stop_thread_list.append(db_connection.stopthread)
        
        helper.CPTestRunner.run(suite)
    finally:
        cherrypy.server.stop()


def run_all(host, port):
    conf = {'server.socket_host': host,
            'server.socket_port': port,
            'server.thread_pool': 10,
            'server.log_to_screen': False,
            'server.log_config_options': False,
            'server.environment': "production",
            'server.show_tracebacks': True,
            }
    def _run(server):
        print
        print "Testing %s on %s:%s..." % (server or "serverless", host, port)
        run(server, conf)
    _run(None)
    _run("cherrypy._cpwsgi.WSGIServer")
    _run("cherrypy._cphttpserver.PooledThreadServer")
    conf['server.thread_pool'] = 1
    _run("cherrypy._cphttpserver.CherryHTTPServer")


def run_localhosts(port):
    for host in ("", "127.0.0.1", "localhost"):
        conf = {'server.socket_host': host,
                'server.socket_port': port,
                'server.thread_pool': 10,
                'server.log_to_screen': False,
                'server.log_config_options': False,
                'server.environment': "production",
                'server.show_tracebacks': True,
                }
        def _run(server):
            print
            print "Testing %s on %s:%s..." % (server or "serverless", host, port)
            run(server, conf)
        _run("cherrypy._cpwsgi.WSGIServer")
        _run("cherrypy._cphttpserver.PooledThreadServer")
        conf['server.thread_pool'] = 1
        _run("cherrypy._cphttpserver.CherryHTTPServer")


if __name__ == "__main__":
    import sys
    host = '127.0.0.1'
    port = 8000
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in [prefix + atom for atom in ("?", "h", "help")
                   for prefix in ("", "-", "--", "\\")]:
            print
            print "test_states.py -?             -> this help page"
            print "test_states.py [host] [port]  -> run the tests on the given host/port"
            print "test_states.py -localhosts [port]  -> try various localhost strings"
            sys.exit(0)
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
        if cmd == "-localhosts":
            run_localhosts(port)
            sys.exit(0)
        host = sys.argv[1].strip("\"'")
    run_all(host, port)

from cherrypy.test import test
test.prefer_parent_path()

import unittest

import cherrypy
from cherrypy.process import wspbus


msg = "Listener %d on channel %s: %s."


class PublishSubscribeTests(unittest.TestCase):

    def get_listener(self, channel, index):
        def listener(arg=None):
            self.responses.append(msg % (index, channel, arg))
        return listener
    
    def test_builtin_channels(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        
        for channel in b.listeners:
            for index, priority in enumerate([100, 50, 0, 51]):
                b.subscribe(channel, self.get_listener(channel, index), priority)
        
        for channel in b.listeners:
            b.publish(channel)
            expected.extend([msg % (i, channel, None) for i in (2, 1, 3, 0)])
            b.publish(channel, arg=79347)
            expected.extend([msg % (i, channel, 79347) for i in (2, 1, 3, 0)])
        
        self.assertEqual(self.responses, expected)
    
    def test_custom_channels(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        
        custom_listeners = ('hugh', 'louis', 'dewey')
        for channel in custom_listeners:
            for index, priority in enumerate([None, 10, 60, 40]):
                b.subscribe(channel, self.get_listener(channel, index), priority)
        
        for channel in custom_listeners:
            b.publish(channel, 'ah so')
            expected.extend([msg % (i, channel, 'ah so') for i in (1, 3, 0, 2)])
            b.publish(channel)
            expected.extend([msg % (i, channel, None) for i in (1, 3, 0, 2)])
        
        self.assertEqual(self.responses, expected)
    
    def test_listener_errors(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        channels = [c for c in b.listeners if c != 'log']
        
        for channel in channels:
            b.subscribe(channel, self.get_listener(channel, 1))
            # This will break since the lambda takes no args.
            b.subscribe(channel, lambda: None, priority=20)
        
        for channel in channels:
            self.assertRaises(TypeError, b.publish, channel, 123)
            expected.append(msg % (1, channel, 123))
        
        self.assertEqual(self.responses, expected)


class BusMethodTests(unittest.TestCase):
    
    def log(self, bus):
        self._log_entries = []
        def logit(msg, level):
            self._log_entries.append(msg)
        bus.subscribe('log', logit)
    
    def assertLog(self, entries):
        self.assertEqual(self._log_entries, entries)
    
    def get_listener(self, channel, index):
        def listener(arg=None):
            self.responses.append(msg % (index, channel, arg))
        return listener
    
    def test_start(self):
        b = wspbus.Bus()
        self.log(b)
        
        self.responses = []
        num = 3
        for index in range(num):
            b.subscribe('start', self.get_listener('start', index))
        
        b.start()
        try:
            # The start method MUST call all 'start' listeners.
            self.assertEqual(set(self.responses),
                             set([msg % (i, 'start', None) for i in range(num)]))
            # The start method MUST move the state to STARTED
            # (or EXITING, if errors occur)
            self.assertEqual(b.state, b.states.STARTED)
            # The start method MUST log its states.
            self.assertLog(['Bus STARTING', 'Bus STARTED'])
        finally:
            # Exit so the atexit handler doesn't complain.
            b.exit()


if __name__ == "__main__":
    setup_server()
    helper.testmain()

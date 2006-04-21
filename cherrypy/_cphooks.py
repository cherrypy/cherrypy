try:
    set
except NameError:
    from sets import Set as set
import cherrypy


class Hook(object):
    """A point at which CherryPy will call registered callbacks."""
    
    def __init__(self, name, failsafe = False):
        self.name = name
        self.failsafe = failsafe
        self.callbacks = []


class HookDispatcher(object):
    
    _input_hooks = [Hook('on_start_resource', failsafe=True),
                    Hook('before_request_body'),
                    Hook('before_main')]
    _output_hooks = [Hook('before_finalize'),
                     Hook('on_end_resource', failsafe=True),
                     Hook('on_end_request', failsafe=True),
                     Hook('before_error_response'),
                     Hook('after_error_response'),
                     ]
    
    def __init__(self):
        self.hooks = dict([(k.name, k) for k
                           in self._input_hooks + self._output_hooks])
    
    def run(self, hook_name):
        """Execute all registered hooks for the given name."""
        hook = self.hooks[hook_name]
        for c in hook.callbacks:
            if cherrypy.config.enabled(c.name):
                kwargs = dict([(k, v) for k, v in conf if k.startswith(c.name + ".")])
                # The on_start_resource, on_end_resource, and on_end_request methods
                # are guaranteed to run even if other methods of the same name fail.
                # We will still log the failure, but proceed on to the next method.
                # The only way to stop all processing from one of these methods is
                # to raise SystemExit and stop the whole server. So, trap your own
                # errors in these methods!
                if hook.failsafe:
                    try:
                        c(**kwargs)
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except:
                        cherrypy.log(traceback=True)
                else:
                    c(**kwargs)
    
    def register(self, hook_name, callback):
        self.hooks[hook_name].callbacks.append(callback)
    
    def register_builtin(self, name):
        from cherrypy.lib import cptools
        if name == "base_url":
            self.register('before_request_body', cptools.base_url)
        elif name == "virtual_host":
            self.register('before_request_body', cptools.virtual_host)
        elif name == "static.file":
            from cherrypy.lib import static
            self.register(static.File(filename))


dispatcher = HookDispatcher()



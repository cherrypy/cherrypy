"""Configuration system for CherryPy.

Configuration in CherryPy is implemented via dictionaries. Keys are strings
which name the mapped value, which may be of any type.


Architecture
------------

CherryPy Requests are part of an Application, which runs in a global context,
and configuration data may apply to any of those three scopes:

    Global: configuration entries which apply everywhere are stored in
    cherrypy.config.
    
    Application: entries which apply to each mounted application are stored
    on the Application object itself, as 'app.config'. This is a two-level
    dict where each key is a path, or "relative URL" (for example, "/" or
    "/path/to/my/page"), and each value is a config dict. Usually, this
    data is provided in the call to cherrypy.tree.mount(root(), config=conf),
    although you may also use app.merge(conf).
    
    Request: each Request object possesses a single 'Request.config' dict.
    Early in the request process, this dict is populated by merging global
    config entries, Application entries (whose path equals or is a parent
    of Request.path_info), and any config acquired while looking up the
    page handler (see next).


Declaration
-----------

Configuration data may be supplied as a Python dictionary, as a filename,
or as an open file object. When you supply a filename or file, CherryPy
uses Python's builtin ConfigParser; you declare Application config by
writing each path as a section header:

    [/path/to/my/page]
    request.stream = True

To declare global configuration entries, place them in a [global] section.

You may also declare config entries directly on the classes and methods
(page handlers) that make up your CherryPy application via the '_cp_config'
attribute. For example:

    class Demo:
        _cp_config = {'tools.gzip.on': True}
        
        def index(self):
            raise cherrypy.InternalRedirect("/cuba")
        index.exposed = True
        index._cp_config = {'request.recursive_redirect': True}


Namespaces
----------

Configuration keys are separated into namespaces by the first "." in the key.
Current namespaces:

    engine:     Controls the 'application engine', including autoreload.
                These can only be declared in the global config.
    hooks:      Declares additional request-processing functions.
    log:        Configures the logging for each application.
                These can only be declared in the global or / config.
    request:    Adds attributes to each Request.
    response:   Adds attributes to each Response.
    server:     Controls the default HTTP server via cherrypy.server.
                These can only be declared in the global config.
    tools:      Runs and configures additional request-processing packages.

The only key that does not exist in a namespace is the "environment" entry.
This special entry 'imports' other config entries from a template stored in
cherrypy._cpconfig.environments[environment]. It only applies to the global
config, and only when you use cherrypy.config.update.
"""

import ConfigParser
import cherrypy


environments = {
    "staging": {
        'engine.autoreload_on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        },
    "production": {
        'engine.autoreload_on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        'log.screen': False,
        },
    "test_suite": {
        'engine.autoreload_on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': True,
        'log.screen': False,
        },
    }

def merge(base, other):
    """Merge one app config (from a dict, file, or filename) into another."""
    if isinstance(other, basestring):
        if other not in cherrypy.engine.reload_files:
            cherrypy.engine.reload_files.append(other)
        other = _Parser().dict_from_file(other)
    elif hasattr(other, 'read'):
        other = _Parser().dict_from_file(other)
    
    # Load other into base
    for section, value_map in other.iteritems():
        base.setdefault(section, {}).update(value_map)


class Config(dict):
    """The 'global' configuration data for the entire CherryPy process."""
    
    defaults = {
        'tools.log_tracebacks.on': True,
        'tools.log_headers.on': True,
        }
    
    namespaces = {"server": lambda k, v: setattr(cherrypy.server, k, v),
                  "engine": lambda k, v: setattr(cherrypy.engine, k, v),
                  "log": lambda k, v: setattr(cherrypy.log, k, v),
                  }
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset self to default values."""
        self.clear()
        dict.update(self, self.defaults)
    
    def update(self, config):
        """Update self from a dict, file or filename."""
        if isinstance(config, basestring):
            # Filename
            if config not in cherrypy.engine.reload_files:
                cherrypy.engine.reload_files.append(config)
            config = _Parser().dict_from_file(config)
        elif hasattr(config, 'read'):
            # Open file object
            config = _Parser().dict_from_file(config)
        else:
            config = config.copy()
        
        if isinstance(config.get("global", None), dict):
            config = config["global"]
        
        if 'environment' in config:
            env = environments[config['environment']]
            for k in env:
                if k not in config:
                    config[k] = env[k]
        
        if 'tools.staticdir.dir' in config:
            config['tools.staticdir.section'] = "global"
        
        # Must use this idiom in order to hit our custom __setitem__.
        for k, v in config.iteritems():
            self[k] = v
    
    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        
        # Override object properties if specified in config.
        atoms = k.split(".", 1)
        namespace = atoms[0]
        if namespace in self.namespaces:
            self.namespaces[namespace](atoms[1], v)


class _Parser(ConfigParser.ConfigParser):
    """Sub-class of ConfigParser that keeps the case of options and that raises
    an exception if the file cannot be read.
    """
    
    def optionxform(self, optionstr):
        return optionstr
    
    def read(self, filenames):
        if isinstance(filenames, basestring):
            filenames = [filenames]
        for filename in filenames:
            # try:
            #     fp = open(filename)
            # except IOError:
            #     continue
            fp = open(filename)
            try:
                self._read(fp, filename)
            finally:
                fp.close()
    
    def as_dict(self, raw=False, vars=None):
        """Convert an INI file to a dictionary"""
        # Load INI file into a dict
        from cherrypy.lib import unrepr
        result = {}
        for section in self.sections():
            if section not in result:
                result[section] = {}
            for option in self.options(section):
                value = self.get(section, option, raw, vars)
                try:
                    value = unrepr(value)
                except Exception, x:
                    msg = ("Config error in section: %s, option: %s, value: %s" %
                           (repr(section), repr(option), repr(value)))
                    raise ValueError(msg, x.__class__.__name__, x.args)
                result[section][option] = value
        return result
    
    def dict_from_file(self, file):
        if hasattr(file, 'read'):
            self.readfp(file)
        else:
            self.read(file)
        return self.as_dict()

del ConfigParser

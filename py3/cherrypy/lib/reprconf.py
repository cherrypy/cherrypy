"""Generic configuration system using unrepr.

Configuration data may be supplied as a Python dictionary, as a filename,
or as an open file object. When you supply a filename or file, Python's
builtin ConfigParser is used (with some extensions).

Namespaces
----------

Configuration keys are separated into namespaces by the first "." in the key.

The only key that cannot exist in a namespace is the "environment" entry.
This special entry 'imports' other config entries from a template stored in
the Config.environments dict.

You can define your own namespaces to be called when new config is merged
by adding a named handler to Config.namespaces. The name can be any string,
and the handler must be either a callable or a context manager.
"""

try:
    # Python 3.0+
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

import operator as _operator
import sys

def as_dict(config):
    """Return a dict from 'config' whether it is a dict, file, or filename."""
    if isinstance(config, str):
        config = Parser().dict_from_file(config)
    elif hasattr(config, 'read'):
        config = Parser().dict_from_file(config)
    return config


class NamespaceSet(dict):
    """A dict of config namespace names and handlers.
    
    Each config entry should begin with a namespace name; the corresponding
    namespace handler will be called once for each config entry in that
    namespace, and will be passed two arguments: the config key (with the
    namespace removed) and the config value.
    
    Namespace handlers may be any Python callable; they may also be
    Python 2.5-style 'context managers', in which case their __enter__
    method should return a callable to be used as the handler.
    See cherrypy.tools (the Toolbox class) for an example.
    """
    
    def __call__(self, config):
        """Iterate through config and pass it to each namespace handler.
        
        config
            A flat dict, where keys use dots to separate
            namespaces, and values are arbitrary.
        
        The first name in each config key is used to look up the corresponding
        namespace handler. For example, a config entry of {'tools.gzip.on': v}
        will call the 'tools' namespace handler with the args: ('gzip.on', v)
        """
        # Separate the given config into namespaces
        ns_confs = {}
        for k in config:
            if "." in k:
                ns, name = k.split(".", 1)
                bucket = ns_confs.setdefault(ns, {})
                bucket[name] = config[k]
        
        for ns, handler in self.items():
            exit = getattr(handler, "__exit__", None)
            if exit:
                with handler as callable:
                    for k, v in ns_confs.get(ns, {}).items():
                        callable(k, v)
            else:
                for k, v in ns_confs.get(ns, {}).items():
                    handler(k, v)
    
    def __repr__(self):
        return "%s.%s(%s)" % (self.__module__, self.__class__.__name__,
                              dict.__repr__(self))
    
    def __copy__(self):
        newobj = self.__class__()
        newobj.update(self)
        return newobj
    copy = __copy__


class Config(dict):
    """A dict-like set of configuration data, with defaults and namespaces.
    
    May take a file, filename, or dict.
    """
    
    defaults = {}
    environments = {}
    namespaces = NamespaceSet()
    
    def __init__(self, file=None, **kwargs):
        self.reset()
        if file is not None:
            self.update(file)
        if kwargs:
            self.update(kwargs)
    
    def reset(self):
        """Reset self to default values."""
        self.clear()
        dict.update(self, self.defaults)
    
    def update(self, config):
        """Update self from a dict, file or filename."""
        if isinstance(config, str):
            # Filename
            config = Parser().dict_from_file(config)
        elif hasattr(config, 'read'):
            # Open file object
            config = Parser().dict_from_file(config)
        else:
            config = config.copy()
        self._apply(config)
    
    def _apply(self, config):
        """Update self from a dict."""
        which_env = config.get('environment')
        if which_env:
            env = self.environments[which_env]
            for k in env:
                if k not in config:
                    config[k] = env[k]
        
        dict.update(self, config)
        self.namespaces(config)
    
    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        self.namespaces({k: v})


class Parser(ConfigParser):
    """Sub-class of ConfigParser that keeps the case of options and that 
    raises an exception if the file cannot be read.
    """
    
    def optionxform(self, optionstr):
        return optionstr
    
    def read(self, filenames):
        if isinstance(filenames, str):
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
        result = {}
        for section in self.sections():
            if section not in result:
                result[section] = {}
            for option in self.options(section):
                value = self.get(section, option, raw=raw, vars=vars)
                try:
                    value = unrepr(value)
                except Exception as x:
                    msg = ("Config error in section: %r, option: %r, "
                           "value: %r. Config values must be valid Python." %
                           (section, option, value))
                    raise ValueError(msg, x.__class__.__name__, x.args)
                result[section][option] = value
        return result
    
    def dict_from_file(self, file):
        if hasattr(file, 'read'):
            self.readfp(file)
        else:
            self.read(file)
        return self.as_dict()


# public domain "unrepr" implementation, found on the web and then improved.

class _Builder:
    
    def build(self, o):
        m = getattr(self, 'build_' + o.__class__.__name__, None)
        if m is None:
            raise TypeError("unrepr does not recognize %s" %
                            repr(o.__class__.__name__))
        return m(o)
    
    def build_Subscript(self, o):
        return self.build(o.value)[self.build(o.slice)]
    
    def build_Index(self, o):
        return self.build(o.value)
    
    def build_Call(self, o):
        callee = self.build(o.func)
        
        if o.args is None:
            args = ()
        else: 
            args = tuple([self.build(a) for a in o.args]) 
        
        if o.starargs is None:
            starargs = ()
        else:
            starargs = self.build(o.starargs)
        
        if o.kwargs is None:
            kwargs = {}
        else:
            kwargs = self.build(o.kwargs)
        
        return callee(*(args + starargs), **kwargs)
    
    def build_List(self, o):
        return list(map(self.build, o.elts))
    
    def build_Str(self, o):
        return o.s
    
    def build_Num(self, o):
        return o.n
    
    def build_Dict(self, o):
        return dict([(self.build(k), self.build(v))
                     for k, v in zip(o.keys, o.values)])
    
    def build_Tuple(self, o):
        return tuple(self.build_List(o))
    
    def build_Name(self, o):
        name = o.id
        if name == 'None':
            return None
        if name == 'True':
            return True
        if name == 'False':
            return False
        
        # See if the Name is a package or module. If it is, import it.
        try:
            return modules(name)
        except ImportError:
            pass
        
        # See if the Name is in builtins.
        try:
            import builtins
            return getattr(builtins, name)
        except AttributeError:
            pass
        
        raise TypeError("unrepr could not resolve the name %s" % repr(name))
        
    def build_UnaryOp(self, o):
        op, operand = map(self.build, [o.op, o.operand])
        return op(operand)
    
    def build_BinOp(self, o):
        left, op, right = map(self.build, [o.left, o.op, o.right]) 
        return op(left, right)

    def build_Add(self, o):
        return _operator.add
        
    def build_USub(self, o):
        return _operator.neg

    def build_Attribute(self, o):
        parent = self.build(o.value)
        return getattr(parent, o.attr)

    def build_NoneType(self, o):
        return None


def _astnode(s):
    """Return a Python ast Node compiled from a string."""
    try:
        import ast
    except ImportError:
        # Fallback to eval when ast package is not available,
        # e.g. IronPython 1.0.
        return eval(s)

    p = ast.parse("__tempvalue__ = " + s)
    return p.body[0].value

def unrepr(s):
    """Return a Python object compiled from a string."""
    if not s:
        return s
    obj = _astnode(s)
    return _Builder().build(obj)


def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        mod = sys.modules[modulePath]
        if mod is None:
            raise KeyError()
    except KeyError:
        # The last [''] is important.
        mod = __import__(modulePath, globals(), locals(), [''])
    return mod

def attributes(full_attribute_name):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    last_dot = full_attribute_name.rfind(".")
    attr_name = full_attribute_name[last_dot + 1:]
    mod_path = full_attribute_name[:last_dot]
    
    mod = modules(mod_path)
    # Let an AttributeError propagate outward.
    try:
        attr = getattr(mod, attr_name)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (mod_path, attr_name))
    
    # Return a reference to the attribute.
    return attr



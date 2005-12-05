import cherrypy
from cherrypy import _cputil

# These are in order for a reason!
# They must be strings matching keys in classMap
_input_order = [
    'CacheFilter',
    'LogDebugInfoFilter',
    'BaseUrlFilter',
    'DecodingFilter',
    'SessionFilter',
    'SessionAuthenticateFilter',
    'StaticFilter',
    'NsgmlsFilter',
    'TidyFilter',
    'XmlRpcFilter',
]

_output_order = [
    'XmlRpcFilter',
    'EncodingFilter',
    'TidyFilter',
    'NsgmlsFilter',
    'LogDebugInfoFilter',
    'GzipFilter',
    'SessionFilter',
    'CacheFilter',
]

_input_methods = ['on_start_resource', 'before_request_body', 'before_main']
_output_methods = ['before_finalize', 'on_end_resource', 'on_end_request',
        'before_error_response', 'after_error_response']

backward_compatibility_dict = {
    'on_start_resource': 'onStartResource',
    'before_request_body': 'beforeRequestBody',
    'before_main': 'beforeMain',
    'before_finalize': 'beforeFinalize',
    'on_end_resource': 'onEndResource',
    'on_end_request': 'onEndRequest',
    'before_error_response': 'beforeErrorResponse',
    'after_error_response': 'afterErrorResponse'
}

def init():
    """Initialize the filters."""
    
    from cherrypy.filters import baseurlfilter, cachefilter, \
        decodingfilter, encodingfilter, gzipfilter, logdebuginfofilter, \
        staticfilter, nsgmlsfilter, tidyfilter, \
        xmlrpcfilter, sessionauthenticatefilter, \
        sessionfilter
    
    classMap = {
        'BaseUrlFilter'      : baseurlfilter.BaseUrlFilter,
        'CacheFilter'        : cachefilter.CacheFilter,
        'DecodingFilter'     : decodingfilter.DecodingFilter,
        'EncodingFilter'     : encodingfilter.EncodingFilter,
        'GzipFilter'         : gzipfilter.GzipFilter,
        'LogDebugInfoFilter' : logdebuginfofilter.LogDebugInfoFilter,
        'NsgmlsFilter'       : nsgmlsfilter.NsgmlsFilter,
        'SessionAuthenticateFilter':
                    sessionauthenticatefilter.SessionAuthenticateFilter,
        'SessionFilter'      : sessionfilter.SessionFilter,
        'StaticFilter'       : staticfilter.StaticFilter,
        'TidyFilter'         : tidyfilter.TidyFilter,
        'XmlRpcFilter'       : xmlrpcfilter.XmlRpcFilter,
    }
    
    instances = {}
    inputs, outputs = [], []
    
    conf = cherrypy.config.get
    
    for name in _input_order + conf('server.inputFilters', []):
        f = instances.get(name)
        if f is None:
            f = instances[name] = classMap[name]()
        inputs.append(f)
    
    for name in conf('server.outputFilters', []) + _output_order:
        f = instances.get(name)
        if f is None:
            f = instances[name] = classMap[name]()
        outputs.append(f)
    
    # Transform the instance lists into a dict of methods
    _filterhooks.clear()
    for name in _input_methods:
        _filterhooks[name] = []
        for f in inputs:
            method = getattr(f, name, None)
            if method:
                _filterhooks[name].append(method)
    for name in _output_methods:
        _filterhooks[name] = []
        for f in outputs:
            method = getattr(f, name, None)
            if method:
                _filterhooks[name].append(method)


_filterhooks = {}


def applyFilters(method_name):
    """Execute the given method for all registered filters."""
    special_methods = []
    for f in _cputil.get_special_attribute("_cp_filters", "_cpFilterList"):
        # Try old name first
        old_method_name = backward_compatibility_dict.get(method_name)
        method = getattr(f, old_method_name, None)
        if (method is None):
            method = getattr(f, method_name, None)
        if method:
            special_methods.append(method)

    if method_name in _input_methods:
        # Run special filters after defaults.
        for method in _filterhooks[method_name] + special_methods:
            method()
    else:
        # Run special filters before defaults.
        for method in special_methods + _filterhooks[method_name]:
            method()

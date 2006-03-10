import cherrypy
from cherrypy import _cputil


# These are in order for a reason!
# Entries in the input_filters and output_filters lists
# may be either a class, or the full package name of a class.

input_filters = [
    "cherrypy.filters.cachefilter.CacheFilter",
    "cherrypy.filters.logdebuginfofilter.LogDebugInfoFilter",
    "cherrypy.filters.baseurlfilter.BaseUrlFilter",
    "cherrypy.filters.virtualhostfilter.VirtualHostFilter",
    "cherrypy.filters.decodingfilter.DecodingFilter",
    "cherrypy.filters.sessionfilter.SessionFilter",
    "cherrypy.filters.sessionauthenticatefilter.SessionAuthenticateFilter",
    "cherrypy.filters.staticfilter.StaticFilter",
    "cherrypy.filters.nsgmlsfilter.NsgmlsFilter",
    "cherrypy.filters.tidyfilter.TidyFilter",
    "cherrypy.filters.xmlrpcfilter.XmlRpcFilter",
    "cherrypy.filters.wsgiappfilter.WSGIAppFilter",
]

output_filters = [
    "cherrypy.filters.responseheadersfilter.ResponseHeadersFilter",
    "cherrypy.filters.xmlrpcfilter.XmlRpcFilter",
    "cherrypy.filters.encodingfilter.EncodingFilter",
    "cherrypy.filters.tidyfilter.TidyFilter",
    "cherrypy.filters.nsgmlsfilter.NsgmlsFilter",
    "cherrypy.filters.logdebuginfofilter.LogDebugInfoFilter",
    "cherrypy.filters.gzipfilter.GzipFilter",
    "cherrypy.filters.sessionfilter.SessionFilter",
    "cherrypy.filters.cachefilter.CacheFilter",
]

_input_methods = ['on_start_resource', 'before_request_body', 'before_main']
_output_methods = ['before_finalize', 'on_end_resource', 'on_end_request',
        'before_error_response', 'after_error_response']

_old_input_methods = ['onStartResource', 'beforeRequestBody', 'beforeMain']
_old_output_methods = ['beforeFinalize', 'onEndResource', 'onEndRequest',
        'beforeErrorResponse', 'afterErrorResponse']

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
    from cherrypy.lib import cptools
    
    instances = {}
    inputs, outputs = [], []
    
    conf = cherrypy.config.get
    
    for filtercls in input_filters + conf('server.input_filters', []):
        if isinstance(filtercls, basestring):
            filtercls = cptools.attributes(filtercls)
        
        f = instances.get(filtercls)
        if f is None:
            f = instances[filtercls] = filtercls()
        inputs.append(f)
    
    for filtercls in conf('server.output_filters', []) + output_filters:
        if isinstance(filtercls, basestring):
            filtercls = cptools.attributes(filtercls)
        
        f = instances.get(filtercls)
        if f is None:
            f = instances[filtercls] = filtercls()
        outputs.append(f)
    
    # Transform the instance lists into a dict of methods
    # in 2.2 we check the old camelCase filter names first
    # to provide backward compatibility with 2.1
    _filterhooks.clear()
    for old_name, new_name in zip(_old_input_methods, _input_methods):
        _filterhooks[new_name] = []
        for f in inputs:
            method = getattr(f, old_name, None)
            if method:
                _filterhooks[new_name].append(method)
            else:
                method = getattr(f, new_name, None)
                if method:
                    _filterhooks[new_name].append(method)
    for old_name, new_name in zip(_old_output_methods, _output_methods):
        _filterhooks[new_name] = []
        for f in outputs:
            method = getattr(f, old_name, None)
            if method:
                _filterhooks[new_name].append(method)
            else:
                method = getattr(f, new_name, None)
                if method:
                    _filterhooks[new_name].append(method)


_filterhooks = {}


def applyFilters(method_name, failsafe=False):
    """Execute the given method for all registered filters."""
    special_methods = []
    for f in _cputil.get_special_attribute("_cp_filters", "_cpFilterList"):
        if cherrypy.lowercase_api is False:
            # Try old name first
            old_method_name = backward_compatibility_dict.get(method_name)
            method = getattr(f, old_method_name, None)
            if (method is None):
                method = getattr(f, method_name, None)
            if method:
                special_methods.append(method)
        else:
            # We know for sure that user uses the new lowercase API
            method = getattr(f, method_name, None)
            if method:
                special_methods.append(method)
    
    if method_name in _input_methods:
        # Run special filters after defaults.
        methods = _filterhooks[method_name] + special_methods
    else:
        # Run special filters before defaults.
        methods = special_methods + _filterhooks[method_name]

    for method in methods:
        # The on_start_resource, on_end_resource, and on_end_request methods
        # are guaranteed to run even if other methods of the same name fail.
        # We will still log the failure, but proceed on to the next method.
        # The only way to stop all processing from one of these methods is
        # to raise SystemExit and stop the whole server. So, trap your own
        # errors in these methods!
        if failsafe:
            try:
                method()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                cherrypy.log(traceback=True)
        else:
            method()


import inspect
import sys

import cherrypy


class PageHandler(object):
    """Callable which sets response.body."""

    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    @property
    def args(self):
        """The ordered args should be accessible from post dispatch hooks."""
        return cherrypy.serving.request.args

    @args.setter
    def args(self, args):
        cherrypy.serving.request.args = args

    @property
    def kwargs(self):
        """The named kwargs should be accessible from post dispatch hooks."""
        return cherrypy.serving.request.kwargs

    @kwargs.setter
    def kwargs(self, kwargs):
        cherrypy.serving.request.kwargs = kwargs

    def __call__(self):
        try:
            return self.callable(*self.args, **self.kwargs)
        except TypeError:
            x = sys.exc_info()[1]
            try:
                test_callable_spec(self.callable, self.args, self.kwargs)
            except cherrypy.HTTPError:
                raise sys.exc_info()[1]
            except:
                raise x
            raise


def test_callable_spec(callable, callable_args, callable_kwargs):
    """
    Inspect callable and test to see if the given args are suitable for it.

    When an error occurs during the handler's invoking stage there are 2
    erroneous cases:
    1.  Too many parameters passed to a function which doesn't define
        one of *args or **kwargs.
    2.  Too little parameters are passed to the function.

    There are 3 sources of parameters to a cherrypy handler.
    1.  query string parameters are passed as keyword parameters to the
        handler.
    2.  body parameters are also passed as keyword parameters.
    3.  when partial matching occurs, the final path atoms are passed as
        positional args.
    Both the query string and path atoms are part of the URI.  If they are
    incorrect, then a 404 Not Found should be raised. Conversely the body
    parameters are part of the request; if they are invalid a 400 Bad Request.
    """
    show_mismatched_params = getattr(
        cherrypy.serving.request, 'show_mismatched_params', False)
    try:
        (args, varargs, varkw, defaults) = getargspec(callable)
    except TypeError:
        if isinstance(callable, object) and hasattr(callable, '__call__'):
            (args, varargs, varkw,
             defaults) = getargspec(callable.__call__)
        else:
            # If it wasn't one of our own types, re-raise
            # the original error
            raise

    if args and args[0] == 'self':
        args = args[1:]

    arg_usage = dict([(arg, 0,) for arg in args])
    vararg_usage = 0
    varkw_usage = 0
    extra_kwargs = set()

    for i, value in enumerate(callable_args):
        try:
            arg_usage[args[i]] += 1
        except IndexError:
            vararg_usage += 1

    for key in callable_kwargs.keys():
        try:
            arg_usage[key] += 1
        except KeyError:
            varkw_usage += 1
            extra_kwargs.add(key)

    # figure out which args have defaults.
    args_with_defaults = args[-len(defaults or []):]
    for i, val in enumerate(defaults or []):
        # Defaults take effect only when the arg hasn't been used yet.
        if arg_usage[args_with_defaults[i]] == 0:
            arg_usage[args_with_defaults[i]] += 1

    missing_args = []
    multiple_args = []
    for key, usage in arg_usage.items():
        if usage == 0:
            missing_args.append(key)
        elif usage > 1:
            multiple_args.append(key)

    if missing_args:
        # In the case where the method allows body arguments
        # there are 3 potential errors:
        # 1. not enough query string parameters -> 404
        # 2. not enough body parameters -> 400
        # 3. not enough path parts (partial matches) -> 404
        #
        # We can't actually tell which case it is,
        # so I'm raising a 404 because that covers 2/3 of the
        # possibilities
        #
        # In the case where the method does not allow body
        # arguments it's definitely a 404.
        message = None
        if show_mismatched_params:
            message = "Missing parameters: %s" % ",".join(missing_args)
        raise cherrypy.HTTPError(404, message=message)

    # the extra positional arguments come from the path - 404 Not Found
    if not varargs and vararg_usage > 0:
        raise cherrypy.HTTPError(404)

    body_params = cherrypy.serving.request.body.params or {}
    body_params = set(body_params.keys())
    qs_params = set(callable_kwargs.keys()) - body_params

    if multiple_args:
        if qs_params.intersection(set(multiple_args)):
            # If any of the multiple parameters came from the query string then
            # it's a 404 Not Found
            error = 404
        else:
            # Otherwise it's a 400 Bad Request
            error = 400

        message = None
        if show_mismatched_params:
            message = "Multiple values for parameters: %s" % ",".join(
                multiple_args)
        raise cherrypy.HTTPError(error, message=message)

    if not varkw and varkw_usage > 0:

        # If there were extra query string parameters, it's a 404 Not Found
        extra_qs_params = set(qs_params).intersection(extra_kwargs)
        if extra_qs_params:
            message = None
            if show_mismatched_params:
                message = "Unexpected query string parameters: %s" % ", ".join(
                    extra_qs_params)
            raise cherrypy.HTTPError(404, message=message)

        # If there were any extra body parameters, it's a 400 Not Found
        extra_body_params = set(body_params).intersection(extra_kwargs)
        if extra_body_params:
            message = None
            if show_mismatched_params:
                message = "Unexpected body parameters: %s" % ", ".join(
                    extra_body_params)
            raise cherrypy.HTTPError(400, message=message)


try:
    import inspect
except ImportError:
    test_callable_spec = lambda callable, args, kwargs: None
else:
    getargspec = inspect.getargspec
    # Python 3 requires using getfullargspec if keyword-only arguments are present
    if hasattr(inspect, 'getfullargspec'):
        def getargspec(callable):
            return inspect.getfullargspec(callable)[:4]


class LateParamPageHandler(PageHandler):
    """When passing cherrypy.request.params to the page handler, we do not
    want to capture that dict too early; we want to give tools like the
    decoding tool a chance to modify the params dict in-between the lookup
    of the handler and the actual calling of the handler. This subclass
    takes that into account, and allows request.params to be 'bound late'
    (it's more complicated than that, but that's the effect).
    """

    @property
    def kwargs(self):
        """page handler kwargs (with cherrypy.request.params copied in)"""
        kwargs = cherrypy.serving.request.params.copy()
        if self._kwargs:
            kwargs.update(self._kwargs)
        return kwargs

    @kwargs.setter
    def kwargs(self, kwargs):
        cherrypy.serving.request.kwargs = kwargs
        self._kwargs = kwargs

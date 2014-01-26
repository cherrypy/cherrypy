import cherrypy
from cherrypy.lib.dispatch.object import Dispatcher
from cherrypy.lib.dispatch.base import LateParamPageHandler


class MethodDispatcher(Dispatcher):
    """Additional dispatch based on cherrypy.request.method.upper().

    Methods named GET, POST, etc will be called on an exposed class.
    The method names must be all caps; the appropriate Allow header
    will be output showing all capitalized method names as allowable
    HTTP verbs.

    Note that the containing class must be exposed, not the methods.
    """

    def __call__(self, path_info):
        """Set handler and config for the current request."""
        request = cherrypy.serving.request
        resource, vpath = self.find_handler(path_info)

        if resource:
            # Set Allow header
            avail = [m for m in dir(resource) if m.isupper()]
            if "GET" in avail and "HEAD" not in avail:
                avail.append("HEAD")
            avail.sort()
            cherrypy.serving.response.headers['Allow'] = ", ".join(avail)

            # Find the subhandler
            meth = request.method.upper()
            func = getattr(resource, meth, None)
            if func is None and meth == "HEAD":
                func = getattr(resource, "GET", None)
            if func:
                # Grab any _cp_config on the subhandler.
                if hasattr(func, "_cp_config"):
                    request.config.update(func._cp_config)

                # Decode any leftover %2F in the virtual_path atoms.
                vpath = [x.replace("%2F", "/") for x in vpath]
                request.handler = LateParamPageHandler(func, *vpath)
            else:
                request.handler = cherrypy.HTTPError(405)
        else:
            request.handler = cherrypy.NotFound()
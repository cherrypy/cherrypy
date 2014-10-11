import types

import cherrypy
from cherrypy.lib.dispatch.base import LateParamPageHandler

try:
    classtype = (type, types.ClassType)
except AttributeError:
    classtype = type


class RoutesDispatcher(object):
    """A Routes based dispatcher for CherryPy."""

    def __init__(self, full_result=False, **mapper_options):
        """
        Routes dispatcher

        Set full_result to True if you wish the controller
        and the action to be passed on to the page handler
        parameters. By default they won't be.
        """
        import routes
        self.full_result = full_result
        self.controllers = {}
        self.mapper = routes.Mapper(**mapper_options)
        self.mapper.controller_scan = self.controllers.keys

    def connect(self, name, route, controller, **kwargs):
        self.controllers[name] = controller
        self.mapper.connect(name, route, controller=name, **kwargs)

    def redirect(self, url):
        raise cherrypy.HTTPRedirect(url)

    def __call__(self, path_info):
        """Set handler and config for the current request."""
        func = self.find_handler(path_info)
        if func:
            cherrypy.serving.request.handler = LateParamPageHandler(func)
        else:
            cherrypy.serving.request.handler = cherrypy.NotFound()

    def find_handler(self, path_info):
        """Find the right page handler, and set request.config."""
        import routes

        request = cherrypy.serving.request

        config = routes.request_config()
        config.mapper = self.mapper
        if hasattr(request, 'wsgi_environ'):
            config.environ = request.wsgi_environ
        config.host = request.headers.get('Host', None)
        config.protocol = request.scheme
        config.redirect = self.redirect

        result = self.mapper.match(path_info)

        config.mapper_dict = result
        params = {}
        if result:
            params = result.copy()
        if not self.full_result:
            params.pop('controller', None)
            params.pop('action', None)
        request.params.update(params)

        # Get config for the root object/path.
        request.config = base = cherrypy.config.copy()
        curpath = ""

        def merge(nodeconf):
            if 'tools.staticdir.dir' in nodeconf:
                nodeconf['tools.staticdir.section'] = curpath or "/"
            base.update(nodeconf)

        app = request.app
        root = app.root
        if hasattr(root, "_cp_config"):
            merge(root._cp_config)
        if "/" in app.config:
            merge(app.config["/"])

        # Mix in values from app.config.
        atoms = [x for x in path_info.split("/") if x]
        if atoms:
            last = atoms.pop()
        else:
            last = None
        for atom in atoms:
            curpath = "/".join((curpath, atom))
            if curpath in app.config:
                merge(app.config[curpath])

        handler = None
        if result:
            controller = result.get('controller')
            controller = self.controllers.get(controller, controller)
            if controller:
                if isinstance(controller, classtype):
                    controller = controller()
                # Get config from the controller.
                if hasattr(controller, "_cp_config"):
                    merge(controller._cp_config)

            action = result.get('action')
            if action is not None:
                handler = getattr(controller, action, None)
                # Get config from the handler
                if hasattr(handler, "_cp_config"):
                    merge(handler._cp_config)
            else:
                handler = controller

        # Do the last path atom here so it can
        # override the controller's _cp_config.
        if last:
            curpath = "/".join((curpath, last))
            if curpath in app.config:
                merge(app.config[curpath])

        return handler

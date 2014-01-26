import cherrypy
from cherrypy.lib.dispatch.base import (punctuation_to_underscores,
                                        validate_translator,
                                        LateParamPageHandler)


class Dispatcher(object):
    """CherryPy Dispatcher which walks a tree of objects to find a handler.

    The tree is rooted at cherrypy.request.app.root, and each hierarchical
    component in the path_info argument is matched to a corresponding nested
    attribute of the root object. Matching handlers must have an 'exposed'
    attribute which evaluates to True. The special method name "index"
    matches a URI which ends in a slash ("/"). The special method name
    "default" may match a portion of the path_info (but only when no longer
    substring of the path_info matches some other object).

    This is the default, built-in dispatcher for CherryPy.
    """

    dispatch_method_name = '_cp_dispatch'
    """
    The name of the dispatch method that nodes may optionally implement
    to provide their own dynamic dispatch algorithm.
    """

    def __init__(self, dispatch_method_name=None,
                 translate=punctuation_to_underscores):
        validate_translator(translate)
        self.translate = translate
        if dispatch_method_name:
            self.dispatch_method_name = dispatch_method_name

    def __call__(self, path_info):
        """Set handler and config for the current request."""
        request = cherrypy.serving.request
        func, vpath = self.find_handler(path_info)

        if func:
            # Decode any leftover %2F in the virtual_path atoms.
            vpath = [x.replace("%2F", "/") for x in vpath]
            request.handler = LateParamPageHandler(func, *vpath)
        else:
            request.handler = cherrypy.NotFound()

    def find_handler(self, path):
        """Return the appropriate page handler, plus any virtual path.

        This will return two objects. The first will be a callable,
        which can be used to generate page output. Any parameters from
        the query string or request body will be sent to that callable
        as keyword arguments.

        The callable is found by traversing the application's tree,
        starting from cherrypy.request.app.root, and matching path
        components to successive objects in the tree. For example, the
        URL "/path/to/handler" might return root.path.to.handler.

        The second object returned will be a list of names which are
        'virtual path' components: parts of the URL which are dynamic,
        and were not used when looking up the handler.
        These virtual path components are passed to the handler as
        positional arguments.
        """
        request = cherrypy.serving.request
        app = request.app
        root = app.root
        dispatch_name = self.dispatch_method_name

        # Get config for the root object/path.
        fullpath = [x for x in path.strip('/').split('/') if x] + ['index']
        fullpath_len = len(fullpath)
        segleft = fullpath_len
        nodeconf = {}
        if hasattr(root, "_cp_config"):
            nodeconf.update(root._cp_config)
        if "/" in app.config:
            nodeconf.update(app.config["/"])
        object_trail = [['root', root, nodeconf, segleft]]

        node = root
        iternames = fullpath[:]
        while iternames:
            name = iternames[0]
            # map to legal Python identifiers (e.g. replace '.' with '_')
            objname = name.translate(self.translate)

            nodeconf = {}
            subnode = getattr(node, objname, None)
            pre_len = len(iternames)
            if subnode is None:
                dispatch = getattr(node, dispatch_name, None)
                if (
                    dispatch and
                    hasattr(dispatch, '__call__') and not
                    getattr(dispatch, 'exposed', False) and
                    pre_len > 1
                ):
                    # Don't expose the hidden 'index' token to _cp_dispatch
                    # We skip this if pre_len == 1 since it makes no sense
                    # to call a dispatcher when we have no tokens left.
                    index_name = iternames.pop()
                    subnode = dispatch(vpath=iternames)
                    iternames.append(index_name)
                else:
                    # We didn't find a path, but keep processing in case there
                    # is a default() handler.
                    iternames.pop(0)
            else:
                # We found the path, remove the vpath entry
                iternames.pop(0)
            segleft = len(iternames)
            if segleft > pre_len:
                # No path segment was removed.  Raise an error.
                raise cherrypy.CherryPyException(
                    "A vpath segment was added.  Custom dispatchers may only "
                    + "remove elements.  While trying to process "
                    + "{0} in {1}".format(name, fullpath)
                )
            elif segleft == pre_len:
                # Assume that the handler used the current path segment, but
                # did not pop it.  This allows things like
                # return getattr(self, vpath[0], None)
                iternames.pop(0)
                segleft -= 1
            node = subnode

            if node is not None:
                # Get _cp_config attached to this node.
                if hasattr(node, "_cp_config"):
                    nodeconf.update(node._cp_config)

            # Mix in values from app.config for this path.
            existing_len = fullpath_len - pre_len
            if existing_len != 0:
                curpath = '/' + '/'.join(fullpath[0:existing_len])
            else:
                curpath = ''
            new_segs = fullpath[fullpath_len - pre_len:fullpath_len - segleft]
            for seg in new_segs:
                curpath += '/' + seg
                if curpath in app.config:
                    nodeconf.update(app.config[curpath])

            object_trail.append([name, node, nodeconf, segleft])

        def set_conf():
            """Collapse all object_trail config into cherrypy.request.config.
            """
            base = cherrypy.config.copy()
            # Note that we merge the config from each node
            # even if that node was None.
            for name, obj, conf, segleft in object_trail:
                base.update(conf)
                if 'tools.staticdir.dir' in conf:
                    base['tools.staticdir.section'] = (
                        '/' + '/'.join(fullpath[0:fullpath_len - segleft]))
            return base

        # Try successive objects (reverse order)
        num_candidates = len(object_trail) - 1
        for i in range(num_candidates, -1, -1):

            name, candidate, nodeconf, segleft = object_trail[i]
            if candidate is None:
                continue

            # Try a "default" method on the current leaf.
            if hasattr(candidate, "default"):
                defhandler = candidate.default
                if getattr(defhandler, 'exposed', False):
                    # Insert any extra _cp_config from the default handler.
                    conf = getattr(defhandler, "_cp_config", {})
                    object_trail.insert(
                        i + 1, ["default", defhandler, conf, segleft])
                    request.config = set_conf()
                    # See https://bitbucket.org/cherrypy/cherrypy/issue/613
                    request.is_index = path.endswith("/")
                    return defhandler, fullpath[fullpath_len - segleft:-1]

            # Uncomment the next line to restrict positional params to
            # "default".
            # if i < num_candidates - 2: continue

            # Try the current leaf.
            if getattr(candidate, 'exposed', False):
                request.config = set_conf()
                if i == num_candidates:
                    # We found the extra ".index". Mark request so tools
                    # can redirect if path_info has no trailing slash.
                    request.is_index = True
                else:
                    # We're not at an 'index' handler. Mark request so tools
                    # can redirect if path_info has NO trailing slash.
                    # Note that this also includes handlers which take
                    # positional parameters (virtual paths).
                    request.is_index = False
                return candidate, fullpath[fullpath_len - segleft:-1]

        # We didn't find anything
        request.config = set_conf()
        return None, []
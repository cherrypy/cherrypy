import sys

import cherrypy
from cherrypy.lib._cpcompat import ntob


def get_xmlrpclib():
    try:
        import xmlrpc.client as x
    except ImportError:
        import xmlrpclib as x
    return x


def process_body():
    """Return (params, method) from request body."""
    try:
        return get_xmlrpclib().loads(cherrypy.request.body.read())
    except Exception:
        return ('ERROR PARAMS', ), 'ERRORMETHOD'


def patched_path(path):
    """Return 'path', doctored for RPC."""
    if not path.endswith('/'):
        path += '/'
    if path.startswith('/RPC2/'):
        # strip the first /rpc2
        path = path[5:]
    return path


def _set_response(body):
    # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
    # "Unless there's a lower-level error, always return 200 OK."
    # Since Python's xmlrpclib interprets a non-200 response
    # as a "Protocol Error", we'll just return 200 every time.
    response = cherrypy.response
    response.status = '200 OK'
    response.body = ntob(body, 'utf-8')
    response.headers['Content-Type'] = 'text/xml'
    response.headers['Content-Length'] = len(body)


def respond(body, encoding='utf-8', allow_none=0):
    xmlrpclib = get_xmlrpclib()
    if not isinstance(body, xmlrpclib.Fault):
        body = (body,)
    _set_response(xmlrpclib.dumps(body, methodresponse=1,
                                  encoding=encoding,
                                  allow_none=allow_none))


def on_error(*args, **kwargs):
    body = str(sys.exc_info()[1])
    xmlrpclib = get_xmlrpclib()
    _set_response(xmlrpclib.dumps(xmlrpclib.Fault(1, body)))


class XMLRPCController(object):

    """A Controller (page handler collection) for XML-RPC.

    To use it, have your controllers subclass this base class (it will
    turn on the tool for you).

    You can also supply the following optional config entries::

        tools.xmlrpc.encoding: 'utf-8'
        tools.xmlrpc.allow_none: 0

    XML-RPC is a rather discontinuous layer over HTTP; dispatching to the
    appropriate handler must first be performed according to the URL, and
    then a second dispatch step must take place according to the RPC method
    specified in the request body. It also allows a superfluous "/RPC2"
    prefix in the URL, supplies its own handler args in the body, and
    requires a 200 OK "Fault" response instead of 404 when the desired
    method is not found.

    Therefore, XML-RPC cannot be implemented for CherryPy via a Tool alone.
    This Controller acts as the dispatch target for the first half (based
    on the URL); it then reads the RPC method from the request body and
    does its own second dispatch step based on that method. It also reads
    body params, and returns a Fault on error.

    The XMLRPCDispatcher strips any /RPC2 prefix; if you aren't using /RPC2
    in your URL's, you can safely skip turning on the XMLRPCDispatcher.
    Otherwise, you need to use declare it in config::

        request.dispatch: cherrypy.dispatch.XMLRPCDispatcher()
    """

    # Note we're hard-coding this into the 'tools' namespace. We could do
    # a huge amount of work to make it relocatable, but the only reason why
    # would be if someone actually disabled the default_toolbox. Meh.
    _cp_config = {'tools.xmlrpc.on': True}

    def default(self, *vpath, **params):
        rpcparams, rpcmethod = process_body()

        subhandler = self
        for attr in str(rpcmethod).split('.'):
            subhandler = getattr(subhandler, attr, None)

        if subhandler and getattr(subhandler, "exposed", False):
            body = subhandler(*(vpath + rpcparams), **params)

        else:
            # https://bitbucket.org/cherrypy/cherrypy/issue/533
            # if a method is not found, an xmlrpclib.Fault should be returned
            # raising an exception here will do that; see
            # cherrypy.lib.xmlrpcutil.on_error
            raise Exception('method "%s" is not supported' % attr)

        conf = cherrypy.serving.request.toolmaps['tools'].get("xmlrpc", {})
        respond(body,
                conf.get('encoding', 'utf-8'),
                conf.get('allow_none', 0))
        return cherrypy.serving.response.body
    default.exposed = True

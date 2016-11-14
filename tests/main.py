import cherrypy

from controllers.userController import UserController


def CORS():
    """Allow web apps not on the same server to use our API
    """
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*" 
    cherrypy.response.headers["Access-Control-Allow-Headers"] = (
        "content-type, Authorization, X-Requested-With"
    )
    
    cherrypy.response.headers["Access-Control-Allow-Methods"] = (
        'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    )
    
if __name__ == '__main__':
    """Starts a cherryPy server and listens for requests
    """
    
    userController = UserController()
    
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
        'tools.CORS.on': True,
    })

    # API method dispatcher
    # we are defining this here because we want to map the HTTP verb to
    # the same method on the controller class. This _api_user_conf will
    # be used on each route we want to be RESTful
    _api_conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }

    # _api_user_conf better explained
    # The default dispatcher in CherryPy stores the HTTP method name at
    # :attr:`cherrypy.request.method<cherrypy._cprequest.Request.method>`.

    # Because HTTP defines these invocation methods, the most direct
    # way to implement REST using CherryPy is to utilize the
    # :class:`MethodDispatcher<cherrypy._cpdispatch.MethodDispatcher>`
    # instead of the default dispatcher. To enable
    # the method dispatcher, add the
    # following to your configuration for the root URI ("/")::

    #     '/': {
    #         'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
    #     }

    # Now, the REST methods will map directly to the same method names on
    # your resources. That is, a GET method on a CherryPy class implements
    # the HTTP GET on the resource represented by that class.

    # http://cherrypy.readthedocs.org/en/3.2.6/_sources/progguide/REST.txt

    cherrypy.tree.mount(userController, '/api/users', _api_conf)
    

    cherrypy.engine.start()
    cherrypy.engine.block()
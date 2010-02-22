********************************
How to use cookies with CherryPy
********************************

CherryPy uses the :mod:`Cookie` module from python and in particular the
:class:`Cookie.SimpleCookie` object type to handle cookies.

* To send a cookie to a browser, set ``cherrypy.response.cookie[key] = value``.
* To retrieve a cookie sent by a browser, use ``cherrypy.request.cookie[key]``.
* To delete a cookie (on the client side), you must *send* the cookie with its
  expiration time set to 0::


    cherrypy.response.cookie[key] = value
    cherrypy.response.cookie[key]['expires'] = 0


It's important to understand that the request cookies are **not** automatically
copied to the response cookies. Clients will send the same cookies on every
request, and therefore ``cherrypy.request.cookie`` should be populated each
time. But the server doesn't need to send the same cookies with every response;
therefore, **``cherrypy.response.cookie`` will usually be empty**. When you wish
to "delete" (expire) a cookie, therefore, you must set
``cherrypy.response.cookie[key] = value`` first, and then set its ``expires``
attribute to 0.

Extended example::

    import cherrypy

    class Root:
        def setCookie(self):
            cookie = cherrypy.response.cookie
            cookie['cookieName'] = 'cookieValue'
            cookie['cookieName']['path'] = '/'
            cookie['cookieName']['max-age'] = 3600
            cookie['cookieName']['version'] = 1
            return "<html><body>Hello, I just sent you a cookie</body></html>"
        setCookie.exposed = True

        def readCookie(self):
            cookie = cherrypy.request.cookie
            res = """<html><body>Hi, you sent me %s cookies.<br />
                    Here is a list of cookie names/values:<br />""" % len(cookie)
            for name in cookie.keys():
                res += "name: %s, value: %s<br>" % (name, cookie[name].value)
            return res + "</body></html>"
        readCookie.exposed = True

    cherrypy.quickstart(Root())


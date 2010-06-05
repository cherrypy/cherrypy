*********************
Errors and Exceptions
*********************


CherryPy provides (and uses) exceptions for declaring that the HTTP response
should be a status other than the default "200 OK". You can ``raise`` them like
normal Python exceptions. You can also call them and they will raise themselves;
this means you can set an :class:`HTTPError` or :class:`HTTPRedirect` as the
``request.handler``.

HTTPError
=========

This exception can be used to automatically send a response using a http status
code, with an appropriate error page. :class:`HTTPError` takes an optional
``status`` argument (which must be between 400 and 599); it defaults to 500
("Internal Server Error"). It also takes an optional ``message`` argument,
which will be returned in the response body. See
`this page <http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4 RFC 2616>`_
for a complete list of available error codes and when to use them.

Examples::

    raise cherrypy.HTTPError(403)
    raise cherrypy.HTTPError("403 Forbidden", "You are not allowed to access this resource.")


NotFound
--------

This exception is raised when CherryPy is unable to map a requested path to an
internal method. It's equivalent to raising
:class:`HTTPError("404 Not Found") <cherrypy.HTTPError>`.

HTTPRedirect
============

This exception will force a HTTP redirect to the URL or URL's you give it.

There are multiple types of redirect, from which you can select via the
``status`` argument. If you do not provide a ``status`` arg, it defaults to 303
(or 302 if responding with HTTP/1.0).

Examples::

    raise cherrypy.HTTPRedirect("")
    raise cherrypy.HTTPRedirect("/abs/path", 307)
    raise cherrypy.HTTPRedirect(["path1", "path2?a=1&b=2"], 301)


Redirecting POST
----------------

When you GET a resource and are redirected by the server to another Location,
there's generally no problem since GET is both a "safe method" (there should
be no side-effects) and an "idempotent method" (multiple calls are no different
than a single call). POST, however, is neither safe nor idempotent--if you
charge a credit card, you don't want to be charged twice by a redirect!

For this reason, *none* of the 3xx responses permit a user-agent (browser) to
resubmit a POST on redirection without first confirming the action with the user:



=====    =================================    ===========
300      Multiple Choices                     Confirm with the user
301      Moved Permanently                    Confirm with the user
302      Found (Object moved temporarily)     Confirm with the user
303      See Other                            GET the new URI--no confirmation
304      Not modified                         (for conditional GET only--POST should not raise this error)
305      Use Proxy                            Confirm with the user
307      Temporary Redirect                   Confirm with the user
=====    =================================    ===========

However, browsers have historically implemented these restrictions poorly;
in particular, many browsers do not force the user to confirm 301, 302 or 307
when redirecting POST. For this reason, CherryPy defaults to
:class:`HTTPRedirect(303) <cherrypy.HTTPRedirect>`, which most user-agents
appear to have implemented correctly. Therefore, if you raise
:class:`HTTPRedirect(new_uri) <cherrypy.HTTPRedirect>` for a POST request,
the user-agent will most likely attempt to GET the new URI (without asking for
confirmation from the user). We realize this is confusing for developers;
but it's the safest thing we could do. You are of course free to raise
:class:`HTTPRedirect(uri, status=302) <cherrypy.HTTPRedirect>` or any other
3xx status if you know what you're doing, but given the environment, we
couldn't let any of those be the default.

InternalRedirect
----------------

This exception will redirect processing to another path within the site
(without informing the client). Provide the new path as an argument when
raising the exception. Provide any params in the querystring for the new URL.

Custom Error Handling
=====================

.. image:: cperrors.gif

Anticipated HTTP responses
--------------------------

The 'error_page' config namespace can be used to provide custom HTML output for
expected responses (like 404 Not Found). Supply a filename from which the output
will be read. The contents will be interpolated with the values %(status)s,
%(message)s, %(traceback)s, and %(version)s using plain old Python
`string formatting <http://www.python.org/doc/2.6.4/library/stdtypes.html#string-formatting-operations>`_.

::

    _cp_config = {'error_page.404': os.path.join(localDir, "static/index.html")}


Beginning in version 3.1, you may also provide a function or other callable as
an error_page entry. It will be passed the same status, message, traceback and
version arguments that are interpolated into templates::

    def error_page_402(status, message, traceback, version):
        return "Error %s - Well, I'm very sorry but you haven't paid!" % status
    cherrypy.config.update({'error_page.402': error_page_402})

Also in 3.1, in addition to the numbered error codes, you may also supply
"error_page.default" to handle all codes which do not have their own error_page entry.



Unanticipated errors
--------------------

CherryPy also has a generic error handling mechanism: whenever an unanticipated
error occurs in your code, it will call :func:`Request.error_response` to set
the response status, headers, and body. By default, this is the same output as
:class:`HTTPError(500) <cherrypy.HTTPError>`. If you want to provide some other
behavior, you generally replace "request.error_response".

Here is some sample code that shows how to display a custom error message and
send an e-mail containing the error::

    from cherrypy import _cperror

    def handle_error():
        cherrypy.response.status = 500
        cherrypy.response.body = ["<html><body>Sorry, an error occured</body></html>"]
        sendMail('error@domain.com', 'Error in your web app', _cperror.format_exc())

    class Root:
        _cp_config = {'request.error_response': handle_error}


Note that you have to explicitly set :attr:`response.body <cherrypy._cprequest.Response.body>`
and not simply return an error message as a result.


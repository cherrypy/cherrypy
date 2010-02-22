*************************
Serving the favorite icon
*************************

By default, CherryPy 3 adds a "favicon_ico" handler method to any root object
which is mounted at "/". This is a staticfile handler, which grabs the
favicon.ico shipped in the CherryPy distribution.

To configure CherryPy to look in another file location, you can, in your server
configuration, do the following::

    [/favicon.ico]
    tools.staticfile.on = True
    tools.staticfile.filename = "/path/to/favicon.ico"

If you want a favicon, but don't want CherryPy to serve it, you can point to an
HTTP URL via a link element in the HTML head. See http://www.w3.org/2005/10/howto-favicon
and http://en.wikipedia.org/wiki/Favicon for instructions.

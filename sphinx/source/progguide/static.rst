Serving Static Content
**********************

Static content is now handled by ``tools.staticfile`` and ``tools.staticdir`` that can easily be enabled and configured in your config file. For instance, if you wanted to serve ``/style.css`` from ``/home/site/style.css`` and ``/static/*`` from ``/home/site/static/*``, you can use the following configuration:

::

    [/]
    tools.staticdir.root = "/home/site"
    
    [/style.css]
    tools.staticfile.on = True
    tools.staticfile.filename = "/home/site/style.css"
    
    [/static]
    tools.staticdir.on = True
    tools.staticdir.dir = "static"


Parameters
==========

 * on: True or False (default). Enable or disable the filter.
 * match: a `regular expression <http://docs.python.org/lib/module-re.html>`_ of files to match.
 * filename: path to the target file.
 * dir: path to the target directory.
 * root: absolute path to a "root"; joined with .dir or .filename if they are relative paths.

Usage
=====

Serving files through the ``staticfile`` tool
---------------------------------------------

Directory structure
::

    cpapp \
       __init__.py
       data \
         scripts \
           dummy.js
         css \
           style.css


Here is our `cpapp/__init__.py`:
::

    #!python
    import os.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    import cherrypy
    
    
    class Root:
        @cherrypy.expose
        def index(self):
            return """<html>
    <head>
            <title>CherryPy static example</title>
            <link rel="stylesheet" type="text/css" href="css/style.css" type="text/css"></link>
            <script type="application/javascript" src="js/some.js"></script>
    </head>
    <html>
    <body>
    <p>Static example</p>
    </body>
    </html>"""


...and a `prod.conf` configuration file:

::

    [global]
    environment: 'production'
    log.error_file: 'site.log'
    log.screen: True
    
    tree.cpapp: cherrypy.Application(cpapp.Root())
    
    [/css/style.css]
    tools.staticfile.on: True
    tools.staticfile.filename: cpapp.current_dir + '/data/css/style.css'
    
    [/js/some.js]
    tools.staticfile.on: True
    tools.staticfile.filename: cpapp.current_dir + '/data/scripts/dummy.js'


Note how we use the absolute path to point at the static files. Note also that when using the ``staticfile`` tool, the logical URI path and the physical file do not need to be the same. Parts of their components can differ as in the case of the Javascript resource.

You can run the above with:

::

    $ cherryd -i cpapp -c prod.conf


Serving files through the ``staticdir`` tool
--------------------------------------------

Keeping the same directory structure as above, we could have written our config file as follows:

::

    [/]
    tools.staticdir.root: cpapp.current_dir + 'data'
    
    [/css]
    tools.staticdir.on: True
    tools.staticdir.dir: 'css'
    
    [/js]
    tools.staticdir.on: True
    tools.staticdir.dir: 'scripts'


However in this case the ``GET /js/some.js`` request will fail with a ``404 Not Found`` response because when using the ``staticdir`` tool the last segment of the URI must match exactly the path of the physical file underneath the directory defined by ``tools.staticdir.dir``.

In our example we must either rename the physical file or change the HTML code accordingly.

staticdir.index
^^^^^^^^^^^^^^^

If `tools.staticdir.index` is provided, it should be the (relative) name of a file to serve for directory requests. For example, if the `staticdir.dir` argument is '/home/me', the Request-URI is 'myapp', and the `.index` arg is 'index.html', the file '/home/me/myapp/index.html' will be served.

Specify the content-type of static resource
-------------------------------------------

Both the ``staticfile`` and ``staticdir`` tool allow you to specify the mime type of resources by their extension.
Although internally CherryPy will most of the time guess the correct mime type (using the Python mimetypes module),
there may be cases when you need to provide the content type values.  You can do this via configuration arguments
``tools.staticdir.content_types`` and ``tools.staticfile.content_types``, as in the following example.

::

    #!python
    import os.path
    import cherrypy
    
    class Root:
        @cherrypy.expose
        def index(self):
            return """<html>
                    <head>
                        <title>CherryPy static tutorial</title>
                    </head>
                    <html>
                    <body>
                    <a href="feed/notes.rss">RSS 2.0</a>
                    <br />
                    <a href="feed/notes.atom">Atom 1.0</a>
                    </body>
                    </html>"""
    
    if __name__ == '__main__':
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Set up site-wide config first so we get a log if errors occur.
        cherrypy.config.update({'environment': 'production',
                                'log.error_file': 'site.log',
                                'log.screen': True})
    
        conf = {'/feed': {'tools.staticdir.on': True,
                          'tools.staticdir.dir': os.path.join(current_dir, 'feeds'),
                          'tools.staticdir.content_types': {'rss': 'application/xml',
                                                            'atom': 'application/atom+xml'}}}
        cherrypy.quickstart(Root(), '/', config=conf)


The value of ``tools.staticdir.content_types`` and ``tools.staticfile.content_types``
is a dictionary whose keys are filename extensions, and values are the corresponding
media-type strings (for the ``Content-Type`` header). Note that the key must NOT include any leading '.'.

Serve static content from a page handler bypassing the static tools
-------------------------------------------------------------------

It may happen that you would need the static tools power but from a page handler itself so that you can add more processing. You can do so by calling the ``serve_file`` function.

::

    #!python
    import os.path
    import cherrypy
    from cherrypy.lib.static import serve_file
    
    class Root:
        @cherrypy.expose
        def feed(self, name):
            accepts = cherrypy.request.headers.elements('Accept')
    
            for accept in accepts:
                if accept.value == 'application/atom+xml':
                    return serve_file(os.path.join(current_dir, 'feeds', '%s.atom' % name),
                                      content_type='application/atom+xml')
    
            return serve_file(os.path.join(current_dir, 'feeds', '%s.rss' % name),
                                  content_type='application/xml')
    
    if __name__ == '__main__':
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Set up site-wide config first so we get a log if errors occur.
        cherrypy.config.update({'environment': 'production',
                                'log.error_file': 'site.log',
                                'log.screen': True})
        cherrypy.quickstart(Root(), '/')


In this example we rely on the Accept header of the HTTP request to tell us which content type is supported by the client. If it can process the Atom content type then we serve the Atom resource, otherwise we serve the RSS one.

In any case by using the serve_file function we benefit from the CherryPy internal processing of the request in regards of HTTP headers such as If-Modified-Since. In fact the static tools use the serve_file function.

Troubleshooting staticdir
=========================

When using staticdir, "root" and "dir" are concatenated using ``os.path.join``. So if you're having problems, try ``os.path.join(root, dir)`` in an interactive interpreter and make sure you at least get a valid, absolute path. Remember, you don't have to use "root" at all if you don't want to; just make "dir" an absolute path. If root + dir is not absolute, an error will be raised asking you to make it absolute. CherryPy doesn't make any assumptions about where your project files are, nor can it trust the current working directory, since that may change or not be under your control depending on your deployment environment.

Once root and dir are joined, the final file is found by ``os.path.join``'ing a ''branch''. The branch is pulled from the current request's URL like this:

::

    http://www2.mydomain.org/vhost /path/to/my/approot /path/to/section / path/to/actual/file.jpg
    |                            | |                 | |              |   |                     |
    +----------- base -----------+ +-- script_name --+ +-- section ---+   +------ branch -------+


The 'base' is the value of the 'Host' request header (unless changed by tools.proxy). The 'script_name' is where you mounted your app root. The 'section' is what part of the remaining URL to ''ignore''; that is, none of its path atoms need to map to filesystem folders. It should exactly match the section header in your application config file where you defined 'tools.staticdir.dir'. In this example, your application config file should have:

::

    [/]
    tools.staticdir.root = '/home/me/testproj'
    
    [/path/to/section]
    tools.staticdir.dir = 'images/jpegs'


Note that the section must start with a slash, but not end with one. And in order for ``os.path.join`` to work on root + dir, our 'images' value neither starts nor ends with a slash. Also note that the values of "root" and "dir" need not have ''anything'' to do with any part of the URL; they are OS path components only. Only the section header needs to match a portion of the URL.

Now we're finally ready to slice off the part of the URL that is our ''branch'' and add it to root + dir. So our final example will try to open the following file:

::

                             root        +      dir      +          branch
    >>> os.path.join('/home/me/testproj', 'images/jpegs', 'path/to/actual/file.jpg')
    '/home/me/testproj/images/jpegs/path/to/actual/file.jpg'


Forming URLs
============

Creating links to static content is the inverse of the above. If you want to serve the file:

::

    /home/me/testproj/images/jpegs/path/to/actual/file.jpg


...you have a choice about where to split up the full path into root, dir, and branch. Remember, the 'root' value only exists to save typing; you could use absolute paths for all "dir" values. So if you're serving multiple static directories, find the common root to them all and use that for your "root" value. For example, instead of this:

::

    [/images]
    tools.staticdir.dir = "/usr/home/me/app/static/images"
    
    [/styles]
    tools.staticdir.dir = "/usr/home/me/app/static/css"
    
    [/scripts]
    tools.staticdir.dir = "/usr/home/me/app/static/js"


...write:

::

    [/]
    tools.staticdir.root = "/usr/home/me/app/static"
    
    [/images]
    tools.staticdir.dir = "images"
    
    [/styles]
    tools.staticdir.dir = "css"
    
    [/scripts]
    tools.staticdir.dir = "js"


Regardless of where you split "root" from "dir", the remainder of the OS path will be the "branch". Assuming the config above, our example branch would then be "jpegs/path/to/actual/file.jpg". Add the branch to the section name where you defined "dir", and use that for your URL. Even better, pass it to ``cherrypy.url()`` (which prepends base and script_name) and emit ''that''.

::

                      section     +                branch
    >>> cherrypy.url('/images' + '/' + 'jpegs/path/to/actual/file.jpg')
    http://www2.mydomain.org/vhost/path/to/my/approot/images/jpegs/path/to/actual/file.jpg


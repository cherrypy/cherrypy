*****
Tools
*****

Tools are a great way to package up behavior that happens outside your page
handlers. For example, you can add static directory serving with the builtin
``staticdir`` tool with just a few lines in your config file::

    [/docroot]
    tools.staticdir.on: True
    tools.staticdir.root: "/path/to/app"
    tools.staticdir.dir: 'static'

This turns on the ``staticdir`` tool for all *URLs* that start with "/docroot".
You can also enable and configure tools *per controller* or *per handler*
using [wiki:ConfigAPI#a_cp_config:attachingconfigtohandlers _cp_config]::

    class docroot(object):

        _cp_config = {'tools.staticdir.on': True,
                      'tools.staticdir.root: "/path/to/app",
                      'tools.staticdir.dir': 'static'}

But we can do even better by using the **builtin decorator support** that all
Tools have::

    class docroot(object):

        @tools.staticdir(root="/path/to/app", dir='static')
        def page(self):
           # ...

...and in this case, we can do even **better** because tools.staticdir is a
'HandlerTool', and therefore can be used directly as a page handler::

    class docroot(object):

        static = tools.staticdir.handler(
                     section='static', root="/path/to/app", dir='static')

Finally, you can use (most) Tools directly, by calling the function they wrap.
They expose this via the 'callable' attribute::

    def page(self):
        tools.response_headers.callable([('Content-Language', 'fr')])
        return "Bonjour, le Monde!"
    page.exposed = True

Because the underlying function is wrapped in a tool, you need to call
``help(tools.whatevertool.callable)`` if you want the docstring for it.
Using ``help(tools.whatevertool)`` will give you help on how to use it
as a Tool (for example, as a decorator).

Tools also are also **inspectable** automatically. They expose their own
arguments as attributes::

    >>> dir(cherrypy.tools.session_auth)
    [..., 'anonymous', 'callable', 'check_username_and_password',
    'do_check', 'do_login', 'do_logout', 'handler', 'login_screen',
    'on_check', 'on_login', 'on_logout', 'run', 'session_key']

This makes IDE calltips especially useful, even when writing config files!

